#!/usr/bin/env python3
'''Apply the final BlueMeter Lite overlay-bridge performance update.

This script is run by GitHub Actions against the generated upstream source.
Users do not need to run Python, a terminal, or a local build.
'''

from __future__ import annotations

import sys
from pathlib import Path


def fail(message: str) -> None:
    raise SystemExit(f"BlueMeter Lite performance patch failed: {message}")


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        fail(f"expected one {label}, found {count}")
    return text.replace(old, new, 1)


def replace_between(
    text: str,
    start_marker: str,
    end_marker: str,
    replacement: str,
    label: str,
) -> str:
    start = text.find(start_marker)
    if start == -1:
        fail(f"could not find start of {label}")

    end = text.find(end_marker, start)
    if end == -1 or end <= start:
        fail(f"could not find end of {label}")

    return text[:start] + replacement.rstrip() + "\n\n" + text[end:]


def main() -> None:
    if len(sys.argv) != 2:
        fail("usage: apply_performance_update.py <upstream-directory>")

    upstream = Path(sys.argv[1]).resolve()
    main_dart = upstream / "lib/main.dart"

    if not main_dart.exists():
        fail(f"missing generated source file: {main_dart}")

    dart = main_dart.read_text(encoding="utf-8")

    dart = replace_once(
        dart,
        "Timer.periodic(const Duration(milliseconds: 1000)",
        "Timer.periodic(_liteOverlayBridgeInterval",
        "one-second overlay bridge timer",
    )
    dart = dart.replace(
        "// Lite: update the Damage, Healing, or Tanking overlay once per second",
        "// Performance: bridge visible meter data at most once every two seconds",
        1,
    )

    dart = replace_once(
        dart,
        "  final Map<String, int> _liteSeasonStrengthCache = {};\n",
        '''  static const Duration _liteOverlayBridgeInterval =
      Duration(seconds: 2);
  final Map<String, int> _liteSeasonStrengthCache = {};
  String _liteLastOverlayPayloadSignature = '';

  void _litePruneSeasonStrengthCache(Set<String> activeUids) {
    if (activeUids.isEmpty) {
      _liteSeasonStrengthCache.clear();
      return;
    }

    _liteSeasonStrengthCache.removeWhere(
      (uid, _) => !activeUids.contains(uid),
    );
  }
''',
        "overlay bridge performance fields",
    )

    update_overlay = '''  Future<void> _updateOverlay() async {
    final storage = DataStorage();
    storage.checkTimeout();

    // Build a lightweight signature first. Player payload maps and the
    // cross-isolate message are created only when visible data changes.
    final activeEntries = <dynamic>[];
    final activeUids = <String>{};
    final signature = StringBuffer()
      ..write(storage.liteAutoResetLocked)
      ..write('|')
      ..write(storage.liteLastResetReason)
      ..write('|')
      ..write(storage.liteEncounterPhase);

    for (final entry in storage.fullDpsDatas.entries) {
      final uid = entry.key;
      final uidText = uid.toString();
      final data = entry.value;
      final hasMetric =
          data.totalAttackDamage.toInt() > 0 ||
          data.totalHeal.toInt() > 0 ||
          data.totalTakenDamage.toInt() > 0;
      if (!hasMetric) continue;

      final info = storage.getPlayerInfoSync(uid);
      if (info == null) continue;

      final className =
          storage.getLiteSubProfessionName(uid) ??
              _liteClassName(info.professionId);

      activeEntries.add(entry);
      activeUids.add(uidText);

      signature
        ..write('|')
        ..write(uidText)
        ..write(':')
        ..write(info.name ?? '')
        ..write(':')
        ..write(className)
        ..write(':')
        ..write(info.combatPower ?? 0)
        ..write(':')
        ..write(info.seasonStrength ?? 0)
        ..write(':')
        ..write(uid == storage.currentPlayerUuid)
        ..write(':')
        ..write(data.totalAttackDamage.toInt())
        ..write(':')
        ..write(data.totalHeal.toInt())
        ..write(':')
        ..write(data.totalTakenDamage.toInt());
    }

    _litePruneSeasonStrengthCache(activeUids);

    final payloadSignature = signature.toString();
    if (payloadSignature == _liteLastOverlayPayloadSignature) {
      return;
    }
    _liteLastOverlayPayloadSignature = payloadSignature;

    final players = activeEntries.map((entry) {
      final uid = entry.key;
      final uidText = uid.toString();
      final dpsData = entry.value;
      final info = storage.getPlayerInfoSync(uid)!;
      final liveSeasonStrength = info.seasonStrength ?? 0;
      if (liveSeasonStrength > 0) {
        _liteSeasonStrengthCache[uidText] = liveSeasonStrength;
      }

      final displayedSeasonStrength = liveSeasonStrength > 0
          ? liveSeasonStrength
          : (_liteSeasonStrengthCache[uidText] ?? 0);

      return <String, dynamic>{
        'uid': uidText,
        'name': info.name ?? 'Unknown',
        'className':
            storage.getLiteSubProfessionName(uid) ??
                _liteClassName(info.professionId),
        'combatPower': info.combatPower ?? 0,
        'illusionBreakingStrength': displayedSeasonStrength,
        'isMe': uid == storage.currentPlayerUuid,
        'totalDamage': dpsData.totalAttackDamage.toInt(),
        'dps': dpsData.liteDps,
        'totalHealing': dpsData.totalHeal.toInt(),
        'hps': dpsData.liteHps,
        'totalTaken': dpsData.totalTakenDamage.toInt(),
        'takenDps': dpsData.liteTakenDps,
      };
    }).toList(growable: false);

    FlutterOverlayWindow.shareData({
      'players': players,
      'combatTime': storage.currentCombatDuration.inSeconds,
      'autoResetLocked': storage.liteAutoResetLocked,
      'lastResetReason': storage.liteLastResetReason,
      'phase': storage.liteEncounterPhase,
    });
  }'''

    dart = replace_between(
        dart,
        "  Future<void> _updateOverlay() async {",
        "  Future<void> _updateOverlayWithSelection() async {",
        update_overlay,
        "overlay data bridge",
    )

    dart = replace_once(
        dart,
        '''      await FlutterOverlayWindow.moveOverlay(
        const OverlayPosition(8, 80),
      );
      return true;
''',
        '''      await FlutterOverlayWindow.moveOverlay(
        const OverlayPosition(8, 80),
      );

      _liteLastOverlayPayloadSignature = '';
      await _updateOverlay();
      return true;
''',
        "overlay startup payload refresh",
    )

    main_dart.write_text(dart, encoding="utf-8")

    print("Final BlueMeter Lite performance update applied.")
    print("- Main overlay bridge: two seconds")
    print("- Unchanged payload transfer: skipped")
    print("- Season-strength cache: pruned to active encounter players")


if __name__ == "__main__":
    main()
