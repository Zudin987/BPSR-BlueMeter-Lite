#!/usr/bin/env python3
"""
Apply the BlueMeter Lite v1.4.0 performance update to an existing repository.

Run this once from the repository root:
    python patch/apply_performance_update.py .

The normal GitHub Actions build can then be used as before.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path


def fail(message: str) -> None:
    raise SystemExit(f"Performance update failed: {message}")


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if old not in text:
        fail(f"could not find {label}")
    return text.replace(old, new, 1)


def main() -> None:
    if len(sys.argv) != 2:
        fail("usage: apply_performance_update.py <repository-root>")

    repo = Path(sys.argv[1]).resolve()
    patch_script = repo / "patch/apply_lite_patch.py"
    overlay = repo / "patch/overlay_widget_lite.dart"

    if not patch_script.exists():
        fail(f"missing {patch_script}")
    if not overlay.exists():
        fail(f"missing {overlay}")

    patch_text = patch_script.read_text(encoding="utf-8")
    overlay_text = overlay.read_text(encoding="utf-8")

    # Version bump.
    patch_text, count = re.subn(
        r'lite_version_name = "[^"]+"',
        'lite_version_name = "1.4.0"',
        patch_text,
        count=1,
    )
    if count != 1:
        fail("could not update lite_version_name")

    patch_text, count = re.subn(
        r"lite_version_code = \d+",
        "lite_version_code = 22",
        patch_text,
        count=1,
    )
    if count != 1:
        fail("could not update lite_version_code")

    # Keep the existing one-second bridge timer. It is already the
    # low-impact setting and avoids four unnecessary rebuilds per second.
    patch_text = patch_text.replace(
        "// Lite: update the adaptive DPS overlay once per second",
        "// Performance mode: bridge live data at most once per second",
    )

    # Add payload deduplication to the generated main.dart bridge. This stops
    # FlutterOverlayWindow.shareData from crossing isolates when nothing visible
    # changed.
    bridge_anchor = """  Future<void> _updateOverlay() async {
    final storage = DataStorage();
    storage.checkTimeout();
"""
    bridge_replacement = """  String _liteLastOverlayPayload = '';

  Future<void> _updateOverlay() async {
    final storage = DataStorage();
    storage.checkTimeout();
"""
    if "_liteLastOverlayPayload" not in patch_text:
        patch_text = replace_once(
            patch_text,
            bridge_anchor,
            bridge_replacement,
            "overlay bridge method",
        )

    share_pattern = re.compile(
        r"""    FlutterOverlayWindow\.shareData\(\{
      'players': players,
      'combatTime': storage\.currentCombatDuration\.inSeconds,
      'autoResetLocked': storage\.liteAutoResetLocked,
      'lastResetReason': storage\.liteLastResetReason,
      'phase': storage\.liteEncounterPhase,
    \}\);""",
        re.MULTILINE,
    )
    share_replacement = """    final payload = <String, dynamic>{
      'players': players,
      'combatTime': storage.currentCombatDuration.inSeconds,
      'autoResetLocked': storage.liteAutoResetLocked,
      'lastResetReason': storage.liteLastResetReason,
      'phase': storage.liteEncounterPhase,
    };

    // Avoid an isolate message and complete overlay rebuild when the visible
    // data is identical to the previous tick.
    final payloadSignature = payload.toString();
    if (payloadSignature == _liteLastOverlayPayload) return;
    _liteLastOverlayPayload = payloadSignature;

    FlutterOverlayWindow.shareData(payload);"""
    patch_text, count = share_pattern.subn(share_replacement, patch_text, count=1)
    if count != 1 and "FlutterOverlayWindow.shareData(payload);" not in patch_text:
        fail("could not add overlay payload deduplication")

    # Coalesce overlay-isolate events and skip setState for identical payloads.
    field_anchor = """  Size? _resizeStartSize;
  Offset? _resizeStartPointer;
"""
    field_replacement = """  Size? _resizeStartSize;
  Offset? _resizeStartPointer;

  Timer? _liteUiFlushTimer;
  Map<String, dynamic>? _litePendingPayload;
  String _liteLastUiSignature = '';
"""
    if "_liteUiFlushTimer" not in overlay_text:
        overlay_text = replace_once(
            overlay_text,
            field_anchor,
            field_replacement,
            "overlay performance fields",
        )

    listener_pattern = re.compile(
        r"""    _overlaySubscription = FlutterOverlayWindow\.overlayListener\.listen\(\(event\) \{
      if \(!mounted \|\| event is! Map\) return;

      final rawPlayers = event\['players'\];
      final rawCombatTime = event\['combatTime'\];
      final rawAutoResetLocked = event\['autoResetLocked'\];

      setState\(\(\) \{
        if \(rawPlayers is List\) \{
          _players = rawPlayers
              \.whereType<Map>\(\)
              \.map\(\(entry\) => Map<String, dynamic>\.from\(entry\)\)
              \.toList\(growable: false\);
        \}

        if \(rawCombatTime is num\) \{
          _combatTime = rawCombatTime\.toInt\(\);
        \}

        if \(rawAutoResetLocked is bool\) \{
          _autoResetLocked = rawAutoResetLocked;
        \}
      \}\);

    \}\);""",
        re.MULTILINE,
    )

    listener_replacement = """    _overlaySubscription = FlutterOverlayWindow.overlayListener.listen((event) {
      if (!mounted || event is! Map) return;

      _litePendingPayload = Map<String, dynamic>.from(event);

      // Coalesce bursts into one UI update. A 250 ms delay remains visually
      // immediate while preventing repeated full-list rebuilds.
      _liteUiFlushTimer ??= Timer(
        const Duration(milliseconds: 250),
        _flushLiteUiPayload,
      );
    });"""

    overlay_text, count = listener_pattern.subn(
        listener_replacement,
        overlay_text,
        count=1,
    )
    if count != 1 and "_flushLiteUiPayload" not in overlay_text:
        fail("could not replace overlay listener")

    init_end_anchor = """    WidgetsBinding.instance.addPostFrameCallback((_) {
      _restoreLayout();
    });
  }

  @override
  void dispose() {
"""
    flush_method = """    WidgetsBinding.instance.addPostFrameCallback((_) {
      _restoreLayout();
    });
  }

  void _flushLiteUiPayload() {
    _liteUiFlushTimer = null;
    final payload = _litePendingPayload;
    _litePendingPayload = null;

    if (!mounted || payload == null) return;

    final signature = payload.toString();
    if (signature == _liteLastUiSignature) return;
    _liteLastUiSignature = signature;

    final rawPlayers = payload['players'];
    final rawCombatTime = payload['combatTime'];
    final rawAutoResetLocked = payload['autoResetLocked'];

    setState(() {
      if (rawPlayers is List) {
        _players = rawPlayers
            .whereType<Map>()
            .map((entry) => Map<String, dynamic>.from(entry))
            .toList(growable: false);
      }

      if (rawCombatTime is num) {
        _combatTime = rawCombatTime.toInt();
      }

      if (rawAutoResetLocked is bool) {
        _autoResetLocked = rawAutoResetLocked;
      }
    });
  }

  @override
  void dispose() {
"""
    if "void _flushLiteUiPayload()" not in overlay_text:
        overlay_text = replace_once(
            overlay_text,
            init_end_anchor,
            flush_method,
            "overlay flush method insertion",
        )

    dispose_anchor = """  void dispose() {
    _overlaySubscription?.cancel();
    super.dispose();
  }
"""
    dispose_replacement = """  void dispose() {
    _liteUiFlushTimer?.cancel();
    _liteUiFlushTimer = null;
    _litePendingPayload = null;
    _overlaySubscription?.cancel();
    super.dispose();
  }
"""
    overlay_text = replace_once(
        overlay_text,
        dispose_anchor,
        dispose_replacement,
        "overlay timer disposal",
    )

    patch_script.write_text(patch_text, encoding="utf-8")
    overlay.write_text(overlay_text, encoding="utf-8")

    print("BlueMeter Lite v1.4.0 performance update applied.")
    print("Build with GitHub Actions as usual.")


if __name__ == "__main__":
    main()
