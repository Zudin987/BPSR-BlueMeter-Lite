#!/usr/bin/env python3
"""Fail CI when BlueMeter Lite regresses to known high-impact hot paths."""

from __future__ import annotations

import sys
from pathlib import Path


def fail(message: str) -> None:
    raise SystemExit(f"Ultra-low-impact verification failed: {message}")


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        fail(f"missing {label}: {needle}")


def forbid(text: str, needle: str, label: str) -> None:
    if needle in text:
        fail(f"forbidden {label}: {needle}")


def main() -> None:
    if len(sys.argv) != 2:
        fail("usage: verify_ultra_low_impact.py <generated-upstream-directory>")

    root = Path(sys.argv[1]).resolve()
    kotlin_root = (
        root
        / "android/app/src/main/kotlin/com/bluemeter/bluemeter_mobile"
    )

    capture = (kotlin_root / "PacketCaptureService.kt").read_text(encoding="utf-8")
    proxy = (kotlin_root / "TcpProxy.kt").read_text(encoding="utf-8")
    activity = (kotlin_root / "MainActivity.kt").read_text(encoding="utf-8")
    event_bus = (kotlin_root / "PacketEventBus.kt").read_text(encoding="utf-8")
    analyzer = (root / "lib/core/analyze/packet_analyzer_v2.dart").read_text(
        encoding="utf-8"
    )
    message_analyzer = (
        root / "lib/core/analyze/message_analyzer_v2.dart"
    ).read_text(encoding="utf-8")
    storage = (root / "lib/core/state/data_storage.dart").read_text(encoding="utf-8")
    database = (root / "lib/core/services/database_service.dart").read_text(
        encoding="utf-8"
    )
    history = (
        root / "lib/core/services/encounter_history_service.dart"
    ).read_text(encoding="utf-8")
    main_dart = (root / "lib/main.dart").read_text(encoding="utf-8")
    pubspec = (root / "pubspec.yaml").read_text(encoding="utf-8")

    # Native forwarding must sleep by blocking on network/TUN readiness, not by
    # waking every millisecond and rescanning all sockets.
    require(capture, "selector.select(SELECT_IDLE_TIMEOUT_MS)", "blocking selector")
    require(capture, "selector.wakeup()", "TUN selector wakeup")
    require(capture, "ArrayBlockingQueue<ByteBuffer>", "bounded TUN queue")
    require(capture, "UDP_IDLE_TIMEOUT_NANOS", "UDP idle expiry")
    require(capture, "data class UdpKey", "four-tuple UDP key")
    require(capture, "PacketEventBus::emitGame", "direct native bridge")
    require(capture, "START_NOT_STICKY", "non-sticky capture service")
    forbid(capture, "Thread.sleep(", "fixed polling sleep")
    forbid(capture, "sendBroadcast(", "packet Intent broadcast")
    forbid(capture, 'split(":")', "UDP string key parsing")

    # TCP should use the shared selector and one server-read byte array rather
    # than copyOfRange per MSS segment.
    require(proxy, "private val selector: Selector", "shared TCP selector")
    require(proxy, "fun handleSelectedKey", "selector key handler")
    require(proxy, "packet.seqNum > session.clientSeq", "out-of-order guard")
    forbid(proxy, "copyOfRange", "per-segment byte-array copy")
    forbid(proxy, "Selector.open()", "private TCP selector")

    # Android packet data must go straight to Flutter's EventChannels.
    require(activity, "PacketEventBus.gameSink", "game EventChannel bridge")
    require(activity, "PacketEventBus.upstreamSink", "upstream EventChannel bridge")
    forbid(activity, "BroadcastReceiver", "packet BroadcastReceiver")
    require(event_bus, "object PacketEventBus", "packet event bus")

    # Dart framing should retain offsets/views instead of rebuilding the whole
    # buffer and copying packet tails.
    require(analyzer, "Uint8List.sublistView", "zero-copy packet view")
    require(analyzer, "_readOffset", "reassembly read offset")
    require(analyzer, "_compact()", "bounded reassembly compaction")
    forbid(analyzer, "BytesBuilder", "BytesBuilder reassembly")
    forbid(analyzer, ".toBytes()", "whole-buffer copy")
    require(message_analyzer, "Uint8List.sublistView", "message payload views")

    # Combat/storage should avoid player DB work and notifier microtasks per hit.
    require(storage, "_litePendingTaken", "bounded unknown taken-damage staging")
    require(storage, "Timer(const Duration(seconds: 2)", "dirty notification throttle")
    require(storage, "_onAction(tick);", "tick-based hot action path")
    forbid(storage, "Future.microtask", "per-hit notifier microtask")
    require(database, "_pendingPlayers", "coalesced player writes")
    require(database, "ON CONFLICT(uid) DO UPDATE", "single player UPSERT")
    forbid(database, "txn.query(", "existence query before every player write")
    require(history, "_cleanupInterval = Duration(days: 1)", "daily history cleanup")

    # Main/overlay rendering should be event-driven and have only one throttle.
    require(main_dart, "DataStorage().addListener(_onLiteStorageChanged)", "event-driven overlay bridge")
    forbid(main_dart, "Timer.periodic", "permanent overlay polling timer")
    forbid(main_dart, "_liteUiFlushTimer", "second overlay throttle")
    forbid(main_dart, "_overlayRefreshInterval", "second overlay refresh interval")

    # Unused upstream integrations should not remain as runtime dependencies.
    for dependency in (
        "cupertino_icons:",
        "es_compression:",
        "provider:",
        "permission_handler:",
        "http:",
        "web_socket_channel:",
    ):
        forbid(pubspec, dependency, "unused dependency")

    test_file = root / "test/lite_performance_test.dart"
    if not test_file.exists():
        fail("missing replay regression test")

    print("Ultra-low-impact static regression checks passed.")


if __name__ == "__main__":
    main()
