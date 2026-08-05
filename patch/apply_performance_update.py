#!/usr/bin/env python3
"""Apply the final BlueMeter Lite overlay-bridge performance update.

This script runs only in GitHub Actions against the generated upstream source.
It detects the indentation produced by apply_lite_patch.py instead of assuming
that generated class members always retain two leading spaces.
"""

from __future__ import annotations

import re
import sys
import textwrap
from pathlib import Path


def fail(message: str) -> None:
    raise SystemExit(f"BlueMeter Lite performance patch failed: {message}")


def regex_once(
    text: str,
    pattern: str,
    replacement: str,
    label: str,
) -> str:
    updated, count = re.subn(
        pattern,
        replacement,
        text,
        count=1,
        flags=re.MULTILINE,
    )
    if count != 1:
        fail(f"expected one {label}, found {count}")
    return updated


def indent_block(block: str, indent: str) -> str:
    cleaned = textwrap.dedent(block).strip("\n")
    return "\n".join(
        f"{indent}{line}" if line else ""
        for line in cleaned.splitlines()
    )


def replace_method(
    text: str,
    method_name: str,
    next_method_name: str,
    replacement: str,
) -> str:
    start_match = re.search(
        rf"^(?P<indent>[ \t]*)Future<void> {re.escape(method_name)}"
        r"\(\) async \{",
        text,
        flags=re.MULTILINE,
    )
    if start_match is None:
        fail(f"could not find {method_name}")

    end_match = re.search(
        rf"^[ \t]*Future<void> {re.escape(next_method_name)}"
        r"\(\) async \{",
        text[start_match.end():],
        flags=re.MULTILINE,
    )
    if end_match is None:
        fail(f"could not find {next_method_name}")

    start = start_match.start()
    end = start_match.end() + end_match.start()
    replacement_text = indent_block(
        replacement,
        start_match.group("indent"),
    )

    return text[:start] + replacement_text + "\n\n" + text[end:]


def main() -> None:
    if len(sys.argv) != 2:
        fail("usage: apply_performance_update.py <upstream-directory>")

    upstream = Path(sys.argv[1]).resolve()
    main_dart = upstream / "lib/main.dart"

    if not main_dart.exists():
        fail(f"missing generated source file: {main_dart}")

    dart = main_dart.read_text(encoding="utf-8")

    if "_liteOverlayBridgeInterval" not in dart:
        dart = regex_once(
            dart,
            r"Timer\.periodic\("
            r"const Duration\(milliseconds:\s*1000\)",
            "Timer.periodic(_liteOverlayBridgeInterval",
            "one-second overlay bridge timer",
        )

        field_match = re.search(
            r"^(?P<indent>[ \t]*)"
            r"final Map<String, int> _liteSeasonStrengthCache = \{\};"
            r"[ \t]*$",
            dart,
            flags=re.MULTILINE,
        )
        if field_match is None:
            fail("expected one overlay bridge performance field, found 0")

        field_block = indent_block(
            """
            static const Duration _liteOverlayBridgeInterval =
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
            """,
            field_match.group("indent"),
        )
        dart = (
            dart[:field_match.start()]
            + field_block
            + dart[field_match.end():]
        )

    dart = dart.replace(
        "// Lite: update the Damage, Healing, or Tanking overlay once per second",
        "// Performance: bridge visible meter data at most once every two seconds",
        1,
    )

    if "if (payloadSignature == _liteLastOverlayPayloadSignature)" not in dart:
        dart = replace_method(
            dart,
            "_updateOverlay",
            "_updateOverlayWithSelection",
            """
            Future<void> _updateOverlay() async {
              final storage = DataStorage();
              storage.checkTimeout();

              // Build a lightweight signature first. Player payload maps and
              // the cross-isolate message are created only when visible data
              // changes.
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
                  _liteSeasonStrengthCache[uidText] =
                      liveSeasonStrength;
                }

                final displayedSeasonStrength =
                    liveSeasonStrength > 0
                        ? liveSeasonStrength
                        : (_liteSeasonStrengthCache[uidText] ?? 0);

                return <String, dynamic>{
                  'uid': uidText,
                  'name': info.name ?? 'Unknown',
                  'className':
                      storage.getLiteSubProfessionName(uid) ??
                          _liteClassName(info.professionId),
                  'combatPower': info.combatPower ?? 0,
                  'illusionBreakingStrength':
                      displayedSeasonStrength,
                  'isMe': uid == storage.currentPlayerUuid,
                  'totalDamage':
                      dpsData.totalAttackDamage.toInt(),
                  'dps': dpsData.liteDps,
                  'totalHealing': dpsData.totalHeal.toInt(),
                  'hps': dpsData.liteHps,
                  'totalTaken':
                      dpsData.totalTakenDamage.toInt(),
                  'takenDps': dpsData.liteTakenDps,
                };
              }).toList(growable: false);

              FlutterOverlayWindow.shareData({
                'players': players,
                'combatTime':
                    storage.currentCombatDuration.inSeconds,
                'autoResetLocked':
                    storage.liteAutoResetLocked,
                'lastResetReason':
                    storage.liteLastResetReason,
                'phase': storage.liteEncounterPhase,
              });
            }
            """,
        )

    if "_liteLastOverlayPayloadSignature = '';" not in dart[
        dart.find("Future<bool> _startOverlay() async {"):
    ]:
        start_payload_pattern = (
            r"^(?P<indent>[ \t]*)"
            r"await FlutterOverlayWindow\.moveOverlay\(\n"
            r"(?P=indent)  const OverlayPosition\(8, 80\),\n"
            r"(?P=indent)\);\n"
            r"(?P=indent)return true;"
        )
        start_payload_match = re.search(
            start_payload_pattern,
            dart,
            flags=re.MULTILINE,
        )
        if start_payload_match is None:
            fail("expected one overlay startup payload anchor, found 0")

        indent = start_payload_match.group("indent")
        startup_replacement = (
            f"{indent}await FlutterOverlayWindow.moveOverlay(\n"
            f"{indent}  const OverlayPosition(8, 80),\n"
            f"{indent});\n\n"
            f"{indent}_liteLastOverlayPayloadSignature = '';\n"
            f"{indent}await _updateOverlay();\n"
            f"{indent}return true;"
        )
        dart = (
            dart[:start_payload_match.start()]
            + startup_replacement
            + dart[start_payload_match.end():]
        )

    main_dart.write_text(dart, encoding="utf-8")

    print("Final BlueMeter Lite performance update applied.")
    print("- Main overlay bridge: two seconds")
    print("- Unchanged payload transfer: skipped")
    print("- Season-strength cache: pruned to active encounter players")


if __name__ == "__main__":
    main()
