import 'dart:typed_data';

import 'package:protobuf/protobuf.dart';

import '../../protocol/blue_protocol.dart';
import '../../services/logger_service.dart';
import '../../state/data_storage.dart';
import 'message_processor.dart';

/// Exact scene-entry packet used by ZDPS.
///
/// WorldNtf.EnterScene (method 0x03) contains EnterSceneInfo at field 1.
/// EnterSceneInfo contains SceneAttrs at field 1. The map and channel are
/// stored as protobuf-encoded values in AttrSceneBasicId and AttrSceneChannel.
class EnterSceneProcessor implements IMessageProcessor {
  EnterSceneProcessor(this._storage);

  static const int _attrSceneBasicId = 341;
  static const int _attrSceneChannel = 343;

  final DataStorage _storage;
  final LoggerService _logger = LoggerService();

  @override
  void process(Uint8List payload) {
    try {
      final packet = _LiteEnterScene.fromBuffer(payload);
      if (!packet.hasEnterSceneInfo()) return;

      final info = packet.enterSceneInfo;
      if (!info.hasSceneAttrs()) return;

      int? mapId;
      int? channelId;

      for (final attr in info.sceneAttrs.attrs) {
        if (attr.rawData.isEmpty) continue;
        final value = _readUnsignedVarint(attr.rawData);
        if (value == null) continue;

        switch (attr.id) {
          case _attrSceneBasicId:
            mapId = value;
          case _attrSceneChannel:
            channelId = value;
        }
      }

      if (mapId == null || mapId <= 0) return;

      _storage.onSceneUpdate(
        mapId: mapId,
        channelId: channelId != null && channelId > 0 ? channelId : null,
      );
      _logger.log(
        'EnterScene: mapId=$mapId'
        '${channelId != null ? ', channelId=$channelId' : ''}',
      );
    } catch (error, stackTrace) {
      _logger.error(
        'Error processing WorldNtf.EnterScene',
        error: error,
        stackTrace: stackTrace,
      );
    }
  }

  int? _readUnsignedVarint(List<int> bytes) {
    var result = 0;
    var shift = 0;

    for (final byte in bytes) {
      result |= (byte & 0x7f) << shift;
      if ((byte & 0x80) == 0) return result;
      shift += 7;
      if (shift > 35) return null;
    }

    return null;
  }
}

/// Minimal typed protobuf definition for WorldNtf.EnterSceneInfo.
/// Unknown fields such as PlayerEnt, GUIDs, and sub-scene data are safely
/// skipped by package:protobuf.
class _LiteEnterSceneInfo extends GeneratedMessage {
  _LiteEnterSceneInfo() : super();

  _LiteEnterSceneInfo.fromBuffer(
    List<int> data, [
    ExtensionRegistry registry = ExtensionRegistry.EMPTY,
  ]) : super() {
    mergeFromBuffer(data, registry);
  }

  static final BuilderInfo _i = BuilderInfo(
    '_LiteEnterSceneInfo',
    package: const PackageName('BlueProto'),
    createEmptyInstance: create,
  )
    ..aOM<AttrCollection>(
      1,
      'sceneAttrs',
      subBuilder: AttrCollection.create,
    )
    ..hasRequiredFields = false;

  @override
  BuilderInfo get info_ => _i;

  @override
  _LiteEnterSceneInfo createEmptyInstance() => create();

  @override
  _LiteEnterSceneInfo clone() =>
      _LiteEnterSceneInfo()..mergeFromMessage(this);

  static _LiteEnterSceneInfo create() => _LiteEnterSceneInfo();

  static PbList<_LiteEnterSceneInfo> createRepeated() =>
      PbList<_LiteEnterSceneInfo>();

  static _LiteEnterSceneInfo getDefault() =>
      _defaultInstance ??= create()..freeze();

  static _LiteEnterSceneInfo? _defaultInstance;

  AttrCollection get sceneAttrs => $_getN(0);

  set sceneAttrs(AttrCollection value) => setField(1, value);

  bool hasSceneAttrs() => $_has(0);

  void clearSceneAttrs() => clearField(1);
}

/// Minimal typed protobuf definition for WorldNtf.EnterScene.
class _LiteEnterScene extends GeneratedMessage {
  _LiteEnterScene() : super();

  _LiteEnterScene.fromBuffer(
    List<int> data, [
    ExtensionRegistry registry = ExtensionRegistry.EMPTY,
  ]) : super() {
    mergeFromBuffer(data, registry);
  }

  static final BuilderInfo _i = BuilderInfo(
    '_LiteEnterScene',
    package: const PackageName('BlueProto'),
    createEmptyInstance: create,
  )
    ..aOM<_LiteEnterSceneInfo>(
      1,
      'enterSceneInfo',
      subBuilder: _LiteEnterSceneInfo.create,
    )
    ..hasRequiredFields = false;

  @override
  BuilderInfo get info_ => _i;

  @override
  _LiteEnterScene createEmptyInstance() => create();

  @override
  _LiteEnterScene clone() =>
      _LiteEnterScene()..mergeFromMessage(this);

  static _LiteEnterScene create() => _LiteEnterScene();

  static PbList<_LiteEnterScene> createRepeated() =>
      PbList<_LiteEnterScene>();

  static _LiteEnterScene getDefault() =>
      _defaultInstance ??= create()..freeze();

  static _LiteEnterScene? _defaultInstance;

  _LiteEnterSceneInfo get enterSceneInfo => $_getN(0);

  set enterSceneInfo(_LiteEnterSceneInfo value) => setField(1, value);

  bool hasEnterSceneInfo() => $_has(0);

  void clearEnterSceneInfo() => clearField(1);
}
