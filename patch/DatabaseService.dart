import 'dart:async';

import 'package:fixnum/fixnum.dart';
import 'package:path/path.dart';
import 'package:sqflite/sqflite.dart';

import '../models/player_info.dart';
import 'logger_service.dart';

/// Lite player metadata cache.
///
/// Player sync packets often update name/class/power/level back-to-back. The
/// upstream implementation opened a transaction, queried existence, wrote a
/// row and ran cleanup for every setter. Lite coalesces all updates for a UID
/// and writes one UPSERT after the burst settles.
class DatabaseService {
  static final DatabaseService _instance = DatabaseService._internal();
  factory DatabaseService() => _instance;
  DatabaseService._internal();

  static Database? _database;
  static const Duration _writeDebounce = Duration(seconds: 2);
  static const Duration _cleanupInterval = Duration(days: 1);

  final LoggerService _logger = LoggerService();
  final Map<String, PlayerInfo> _pendingPlayers = <String, PlayerInfo>{};
  Timer? _flushTimer;
  DateTime? _lastCleanupAt;
  bool _flushInProgress = false;

  Future<Database> get database async {
    final current = _database;
    if (current != null) return current;
    _database = await _initDatabase();
    return _database!;
  }

  Future<Database> _initDatabase() async {
    final dbPath = join(await getDatabasesPath(), 'bluemeter.db');
    return openDatabase(
      dbPath,
      version: 1,
      onCreate: _onCreate,
    );
  }

  Future<void> _onCreate(Database db, int version) async {
    await db.execute('''
      CREATE TABLE players(
        uid TEXT PRIMARY KEY,
        name TEXT,
        professionId INTEGER,
        combatPower INTEGER,
        level INTEGER,
        rankLevel INTEGER,
        critical INTEGER,
        lucky INTEGER,
        maxHp TEXT,
        hp TEXT,
        last_seen INTEGER
      )
    ''');
  }

  void savePlayer(PlayerInfo player) {
    _pendingPlayers[player.uid.toString()] = player;
    _flushTimer ??= Timer(_writeDebounce, () {
      _flushTimer = null;
      unawaited(flushPending());
    });
  }

  Future<void> flushPending() async {
    if (_flushInProgress || _pendingPlayers.isEmpty) return;

    _flushInProgress = true;
    final pending = Map<String, PlayerInfo>.from(_pendingPlayers);
    _pendingPlayers.clear();

    try {
      final db = await database;
      final seenAt = DateTime.now().millisecondsSinceEpoch;

      await db.transaction((txn) async {
        for (final player in pending.values) {
          await txn.rawInsert(
            '''
            INSERT INTO players(
              uid, name, professionId, combatPower, level, rankLevel,
              critical, lucky, maxHp, hp, last_seen
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(uid) DO UPDATE SET
              name = COALESCE(excluded.name, players.name),
              professionId = CASE
                WHEN excluded.professionId IS NOT NULL
                     AND excluded.professionId != 0
                THEN excluded.professionId ELSE players.professionId END,
              combatPower = CASE
                WHEN excluded.combatPower IS NOT NULL
                     AND excluded.combatPower != 0
                THEN excluded.combatPower ELSE players.combatPower END,
              level = CASE
                WHEN excluded.level IS NOT NULL AND excluded.level != 0
                THEN excluded.level ELSE players.level END,
              rankLevel = CASE
                WHEN excluded.rankLevel IS NOT NULL AND excluded.rankLevel != 0
                THEN excluded.rankLevel ELSE players.rankLevel END,
              critical = CASE
                WHEN excluded.critical IS NOT NULL AND excluded.critical != 0
                THEN excluded.critical ELSE players.critical END,
              lucky = CASE
                WHEN excluded.lucky IS NOT NULL AND excluded.lucky != 0
                THEN excluded.lucky ELSE players.lucky END,
              maxHp = COALESCE(excluded.maxHp, players.maxHp),
              last_seen = excluded.last_seen
            ''',
            <Object?>[
              player.uid.toString(),
              player.name,
              player.professionId,
              player.combatPower,
              player.level,
              player.rankLevel,
              player.critical,
              player.lucky,
              player.maxHp?.toString(),
              null,
              seenAt,
            ],
          );
        }
      });

      await _cleanupIfDue(db);
    } catch (error) {
      _logger.error('Error persisting player cache', error: error);
      // Keep only the latest object per UID if the database was temporarily
      // unavailable. A later live update will retry naturally.
      for (final entry in pending.entries) {
        _pendingPlayers.putIfAbsent(entry.key, () => entry.value);
      }
    } finally {
      _flushInProgress = false;
      if (_pendingPlayers.isNotEmpty && _flushTimer == null) {
        _flushTimer = Timer(_writeDebounce, () {
          _flushTimer = null;
          unawaited(flushPending());
        });
      }
    }
  }

  Future<void> _cleanupIfDue(Database db) async {
    final now = DateTime.now();
    final previous = _lastCleanupAt;
    if (previous != null && now.difference(previous) < _cleanupInterval) {
      return;
    }

    await db.rawDelete(
      'DELETE FROM players WHERE uid NOT IN '
      '(SELECT uid FROM players ORDER BY last_seen DESC LIMIT 100)',
    );
    _lastCleanupAt = now;
  }

  Future<PlayerInfo?> getPlayer(Int64 uid) async {
    try {
      final db = await database;
      final maps = await db.query(
        'players',
        where: 'uid = ?',
        whereArgs: <Object?>[uid.toString()],
        limit: 1,
      );

      if (maps.isEmpty) return null;
      final map = maps.first;
      return PlayerInfo(
        uid: Int64.parseInt(map['uid'] as String),
        name: map['name'] as String?,
        professionId: map['professionId'] as int?,
        combatPower: map['combatPower'] as int?,
        level: map['level'] as int?,
        rankLevel: map['rankLevel'] as int?,
        critical: map['critical'] as int?,
        lucky: map['lucky'] as int?,
        maxHp: map['maxHp'] != null
            ? Int64.parseInt(map['maxHp'] as String)
            : null,
        hp: map['hp'] != null ? Int64.parseInt(map['hp'] as String) : null,
      );
    } catch (error) {
      _logger.error('Error reading player cache', error: error);
      return null;
    }
  }
}
