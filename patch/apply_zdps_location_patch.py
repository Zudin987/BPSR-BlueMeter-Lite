#!/usr/bin/env python3
"""Apply the safe encounter-location fix during GitHub Actions.

The previous version manually guessed the nested SocialNtf protobuf layout and
could mistake a player UID for a map ID. This version removes that guesswork.
It uses the already-generated SyncContainerData.SceneData parser, snapshots the
scene when combat begins, and compiles ZDPS's scene-name table into the app.
"""

from __future__ import annotations

import json
import sys
import urllib.request
from pathlib import Path

SCENE_TABLE_URL = (
    "https://raw.githubusercontent.com/Blue-Protocol-Source/"
    "BPSR-ZDPS/master/BPSR-ZDPS/Data/SceneTable.json"
)


def fail(message: str) -> None:
    raise SystemExit(f"ZDPS location patch failed: {message}")


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        fail(f"expected one {label}, found {count}")
    return text.replace(old, new, 1)


def dart_string(value: str) -> str:
    # JSON strings are valid Dart double-quoted strings after escaping Dart's
    # interpolation marker.
    return json.dumps(value, ensure_ascii=False).replace("$", r"\$")


def load_fallback_catalog(source: Path) -> dict[int, str]:
    text = source.read_text(encoding="utf-8")
    # Keep a small fallback without adding another parser dependency.
    names: dict[int, str] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("//") or ":" not in line:
            continue
        left, right = line.split(":", 1)
        try:
            map_id = int(left.strip())
        except ValueError:
            continue
        value = right.strip().rstrip(",")
        if len(value) < 2 or value[0] not in "'\"" or value[-1] != value[0]:
            continue
        # All fallback labels are simple literals with only one apostrophe in
        # the double-quoted Skimmer entry.
        names[map_id] = value[1:-1]
    return names


def fetch_zdps_catalog(fallback_source: Path) -> dict[int, str]:
    fallback = load_fallback_catalog(fallback_source)
    try:
        request = urllib.request.Request(
            SCENE_TABLE_URL,
            headers={"User-Agent": "BPSR-BlueMeter-Lite-GitHub-Actions"},
        )
        with urllib.request.urlopen(request, timeout=30) as response:
            payload = json.loads(response.read().decode("utf-8"))

        names: dict[int, str] = {}
        for key, value in payload.items():
            if not isinstance(value, dict):
                continue
            try:
                map_id = int(value.get("Id", key))
            except (TypeError, ValueError):
                continue
            name = str(value.get("Name", "")).strip()
            if map_id > 0 and name:
                names[map_id] = name

        if names:
            print(f"Loaded {len(names)} scene names from ZDPS SceneTable.json.")
            return names
    except Exception as exc:  # Network failure must not break APK builds.
        print(f"Warning: could not download ZDPS scene table: {exc}")

    print(f"Using {len(fallback)} bundled fallback scene names.")
    return fallback


def write_catalog(destination: Path, source: Path) -> None:
    names = fetch_zdps_catalog(source)
    lines = [
        "/// Generated during GitHub Actions from ZDPS SceneTable.json.",
        "class LiteSceneCatalog {",
        "  const LiteSceneCatalog._();",
        "",
        "  static const Map<int, String> names = <int, String>{",
    ]
    for map_id, name in sorted(names.items()):
        lines.append(f"    {map_id}: {dart_string(name)},")
    lines.extend(
        [
            "  };",
            "",
            "  static String? nameFor(int mapId) => names[mapId];",
            "  static bool contains(int mapId) => names.containsKey(mapId);",
            "}",
            "",
        ]
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text("\n".join(lines), encoding="utf-8")


def patch_storage(path: Path) -> None:
    text = path.read_text(encoding="utf-8")

    text = replace_once(
        text,
        "import '../services/encounter_history_service.dart';\n",
        "import '../services/encounter_history_service.dart';\n"
        "import '../data/lite_scene_catalog.dart';\n",
        "scene catalog import",
    )

    text = replace_once(
        text,
        """bool _liteSeenFullPlayerContainer = false;
DateTime? _liteLastMapLoadSignalAt;
""",
        """bool _liteSeenFullPlayerContainer = false;
DateTime? _liteLastMapLoadSignalAt;

// Freeze the decoded SyncContainer scene when the encounter starts. This is
// intentionally separate from _mapId because _mapId can change before the old
// encounter is written to history.
int _liteEncounterMapId = 0;
int _liteEncounterChannelId = 0;
int _liteEncounterLineId = 0;

bool _liteIsDecodedSceneId(int? value) {
  if (value == null || value <= 0) return false;

  // Accept only IDs present in the scene table compiled from ZDPS. This
  // blocks player UIDs and other unrelated protobuf integers from history.
  return value != _currentPlayerUuid.toInt() &&
      LiteSceneCatalog.contains(value);
}

void _liteCaptureEncounterSceneIfNeeded() {
  if (_liteEncounterMapId > 0 || !_liteIsDecodedSceneId(_mapId)) {
    return;
  }

  _liteEncounterMapId = _mapId;
  _liteEncounterChannelId = _channelId;
  _liteEncounterLineId = _lineId;
}
""",
        "encounter scene snapshot fields",
    )

    text = replace_once(
        text,
        """    'mapId': _mapId,
    'channelId': _channelId,
    'lineId': _lineId,
""",
        """    'mapId': _liteEncounterMapId > 0 ? _liteEncounterMapId : _mapId,
    'channelId': _liteEncounterMapId > 0
        ? _liteEncounterChannelId
        : _channelId,
    'lineId': _liteEncounterMapId > 0
        ? _liteEncounterLineId
        : _lineId,
""",
        "history scene snapshot",
    )

    text = replace_once(
        text,
        """void _liteClearEncounterData() {
  _fullDpsDatas.clear();
  _liteSubProfessionNames.clear();
""",
        """void _liteClearEncounterData() {
  _fullDpsDatas.clear();
  _liteSubProfessionNames.clear();
  _liteEncounterMapId = 0;
  _liteEncounterChannelId = 0;
  _liteEncounterLineId = 0;
""",
        "encounter scene cleanup",
    )

    text = replace_once(
        text,
        """void _onAction() {
  final now = DateTime.now();
""",
        """void _onAction() {
  final now = DateTime.now();
  _liteCaptureEncounterSceneIfNeeded();
""",
        "combat-start scene capture",
    )

    text = replace_once(
        text,
        """void reset({bool resetTimer = true}) {
  _fullDpsDatas.clear();
  _liteSubProfessionNames.clear();

  if (resetTimer) {
""",
        """void reset({bool resetTimer = true}) {
  _fullDpsDatas.clear();
  _liteSubProfessionNames.clear();
  _liteEncounterMapId = 0;
  _liteEncounterChannelId = 0;
  _liteEncounterLineId = 0;

  if (resetTimer) {
""",
        "manual reset scene cleanup",
    )

    text = replace_once(
        text,
        "  final receivedMapId = mapId != null && mapId > 0;\n",
        "  final receivedMapId = _liteIsDecodedSceneId(mapId);\n",
        "decoded scene validation",
    )

    text = replace_once(
        text,
        """  if (receivedMapId) {
    _mapId = mapId!;
  }
""",
        """  if (receivedMapId) {
    _mapId = mapId!;

    // SceneData can arrive immediately before or just after the first combat
    // packet. Capture it once and never let a later map transition rename the
    // encounter that is already in progress.
    if (_liteHasEncounterData) {
      _liteCaptureEncounterSceneIfNeeded();
    }
  }
""",
        "decoded scene assignment",
    )

    path.write_text(text, encoding="utf-8")


def main() -> None:
    if len(sys.argv) != 2:
        fail("usage: apply_zdps_location_patch.py <upstream-directory>")

    upstream = Path(sys.argv[1]).resolve()
    patch_dir = Path(__file__).resolve().parent
    storage = upstream / "lib/core/state/data_storage.dart"
    catalog_destination = upstream / "lib/core/data/lite_scene_catalog.dart"
    history_destination = upstream / "lib/views/encounter_history_view.dart"
    catalog_source = patch_dir / "lite_scene_catalog.dart"
    history_source = patch_dir / "encounter_history_view.dart"

    for required in (storage, catalog_source, history_source):
        if not required.exists():
            fail(f"missing required file: {required}")

    write_catalog(catalog_destination, catalog_source)
    patch_storage(storage)
    history_destination.parent.mkdir(parents=True, exist_ok=True)
    history_destination.write_text(
        history_source.read_text(encoding="utf-8"),
        encoding="utf-8",
    )

    print("Safe SyncContainer encounter-location patch applied.")
    print("Manual SocialNtf protobuf guessing is disabled.")


if __name__ == "__main__":
    main()
