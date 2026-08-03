#!/usr/bin/env python3
# Apply the BlueMeter Lite patch to an upstream BlueMeter Mobile checkout.

from __future__ import annotations

import re
import shutil
import sys
import textwrap
from pathlib import Path


def fail(message: str) -> None:
    raise SystemExit(f"BlueMeter Lite patch failed: {message}")


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if old not in text:
        fail(f"could not find {label}")
    return text.replace(old, new, 1)


def regex_once(text: str, pattern: str, replacement: str, label: str) -> str:
    updated, count = re.subn(
        pattern,
        replacement,
        text,
        count=1,
        flags=re.MULTILINE | re.DOTALL,
    )
    if count != 1:
        fail(f"expected one {label}, found {count}")
    return updated


def main() -> None:
    if len(sys.argv) != 2:
        fail("usage: apply_lite_patch.py <upstream-directory>")

    upstream = Path(sys.argv[1]).resolve()
    patch_dir = Path(__file__).resolve().parent

    main_dart = upstream / "lib/main.dart"
    packet_service = (
        upstream
        / "android/app/src/main/kotlin/com/bluemeter/bluemeter_mobile/"
        / "PacketCaptureService.kt"
    )
    tcp_proxy = packet_service.parent / "TcpProxy.kt"
    pubspec = upstream / "pubspec.yaml"
    manifest = upstream / "android/app/src/main/AndroidManifest.xml"
    app_gradle = upstream / "android/app/build.gradle.kts"
    data_storage = upstream / "lib/core/state/data_storage.dart"

    for required in (
        main_dart,
        packet_service,
        tcp_proxy,
        pubspec,
        manifest,
        app_gradle,
        data_storage,
    ):
        if not required.exists():
            fail(f"missing upstream file: {required}")

    shutil.copyfile(patch_dir / "TcpProxy.kt", tcp_proxy)

    service = packet_service.read_text(encoding="utf-8")
    service = replace_once(
        service,
        "        }, 500, 500, TimeUnit.MILLISECONDS)",
        "        }, 1000, 1000, TimeUnit.MILLISECONDS)",
        "500 ms Kotlin flush interval",
    )

    allowed_apps = r'''
        // Capture only installed BPSR clients. Never fall back to all-device capture.
        val supportedGamePackages = listOf(
            "sea.haoplay.game.gp.bpsr",
            "com.bpsr.apj",
            "tw.haoplay.game.gp.xhgm",
            "asia.xdg.game.gp.bpsr"
        )
        var allowedPackageCount = 0

        for (gamePackage in supportedGamePackages) {
            try {
                builder.addAllowedApplication(gamePackage)
                allowedPackageCount++
                Log.i("BlueMeterLite", "Capturing package: $gamePackage")
            } catch (_: Exception) {
                // Package is not installed on this device.
            }
        }

        if (allowedPackageCount == 0) {
            Log.e("BlueMeterLite", "No supported BPSR package is installed")
            isRunning = false
            flushTask?.cancel(false)
            flushTask = null
            stopSelf()
            return
        }
'''

    service = regex_once(
        service,
        r"\s*// Only capture game traffic.*?"
        r"try \{\s*builder\.addAllowedApplication\(\"com\.bpsr\.apj\"\)\s*\}"
        r"\s*catch \(e: Exception\) \{\s*"
        r"Log\.w\(\"BlueMeter\", \"Could not restrict VPN to game app: "
        r"\$\{e\.message\}\"\)\s*\}",
        "\n" + textwrap.dedent(allowed_apps).rstrip(),
        "Android package allow-list block",
    )
    packet_service.write_text(service, encoding="utf-8")

    manifest_text = manifest.read_text(encoding="utf-8")
    manifest_text = replace_once(
        manifest_text,
        'android:label="BlueMeter Mobile"',
        'android:label="BlueMeter Lite"',
        "Android application label",
    )
    manifest_text = replace_once(
        manifest_text,
        "    <queries>\n",
        """    <queries>
        <package android:name="sea.haoplay.game.gp.bpsr" />
        <package android:name="com.bpsr.apj" />
        <package android:name="tw.haoplay.game.gp.xhgm" />
        <package android:name="asia.xdg.game.gp.bpsr" />
""",
        "Android package visibility queries",
    )
    manifest.write_text(manifest_text, encoding="utf-8")

    gradle_text = app_gradle.read_text(encoding="utf-8")
    gradle_text = replace_once(
        gradle_text,
        'applicationId = "com.bluemeter.bluemeter_mobile"',
        'applicationId = "com.bluemeter.lite"',
        "Android application ID",
    )
    app_gradle.write_text(gradle_text, encoding="utf-8")

    # Keep only the counters required for a DPS ranking. This avoids per-hit
    # skill, target, timeline, healing, and damage-taken allocations.
    storage_text = data_storage.read_text(encoding="utf-8")
    damage_start = storage_text.find("  void addDamage(")
    healing_start = storage_text.find("  void addHealing(")
    reset_start = storage_text.find("  void reset(")

    if (
        damage_start == -1
        or healing_start == -1
        or reset_start == -1
        or not (damage_start < healing_start < reset_start)
    ):
        fail("could not locate DataStorage combat methods")

    lite_combat_methods = r"""
  void addDamage(
    Int64 attackerUid,
    Int64 targetUid,
    Int64 damage,
    int tick, {
    String? skillId,
    bool isLucky = false,
    bool isCrit = false,
  }) {
    _onAction();

    final attackerData = getOrCreateDpsData(attackerUid);
    attackerData.startLoggedTick ??= tick;
    attackerData.lastLoggedTick = tick;
    attackerData.totalAttackDamage += damage;

    if (attackerData.startLoggedTick != null) {
      attackerData.activeCombatTicks =
          tick - attackerData.startLoggedTick!;
    }

    _scheduleNotify();
  }

  void addHealing(
    Int64 healerUid,
    Int64 targetUid,
    Int64 healAmount,
    int tick, {
    String? skillId,
    bool isCrit = false,
  }) {
    // BlueMeter Lite intentionally does not collect healing details.
  }

"""

    storage_text = (
        storage_text[:damage_start]
        + textwrap.dedent(lite_combat_methods)
        + storage_text[reset_start:]
    )
    data_storage.write_text(storage_text, encoding="utf-8")

    dart = main_dart.read_text(encoding="utf-8")

    imports_to_remove = [
        "import 'package:bluemeter_mobile/views/dps_view.dart';\n",
        "import 'package:bluemeter_mobile/views/nearby_view.dart';\n",
        "import 'package:bluemeter_mobile/views/tools_view.dart';\n",
        "import 'package:bluemeter_mobile/views/hunt_view.dart';\n",
        "import 'package:bluemeter_mobile/views/settings_view.dart';\n",
        "import 'package:bluemeter_mobile/widgets/player_detail_card.dart';\n",
        "import 'core/services/monster_name_service.dart';\n",
        "import 'core/services/bptimer_service.dart';\n",
        "import 'core/models/dps_data.dart';\n",
        "import 'core/models/player_info.dart';\n",
        "import 'core/models/overlay_settings.dart';\n",
    ]
    for import_line in imports_to_remove:
        dart = dart.replace(import_line, "")

    dart = regex_once(
        dart,
        r"\s*await MonsterNameService\(\)\.load\(\);\s*"
        r"// Pre-load known mobs for HP reporting \(non-blocking\)\s*"
        r"BPTimerService\(\)\.ensureMobsLoaded\(\);",
        "",
        "monster/BPTimer startup",
    )

    overlay_start = dart.find("class OverlayWidget extends StatefulWidget")
    overlay_end = dart.find("class MyApp extends StatelessWidget")
    if overlay_start == -1 or overlay_end == -1 or overlay_end <= overlay_start:
        fail("could not locate OverlayWidget replacement boundaries")

    lite_overlay = (patch_dir / "overlay_widget_lite.dart").read_text(
        encoding="utf-8"
    ).rstrip()
    dart = dart[:overlay_start] + lite_overlay + "\n\n" + dart[overlay_end:]

    dart = dart.replace(
        "  final BPTimerService _bpTimerService = BPTimerService();\n",
        "",
    )
    dart = dart.replace(
        "  int _lastReportedLineId = 0; // Track line changes for throttle reset\n",
        "",
    )

    dart = replace_once(
        dart,
        "Timer.periodic(const Duration(milliseconds: 500)",
        "Timer.periodic(const Duration(milliseconds: 1000)",
        "overlay refresh interval",
    )
    dart = dart.replace(
        "// Update overlay at 2 FPS (500ms) to prevent log spam and UI overload",
        "// Lite: update the fixed overlay once per second",
    )

    data_block_start = dart.find(
        "  final Map<String, String> _targetNameCache = {};"
    )
    packet_handler_start = dart.find(
        "  Future<void> _onPacketData(dynamic event) async"
    )
    if (
        data_block_start == -1
        or packet_handler_start == -1
        or packet_handler_start <= data_block_start
    ):
        fail("could not locate overlay data bridge replacement boundaries")

    lite_data_bridge = r'''
  Future<void> _updateOverlay() async {
    final storage = DataStorage();
    storage.checkTimeout();

    final players = storage.fullDpsDatas.entries
        .where((entry) => entry.value.totalAttackDamage.toInt() > 0)
        .map((entry) {
          final uid = entry.key;
          final dpsData = entry.value;
          final info = storage.getPlayerInfoSync(uid);

          return <String, dynamic>{
            'uid': uid.toString(),
            'name': info?.name ?? 'Unknown',
            'isMe': uid == storage.currentPlayerUuid,
            'dps': dpsData.simpleDps,
            'total': dpsData.totalAttackDamage.toInt(),
          };
        })
        .toList(growable: false);

    FlutterOverlayWindow.shareData({
      'players': players,
      'combatTime': storage.currentCombatDuration.inSeconds,
    });
  }

  Future<void> _updateOverlayWithSelection() async {
    await _updateOverlay();
  }

'''

    dart = (
        dart[:data_block_start]
        + textwrap.dedent(lite_data_bridge)
        + dart[packet_handler_start:]
    )

    dart = dart.replace("title: 'BlueMeter Mobile'", "title: 'BlueMeter Lite'")
    dart = dart.replace(
        "title: const Text('BlueMeter Mobile')",
        "title: const Text('BlueMeter Lite')",
    )
    dart = dart.replace(
        'overlayTitle: "BlueMeter DPS"',
        'overlayTitle: "BlueMeter Lite"',
    )
    dart = dart.replace(
        'overlayContent: "DPS Meter Active"',
        'overlayContent: "Lite DPS Meter Active"',
    )

    dart = regex_once(
        dart,
        r"height:\s*400,\s*width:\s*600,",
        "height: 226,\n      width: 360,",
        "overlay dimensions",
    )
    dart = replace_once(
        dart,
        "const OverlayPosition(0, 100)",
        "const OverlayPosition(8, 80)",
        "initial overlay position",
    )

    main_dart.write_text(dart, encoding="utf-8")

    yaml = pubspec.read_text(encoding="utf-8")
    yaml = regex_once(
        yaml,
        r'^description:\s*".*?"$',
        'description: "Lightweight Android DPS overlay for BPSR."',
        "pubspec description",
    )
    yaml = regex_once(
        yaml,
        r"^version:\s*.+$",
        "version: 1.2.0+5",
        "pubspec version",
    )
    pubspec.write_text(yaml, encoding="utf-8")

    print("BlueMeter Lite patch applied successfully.")
    print(f"Patched source: {upstream}")


if __name__ == "__main__":
    main()
