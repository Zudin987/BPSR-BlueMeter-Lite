#!/usr/bin/env python3
"""Apply BlueMeter Lite's ultra-low-impact runtime optimizations.

Runs against the generated pinned-upstream source after the existing Lite,
location and overlay-bridge patches. Method replacements intentionally key on
stable method names rather than exact whitespace so the build kit remains
reproducible across harmless formatting changes.
"""

from __future__ import annotations

import re
import shutil
import sys
import textwrap
from pathlib import Path


def fail(message: str) -> None:
    raise SystemExit(f"BlueMeter Lite engine optimization failed: {message}")


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        fail(f"expected one {label}, found {count}")
    return text.replace(old, new, 1)


def replace_method_range(
    text: str,
    start_token: str,
    next_token: str,
    replacement: str,
    label: str,
) -> str:
    start_token_index = text.find(start_token)
    if start_token_index == -1:
        fail(f"could not find start of {label}: {start_token}")
    start = text.rfind("\n", 0, start_token_index) + 1

    next_token_index = text.find(next_token, start_token_index + len(start_token))
    if next_token_index == -1:
        fail(f"could not find end of {label}: {next_token}")
    end = text.rfind("\n", 0, next_token_index) + 1

    return (
        text[:start]
        + textwrap.dedent(replacement).strip("\n")
        + "\n\n"
        + text[end:]
    )


def main() -> None:
    if len(sys.argv) != 2:
        fail("usage: apply_engine_optimizations.py <upstream-directory>")

    root = Path(sys.argv[1]).resolve()
    patch = Path(__file__).resolve().parent
    kotlin_root = (
        root
        / "android/app/src/main/kotlin/com/bluemeter/bluemeter_mobile"
    )

    replacements = {
        patch / "PacketCaptureService.kt": kotlin_root / "PacketCaptureService.kt",
        patch / "TcpProxy.kt": kotlin_root / "TcpProxy.kt",
        patch / "MainActivityLite.kt": kotlin_root / "MainActivity.kt",
        patch / "PacketEventBus.kt": kotlin_root / "PacketEventBus.kt",
        patch / "PacketAnalyzerV2.dart": root / "lib/core/analyze/packet_analyzer_v2.dart",
        patch / "DatabaseService.dart": root / "lib/core/services/database_service.dart",
        patch / "EncounterHistoryServiceLite.dart": (
            root / "lib/core/services/encounter_history_service.dart"
        ),
        patch / "lite_performance_test.dart": root / "test/lite_performance_test.dart",
    }

    for source, destination in replacements.items():
        if not source.exists():
            fail(f"missing patch source: {source}")
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)

    old_widget_test = root / "test/widget_test.dart"
    if old_widget_test.exists():
        old_widget_test.unlink()

    # ------------------------------------------------------------------
    # Native/Dart packet parsing: safe pooling + low-copy slices.
    # ------------------------------------------------------------------
    packet_path = kotlin_root / "Packet.kt"
    packet_text = packet_path.read_text(encoding="utf-8")
    packet_text = replace_once(
        packet_text,
        """    private fun parse() {
        val buffer = backingBuffer ?: return
        buffer.position(0)
""",
        """    private fun parse() {
        // Packet instances are pooled. Reset every parsed field so a short or
        // malformed packet can never inherit metadata from a previous packet.
        ipVersion = 0
        ipHeaderLength = 0
        protocol = 0
        sourceIpInt = 0
        destIpInt = 0
        sourcePort = 0
        destPort = 0
        seqNum = 0
        ackNum = 0
        flags = 0
        tcpHeaderLength = 0
        payloadSize = 0
        isTcp = false
        isUdp = false

        val buffer = backingBuffer ?: return
        buffer.position(0)
""",
        "pooled Packet field reset",
    )
    packet_path.write_text(packet_text, encoding="utf-8")

    message_path = root / "lib/core/analyze/message_analyzer_v2.dart"
    message_text = message_path.read_text(encoding="utf-8")
    message_text = replace_once(
        message_text,
        "    Uint8List protobuf = data.sublist(12);",
        "    Uint8List protobuf = Uint8List.sublistView(data, 12);",
        "Return payload zero-copy view",
    )
    message_text = replace_once(
        message_text,
        """      final body = streamData.sublist(offset + 4, offset + packetSize);
      process(body);
""",
        """      final body = Uint8List.sublistView(
        streamData,
        offset + 4,
        offset + packetSize,
      );
      process(body);
""",
        "FrameDown packet zero-copy view",
    )
    message_path.write_text(message_text, encoding="utf-8")

    # ------------------------------------------------------------------
    # Combat storage: one dirty notification per burst, no NPC player-DB
    # candidates, bounded early-identity staging and lower wall-clock churn.
    # ------------------------------------------------------------------
    storage_path = root / "lib/core/state/data_storage.dart"
    storage = storage_path.read_text(encoding="utf-8")

    storage = replace_once(
        storage,
        """  // Batched notification to avoid excessive rebuilds
  bool _notifyScheduled = false;
  void _scheduleNotify() {
    if (!_notifyScheduled) {
      _notifyScheduled = true;
      Future.microtask(() {
        _notifyScheduled = false;
        notifyListeners();
      });
    }
  }
""",
        """  // One-shot dirty signal: no permanent polling timer exists.
  Timer? _notifyTimer;
  void _scheduleNotify() {
    _notifyTimer ??= Timer(const Duration(seconds: 2), () {
      _notifyTimer = null;
      notifyListeners();
    });
  }
""",
        "DataStorage dirty notification throttle",
    )

    storage, count = re.subn(
        r"^(?P<indent>[ \t]*)final Map<Int64, String> "
        r"_liteSubProfessionNames = \{\};$",
        r"\g<indent>final Map<Int64, String> _liteSubProfessionNames = {};\n"
        r"\g<indent>final Map<Int64, DpsData> _litePendingCombat = {};\n"
        r"\g<indent>static const int _litePendingCombatLimit = 64;",
        storage,
        count=1,
        flags=re.MULTILINE,
    )
    if count != 1:
        fail(f"expected one pending combat insertion point, found {count}")

    optimized_detection = r"""
  void _liteDetectSubProfession(
    Int64 uid,
    String? skillId,
  ) {
    if (_liteSubProfessionNames.containsKey(uid)) return;

    final detectedSubProfession = _liteSubProfessionFromSkillId(skillId);
    if (detectedSubProfession != null) {
      _liteSubProfessionNames[uid] = detectedSubProfession;
    }
  }

  DpsData? _liteMetricDataForUid(Int64 uid) {
    if (_monsterInfoDatas.containsKey(uid)) return null;

    if (uid == _currentPlayerUuid || _playerInfoDatas.containsKey(uid)) {
      return getOrCreateDpsData(uid);
    }

    // Combat can arrive before a nearby-player identity packet. Keep only a
    // small bounded staging set; promote confirmed players and discard monsters.
    var pending = _litePendingCombat[uid];
    if (pending != null) return pending;

    if (_litePendingCombat.length >= _litePendingCombatLimit) {
      _litePendingCombat.remove(_litePendingCombat.keys.first);
    }
    pending = DpsData(uid: uid);
    _litePendingCombat[uid] = pending;
    return pending;
  }

  void _litePromotePendingCombat(Int64 uid) {
    final pending = _litePendingCombat.remove(uid);
    if (pending == null) return;

    final live = getOrCreateDpsData(uid);
    live.totalAttackDamage += pending.totalAttackDamage;
    live.totalHeal += pending.totalHeal;
    live.totalTakenDamage += pending.totalTakenDamage;

    if (pending.liteDamageStartTick != null &&
        (live.liteDamageStartTick == null ||
            pending.liteDamageStartTick! < live.liteDamageStartTick!)) {
      live.liteDamageStartTick = pending.liteDamageStartTick;
    }
    if (pending.liteDamageLastTick > live.liteDamageLastTick) {
      live.liteDamageLastTick = pending.liteDamageLastTick;
    }

    if (pending.liteHealingStartTick != null &&
        (live.liteHealingStartTick == null ||
            pending.liteHealingStartTick! < live.liteHealingStartTick!)) {
      live.liteHealingStartTick = pending.liteHealingStartTick;
    }
    if (pending.liteHealingLastTick > live.liteHealingLastTick) {
      live.liteHealingLastTick = pending.liteHealingLastTick;
    }

    if (pending.liteTakenStartTick != null &&
        (live.liteTakenStartTick == null ||
            pending.liteTakenStartTick! < live.liteTakenStartTick!)) {
      live.liteTakenStartTick = pending.liteTakenStartTick;
    }
    if (pending.liteTakenLastTick > live.liteTakenLastTick) {
      live.liteTakenLastTick = pending.liteTakenLastTick;
    }
  }
"""
    storage = replace_method_range(
        storage,
        "void _liteDetectSubProfession(",
        "void addDamage(",
        optimized_detection,
        "specialization/pending combat helpers",
    )

    optimized_damage = r"""
  void addDamage(
    Int64 attackerUid,
    Int64 targetUid,
    Int64 damage,
    int tick, {
    String? skillId,
    bool isLucky = false,
    bool isCrit = false,
  }) {
    _onAction(tick);

    final attackerData = _liteMetricDataForUid(attackerUid);
    if (attackerData != null) {
      if (attackerUid == _currentPlayerUuid ||
          _playerInfoDatas.containsKey(attackerUid)) {
        _liteDetectSubProfession(attackerUid, skillId);
      }
      attackerData.totalAttackDamage += damage;
      attackerData.liteDamageStartTick ??= tick;
      attackerData.liteDamageLastTick = tick;
    }

    final targetData = _liteMetricDataForUid(targetUid);
    if (targetData != null) {
      targetData.totalTakenDamage += damage;
      targetData.liteTakenStartTick ??= tick;
      targetData.liteTakenLastTick = tick;
    }

    _liteMarkBossEngaged(targetUid);
    _scheduleNotify();
  }
"""
    storage = replace_method_range(
        storage,
        "void addDamage(",
        "void addHealing(",
        optimized_damage,
        "Lite addDamage",
    )

    optimized_healing = r"""
  void addHealing(
    Int64 healerUid,
    Int64 targetUid,
    Int64 healAmount,
    int tick, {
    String? skillId,
    bool isCrit = false,
  }) {
    _onAction(tick);

    final healerData = _liteMetricDataForUid(healerUid);
    if (healerData != null) {
      if (healerUid == _currentPlayerUuid ||
          _playerInfoDatas.containsKey(healerUid)) {
        _liteDetectSubProfession(healerUid, skillId);
      }
      healerData.totalHeal += healAmount;
      healerData.liteHealingStartTick ??= tick;
      healerData.liteHealingLastTick = tick;
    }

    _scheduleNotify();
  }
"""
    storage = replace_method_range(
        storage,
        "void addHealing(",
        "void reset(",
        optimized_healing,
        "Lite addHealing",
    )

    storage = replace_once(
        storage,
        """  DpsData getOrCreateDpsData(Int64 uid) {
    if (!_fullDpsDatas.containsKey(uid)) {
      _fullDpsDatas[uid] = DpsData(uid: uid);
    }

    if (!_playerInfoDatas.containsKey(uid) && 
        !_pendingFetches.contains(uid)) {
      getPlayerInfo(uid);
    }

    return _fullDpsDatas[uid]!;
  }
""",
        """  DpsData getOrCreateDpsData(Int64 uid) {
    return _fullDpsDatas.putIfAbsent(uid, () => DpsData(uid: uid));
  }
""",
        "DpsData allocation without hot-path DB lookup",
    )

    storage = replace_once(
        storage,
        """  void ensurePlayer(Int64 uid) {
    if (!_playerInfoDatas.containsKey(uid)) {
      _playerInfoDatas[uid] = PlayerInfo(uid: uid);
      _fetchPlayerFromDb(uid);
      notifyListeners();
    }
  }
""",
        """  void ensurePlayer(Int64 uid) {
    if (!_playerInfoDatas.containsKey(uid)) {
      _playerInfoDatas[uid] = PlayerInfo(uid: uid);
      _fetchPlayerFromDb(uid);
      notifyListeners();
    }
    _litePromotePendingCombat(uid);
  }
""",
        "pending combat promotion on player identity",
    )

    storage = replace_once(
        storage,
        """  bool ensureMonster(Int64 uid, {bool forceRespawn = false, bool isSummon = false}) {
    if (forceRespawn) _deadMonsters.remove(uid);
    if (_deadMonsters.contains(uid)) return false;

    if (!_monsterInfoDatas.containsKey(uid)) {
""",
        """  bool ensureMonster(Int64 uid, {bool forceRespawn = false, bool isSummon = false}) {
    if (forceRespawn) _deadMonsters.remove(uid);
    if (_deadMonsters.contains(uid)) return false;

    _litePendingCombat.remove(uid);

    if (!_monsterInfoDatas.containsKey(uid)) {
""",
        "pending combat discard on monster identity",
    )

    storage = replace_once(
        storage,
        "DateTime? _liteLastAutoSplitAt;\n",
        "DateTime? _liteLastAutoSplitAt;\nint? _liteLastWallClockTick;\n",
        "Lite hot-path wall clock tick",
    )

    optimized_action = r"""
  void _onAction(int tick) {
    // Combat packets already contain millisecond ticks. Refresh wall-clock
    // fields at most about once per second instead of constructing DateTime per hit.
    if (!_isCombatActive) {
      final now = DateTime.now();
      _isCombatActive = true;
      _combatStartTime ??= now;
      _lastActionTime = now;
      _liteLastWallClockTick = tick;
      return;
    }

    final lastTick = _liteLastWallClockTick;
    if (lastTick == null || tick < lastTick || tick - lastTick >= 1000) {
      _lastActionTime = DateTime.now();
      _liteLastWallClockTick = tick;
    }
  }
"""
    storage = replace_method_range(
        storage,
        "void _onAction() {",
        "Map<Int64, PlayerInfo> get playerInfoDatas",
        optimized_action,
        "tick-based Lite action clock",
    )

    # Release staged unknown identities on either automatic or manual reset.
    clear_anchor = "  _fullDpsDatas.clear();\n  _liteSubProfessionNames.clear();"
    clear_count = storage.count(clear_anchor)
    if clear_count != 2:
        fail(f"expected two encounter clear blocks, found {clear_count}")
    storage = storage.replace(
        clear_anchor,
        clear_anchor + "\n  _litePendingCombat.clear();",
    )

    storage_path.write_text(storage, encoding="utf-8")

    # ------------------------------------------------------------------
    # Flutter bridge/rendering: DataStorage dirty events are the only visible
    # update throttle. Remove permanent polling and the overlay's second timer.
    # ------------------------------------------------------------------
    main_path = root / "lib/main.dart"
    dart = main_path.read_text(encoding="utf-8")

    dart = dart.replace("import 'package:provider/provider.dart';\n", "", 1)
    dart = replace_once(
        dart,
        """  runApp(
    ChangeNotifierProvider(
      create: (context) => DataStorage(),
      child: const MyApp(),
    ),
  );
""",
        "  runApp(const MyApp());\n",
        "main provider wrapper",
    )
    dart = replace_once(
        dart,
        """  runApp(
    ChangeNotifierProvider(
      create: (context) => DataStorage(),
      child: const MaterialApp(debugShowCheckedModeBanner: false, home: OverlayWidget()),
    ),
  );
""",
        """  runApp(
    const MaterialApp(
      debugShowCheckedModeBanner: false,
      home: OverlayWidget(),
    ),
  );
""",
        "overlay provider wrapper",
    )

    dart, _ = re.subn(
        r"^[ \t]*static const Duration _liteOverlayBridgeInterval =\n"
        r"[ \t]*Duration\(seconds: 2\);\n",
        "",
        dart,
        count=1,
        flags=re.MULTILINE,
    )
    dart = dart.replace("  Timer? _overlayUpdateTimer;\n", "", 1)
    dart = dart.replace("    _overlayUpdateTimer?.cancel();\n", "", 1)

    dart, periodic_count = re.subn(
        r"\n[ \t]*// Performance: bridge visible meter data at most once every two seconds\n"
        r"[ \t]*_overlayUpdateTimer = Timer\.periodic\([^;]+?\n[ \t]*\);\n",
        "\n",
        dart,
        count=1,
        flags=re.MULTILINE | re.DOTALL,
    )
    if periodic_count != 1:
        dart, periodic_count = re.subn(
            r"\n[ \t]*_overlayUpdateTimer = Timer\.periodic\("
            r"_liteOverlayBridgeInterval, \(_\) \{\n"
            r"[ \t]*_updateOverlay\(\);\n[ \t]*\}\);\n",
            "\n",
            dart,
            count=1,
            flags=re.MULTILINE,
        )
    if periodic_count != 1:
        fail("could not remove permanent overlay bridge timer")

    dart = replace_once(
        dart,
        "  Future<void> _updateOverlay() async {\n",
        """  void _onLiteStorageChanged() {
    if (!_isVpnRunning) return;
    unawaited(_updateOverlay());
  }

  Future<void> _updateOverlay() async {
""",
        "event-driven overlay callback",
    )

    dart = replace_once(
        dart,
        """      setState(() {
        _isVpnRunning = true;
      });

      _packetSubscription = eventChannel.receiveBroadcastStream().listen(
""",
        """      setState(() {
        _isVpnRunning = true;
      });

      DataStorage().removeListener(_onLiteStorageChanged);
      DataStorage().addListener(_onLiteStorageChanged);
      _liteLastOverlayPayloadSignature = '';
      await _updateOverlay();

      _packetSubscription = eventChannel.receiveBroadcastStream().listen(
""",
        "start event-driven overlay listener",
    )

    dart = replace_once(
        dart,
        """      DataStorage().finishLiteEncounter(
        'meter_stopped',
        manual: true,
      );
      await platform.invokeMethod('stopVpn');
""",
        """      DataStorage().finishLiteEncounter(
        'meter_stopped',
        manual: true,
      );
      DataStorage().removeListener(_onLiteStorageChanged);
      await platform.invokeMethod('stopVpn');
""",
        "stop event-driven overlay listener",
    )

    dart = replace_once(
        dart,
        """    IsolateNameServer.removePortNameMapping('overlay_communication_port');
    _receivePort?.close();
""",
        """    IsolateNameServer.removePortNameMapping('overlay_communication_port');
    DataStorage().removeListener(_onLiteStorageChanged);
    _receivePort?.close();
""",
        "dispose event-driven overlay listener",
    )

    # initializeLiteEncounterState() already requests the gated cleanup.
    dart = dart.replace(
        "    unawaited(EncounterHistoryService().deleteExpired());\n",
        "",
        1,
    )

    dart = dart.replace(
        "  static const Duration _overlayRefreshInterval = Duration(seconds: 2);\n",
        "",
        1,
    )
    dart = dart.replace("  Timer? _liteUiFlushTimer;\n", "", 1)
    dart = replace_once(
        dart,
        """      // Keep only the newest cumulative snapshot. No hit is discarded because
      // totals are still calculated by DataStorage before reaching the overlay.
      _liteUiFlushTimer ??= Timer(
        _overlayRefreshInterval,
        _flushLiteUiPayload,
      );
""",
        """      // The main isolate already coalesces dirty state. Apply the delivered
      // cumulative snapshot immediately so there is no second visual delay.
      _flushLiteUiPayload();
""",
        "overlay second throttle",
    )
    dart = dart.replace("    _liteUiFlushTimer = null;\n", "", 1)
    dart = dart.replace("    _liteUiFlushTimer?.cancel();\n", "", 1)
    dart = dart.replace("    _liteUiFlushTimer = null;\n", "", 1)

    main_path.write_text(dart, encoding="utf-8")

    # ------------------------------------------------------------------
    # Dependencies/assets unused by the final Lite runtime.
    # ------------------------------------------------------------------
    pubspec_path = root / "pubspec.yaml"
    pubspec = pubspec_path.read_text(encoding="utf-8")
    for dependency in (
        "  cupertino_icons: ^1.0.8\n",
        "  es_compression: ^2.0.0\n",
        "  provider: ^6.1.2\n",
        "  permission_handler: ^11.3.0\n",
        "  http: ^1.2.0\n",
        "  web_socket_channel: ^3.0.0\n",
    ):
        pubspec = pubspec.replace(dependency, "")

    pubspec = pubspec.replace(
        """  assets:
      - assets/img/
      - assets/img/classes/
""",
        "",
        1,
    )
    pubspec_path.write_text(pubspec, encoding="utf-8")

    print("BlueMeter Lite ultra-low-impact engine optimizations applied.")
    print("- selector-driven TCP/UDP forwarding")
    print("- direct native EventChannel bridge")
    print("- bounded packet pools/queues and UDP expiry")
    print("- low-copy Dart reassembly and message views")
    print("- bounded unknown combat staging; no NPC player DB candidates")
    print("- coalesced SQLite writes and daily cleanup")
    print("- event-driven single-throttle overlay updates")
    print("- unused runtime dependencies removed")


if __name__ == "__main__":
    main()
