import 'dart:typed_data';

import 'package:fixnum/fixnum.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:bluemeter_mobile/core/analyze/packet_analyzer_v2.dart';
import 'package:bluemeter_mobile/core/state/data_storage.dart';

Uint8List _emptyProtocolPackets(int count) {
  final bytes = Uint8List(count * 6);
  final view = ByteData.sublistView(bytes);
  for (var index = 0; index < count; index++) {
    final offset = index * 6;
    view.setUint32(offset, 6, Endian.big);
    view.setUint16(offset + 4, 0, Endian.big);
  }
  return bytes;
}

void main() {
  group('Lite packet reassembly', () {
    test('drains a raid-sized replay without growing or retaining bytes', () {
      final analyzer = PacketAnalyzerV2(DataStorage(), tag: 'test');
      final replay = _emptyProtocolPackets(10000);

      analyzer.processPacket(replay);

      expect(analyzer.bufferedByteCount, 0);
      expect(analyzer.bufferCapacity, lessThanOrEqualTo(64 * 1024));
    });

    test('handles extreme fragmentation without losing framing', () {
      final analyzer = PacketAnalyzerV2(DataStorage(), tag: 'test');
      final replay = _emptyProtocolPackets(256);

      for (final byte in replay) {
        analyzer.processPacket(Uint8List.fromList(<int>[byte]));
      }

      expect(analyzer.bufferedByteCount, 0);
    });

    test('reset marker discards stale partial stream state', () {
      final analyzer = PacketAnalyzerV2(DataStorage(), tag: 'test');
      analyzer.processPacket(Uint8List.fromList(<int>[0, 0, 0]));

      final packet = _emptyProtocolPackets(1);
      final resetAndPacket = Uint8List(4 + packet.length)
        ..setRange(0, 4, <int>[0xFF, 0xFF, 0xFF, 0xFF])
        ..setRange(4, 4 + packet.length, packet);

      analyzer.processPacket(resetAndPacket);
      expect(analyzer.bufferedByteCount, 0);
    });
  });

  group('Lite combat storage', () {
    test('known monsters never become player DPS entries', () {
      final storage = DataStorage()..reset();
      final attacker = Int64(101);
      final monster = Int64(202);

      storage.ensurePlayer(attacker);
      storage.ensureMonster(monster);
      storage.addDamage(attacker, monster, Int64(1000), 1000);

      expect(storage.getDpsData(monster), isNull);
    });

    test('unknown taken damage is promoted when UID becomes a player', () {
      final storage = DataStorage()..reset();
      final attacker = Int64(303);
      final laterPlayer = Int64(404);

      storage.ensurePlayer(attacker);
      storage.addDamage(attacker, laterPlayer, Int64(750), 2000);
      expect(storage.getDpsData(laterPlayer), isNull);

      storage.ensurePlayer(laterPlayer);
      expect(
        storage.getDpsData(laterPlayer)?.totalTakenDamage.toInt(),
        750,
      );
    });
  });
}
