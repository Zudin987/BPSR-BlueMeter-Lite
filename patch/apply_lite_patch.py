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
    attr_type = upstream / "lib/core/models/attr_type.dart"
    icon_patch_root = patch_dir / "android_icons"

    for required in (
        main_dart,
        packet_service,
        tcp_proxy,
        pubspec,
        manifest,
        app_gradle,
        data_storage,
        attr_type,
        icon_patch_root,
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

    # Replace the Android launcher icons with the provided portrait.
    icon_targets = [
        ("mipmap-mdpi", 48),
        ("mipmap-hdpi", 72),
        ("mipmap-xhdpi", 96),
        ("mipmap-xxhdpi", 144),
        ("mipmap-xxxhdpi", 192),
    ]

    res_root = upstream / "android/app/src/main/res"
    for folder_name, _ in icon_targets:
        source_folder = icon_patch_root / folder_name
        target_folder = res_root / folder_name
        target_folder.mkdir(parents=True, exist_ok=True)

        for icon_name in ("ic_launcher.png", "ic_launcher_round.png"):
            source_icon = source_folder / icon_name
            if not source_icon.exists():
                fail(f"missing launcher icon asset: {source_icon}")
            shutil.copyfile(source_icon, target_folder / icon_name)

    # Season 3 fix. BlueMeter previously used 12690/12691, which are
    # season-damage-increase percentage attributes. Illusion-Breaking Strength
    # is AttrSeasonStrength 11440, with total variant 11441.
    attr_text = attr_type.read_text(encoding="utf-8")
    attr_text = replace_once(
        attr_text,
        "  attrSeasonStrength(12690),",
        "  attrSeasonStrength(11440),",
        "Season 3 Illusion-Breaking Strength base attribute",
    )
    attr_text = replace_once(
        attr_text,
        "  attrSeasonStrengthTotal(12691),",
        "  attrSeasonStrengthTotal(11441),",
        "Season 3 Illusion-Breaking Strength total attribute",
    )
    attr_type.write_text(attr_text, encoding="utf-8")

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
  final Map<Int64, String> _liteSubProfessionNames = {};

  String? getLiteSubProfessionName(Int64 uid) {
    return _liteSubProfessionNames[uid];
  }

  String? _liteSubProfessionFromSkillId(String? rawSkillId) {
    if (rawSkillId == null || rawSkillId.isEmpty) return null;

    final skillId = int.tryParse(rawSkillId);
    if (skillId == null) return null;

    // Current ZDPS sub-profession detection IDs.
    switch (skillId) {
      case 1714:
      case 1734:
        return 'Iaido';

      case 1715:
      case 1738:
      case 179906:
        return 'Moonstrike';

      case 120901:
      case 120902:
        return 'Icicle';

      case 1241:
        return 'Frostbeam';

      case 160102:
      case 2208181:
      case 2208172:
        return 'Formless Expertise';

      case 1606:
      case 1621:
      case 1622:
      case 35104:
        return 'Crimson Expertise';

      case 1405:
      case 1418:
        return 'Vanguard';

      case 1419:
        return 'Skyward';

      case 1518:
      case 1541:
      case 21402:
        return 'Smite';

      case 20301:
        return 'Lifebind';

      case 1941:
      case 2201240:
        return 'Earthfort';

      case 1930:
      case 1931:
      case 1934:
      case 1935:
        return 'Block';

      case 2292:
      case 1700820:
      case 1700825:
      case 1700827:
        return 'Wildpack';

      case 220112:
      case 2203622:
      case 220106:
        return 'Falconry';

      case 2405:
      case 2411:
      case 2206401:
        return 'Recovery';

      case 2406:
      case 55412:
      case 55417:
        return 'Shield';

      case 2321:
      case 2335:
        return 'Dissonance';

      case 2301:
      case 2336:
      case 2361:
      case 55302:
        return 'Concerto';

      default:
        return null;
    }
  }

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

    final detectedSubProfession =
        _liteSubProfessionFromSkillId(skillId);
    if (detectedSubProfession != null) {
      _liteSubProfessionNames[attackerUid] = detectedSubProfession;
    }

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
        "// Lite: update the adaptive DPS overlay once per second",
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
  String _liteClassName(int? professionId) {
    switch (professionId) {
      case 1:
        return 'Stormblade';
      case 2:
        return 'Frost Mage';
      case 3:
        return 'Twin Striker';
      case 4:
        return 'Wind Knight';
      case 5:
        return 'Verdant Oracle';
      case 8:
        return 'Dorothy';
      case 9:
        return 'Heavy Guardian';
      case 10:
        return 'Dark Spirit Dance Ritual Blade';
      case 11:
        return 'Marksman';
      case 12:
        return 'Shield Knight';
      case 13:
        return 'Beat Performer';
      case 14:
        return 'Lucy';
      case 15:
        return 'Natsu';
      default:
        return 'Unknown';
    }
  }

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
            'className':
                storage.getLiteSubProfessionName(uid) ??
                    _liteClassName(info?.professionId),
            'combatPower': info?.combatPower ?? 0,
            'illusionBreakingStrength': info?.seasonStrength ?? 0,
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
        "height: 180,\n      width: 360,",
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
        r"^version:\s*[^\r\n]+$",
        "version: 1.8.0+11",
        "pubspec version",
    )
    pubspec.write_text(yaml, encoding="utf-8")

    print("BlueMeter Lite patch applied successfully.")
    print(f"Patched source: {upstream}")


if __name__ == "__main__":
    main()
