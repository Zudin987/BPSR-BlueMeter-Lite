#!/usr/bin/env python3
# Apply the BlueMeter Lite patch to an upstream BlueMeter Mobile checkout.

from __future__ import annotations

import re
import subprocess
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


def replace_between(
    text: str,
    start: str,
    end: str,
    replacement: str,
    label: str,
) -> str:
    start_index = text.find(start)
    if start_index == -1:
        fail(f"could not find start of {label}")

    end_index = text.find(end, start_index)
    if end_index == -1:
        fail(f"could not find end of {label}")

    return (
        text[:start_index]
        + textwrap.dedent(replacement).rstrip()
        + "\n\n"
        + text[end_index:]
    )


def main() -> None:
    if len(sys.argv) != 2:
        fail("usage: apply_lite_patch.py <upstream-directory>")

    upstream = Path(sys.argv[1]).resolve()
    patch_dir = Path(__file__).resolve().parent

    lite_version_name = "1.3.1"
    lite_version_code = 21

    upstream_commit_file = upstream / "UPSTREAM_COMMIT.txt"
    if upstream_commit_file.exists():
        upstream_commit = upstream_commit_file.read_text(
            encoding="utf-8"
        ).strip()
    else:
        try:
            upstream_commit = subprocess.check_output(
                ["git", "-C", str(upstream), "rev-parse", "HEAD"],
                text=True,
            ).strip()
        except Exception:
            upstream_commit = "unknown"

    upstream_commit_short = (
        upstream_commit[:12] if upstream_commit != "unknown" else "unknown"
    )

    main_dart = upstream / "lib/main.dart"
    packet_service = (
        upstream
        / "android/app/src/main/kotlin/com/bluemeter/bluemeter_mobile/"
        / "PacketCaptureService.kt"
    )
    main_activity = packet_service.parent / "MainActivity.kt"
    tcp_proxy = packet_service.parent / "TcpProxy.kt"
    pubspec = upstream / "pubspec.yaml"
    manifest = upstream / "android/app/src/main/AndroidManifest.xml"
    app_gradle = upstream / "android/app/build.gradle.kts"
    data_storage = upstream / "lib/core/state/data_storage.dart"
    dps_data = upstream / "lib/core/models/dps_data.dart"
    attr_type = upstream / "lib/core/models/attr_type.dart"
    sync_near_entities_processor = (
        upstream
        / "lib/core/analyze/processors/sync_near_entities_processor.dart"
    )
    sync_container_data_processor = (
        upstream
        / "lib/core/analyze/processors/sync_container_data_processor.dart"
    )
    encounter_history_service = (
        upstream
        / "lib/core/services/encounter_history_service.dart"
    )
    encounter_history_view = (
        upstream
        / "lib/views/encounter_history_view.dart"
    )
    icon_patch_root = patch_dir / "android_icons"

    for required in (
        main_dart,
        packet_service,
        main_activity,
        tcp_proxy,
        pubspec,
        manifest,
        app_gradle,
        data_storage,
        dps_data,
        attr_type,
        sync_near_entities_processor,
        sync_container_data_processor,
        icon_patch_root,
    ):
        if not required.exists():
            fail(f"missing upstream file: {required}")

    shutil.copyfile(patch_dir / "TcpProxy.kt", tcp_proxy)
    shutil.copyfile(
        patch_dir / "encounter_history_service.dart",
        encounter_history_service,
    )
    shutil.copyfile(
        patch_dir / "encounter_history_view.dart",
        encounter_history_view,
    )


    activity_text = main_activity.read_text(encoding="utf-8")
    activity_text = replace_once(
        activity_text,
        (
            '    private val UPSTREAM_EVENT_CHANNEL = '
            '"com.bluemeter.mobile/upstream_stream"\n'
        ),
        (
            '    private val UPSTREAM_EVENT_CHANNEL = '
            '"com.bluemeter.mobile/upstream_stream"\n'
            '    private val supportedGamePackages = listOf(\n'
            '        "sea.haoplay.game.gp.bpsr",\n'
            '        "com.bpsr.apj",\n'
            '        "tw.haoplay.game.gp.xhgm",\n'
            '        "asia.xdg.game.gp.bpsr"\n'
            '    )\n'
        ),
        "MainActivity supported package list",
    )
    activity_text = replace_once(
        activity_text,
        '            if (call.method == "startVpn") {',
        '''            if (call.method == "getInstalledSupportedPackages") {
                val installedPackages = supportedGamePackages.filter {
                    gamePackage ->
                    try {
                        packageManager.getApplicationInfo(gamePackage, 0)
                        true
                    } catch (_: Exception) {
                        false
                    }
                }
                result.success(installedPackages)
            } else if (call.method == "startVpn") {''',
        "MainActivity installed-package method",
    )
    main_activity.write_text(activity_text, encoding="utf-8")

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
        'android:windowSoftInputMode="adjustResize">',
        'android:windowSoftInputMode="adjustResize"\n'
        '            android:screenOrientation="portrait">',
        "portrait MainActivity orientation",
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
        "plugins {\n",
        (
            "import java.io.FileInputStream\n"
            "import java.util.Properties\n\n"
            "plugins {\n"
        ),
        "Android signing imports",
    )
    gradle_text = replace_once(
        gradle_text,
        "}\n\nandroid {\n",
        (
            "}\n\n"
            'val keystorePropertiesFile = rootProject.file("key.properties")\n'
            "val keystoreProperties = Properties()\n"
            "if (keystorePropertiesFile.exists()) {\n"
            "    keystoreProperties.load(FileInputStream(keystorePropertiesFile))\n"
            "}\n\n"
            "android {\n"
        ),
        "Android signing properties",
    )
    gradle_text = replace_once(
        gradle_text,
        'applicationId = "com.bluemeter.bluemeter_mobile"',
        'applicationId = "com.bluemeter.lite"',
        "Android application ID",
    )
    gradle_text = replace_once(
        gradle_text,
        """    buildTypes {
        release {
            // TODO: Add your own signing config for the release build.
            // Signing with the debug keys for now, so `flutter run --release` works.
            signingConfig = signingConfigs.getByName("debug")
        }
    }""",
        """    signingConfigs {
        if (keystorePropertiesFile.exists()) {
            create("release") {
                keyAlias = keystoreProperties["keyAlias"] as String
                keyPassword = keystoreProperties["keyPassword"] as String
                storeFile = file(keystoreProperties["storeFile"] as String)
                storePassword = keystoreProperties["storePassword"] as String
            }
        }
    }

    buildTypes {
        release {
            signingConfig = if (keystorePropertiesFile.exists()) {
                signingConfigs.getByName("release")
            } else {
                // Local development can still build without private release secrets.
                signingConfigs.getByName("debug")
            }
        }
    }""",
        "Android release signing block",
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

    # Remote-player Season 3 fix:
    # BlueMeter already handles Season Strength in later delta packets, but
    # its initial SyncNearEntities appearance path ignores that attribute.
    near_text = sync_near_entities_processor.read_text(encoding="utf-8")
    near_text = regex_once(
        near_text,
        (
            r"^(?P<indent>[ \t]*)case AttrType\.attrFightPoint:[ \t]*\n"
            r"(?P=indent)[ \t]+_storage\.setPlayerCombatPower\("
            r"playerUid,[ \t]*reader\.readInt32\(\)\);[ \t]*\n"
            r"(?P=indent)[ \t]+break;[ \t]*\n"
            r"(?:[ \t]*\n)*"
            r"(?P=indent)case AttrType\.attrLevel:"
        ),
        (
            r"\g<indent>case AttrType.attrFightPoint:\n"
            r"\g<indent>  _storage.setPlayerCombatPower("
            r"playerUid, reader.readInt32());\n"
            r"\g<indent>  break;\n\n"
            r"\g<indent>case AttrType.attrSeasonStrength:\n"
            r"\g<indent>case AttrType.attrSeasonStrengthTotal:\n"
            r"\g<indent>  _storage.setPlayerSeasonStrength(\n"
            r"\g<indent>    playerUid,\n"
            r"\g<indent>    reader.readInt32(),\n"
            r"\g<indent>  );\n"
            r"\g<indent>  break;\n\n"
            r"\g<indent>case AttrType.attrLevel:"
        ),
        "initial nearby-player Season 3 strength cases",
    )
    sync_near_entities_processor.write_text(near_text, encoding="utf-8")

    container_text = sync_container_data_processor.read_text(
        encoding="utf-8"
    )

    # Find the complete SceneData section by line markers instead of matching
    # its exact indentation and every explanatory comment.
    scene_marker = "// SceneData → lineId, mapId, channelId"
    attr_marker = "// Attr → HP"

    scene_marker_index = container_text.find(scene_marker)
    if scene_marker_index == -1:
        fail("could not locate SceneData section")

    scene_section_start = container_text.rfind(
        "\n",
        0,
        scene_marker_index,
    )
    scene_section_start = (
        0 if scene_section_start == -1 else scene_section_start + 1
    )

    attr_marker_index = container_text.find(
        attr_marker,
        scene_marker_index,
    )
    if attr_marker_index == -1:
        fail("could not locate Attr section after SceneData")

    scene_section_end = container_text.rfind(
        "\n",
        scene_marker_index,
        attr_marker_index,
    )
    scene_section_end = (
        attr_marker_index
        if scene_section_end == -1
        else scene_section_end + 1
    )

    lite_scene_section = """      // SceneData can arrive in either the large full-player packet or a
      // smaller packet for the already-known current player during transitions.
      // Continue ignoring scene data belonging to NPCs and other characters.
      final isCurrentPlayerScene =
          isFullPlayerData ||
          playerUid == _storage.currentPlayerUuid;

      if (vData.hasSceneData() && isCurrentPlayerScene) {
        final scene = vData.sceneData;
        _storage.onSceneUpdate(
          // lineId == 0 is meaningful for an instanced/dungeon scene.
          lineId: scene.lineId,
          mapId: scene.mapId,
          channelId: scene.channelId,
        );
      }
"""

    container_text = (
        container_text[:scene_section_start]
        + lite_scene_section
        + container_text[scene_section_end:]
    )

    sync_container_data_processor.write_text(
        container_text,
        encoding="utf-8",
    )

    dps_text = dps_data.read_text(encoding="utf-8")

    # Insert lightweight metric clocks using a stable field anchor instead of
    # depending on an exact combination of blank lines.
    if "int? liteDamageStartTick;" not in dps_text:
        metric_clock_anchor = "  int activeCombatTicks = 0;"
        metric_clock_index = dps_text.find(metric_clock_anchor)
        if metric_clock_index == -1:
            fail("could not locate DpsData activeCombatTicks field")

        metric_clock_insert_at = (
            metric_clock_index + len(metric_clock_anchor)
        )
        metric_clock_fields = """

  // BlueMeter Lite keeps separate clocks for each live meter so Healing or
  // Tanking activity never changes a player's DPS denominator.
  int? liteDamageStartTick;
  int liteDamageLastTick = 0;
  int? liteHealingStartTick;
  int liteHealingLastTick = 0;
  int? liteTakenStartTick;
  int liteTakenLastTick = 0;
"""
        dps_text = (
            dps_text[:metric_clock_insert_at]
            + metric_clock_fields
            + dps_text[metric_clock_insert_at:]
        )

    # Add rate getters immediately before the DpsData class's final brace.
    # This remains stable even when upstream reformats simpleTakenDps.
    if "double get liteHps" not in dps_text:
        if "double get simpleTakenDps" not in dps_text:
            fail("could not locate DpsData simpleTakenDps getter")

        dps_class_close = dps_text.rfind("\n}")
        if dps_class_close == -1:
            fail("could not locate DpsData closing brace")

        lite_rate_getters = """

  double _liteRate(Int64 total, int? startTick, int lastTick) {
    if (startTick == null || total.toInt() <= 0) return 0.0;
    double seconds = (lastTick - startTick) / 1000.0;
    if (seconds < 1.0) seconds = 1.0;
    return total.toDouble() / seconds;
  }

  double get liteDps =>
      _liteRate(totalAttackDamage, liteDamageStartTick, liteDamageLastTick);

  double get liteHps =>
      _liteRate(totalHeal, liteHealingStartTick, liteHealingLastTick);

  double get liteTakenDps =>
      _liteRate(totalTakenDamage, liteTakenStartTick, liteTakenLastTick);
"""
        dps_text = (
            dps_text[:dps_class_close]
            + lite_rate_getters
            + dps_text[dps_class_close:]
        )

    dps_data.write_text(dps_text, encoding="utf-8")

    # Keep only lightweight live totals for Damage, Healing, and Tanking.
    # Skill, target, timeline, overheal, mitigation, and death breakdowns stay
    # disabled to preserve the Lite app's low memory and CPU overhead.
    storage_text = data_storage.read_text(encoding="utf-8")
    storage_text = replace_once(
        storage_text,
        "import 'package:fixnum/fixnum.dart';\n",
        (
            "import 'dart:async';\n"
            "import 'dart:math' as math;\n\n"
            "import 'package:fixnum/fixnum.dart';\n"
        ),
        "Lite encounter utility imports",
    )
    storage_text = replace_once(
        storage_text,
        "import '../services/database_service.dart';\n",
        (
            "import '../services/database_service.dart';\n"
            "import '../services/encounter_history_service.dart';\n"
        ),
        "Lite encounter history import",
    )
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

  void _liteDetectSubProfession(
    Int64 uid,
    String? skillId,
  ) {
    final detectedSubProfession =
        _liteSubProfessionFromSkillId(skillId);
    if (detectedSubProfession != null) {
      _liteSubProfessionNames[uid] = detectedSubProfession;
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
    _liteDetectSubProfession(attackerUid, skillId);

    // Damage output.
    final attackerData = getOrCreateDpsData(attackerUid);
    attackerData.totalAttackDamage += damage;
    attackerData.liteDamageStartTick ??= tick;
    attackerData.liteDamageLastTick = tick;

    // Damage received. NPC entries can exist internally, but the Lite bridge
    // only sends entities that have PlayerInfo to the Android overlay.
    final targetData = getOrCreateDpsData(targetUid);
    targetData.totalTakenDamage += damage;
    targetData.liteTakenStartTick ??= tick;
    targetData.liteTakenLastTick = tick;

    _liteMarkBossEngaged(targetUid);
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
    _onAction();
    _liteDetectSubProfession(healerUid, skillId);

    // Totals only: no skill, target, timeline, overheal, or crit breakdown.
    final healerData = getOrCreateDpsData(healerUid);
    healerData.totalHeal += healAmount;
    healerData.liteHealingStartTick ??= tick;
    healerData.liteHealingLastTick = tick;

    _scheduleNotify();
  }

"""

    storage_text = (
        storage_text[:damage_start]
        + textwrap.dedent(lite_combat_methods)
        + storage_text[reset_start:]
    )

    # Add lightweight automatic encounter splitting and history.
    lite_scene_and_state = r"""
static const String _liteAutoResetPreference =
    'lite_auto_reset_locked';

bool _liteAutoResetLocked = false;
bool get liteAutoResetLocked => _liteAutoResetLocked;

String _liteLastResetReason = '';
String get liteLastResetReason => _liteLastResetReason;

int _liteEncounterPhase = 1;
int get liteEncounterPhase => _liteEncounterPhase;

DateTime? _liteLastAutoSplitAt;
DateTime? _litePlayerDeathAt;
Map<String, double>? _litePlayerDeathPosition;
bool _litePlayerRevived = false;
bool _liteBossResetAfterDeath = false;

Int64? _liteBossUid;
Int64 _liteBossMaxHp = Int64.ZERO;
int? _liteBossTemplateId;
String _liteBossName = '';
double _liteBossLowestHpRatio = 1.0;
bool _liteBossEngaged = false;

bool get _liteHasEncounterData {
  return _fullDpsDatas.values.any((data) {
    return data.totalAttackDamage.toInt() > 0 ||
        data.totalHeal.toInt() > 0 ||
        data.totalTakenDamage.toInt() > 0;
  });
}

bool get _liteInsideDungeon {
  return _mapId > 0 && _lineId == 0;
}

void initializeLiteEncounterState() {
  SharedPreferences.getInstance().then((prefs) {
    _liteAutoResetLocked =
        prefs.getBool(_liteAutoResetPreference) ?? false;
    _scheduleNotify();
  });

  unawaited(EncounterHistoryService().deleteExpired());
}

void setLiteAutoResetLocked(bool value) {
  if (_liteAutoResetLocked == value) return;

  _liteAutoResetLocked = value;
  SharedPreferences.getInstance().then((prefs) {
    return prefs.setBool(_liteAutoResetPreference, value);
  });
  _scheduleNotify();
}

String _liteBaseProfessionName(int? professionId) {
  return switch (professionId) {
    1 => 'Stormblade',
    2 => 'Frost Mage',
    3 => 'Twin Striker',
    4 => 'Wind Knight',
    5 => 'Verdant Oracle',
    8 => 'Dorothy',
    9 => 'Heavy Guardian',
    10 => 'Dark Spirit Dance Ritual Blade',
    11 => 'Marksman',
    12 => 'Shield Knight',
    13 => 'Beat Performer',
    14 => 'Lucy',
    15 => 'Natsu',
    _ => 'Unknown',
  };
}

Map<String, dynamic>? _liteBuildEncounterSnapshot(
  String reason,
) {
  if (!_liteHasEncounterData) return null;

  final endedAt = DateTime.now();
  final startedAt = _combatStartTime ?? endedAt;
  final durationSeconds = endedAt
      .difference(startedAt)
      .inSeconds
      .clamp(0, 86400)
      .toInt();

  final players = _fullDpsDatas.entries
      .where((entry) => _playerInfoDatas.containsKey(entry.key))
      .map((entry) {
        final uid = entry.key;
        final data = entry.value;
        final info = _playerInfoDatas[uid]!;

        return <String, dynamic>{
          'uid': uid.toString(),
          'name': info.name ?? 'Unknown',
          'className':
              _liteSubProfessionNames[uid] ??
                  _liteBaseProfessionName(info.professionId),
          'professionId': info.professionId ?? 0,
          'combatPower': info.combatPower ?? 0,
          'illusionBreakingStrength':
              info.seasonStrength ?? 0,
          'isMe': uid == _currentPlayerUuid,
          'totalDamage': data.totalAttackDamage.toInt(),
          'dps': data.liteDps,
          'totalHealing': data.totalHeal.toInt(),
          'hps': data.liteHps,
          'totalTaken': data.totalTakenDamage.toInt(),
          'takenDps': data.liteTakenDps,
        };
      })
      .where((player) {
        return (player['totalDamage'] as int) > 0 ||
            (player['totalHealing'] as int) > 0 ||
            (player['totalTaken'] as int) > 0;
      })
      .toList(growable: false);

  if (players.isEmpty) return null;

  return <String, dynamic>{
    'startedAt': startedAt.millisecondsSinceEpoch,
    'endedAt': endedAt.millisecondsSinceEpoch,
    'durationSeconds': durationSeconds,
    'reason': reason,
    'mapId': _mapId,
    'channelId': _channelId,
    'lineId': _lineId,
    'phase': _liteEncounterPhase,
    'bossName': _liteBossName,
    'players': players,
  };
}

void _liteResetDetectionState() {
  _litePlayerDeathAt = null;
  _litePlayerDeathPosition = null;
  _litePlayerRevived = false;
  _liteBossResetAfterDeath = false;

  _liteBossUid = null;
  _liteBossMaxHp = Int64.ZERO;
  _liteBossTemplateId = null;
  _liteBossName = '';
  _liteBossLowestHpRatio = 1.0;
  _liteBossEngaged = false;
}

void _liteClearEncounterData() {
  _fullDpsDatas.clear();
  _liteSubProfessionNames.clear();
  _combatStartTime = null;
  _lastActionTime = null;
  _isCombatActive = false;
  _liteResetDetectionState();
  notifyListeners();
}

bool finishLiteEncounter(
  String reason, {
  bool manual = false,
}) {
  if (!manual && _liteAutoResetLocked) {
    return false;
  }

  final snapshot = _liteBuildEncounterSnapshot(reason);
  if (snapshot != null) {
    unawaited(
      EncounterHistoryService().saveEncounter(snapshot),
    );
  }

  _liteLastResetReason = reason;

  if (reason == 'new_phase') {
    _liteEncounterPhase += 1;
  } else {
    _liteEncounterPhase = 1;
  }

  _liteClearEncounterData();
  return true;
}

bool _liteRequestAutoSplit(String reason) {
  if (_liteAutoResetLocked || !_liteHasEncounterData) {
    return false;
  }

  final now = DateTime.now();
  final lastSplit = _liteLastAutoSplitAt;
  if (
    lastSplit != null &&
    now.difference(lastSplit) <
        const Duration(milliseconds: 1800)
  ) {
    return false;
  }

  _liteLastAutoSplitAt = now;
  return finishLiteEncounter(reason);
}

double _litePositionDistance(
  Map<String, double> left,
  Map<String, double> right,
) {
  final dx = (left['x'] ?? 0) - (right['x'] ?? 0);
  final dy = (left['y'] ?? 0) - (right['y'] ?? 0);
  final dz = (left['z'] ?? 0) - (right['z'] ?? 0);
  return math.sqrt(dx * dx + dy * dy + dz * dz);
}

bool get _liteRecentPlayerDeath {
  final deathAt = _litePlayerDeathAt;
  if (deathAt == null) return false;

  return DateTime.now().difference(deathAt) <
      const Duration(seconds: 45);
}

void _liteTryConfirmWipe() {
  if (
    _liteAutoResetLocked ||
    !_litePlayerRevived ||
    !_liteRecentPlayerDeath ||
    !_liteHasEncounterData
  ) {
    return;
  }

  final currentPosition =
      _playerInfoDatas[_currentPlayerUuid]?.position;
  final deathPosition = _litePlayerDeathPosition;

  final teleported =
      currentPosition != null &&
      deathPosition != null &&
      _litePositionDistance(
            currentPosition,
            deathPosition,
          ) >=
          10.0;

  if (teleported || _liteBossResetAfterDeath) {
    _liteRequestAutoSplit('wipe');
  }
}

bool _liteIsBossCandidate(Int64 maxHp) {
  if (maxHp <= Int64.ZERO || !_liteInsideDungeon) {
    return false;
  }

  final ownMaxHp =
      _playerInfoDatas[_currentPlayerUuid]?.maxHp ??
      Int64.ZERO;
  final threshold = ownMaxHp > Int64.ZERO
      ? Int64(ownMaxHp.toInt() * 10)
      : Int64(2000000);

  return maxHp >= threshold;
}

void _liteConsiderBoss(Int64 uid, Int64 maxHp) {
  final monster = _monsterInfoDatas[uid];
  if (
    monster == null ||
    monster.isSummon ||
    !_liteIsBossCandidate(maxHp)
  ) {
    return;
  }

  final oldBossUid = _liteBossUid;
  final shouldSplitForNewBoss =
      oldBossUid != null &&
      oldBossUid != uid &&
      _liteBossEngaged &&
      _liteHasEncounterData;

  final shouldSplitTrashToBoss =
      oldBossUid == null &&
      _liteHasEncounterData &&
      _combatStartTime != null &&
      DateTime.now().difference(_combatStartTime!) >
          const Duration(seconds: 3);

  if (shouldSplitForNewBoss || shouldSplitTrashToBoss) {
    _liteRequestAutoSplit('new_phase');
  }

  _liteBossUid = uid;
  _liteBossMaxHp = maxHp;
  _liteBossTemplateId = monster.templateId;
  _liteBossName = monster.name ?? '';
  _liteBossLowestHpRatio = 1.0;
  _liteBossEngaged = false;
}

void _liteMarkBossEngaged(Int64 targetUid) {
  if (_liteBossUid == targetUid) {
    _liteBossEngaged = true;
  }
}

void _liteObserveBossHp(
  Int64 uid,
  Int64? oldHp,
  Int64 newHp,
) {
  if (
    _liteBossUid != uid ||
    _liteBossMaxHp <= Int64.ZERO
  ) {
    return;
  }

  final newRatio =
      newHp.toDouble() / _liteBossMaxHp.toDouble();
  final oldRatio = oldHp == null
      ? newRatio
      : oldHp.toDouble() / _liteBossMaxHp.toDouble();

  if (newRatio < _liteBossLowestHpRatio) {
    _liteBossLowestHpRatio = newRatio;
  }

  final resetToFull =
      _liteBossEngaged &&
      oldRatio < 0.70 &&
      newRatio > 0.93 &&
      newRatio - oldRatio > 0.25;

  if (!resetToFull) return;

  final bossTemplateId = _liteBossTemplateId;
  final bossName = _liteBossName;
  final bossMaxHp = _liteBossMaxHp;

  if (_liteRecentPlayerDeath) {
    _liteBossResetAfterDeath = true;
    _liteTryConfirmWipe();
    return;
  }

  if (_liteRequestAutoSplit('new_phase')) {
    _liteBossUid = uid;
    _liteBossMaxHp = bossMaxHp;
    _liteBossTemplateId = bossTemplateId;
    _liteBossName = bossName;
    _liteBossLowestHpRatio = newRatio;
    _liteBossEngaged = false;
  }
}

/// Scene, line, and channel changes are direct packet signals.
/// Wipe and phase detection use conservative player/boss-state rules
/// because BlueMeter Mobile does not decode ZDPS's objective stream.
void onSceneUpdate({
  int? lineId,
  int? mapId,
  int? channelId,
}) {
  final oldLineId = _lineId;
  final oldMapId = _mapId;
  final oldChannelId = _channelId;

  final receivedLineId = lineId != null;
  final receivedMapId = mapId != null && mapId > 0;
  final receivedChannelId =
      channelId != null && channelId > 0;

  final dungeonEntry =
      receivedLineId &&
      lineId == 0 &&
      oldLineId > 0;

  final dungeonExit =
      receivedLineId &&
      lineId! > 0 &&
      oldLineId == 0;

  final lineChanged =
      receivedLineId &&
      oldLineId != lineId &&
      !dungeonEntry &&
      !dungeonExit;

  final mapChanged =
      receivedMapId &&
      oldMapId > 0 &&
      oldMapId != mapId;

  final channelChanged =
      receivedChannelId &&
      oldChannelId > 0 &&
      oldChannelId != channelId;

  String? splitReason;
  if (dungeonEntry) {
    splitReason = 'new_dungeon';
  } else if (dungeonExit) {
    splitReason = 'map_change';
  } else if (mapChanged) {
    splitReason = 'map_change';
  } else if (channelChanged) {
    splitReason = 'channel_change';
  } else if (lineChanged) {
    splitReason = 'line_change';
  }

  // Save/reset before replacing IDs, so history keeps the old scene.
  if (splitReason != null && !_liteAutoResetLocked) {
    _liteRequestAutoSplit(splitReason);
    _playerInfoDatas.removeWhere(
      (uid, _) => uid != _currentPlayerUuid,
    );
  }

  if (receivedMapId) {
    _mapId = mapId!;
  }
  if (receivedChannelId) {
    _channelId = channelId!;
  }
  if (receivedLineId) {
    _lineId = lineId!;
  }

  if (splitReason == null) return;

  // Refresh scene caches even while auto reset is locked.
  _monsterInfoDatas.clear();
  _deadMonsters.clear();
  _liteResetDetectionState();
  notifyListeners();
}
"""
    storage_text = replace_between(
        storage_text,
        "  /// Called when SyncContainerData provides scene info.",
        "  void clearMonsters() {",
        lite_scene_and_state,
        "Lite scene and encounter state",
    )

    lite_action_method = r"""
void _onAction() {
  final now = DateTime.now();

  // Keep the current encounter across ordinary combat downtime. A real
  // scene, wipe, phase, or manual event decides when the totals are split.
  if (!_isCombatActive) {
    _isCombatActive = true;
    _combatStartTime ??= now;
  }

  _lastActionTime = now;
}
"""
    storage_text = replace_between(
        storage_text,
        "  void _onAction() {",
        "  Map<Int64, PlayerInfo> get playerInfoDatas",
        lite_action_method,
        "Lite encounter action method",
    )

    lite_reset_method = r"""
void reset({bool resetTimer = true}) {
  _fullDpsDatas.clear();
  _liteSubProfessionNames.clear();

  if (resetTimer) {
    _combatStartTime = null;
    _lastActionTime = null;
    _isCombatActive = false;
    _liteResetDetectionState();
    _liteEncounterPhase = 1;
  }

  notifyListeners();
}
"""
    storage_text = replace_between(
        storage_text,
        "  void reset({bool resetTimer = true}) {",
        "  // --- Player Info Setters ---",
        lite_reset_method,
        "Lite reset method",
    )

    lite_player_hp = r"""
void setPlayerHp(Int64 uid, int value) {
  ensurePlayer(uid);

  final info = _playerInfoDatas[uid]!;
  final oldValue = info.hp?.toInt();
  info.hp = Int64(value);

  if (uid == _currentPlayerUuid && _liteHasEncounterData) {
    final died =
        value <= 0 &&
        (oldValue == null || oldValue > 0);

    if (died) {
      _litePlayerDeathAt = DateTime.now();
      _litePlayerDeathPosition =
          info.position == null
              ? null
              : Map<String, double>.from(info.position!);
      _litePlayerRevived = false;
      _liteBossResetAfterDeath = false;
    }

    final revived =
        value > 0 &&
        oldValue != null &&
        oldValue <= 0 &&
        _liteRecentPlayerDeath;

    if (revived) {
      _litePlayerRevived = true;
      _liteTryConfirmWipe();
    }
  }

  _scheduleNotify();
}
"""
    storage_text = replace_between(
        storage_text,
        "  void setPlayerHp(Int64 uid, int value) {",
        "  void setPlayerMaxHp(Int64 uid, int value) {",
        lite_player_hp,
        "Lite player HP wipe detection",
    )

    lite_player_position = r"""
void setPlayerPosition(
  Int64 uid,
  Map<String, double> position,
) {
  ensurePlayer(uid);
  _playerInfoDatas[uid]!.position = position;

  if (uid == _currentPlayerUuid) {
    _liteTryConfirmWipe();
  }

  _scheduleNotify();
}
"""
    storage_text = replace_between(
        storage_text,
        "  void setPlayerPosition(Int64 uid, Map<String, double> position) {",
        "  void setPlayerRotation(Int64 uid, Map<String, double> rotation) {",
        lite_player_position,
        "Lite player teleport detection",
    )

    lite_monster_template = r"""
void setMonsterTemplateId(Int64 uid, int id) {
  if (!ensureMonster(uid)) return;

  final monster = _monsterInfoDatas[uid]!;
  monster.templateId = id;

  if (monster.name == null || monster.name!.isEmpty) {
    final name = MonsterNameService().getName(id);
    if (name != null) {
      monster.name = name;
    }
  }

  if (_liteBossUid == uid) {
    _liteBossTemplateId = id;
    _liteBossName = monster.name ?? _liteBossName;
  }

  _scheduleNotify();
}
"""
    storage_text = replace_between(
        storage_text,
        "  void setMonsterTemplateId(Int64 uid, int id) {",
        "  void setMonsterName(Int64 uid, String name) {",
        lite_monster_template,
        "Lite boss template tracking",
    )

    lite_monster_name = r"""
void setMonsterName(Int64 uid, String name) {
  if (!ensureMonster(uid)) return;

  _monsterInfoDatas[uid]!.name = name;
  if (_liteBossUid == uid) {
    _liteBossName = name;
  }

  _scheduleNotify();
}
"""
    storage_text = replace_between(
        storage_text,
        "  void setMonsterName(Int64 uid, String name) {",
        "  void setMonsterLevel(Int64 uid, int level) {",
        lite_monster_name,
        "Lite boss name tracking",
    )

    lite_monster_hp = r"""
void setMonsterHp(Int64 uid, Int64 hp) {
  if (!ensureMonster(uid)) return;

  final monster = _monsterInfoDatas[uid]!;
  final oldHp = monster.hp;
  monster.hp = hp;

  _liteObserveBossHp(uid, oldHp, hp);
  _scheduleNotify();
}
"""
    storage_text = replace_between(
        storage_text,
        "  void setMonsterHp(Int64 uid, Int64 hp) {",
        "  void decreaseMonsterHp(Int64 uid, Int64 damage) {",
        lite_monster_hp,
        "Lite boss HP reset detection",
    )

    lite_decrease_monster_hp = r"""
void decreaseMonsterHp(Int64 uid, Int64 damage) {
  final monster = _monsterInfoDatas[uid];
  if (monster == null) return;

  final currentHp = monster.hp ?? Int64.ZERO;
  if (currentHp <= Int64.ZERO) return;

  var newHp = currentHp - damage;
  if (newHp < Int64.ZERO) {
    newHp = Int64.ZERO;
  }

  monster.hp = newHp;
  _liteObserveBossHp(uid, currentHp, newHp);
  _scheduleNotify();
}
"""
    storage_text = replace_between(
        storage_text,
        "  void decreaseMonsterHp(Int64 uid, Int64 damage) {",
        "  void setMonsterMaxHp(Int64 uid, Int64 maxHp) {",
        lite_decrease_monster_hp,
        "Lite boss damage observation",
    )

    lite_monster_max_hp = r"""
void setMonsterMaxHp(Int64 uid, Int64 maxHp) {
  if (!ensureMonster(uid)) return;

  _monsterInfoDatas[uid]!.maxHp = maxHp;
  _liteConsiderBoss(uid, maxHp);
  _scheduleNotify();
}
"""
    storage_text = replace_between(
        storage_text,
        "  void setMonsterMaxHp(Int64 uid, Int64 maxHp) {",
        "  void setMonsterPosition(Int64 uid, Map<String, double> position) {",
        lite_monster_max_hp,
        "Lite boss candidate detection",
    )

    data_storage.write_text(storage_text, encoding="utf-8")

    dart = main_dart.read_text(encoding="utf-8")


    dart = replace_once(
        dart,
        (
            "import 'package:flutter_overlay_window/"
            "flutter_overlay_window.dart';\n"
        ),
        (
            "import 'package:flutter_overlay_window/"
            "flutter_overlay_window.dart';\n"
            "import 'package:shared_preferences/shared_preferences.dart';\n"
            "import 'package:url_launcher/url_launcher.dart';\n"
            "import 'core/services/encounter_history_service.dart';\n"
            "import 'views/encounter_history_view.dart';\n"
        ),
        "Lite persistence and URL imports",
    )

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


    dart = replace_once(
        dart,
        """  await SystemChrome.setPreferredOrientations([
    DeviceOrientation.landscapeLeft,
    DeviceOrientation.landscapeRight,
  ]);""",
        """  await SystemChrome.setPreferredOrientations([
    DeviceOrientation.portraitUp,
    DeviceOrientation.portraitDown,
  ]);""",
        "portrait main-app orientation",
    )


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
        "// Lite: update the Damage, Healing, or Tanking overlay once per second",
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
  final Map<String, int> _liteSeasonStrengthCache = {};

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
        .where((entry) {
          final data = entry.value;
          final hasMetric =
              data.totalAttackDamage.toInt() > 0 ||
              data.totalHeal.toInt() > 0 ||
              data.totalTakenDamage.toInt() > 0;
          return hasMetric && storage.getPlayerInfoSync(entry.key) != null;
        })
        .map((entry) {
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
        })
        .toList(growable: false);

    FlutterOverlayWindow.shareData({
      'players': players,
      'combatTime': storage.currentCombatDuration.inSeconds,
      'autoResetLocked': storage.liteAutoResetLocked,
      'lastResetReason': storage.liteLastResetReason,
      'phase': storage.liteEncounterPhase,
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


    home_state_start = dart.find(
        "class _HomePageState extends State<HomePage>"
    )
    if home_state_start == -1:
        fail("could not locate HomePage state")

    channel_marker = """  static const upstreamEventChannel = EventChannel(
    'com.bluemeter.mobile/upstream_stream',
  );
"""
    channel_index = dart.find(channel_marker, home_state_start)
    if channel_index == -1:
        fail("could not locate HomePage channel constants")

    lite_constants = f"""  static const Map<String, String> _liteClientLabels = {{
    'sea.haoplay.game.gp.bpsr': 'HaoPlay SEA',
    'com.bpsr.apj': 'A Plus Japan / Global',
    'tw.haoplay.game.gp.xhgm': 'Taiwan / Hong Kong / Macau',
    'asia.xdg.game.gp.bpsr': 'X.D. regional client',
  }};

  static const String _liteVersion = '{lite_version_name}';
  static const String _liteUpstreamCommit = '{upstream_commit}';

"""
    channel_insert_at = channel_index + len(channel_marker)
    dart = (
        dart[:channel_insert_at]
        + lite_constants
        + dart[channel_insert_at:]
    )

    vpn_field = "  bool _isVpnRunning = false;"
    vpn_field_index = dart.find(vpn_field, home_state_start)
    if vpn_field_index == -1:
        fail("could not locate HomePage VPN state field")

    vpn_field_insert_at = vpn_field_index + len(vpn_field)
    dart = (
        dart[:vpn_field_insert_at]
        + "\n"
        + "  List<String> _installedSupportedPackages = const [];\n"
        + "  bool _clientCheckComplete = false;\n"
        + "  bool _clientCheckFailed = false;"
        + dart[vpn_field_insert_at:]
    )

    home_init_start = dart.find(
        "  void initState() {",
        home_state_start,
    )
    home_super = dart.find(
        "    super.initState();",
        home_init_start,
    )
    if home_init_start == -1 or home_super == -1:
        fail("could not locate HomePage initState")

    home_super_end = home_super + len("    super.initState();")
    dart = (
        dart[:home_super_end]
        + "\n    _refreshSupportedClients();"
        + "\n    DataStorage().initializeLiteEncounterState();"
        + "\n    unawaited(EncounterHistoryService().deleteExpired());"
        + dart[home_super_end:]
    )


    dart = replace_once(
        dart,
        "        DataStorage().reset();",
        """        DataStorage().finishLiteEncounter(
          'manual_reset',
          manual: true,
        );""",
        "manual reset history command",
    )
    dart = replace_once(
        dart,
        """      } else if (message is Map && message.containsKey('selectPlayer')) {""",
        """      } else if (
        message is Map &&
        message.containsKey('autoResetLocked')
      ) {
        final locked = message['autoResetLocked'] == true;
        DataStorage().setLiteAutoResetLocked(locked);
        _updateOverlay();
      } else if (message is Map && message.containsKey('selectPlayer')) {""",
        "auto-reset lock overlay command",
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

    overlay_start_method = dart.find(
        "  Future<void> _startOverlay() async {",
        home_state_start,
    )
    overlay_end_method = dart.find(
        "  Future<void> _startVpn() async {",
        overlay_start_method,
    )
    if (
        overlay_start_method == -1
        or overlay_end_method == -1
        or overlay_end_method <= overlay_start_method
    ):
        fail("could not locate overlay startup method")

    lite_start_overlay = r"""
  Future<bool> _startOverlay() async {
    try {
      if (!await FlutterOverlayWindow.isPermissionGranted()) {
        await FlutterOverlayWindow.requestPermission();
      }

      if (!await FlutterOverlayWindow.isPermissionGranted()) {
        return false;
      }

      // isActive() can remain true for a stale or invisible overlay engine.
      // Always recreate the window so Start is a reliable recovery action.
      if (await FlutterOverlayWindow.isActive()) {
        await FlutterOverlayWindow.closeOverlay();
        await Future<void>.delayed(const Duration(milliseconds: 250));
      }

      await FlutterOverlayWindow.showOverlay(
        enableDrag: false,
        overlayTitle: 'BlueMeter Lite',
        overlayContent: 'Lite DPS Meter Active',
        flag: OverlayFlag.defaultFlag,
        alignment: OverlayAlignment.topLeft,
        visibility: NotificationVisibility.visibilityPublic,
        positionGravity: PositionGravity.none,
        height: 180,
        width: 360,
      );

      await Future<void>.delayed(const Duration(milliseconds: 300));

      if (!await FlutterOverlayWindow.isActive()) {
        return false;
      }

      // First make the window visibly recoverable. The overlay isolate then
      // restores its saved, screen-clamped layout after it is fully attached.
      await FlutterOverlayWindow.moveOverlay(
        const OverlayPosition(8, 80),
      );
      return true;
    } catch (error) {
      _logger.error(
        'Failed to start overlay',
        error: error,
      );
      return false;
    }
  }

"""
    dart = (
        dart[:overlay_start_method]
        + textwrap.dedent(lite_start_overlay)
        + dart[overlay_end_method:]
    )


    home_tail_start = dart.find(
        "  Future<void> _startVpn() async {",
        home_state_start,
    )
    if home_tail_start == -1:
        fail("could not locate HomePage service methods")

    lite_home_tail = r"""
  Future<List<String>> _refreshSupportedClients() async {
    try {
      final installed =
          await platform.invokeListMethod<String>(
            'getInstalledSupportedPackages',
          ) ??
          const <String>[];

      if (mounted) {
        setState(() {
          _installedSupportedPackages =
              List<String>.from(installed, growable: false);
          _clientCheckComplete = true;
          _clientCheckFailed = false;
        });
      }

      return installed;
    } on PlatformException catch (error) {
      _logger.error(
        'Could not check installed BPSR clients',
        error: error.message,
      );

      if (mounted) {
        setState(() {
          _installedSupportedPackages = const [];
          _clientCheckComplete = true;
          _clientCheckFailed = true;
        });
      }

      return const <String>[];
    }
  }

  String _clientName(String packageName) {
    return _liteClientLabels[packageName] ?? packageName;
  }

  Future<void> _showUnsupportedClientDialog() async {
    if (!mounted) return;

    await showDialog<void>(
      context: context,
      builder: (dialogContext) {
        return AlertDialog(
          icon: const Icon(Icons.phone_android_rounded),
          title: const Text('No supported BPSR client found'),
          content: const Text(
            'Install one of these Android clients before starting the meter:\n\n'
            '• HaoPlay SEA\n'
            '• A Plus Japan / Global\n'
            '• Taiwan / Hong Kong / Macau\n'
            '• X.D. regional client',
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(dialogContext).pop(),
              child: const Text('OK'),
            ),
          ],
        );
      },
    );
  }

  Future<void> _openExternalUrl(String rawUrl) async {
    final uri = Uri.parse(rawUrl);
    final opened = await launchUrl(
      uri,
      mode: LaunchMode.externalApplication,
    );

    if (!opened && mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Could not open the link.'),
        ),
      );
    }
  }

  Future<void> _showAboutDialog() async {
    if (!mounted) return;

    await showDialog<void>(
      context: context,
      builder: (dialogContext) {
        return AlertDialog(
          icon: const Icon(Icons.speed_rounded),
          title: const Text('About BlueMeter Lite'),
          content: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 520),
            child: SingleChildScrollView(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(
                    'BlueMeter Lite $_liteVersion',
                    style: TextStyle(fontWeight: FontWeight.w700),
                  ),
                  SizedBox(height: 3),
                  Text(
                    'by MrEz',
                    style: TextStyle(fontWeight: FontWeight.w600),
                  ),
                  SizedBox(height: 10),
                  Text(
                    'A lightweight Android DPS overlay for '
                    'Blue Protocol: Star Resonance.',
                  ),
                  SizedBox(height: 14),
                  Text(
                    'Privacy',
                    style: TextStyle(fontWeight: FontWeight.w700),
                  ),
                  SizedBox(height: 4),
                  Text(
                    'Supported BPSR traffic is processed locally on this '
                    'device. BlueMeter Lite adds no advertising, analytics, '
                    'accounts or project-operated relay server.',
                  ),
                  SizedBox(height: 14),
                  Text(
                    'Open source',
                    style: TextStyle(fontWeight: FontWeight.w700),
                  ),
                  SizedBox(height: 4),
                  Text(
                    'License: GNU AGPL-3.0\n'
                    'Based on BlueMeter Mobile\n'
                    'Upstream commit: $_liteUpstreamCommit',
                  ),
                  SizedBox(height: 14),
                  Text(
                    'Unofficial community project. Not affiliated with the '
                    'game developers or publishers.',
                  ),
                ],
              ),
            ),
          ),
          actions: [
            TextButton(
              onPressed: () => _openExternalUrl(
                'https://github.com/Zudin987/BPSR-BlueMeter-Lite',
              ),
              child: const Text('GitHub'),
            ),
            TextButton(
              onPressed: () => _openExternalUrl(
                'https://github.com/Zudin987/'
                'BPSR-BlueMeter-Lite/blob/main/PRIVACY.md',
              ),
              child: const Text('Privacy'),
            ),
            TextButton(
              onPressed: () => _openExternalUrl(
                'https://github.com/Zudin987/'
                'BPSR-BlueMeter-Lite/blob/main/LICENSE',
              ),
              child: const Text('License'),
            ),
            TextButton(
              onPressed: () => Navigator.of(dialogContext).pop(),
              child: const Text('Close'),
            ),
          ],
        );
      },
    );
  }

  Future<void> _startVpn() async {
    try {
      await platform.invokeMethod('startVpn');
      if (!mounted) return;

      setState(() {
        _isVpnRunning = true;
      });

      _packetSubscription = eventChannel.receiveBroadcastStream().listen(
        _onPacketData,
      );
      _upstreamSubscription =
          upstreamEventChannel.receiveBroadcastStream().listen(
            _onUpstreamData,
          );
    } on PlatformException catch (error) {
      _logger.error('Failed to start VPN', error: error.message);
    }
  }

  Future<void> _stopVpn() async {
    try {
      DataStorage().finishLiteEncounter(
        'meter_stopped',
        manual: true,
      );
      await platform.invokeMethod('stopVpn');
      if (!mounted) return;

      setState(() {
        _isVpnRunning = false;
      });

      await _packetSubscription?.cancel();
      await _upstreamSubscription?.cancel();
      _packetSubscription = null;
      _upstreamSubscription = null;
    } on PlatformException catch (error) {
      _logger.error('Failed to stop VPN', error: error.message);
    }
  }

  Future<void> _toggleService() async {
    if (_isVpnRunning) {
      await _stopVpn();
      await FlutterOverlayWindow.closeOverlay();
      return;
    }

    final installedClients = await _refreshSupportedClients();
    if (installedClients.isEmpty) {
      await _showUnsupportedClientDialog();
      return;
    }

    final overlayPermission =
        await FlutterOverlayWindow.isPermissionGranted();
    if (!overlayPermission) {
      await FlutterOverlayWindow.requestPermission();
      return;
    }

    final overlayStarted = await _startOverlay();
    if (!overlayStarted) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text(
              'Could not open the overlay. Check Display over other apps permission.',
            ),
          ),
        );
      }
      return;
    }

    await _startVpn();
  }

  @override
  Widget build(BuildContext context) {
    final colorScheme = Theme.of(context).colorScheme;
    final detectedNames = _installedSupportedPackages
        .map(_clientName)
        .join(', ');

    final String clientStatus;
    final Color statusColor;
    final IconData statusIcon;

    if (!_clientCheckComplete) {
      clientStatus = 'Checking installed BPSR client…';
      statusColor = colorScheme.secondary;
      statusIcon = Icons.hourglass_top_rounded;
    } else if (_clientCheckFailed) {
      clientStatus = 'Could not check installed clients.';
      statusColor = colorScheme.error;
      statusIcon = Icons.error_outline_rounded;
    } else if (_installedSupportedPackages.isEmpty) {
      clientStatus = 'No supported BPSR client detected';
      statusColor = colorScheme.error;
      statusIcon = Icons.warning_amber_rounded;
    } else {
      clientStatus = 'Detected: $detectedNames';
      statusColor = Colors.greenAccent.shade400;
      statusIcon = Icons.check_circle_outline_rounded;
    }

    return Scaffold(
      appBar: AppBar(
        title: const Text('BlueMeter Lite'),
        actions: [
          IconButton(
            tooltip: 'About',
            onPressed: _showAboutDialog,
            icon: const Icon(Icons.info_outline_rounded),
          ),
        ],
      ),
      body: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(24),
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 620),
              child: Card(
                clipBehavior: Clip.antiAlias,
                child: Padding(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 28,
                    vertical: 24,
                  ),
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Icon(
                        Icons.speed_rounded,
                        size: 54,
                        color: colorScheme.primary,
                      ),
                      const SizedBox(height: 10),
                      Text(
                        'BlueMeter Lite',
                        style: Theme.of(context).textTheme.headlineSmall
                            ?.copyWith(fontWeight: FontWeight.w800),
                      ),
                      const SizedBox(height: 2),
                      Text(
                        'by MrEz',
                        style: Theme.of(context).textTheme.labelLarge
                            ?.copyWith(
                              color: colorScheme.primary,
                              fontWeight: FontWeight.w600,
                            ),
                      ),
                      const SizedBox(height: 7),
                      Text(
                        'Lightweight BPSR DPS overlay — no PC required.',
                        textAlign: TextAlign.center,
                        style: Theme.of(context).textTheme.bodyMedium,
                      ),
                      const SizedBox(height: 18),
                      Container(
                        width: double.infinity,
                        padding: const EdgeInsets.symmetric(
                          horizontal: 14,
                          vertical: 11,
                        ),
                        decoration: BoxDecoration(
                          color: statusColor.withValues(alpha: 0.10),
                          border: Border.all(
                            color: statusColor.withValues(alpha: 0.45),
                          ),
                          borderRadius: BorderRadius.circular(10),
                        ),
                        child: Row(
                          children: [
                            Icon(
                              statusIcon,
                              size: 20,
                              color: statusColor,
                            ),
                            const SizedBox(width: 10),
                            Expanded(
                              child: Text(
                                clientStatus,
                                style: TextStyle(
                                  color: statusColor,
                                  fontWeight: FontWeight.w600,
                                ),
                              ),
                            ),
                          ],
                        ),
                      ),
                      const SizedBox(height: 20),
                      FilledButton.icon(
                        onPressed: _toggleService,
                        icon: Icon(
                          _isVpnRunning
                              ? Icons.stop_circle_outlined
                              : Icons.play_circle_outline_rounded,
                        ),
                        label: Text(
                          _isVpnRunning
                              ? 'Stop DPS Meter'
                              : 'Start DPS Meter',
                        ),
                        style: FilledButton.styleFrom(
                          minimumSize: const Size(250, 52),
                          backgroundColor: _isVpnRunning
                              ? colorScheme.error
                              : null,
                        ),
                      ),
                      const SizedBox(height: 10),
                      Text(
                        _isVpnRunning
                            ? 'The local VPN and overlay are active.'
                            : 'Android will request overlay and VPN permission.',
                        textAlign: TextAlign.center,
                        style: Theme.of(context).textTheme.bodySmall,
                      ),
                      const SizedBox(height: 4),
                      OutlinedButton.icon(
                        onPressed: () {
                          Navigator.of(context).push(
                            MaterialPageRoute<void>(
                              builder: (_) =>
                                  const EncounterHistoryView(),
                            ),
                          );
                        },
                        icon: const Icon(Icons.history_rounded),
                        label: const Text('Encounter history'),
                      ),
                      const SizedBox(height: 8),
                      TextButton.icon(
                        onPressed: _showAboutDialog,
                        icon: const Icon(Icons.info_outline_rounded),
                        label: const Text('About and privacy'),
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
"""
    lite_home_tail = textwrap.dedent(lite_home_tail).lstrip()
    dart = dart[:home_tail_start] + lite_home_tail.rstrip() + "\n}\n"

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
        f"version: {lite_version_name}+{lite_version_code}",
        "pubspec version",
    )
    pubspec.write_text(yaml, encoding="utf-8")

    print("BlueMeter Lite patch applied successfully.")
    print(f"Patched source: {upstream}")


if __name__ == "__main__":
    main()
