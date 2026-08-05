#!/usr/bin/env python3
"""Apply exact EnterScene encounter-location capture during GitHub Actions.

ZDPS reads the map from WorldNtf.EnterScene -> EnterSceneInfo.SceneAttrs ->
AttrSceneBasicId. BlueMeter Lite mirrors that typed packet path instead of
relying only on SyncContainerData or guessing fields from SocialNtf packets.
"""

from __future__ import annotations

import json
import shutil
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
    return json.dumps(value, ensure_ascii=False).replace("$", r"\$")


def load_fallback_catalog(source: Path) -> dict[int, str]:
    text = source.read_text(encoding="utf-8")
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
    except Exception as exc:
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
        """bool _liteSeenFullPlayerContainer = false;
DateTime? _liteLastMapLoadSignalAt;
""",
        """bool _liteSeenFullPlayerContainer = false;
DateTime? _liteLastMapLoadSignalAt;

// Freeze the exact decoded scene when combat starts. _mapId may change before
// the encounter that just ended is written to history.
int _liteEncounterMapId = 0;
int _liteEncounterChannelId = 0;
int _liteEncounterLineId = 0;

bool _liteIsDecodedSceneId(int? value) {
  if (value == null || value <= 0) return false;

  // Callers now provide typed map fields only:
  // - SyncContainerData.SceneData.mapId
  // - EnterScene.SceneAttrs AttrSceneBasicId (341)
  // Do not require the naming catalog here; a newly added game map may not be
  // listed yet, but its exact typed scene ID is still valid.
  return value != _currentPlayerUuid.toInt();
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

    // Capture a typed scene that arrives immediately after combat begins, but
    // never overwrite a scene already frozen for this encounter.
    if (_liteHasEncounterData) {
      _liteCaptureEncounterSceneIfNeeded();
    }
  }
""",
        "decoded scene assignment",
    )

    path.write_text(text, encoding="utf-8")


def patch_registry(path: Path) -> None:
    text = path.read_text(encoding="utf-8")

    text = replace_once(
        text,
        "import 'processors/dungeon_snapshot_processor.dart';\n",
        "import 'processors/dungeon_snapshot_processor.dart';\n"
        "import 'processors/enter_scene_processor.dart';\n",
        "EnterScene processor import",
    )

    text = replace_once(
        text,
        "  static const int _methodSyncDungeonData = 0x00000017;\n",
        "  static const int _methodSyncDungeonData = 0x00000017;\n"
        "  static const int _methodEnterScene = 0x00000003;\n",
        "EnterScene method ID",
    )

    text = replace_once(
        text,
        "    _processors[_methodSyncDungeonData] = DungeonSnapshotProcessor(storage);\n",
        "    _processors[_methodSyncDungeonData] = DungeonSnapshotProcessor(storage);\n"
        "    _processors[_methodEnterScene] = EnterSceneProcessor(storage);\n",
        "EnterScene registration",
    )

    path.write_text(text, encoding="utf-8")


def main() -> None:
    if len(sys.argv) != 2:
        fail("usage: apply_zdps_location_patch.py <upstream-directory>")

    upstream = Path(sys.argv[1]).resolve()
    patch_dir = Path(__file__).resolve().parent

    storage = upstream / "lib/core/state/data_storage.dart"
    registry = upstream / "lib/core/analyze/message_handler_registry.dart"
    processor_destination = (
        upstream / "lib/core/analyze/processors/enter_scene_processor.dart"
    )
    catalog_destination = upstream / "lib/core/data/lite_scene_catalog.dart"
    history_destination = upstream / "lib/views/encounter_history_view.dart"

    processor_source = patch_dir / "enter_scene_processor.dart"
    catalog_source = patch_dir / "lite_scene_catalog.dart"
    history_source = patch_dir / "encounter_history_view.dart"

    for required in (
        storage,
        registry,
        processor_source,
        catalog_source,
        history_source,
    ):
        if not required.exists():
            fail(f"missing required file: {required}")

    write_catalog(catalog_destination, catalog_source)
    patch_storage(storage)
    patch_registry(registry)

    processor_destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(processor_source, processor_destination)

    history_destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(history_source, history_destination)

    print("Exact WorldNtf.EnterScene encounter-location patch applied.")
    print("Scene map ID source: SceneAttrs AttrSceneBasicId (341).")


if __name__ == "__main__":
    main()
