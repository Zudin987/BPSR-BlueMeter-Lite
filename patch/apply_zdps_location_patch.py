#!/usr/bin/env python3
"""Patch the built BlueMeter source to capture scene IDs like ZDPS.

This script is intended to run in GitHub Actions after apply_lite_patch.py.
It does not run on the user's phone or PC.
"""

from __future__ import annotations

import sys
from pathlib import Path


def fail(message: str) -> None:
    raise SystemExit(f"ZDPS location patch failed: {message}")


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        fail(f"expected one {label}, found {count}")
    return text.replace(old, new, 1)


def patch_analyzer(path: Path) -> None:
    text = path.read_text(encoding="utf-8")

    if "_liteSocialServiceUuid" in text:
        return

    text = replace_once(
        text,
        '  static final BigInt _combatServiceUuid = BigInt.parse("63335342", radix: 16);\n',
        '''  static final BigInt _combatServiceUuid = BigInt.parse("63335342", radix: 16);\n\n  // ZDPS reads SocialNtf.NotifySocialData before the actual map load.\n  // It contains the destination LevelMapId and line number.\n  static final BigInt _liteSocialServiceUuid = BigInt.from(625772963);\n  static const int _liteNotifySocialDataMethodId = 0x00000001;\n''',
        "SocialNtf constants",
    )

    text = replace_once(
        text,
        '''    final isCombat = serviceUuid == _combatServiceUuid;\n    final hasProcessor = _registry.getProcessor(methodId) != null;\n\n    if (!isCombat && !hasProcessor) {\n''',
        '''    final isCombat = serviceUuid == _combatServiceUuid;\n    final isLiteSocialSceneNotify =\n        serviceUuid == _liteSocialServiceUuid &&\n        methodId == _liteNotifySocialDataMethodId;\n    final hasProcessor = _registry.getProcessor(methodId) != null;\n\n    if (!isCombat && !hasProcessor && !isLiteSocialSceneNotify) {\n''',
        "non-combat service filter",
    )

    text = replace_once(
        text,
        '''    final processor = _registry.getProcessor(methodId);\n    if (processor != null) {\n''',
        '''    if (isLiteSocialSceneNotify) {\n      final sceneHint = _LiteSocialSceneDecoder.decode(msgPayload);\n      if (sceneHint != null) {\n        _storage.onLiteSocialSceneHint(\n          mapId: sceneHint.mapId,\n          lineId: sceneHint.lineId,\n        );\n      }\n      return;\n    }\n\n    final processor = _registry.getProcessor(methodId);\n    if (processor != null) {\n''',
        "SocialNtf payload dispatch",
    )

    decoder = r'''

class _LiteSceneHint {
  const _LiteSceneHint({
    required this.mapId,
    this.lineId,
  });

  final int mapId;
  final int? lineId;
}

class _LiteProtoField {
  const _LiteProtoField({
    required this.number,
    required this.wireType,
    this.varintValue,
    this.bytesValue,
  });

  final int number;
  final int wireType;
  final int? varintValue;
  final Uint8List? bytesValue;
}

class _LiteVarintResult {
  const _LiteVarintResult(this.value, this.nextOffset);

  final int value;
  final int nextOffset;
}

/// Lightweight parser for the one ZDPS scene packet BlueMeter needs.
///
/// The upstream project does not ship SocialNtf generated protobuf classes,
/// so this reads the protobuf wire format directly. Parsing is restricted to
/// SocialNtf.NotifySocialData by service and method IDs before this is called.
class _LiteSocialSceneDecoder {
  static const Set<int> _knownMapIds = <int>{
    7, 8, 9, 10, 11,
    71, 72, 73, 74, 75, 76,
    91, 92,
    6043, 6044, 6045,
    6421, 6422, 6423,
    6521, 6522, 6523, 6524, 6525,
    12000,
    12011, 12012, 12013, 12014, 12015,
    12018, 12019, 12022, 12023,
  };

  static _LiteSceneHint? decode(Uint8List payload) {
    if (payload.isEmpty || payload.length > 1024 * 1024) return null;

    // Expected generated-protobuf path:
    // NotifySocialData.VRequest.Data.SceneData.
    // Try several wrapper-field layouts because regional clients may use
    // slightly different generated message wrappers.
    const paths = <List<int>>[
      <int>[1, 1, 3],
      <int>[1, 2, 3],
      <int>[2, 1, 3],
      <int>[1, 3],
    ];

    for (final path in paths) {
      final sceneBytes = _followMessagePath(payload, path);
      final scene = sceneBytes == null ? null : _readScene(sceneBytes, true);
      if (scene != null) return scene;
    }

    // Fallback: locate a nested SceneData-shaped protobuf message. Scene data
    // uses field 1 for the map and commonly carries channel/plane/line fields
    // 2, 9, or 15. Known map IDs receive priority to avoid false positives.
    return _searchNested(payload, 0);
  }

  static Uint8List? _followMessagePath(
    Uint8List data,
    List<int> fieldPath,
  ) {
    var current = data;
    for (final fieldNumber in fieldPath) {
      final fields = _readFields(current);
      if (fields == null) return null;

      Uint8List? next;
      for (final field in fields) {
        if (field.number == fieldNumber && field.wireType == 2) {
          next = field.bytesValue;
          break;
        }
      }
      if (next == null) return null;
      current = next;
    }
    return current;
  }

  static _LiteSceneHint? _searchNested(Uint8List data, int depth) {
    if (depth > 6 || data.isEmpty) return null;
    final fields = _readFields(data);
    if (fields == null) return null;

    final direct = _readScene(data, false);
    if (direct != null && _knownMapIds.contains(direct.mapId)) {
      return direct;
    }

    for (final field in fields) {
      final nested = field.bytesValue;
      if (field.wireType != 2 || nested == null || nested.isEmpty) continue;
      final found = _searchNested(nested, depth + 1);
      if (found != null) return found;
    }
    return null;
  }

  static _LiteSceneHint? _readScene(
    Uint8List data,
    bool acceptUnknownMap,
  ) {
    final fields = _readFields(data);
    if (fields == null) return null;

    int? mapId;
    int? lineId;
    var hasSceneCompanionField = false;

    for (final field in fields) {
      if (field.wireType != 0) continue;
      if (field.number == 1) {
        mapId = field.varintValue;
      } else if (field.number == 15) {
        lineId = field.varintValue;
        hasSceneCompanionField = true;
      } else if (field.number == 2 || field.number == 9) {
        hasSceneCompanionField = true;
      }
    }

    if (mapId == null || mapId <= 0 || mapId > 500000) return null;
    if (!acceptUnknownMap &&
        !_knownMapIds.contains(mapId) &&
        !hasSceneCompanionField) {
      return null;
    }

    return _LiteSceneHint(
      mapId: mapId,
      lineId: lineId != null && lineId > 0 ? lineId : null,
    );
  }

  static List<_LiteProtoField>? _readFields(Uint8List data) {
    final fields = <_LiteProtoField>[];
    var offset = 0;

    while (offset < data.length) {
      final key = _readVarint(data, offset);
      if (key == null || key.value == 0) return null;
      offset = key.nextOffset;

      final fieldNumber = key.value >> 3;
      final wireType = key.value & 0x07;
      if (fieldNumber <= 0) return null;

      switch (wireType) {
        case 0:
          final value = _readVarint(data, offset);
          if (value == null) return null;
          offset = value.nextOffset;
          fields.add(
            _LiteProtoField(
              number: fieldNumber,
              wireType: wireType,
              varintValue: value.value,
            ),
          );
          break;
        case 1:
          if (offset + 8 > data.length) return null;
          offset += 8;
          fields.add(
            _LiteProtoField(number: fieldNumber, wireType: wireType),
          );
          break;
        case 2:
          final lengthResult = _readVarint(data, offset);
          if (lengthResult == null) return null;
          offset = lengthResult.nextOffset;
          final length = lengthResult.value;
          if (length < 0 || offset + length > data.length) return null;
          final bytes = Uint8List.sublistView(data, offset, offset + length);
          offset += length;
          fields.add(
            _LiteProtoField(
              number: fieldNumber,
              wireType: wireType,
              bytesValue: bytes,
            ),
          );
          break;
        case 5:
          if (offset + 4 > data.length) return null;
          offset += 4;
          fields.add(
            _LiteProtoField(number: fieldNumber, wireType: wireType),
          );
          break;
        default:
          return null;
      }
    }

    return fields;
  }

  static _LiteVarintResult? _readVarint(Uint8List data, int offset) {
    var result = 0;
    var shift = 0;
    var cursor = offset;

    while (cursor < data.length && shift <= 63) {
      final byte = data[cursor++];
      result |= (byte & 0x7f) << shift;
      if ((byte & 0x80) == 0) {
        return _LiteVarintResult(result, cursor);
      }
      shift += 7;
    }
    return null;
  }
}
'''

    if not text.rstrip().endswith("}"):
        fail("message analyzer does not end with a class brace")
    text = text.rstrip() + decoder + "\n"
    path.write_text(text, encoding="utf-8")


def patch_storage(path: Path) -> None:
    text = path.read_text(encoding="utf-8")

    if "void onLiteSocialSceneHint" in text:
        return

    text = replace_once(
        text,
        '''bool _liteSeenFullPlayerContainer = false;\nDateTime? _liteLastMapLoadSignalAt;\n''',
        '''bool _liteSeenFullPlayerContainer = false;\nDateTime? _liteLastMapLoadSignalAt;\n\n// Keep the location belonging to the encounter separate from the next map.\n// SocialNtf announces the destination before the actual map-load packet.\nint _liteEncounterMapId = 0;\nint _litePendingMapId = 0;\nint? _litePendingLineId;\n''',
        "encounter scene state fields",
    )

    scene_helpers = r'''
void onLiteSocialSceneHint({
  required int mapId,
  int? lineId,
}) {
  if (mapId <= 0) return;

  // Before combat begins, the Social notification already describes the map
  // where the next encounter will happen, so it can become current directly.
  if (!_liteHasEncounterData) {
    _liteEncounterMapId = mapId;
    _mapId = mapId;
    if (lineId != null && lineId > 0) {
      _lineId = lineId;
    }
    _litePendingMapId = 0;
    _litePendingLineId = null;
    return;
  }

  // During combat, never replace the current encounter's location. Save the
  // destination and promote it only after the map boundary saves the encounter.
  _litePendingMapId = mapId;
  _litePendingLineId = lineId != null && lineId > 0 ? lineId : null;
}

void _litePromotePendingScene() {
  if (_litePendingMapId > 0) {
    _liteEncounterMapId = _litePendingMapId;
    _mapId = _litePendingMapId;
  } else if (_mapId > 0) {
    _liteEncounterMapId = _mapId;
  }

  final pendingLineId = _litePendingLineId;
  if (pendingLineId != null && pendingLineId > 0) {
    _lineId = pendingLineId;
  }

  _litePendingMapId = 0;
  _litePendingLineId = null;
}

'''

    text = replace_once(
        text,
        "void initializeLiteEncounterState() {\n",
        scene_helpers + "void initializeLiteEncounterState() {\n",
        "Social scene helper insertion",
    )

    text = replace_once(
        text,
        '''void onLiteFullPlayerContainerSync() {\n  final now = DateTime.now();\n\n  if (!_liteSeenFullPlayerContainer) {\n    _liteSeenFullPlayerContainer = true;\n    _liteLastMapLoadSignalAt = now;\n    return;\n  }\n\n  _liteLastMapLoadSignalAt = now;\n  _liteRequestAutoSplit('map_change');\n\n  _monsterInfoDatas.clear();\n''',
        '''void onLiteFullPlayerContainerSync() {\n  final now = DateTime.now();\n\n  if (!_liteSeenFullPlayerContainer) {\n    _liteSeenFullPlayerContainer = true;\n    _liteLastMapLoadSignalAt = now;\n    _litePromotePendingScene();\n    return;\n  }\n\n  _liteLastMapLoadSignalAt = now;\n\n  // Save the old encounter first. The Social notification already holds the\n  // destination, but must not rename the encounter that is ending.\n  _liteRequestAutoSplit('map_change');\n  _litePromotePendingScene();\n\n  _monsterInfoDatas.clear();\n''',
        "full-player map boundary",
    )

    text = replace_once(
        text,
        "    'mapId': _mapId,\n",
        "    'mapId': _liteEncounterMapId > 0 ? _liteEncounterMapId : _mapId,\n",
        "history snapshot map ID",
    )

    text = replace_once(
        text,
        '''  if (receivedMapId) {\n    _mapId = mapId!;\n  }\n''',
        '''  if (receivedMapId) {\n    _mapId = mapId!;\n\n    // SyncContainerData remains a useful fallback when it contains a valid\n    // map ID. The split above has already saved the old location.\n    if (!_liteHasEncounterData ||\n        splitReason != null ||\n        _liteEncounterMapId <= 0) {\n      _liteEncounterMapId = mapId;\n    }\n\n    if (_litePendingMapId == mapId) {\n      _litePendingMapId = 0;\n      _litePendingLineId = null;\n    }\n  }\n''',
        "SyncContainerData map fallback",
    )

    path.write_text(text, encoding="utf-8")


def main() -> None:
    if len(sys.argv) != 2:
        fail("usage: apply_zdps_location_patch.py <upstream-directory>")

    upstream = Path(sys.argv[1]).resolve()
    analyzer = upstream / "lib/core/analyze/message_analyzer_v2.dart"
    storage = upstream / "lib/core/state/data_storage.dart"

    for required in (analyzer, storage):
        if not required.exists():
            fail(f"missing patched upstream file: {required}")

    patch_analyzer(analyzer)
    patch_storage(storage)

    print("ZDPS-style encounter location capture patch applied.")


if __name__ == "__main__":
    main()
