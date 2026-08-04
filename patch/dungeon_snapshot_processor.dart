import 'dart:typed_data';

import '../../state/data_storage.dart';
import 'message_processor.dart';

/// Handles WorldNtf.SyncDungeonData (method ID 0x17).
///
/// ZDPS receives this dedicated packet when dungeon data is initialized.
/// Lite needs only the boundary signal here; objective parsing will be added
/// separately after map/dungeon reset behaviour is verified.
class DungeonSnapshotProcessor implements IMessageProcessor {
  DungeonSnapshotProcessor(this._storage);

  final DataStorage _storage;

  @override
  void process(Uint8List payload) {
    _storage.onLiteDungeonSnapshot();
  }
}
