import 'dart:convert';

import 'package:path/path.dart';
import 'package:sqflite/sqflite.dart';

class LiteEncounterHistory {
  const LiteEncounterHistory({
    required this.id,
    required this.startedAt,
    required this.endedAt,
    required this.durationSeconds,
    required this.reason,
    required this.mapId,
    required this.channelId,
    required this.lineId,
    required this.phase,
    required this.bossName,
    required this.players,
  });

  final int id;
  final DateTime startedAt;
  final DateTime endedAt;
  final int durationSeconds;
  final String reason;
  final int mapId;
  final int channelId;
  final int lineId;
  final int phase;
  final String bossName;
  final List<Map<String, dynamic>> players;

  factory LiteEncounterHistory.fromMap(Map<String, Object?> map) {
    final decoded = jsonDecode(map['players_json'] as String);
    final players = decoded is List
        ? decoded
              .whereType<Map>()
              .map((entry) => Map<String, dynamic>.from(entry))
              .toList(growable: false)
        : const <Map<String, dynamic>>[];

    return LiteEncounterHistory(
      id: map['id'] as int,
      startedAt: DateTime.fromMillisecondsSinceEpoch(map['started_at'] as int),
      endedAt: DateTime.fromMillisecondsSinceEpoch(map['ended_at'] as int),
      durationSeconds: map['duration_seconds'] as int,
      reason: (map['reason'] as String?) ?? 'unknown',
      mapId: (map['map_id'] as int?) ?? 0,
      channelId: (map['channel_id'] as int?) ?? 0,
      lineId: (map['line_id'] as int?) ?? 0,
      phase: (map['phase'] as int?) ?? 1,
      bossName: (map['boss_name'] as String?) ?? '',
      players: players,
    );
  }
}

class EncounterHistoryService {
  EncounterHistoryService._internal();

  static final EncounterHistoryService _instance =
      EncounterHistoryService._internal();

  factory EncounterHistoryService() => _instance;

  static const Duration retention = Duration(days: 7);
  static const Duration _cleanupInterval = Duration(days: 1);

  Database? _database;
  DateTime? _lastCleanupAt;

  Future<Database> get database async {
    final current = _database;
    if (current != null) return current;

    final dbPath = join(
      await getDatabasesPath(),
      'bluemeter_lite_history.db',
    );

    final opened = await openDatabase(
      dbPath,
      version: 1,
      onCreate: (db, version) async {
        await db.execute('''
          CREATE TABLE encounter_history(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            started_at INTEGER NOT NULL,
            ended_at INTEGER NOT NULL,
            duration_seconds INTEGER NOT NULL,
            reason TEXT NOT NULL,
            map_id INTEGER NOT NULL DEFAULT 0,
            channel_id INTEGER NOT NULL DEFAULT 0,
            line_id INTEGER NOT NULL DEFAULT 0,
            phase INTEGER NOT NULL DEFAULT 1,
            boss_name TEXT NOT NULL DEFAULT '',
            players_json TEXT NOT NULL
          )
        ''');

        await db.execute('''
          CREATE INDEX encounter_history_ended_at
          ON encounter_history(ended_at DESC)
        ''');
      },
    );

    _database = opened;
    return opened;
  }

  Future<void> saveEncounter(Map<String, dynamic> encounter) async {
    final rawPlayers = encounter['players'];
    if (rawPlayers is! List || rawPlayers.isEmpty) return;

    final db = await database;
    await deleteExpired(databaseOverride: db);

    await db.insert(
      'encounter_history',
      <String, Object?>{
        'started_at': encounter['startedAt'] as int,
        'ended_at': encounter['endedAt'] as int,
        'duration_seconds': encounter['durationSeconds'] as int,
        'reason': encounter['reason'] as String,
        'map_id': encounter['mapId'] as int,
        'channel_id': encounter['channelId'] as int,
        'line_id': encounter['lineId'] as int,
        'phase': encounter['phase'] as int,
        'boss_name': encounter['bossName'] as String,
        'players_json': jsonEncode(rawPlayers),
      },
      conflictAlgorithm: ConflictAlgorithm.abort,
    );
  }

  Future<List<LiteEncounterHistory>> loadRecent({int limit = 100}) async {
    final db = await database;
    await deleteExpired(databaseOverride: db);

    final rows = await db.query(
      'encounter_history',
      orderBy: 'ended_at DESC',
      limit: limit,
    );

    return rows.map(LiteEncounterHistory.fromMap).toList(growable: false);
  }

  Future<void> deleteExpired({
    Database? databaseOverride,
    bool force = false,
  }) async {
    final now = DateTime.now();
    final previous = _lastCleanupAt;
    if (!force && previous != null && now.difference(previous) < _cleanupInterval) {
      return;
    }

    final db = databaseOverride ?? await database;
    final cutoff = now.subtract(retention).millisecondsSinceEpoch;
    await db.delete(
      'encounter_history',
      where: 'ended_at < ?',
      whereArgs: <Object?>[cutoff],
    );
    _lastCleanupAt = now;
  }

  Future<void> deleteEncounter(int id) async {
    final db = await database;
    await db.delete(
      'encounter_history',
      where: 'id = ?',
      whereArgs: <Object?>[id],
    );
  }

  Future<void> deleteAll() async {
    final db = await database;
    await db.delete('encounter_history');
  }
}
