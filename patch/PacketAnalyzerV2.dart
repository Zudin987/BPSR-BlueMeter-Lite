import 'dart:typed_data';

import '../services/logger_service.dart';
import '../state/data_storage.dart';
import 'message_analyzer_v2.dart';

/// Low-copy protocol reassembler used by BlueMeter Lite.
///
/// Upstream rebuilt the complete BytesBuilder and copied both the packet body
/// and remaining tail for every decoded packet. Raid-sized batches therefore
/// created repeated O(n) copies. This implementation keeps one reusable byte
/// array and advances offsets, compacting only when the tail actually needs
/// room.
class PacketAnalyzerV2 {
  static const int _initialCapacity = 64 * 1024;
  static const int _maximumPacketSize = 10 * 1000 * 1000;

  Uint8List _storage = Uint8List(_initialCapacity);
  int _readOffset = 0;
  int _writeOffset = 0;

  final MessageAnalyzerV2 _messageAnalyzer;
  final LoggerService _logger = LoggerService();
  final String tag;

  PacketAnalyzerV2(DataStorage storage, {this.tag = 'game'})
      : _messageAnalyzer = MessageAnalyzerV2(storage, tag: tag);

  int get bufferedByteCount => _writeOffset - _readOffset;
  int get bufferCapacity => _storage.length;

  void processPacket(Uint8List chunk) {
    if (chunk.isEmpty) return;

    // Kotlin emits 0xFFFFFFFF at the start of a port-5003 batch when the
    // underlying session changes. Discard stale reassembly bytes before the
    // new stream is appended.
    if (chunk.length >= 4) {
      final marker = ByteData.sublistView(chunk, 0, 4).getUint32(0, Endian.big);
      if (marker == 0xFFFFFFFF) {
        clearBuffer();
        if (chunk.length > 4) {
          _append(Uint8List.sublistView(chunk, 4));
          _drainBuffer();
        }
        return;
      }
    }

    _append(chunk);
    _drainBuffer();
  }

  void clearBuffer() {
    _readOffset = 0;
    _writeOffset = 0;
  }

  void _append(Uint8List chunk) {
    final required = bufferedByteCount + chunk.length;

    // Reclaim consumed prefix bytes before growing the backing allocation.
    if (_readOffset > 0 && _writeOffset + chunk.length > _storage.length) {
      _compact();
    }

    if (_writeOffset + chunk.length > _storage.length) {
      _grow(required);
    }

    _storage.setRange(_writeOffset, _writeOffset + chunk.length, chunk);
    _writeOffset += chunk.length;
  }

  void _grow(int requiredActiveBytes) {
    var nextCapacity = _storage.length;
    while (nextCapacity < requiredActiveBytes) {
      nextCapacity *= 2;
    }

    // A valid protocol packet may be up to _maximumPacketSize. The small
    // overhead leaves room for a fragmented next header without repeated grow.
    final hardLimit = _maximumPacketSize + 64 * 1024;
    if (nextCapacity > hardLimit) {
      nextCapacity = hardLimit;
    }
    if (nextCapacity < requiredActiveBytes) {
      throw StateError('BlueMeter reassembly buffer exceeded hard limit');
    }

    final activeBytes = bufferedByteCount;
    final replacement = Uint8List(nextCapacity);
    replacement.setRange(
      0,
      activeBytes,
      _storage,
      _readOffset,
    );
    _storage = replacement;
    _readOffset = 0;
    _writeOffset = activeBytes;
  }

  void _compact() {
    if (_readOffset == 0) return;
    final activeBytes = bufferedByteCount;
    if (activeBytes > 0) {
      _storage.setRange(0, activeBytes, _storage, _readOffset);
    }
    _readOffset = 0;
    _writeOffset = activeBytes;
  }

  void _drainBuffer() {
    while (bufferedByteCount >= 4) {
      final header = ByteData.sublistView(
        _storage,
        _readOffset,
        _readOffset + 4,
      );
      final packetSize = header.getUint32(0, Endian.big);

      // Server stream signature: 00 63 33 53 42 00. Its first four bytes look
      // like a packet length, so consume the complete six-byte marker directly.
      if (packetSize == 0x00633353) {
        if (bufferedByteCount < 6) break;
        _readOffset += 6;
        continue;
      }

      if (packetSize < 4 || packetSize > _maximumPacketSize) {
        _logger.log(
          'Invalid packet size: $packetSize '
          '(0x${packetSize.toRadixString(16)}). '
          'Buffered: $bufferedByteCount. Clearing buffer.',
        );
        clearBuffer();
        return;
      }

      if (bufferedByteCount < packetSize) break;

      final packetBody = Uint8List.sublistView(
        _storage,
        _readOffset + 4,
        _readOffset + packetSize,
      );
      _readOffset += packetSize;

      try {
        _messageAnalyzer.process(packetBody);
      } catch (error) {
        _logger.error('Error processing packet', error: error);
      }
    }

    if (_readOffset == _writeOffset) {
      clearBuffer();
    } else if (_readOffset >= (_storage.length ~/ 2)) {
      // At most one compaction after draining a batch, never once per packet.
      _compact();
    }
  }
}
