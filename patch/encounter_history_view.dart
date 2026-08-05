import 'dart:ui';

import 'package:flutter/material.dart';

import '../core/services/encounter_history_service.dart';

// Scene labels are resolved from the same map IDs already stored with each
// encounter. Existing history entries therefore gain readable names without a
// database migration. Unknown IDs safely fall back to the boss or reset label.
const Map<int, String> _liteSceneNames = <int, String>{
  7: 'Asteria Plains',
  8: 'Asterleeds',
  9: 'Bahamar Highlands',
  10: 'Montegnor Valley',
  11: 'Starland',
  71: 'Duskdye Woods',
  72: 'Everfall Forest',
  73: 'Windhowl Canyon',
  74: 'Underground District',
  75: "Skimmer's Lair",
  76: 'Land of Crimson Illusion',
  91: 'Sunken Corridor',
  92: 'Gloomy Depths',
  6043: 'Chaotic - Soundless City',
  6044: 'Chaotic - Soundless City',
  6045: 'Chaotic - Soundless City',
  6421: 'Chaotic - Soundless City',
  6422: 'Chaotic - Soundless City',
  6423: 'Chaotic - Soundless City',
  6521: 'Chaotic - Mech Facility',
  6522: 'Chaotic - Mech Facility',
  6523: 'Chaotic - Mech Facility',
  6524: 'Chaotic - Mech Facility',
  6525: 'Chaotic - Mech Facility',
  12000: 'Guild Center',
  12011: 'Guild Hunt - Hard',
  12012: 'Guild Hunt - Normal',
  12013: 'Guild Hunt - Easy',
  12014: 'Guild Hunt - Normal',
  12015: 'Guild Hunt - Hard',
  12018: 'Guild Hunt - Normal',
  12019: 'Guild Hunt - Hard',
  12022: 'Guild Hunt - Normal',
  12023: 'Guild Hunt - Hard',
};

String _historyReasonLabel(String reason) {
  return switch (reason) {
    'wipe' => 'Wipe',
    'channel_change' => 'Channel change',
    'line_change' => 'Line change',
    'new_dungeon' => 'New dungeon',
    'map_change' => 'Map change',
    'new_phase' => 'New phase',
    'manual_reset' => 'Manual reset',
    'meter_stopped' => 'Meter stopped',
    _ => reason.replaceAll('_', ' '),
  };
}

String? _historySceneName(LiteEncounterHistory encounter) {
  if (encounter.mapId <= 0) return null;
  return _liteSceneNames[encounter.mapId];
}

String _historyTitle(LiteEncounterHistory encounter) {
  final sceneName = _historySceneName(encounter);
  if (sceneName != null && sceneName.isNotEmpty) return sceneName;

  final bossName = encounter.bossName.trim();
  if (bossName.isNotEmpty) return bossName;

  // A saved map ID is more useful than the reset trigger. This fallback also
  // exposes unknown IDs so they can be added to the scene table later instead
  // of incorrectly labelling the encounter only as "Map change".
  if (encounter.mapId > 0) {
    return 'Unknown location (Map ${encounter.mapId})';
  }

  return _historyReasonLabel(encounter.reason);
}

class EncounterHistoryView extends StatefulWidget {
  const EncounterHistoryView({super.key});

  @override
  State<EncounterHistoryView> createState() =>
      _EncounterHistoryViewState();
}

class _EncounterHistoryViewState extends State<EncounterHistoryView> {
  late Future<List<LiteEncounterHistory>> _historyFuture;

  @override
  void initState() {
    super.initState();
    _reload();
  }

  void _reload() {
    _historyFuture = EncounterHistoryService().loadRecent();
  }

  Future<void> _refresh() async {
    setState(_reload);
    await _historyFuture;
  }

  Future<void> _deleteAll() async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (dialogContext) {
        return AlertDialog(
          title: const Text('Delete encounter history?'),
          content: const Text(
            'This removes every saved encounter from this phone.',
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(dialogContext).pop(false),
              child: const Text('Cancel'),
            ),
            FilledButton(
              onPressed: () => Navigator.of(dialogContext).pop(true),
              child: const Text('Delete all'),
            ),
          ],
        );
      },
    );
    if (confirmed != true) return;

    await EncounterHistoryService().deleteAll();
    if (!mounted) return;
    setState(_reload);
  }

  Future<void> _deleteEncounter(int id) async {
    await EncounterHistoryService().deleteEncounter(id);
    if (!mounted) return;
    setState(_reload);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Encounter history'),
        actions: [
          IconButton(
            tooltip: 'Delete all history',
            onPressed: _deleteAll,
            icon: const Icon(Icons.delete_sweep_outlined),
          ),
        ],
      ),
      body: FutureBuilder<List<LiteEncounterHistory>>(
        future: _historyFuture,
        builder: (context, snapshot) {
          if (snapshot.connectionState != ConnectionState.done) {
            return const Center(child: CircularProgressIndicator());
          }

          if (snapshot.hasError) {
            return Center(
              child: Padding(
                padding: const EdgeInsets.all(24),
                child: Text(
                  'Could not load encounter history.\n${snapshot.error}',
                  textAlign: TextAlign.center,
                ),
              ),
            );
          }

          final history = snapshot.data ?? const <LiteEncounterHistory>[];
          if (history.isEmpty) {
            return RefreshIndicator(
              onRefresh: _refresh,
              child: ListView(
                physics: const AlwaysScrollableScrollPhysics(),
                padding: const EdgeInsets.all(24),
                children: const [
                  SizedBox(height: 90),
                  Icon(Icons.history_rounded, size: 56),
                  SizedBox(height: 14),
                  Text(
                    'No saved encounters yet',
                    textAlign: TextAlign.center,
                    style: TextStyle(
                      fontWeight: FontWeight.w700,
                      fontSize: 18,
                    ),
                  ),
                  SizedBox(height: 8),
                  Text(
                    'Encounters are saved after automatic splits, '
                    'manual resets, and meter stops.\n\n'
                    'Entries older than seven days are deleted '
                    'automatically.',
                    textAlign: TextAlign.center,
                  ),
                ],
              ),
            );
          }

          return RefreshIndicator(
            onRefresh: _refresh,
            child: ListView.separated(
              padding: const EdgeInsets.fromLTRB(16, 12, 16, 28),
              itemCount: history.length + 1,
              separatorBuilder: (_, __) => const SizedBox(height: 8),
              itemBuilder: (context, index) {
                if (index == 0) {
                  return const Padding(
                    padding: EdgeInsets.only(
                      left: 4,
                      right: 4,
                      bottom: 4,
                    ),
                    child: Text(
                      'Saved locally • automatically deleted after 7 days',
                      style: TextStyle(fontSize: 12),
                    ),
                  );
                }

                final encounter = history[index - 1];
                return _EncounterHistoryCard(
                  encounter: encounter,
                  onDelete: () => _deleteEncounter(encounter.id),
                );
              },
            ),
          );
        },
      ),
    );
  }
}

class _EncounterHistoryCard extends StatelessWidget {
  const _EncounterHistoryCard({
    required this.encounter,
    required this.onDelete,
  });

  final LiteEncounterHistory encounter;
  final VoidCallback onDelete;

  String _formatDate(DateTime date) {
    String two(int value) => value.toString().padLeft(2, '0');
    return '${date.year}-${two(date.month)}-${two(date.day)} '
        '${two(date.hour)}:${two(date.minute)}';
  }

  String _formatDuration(int seconds) {
    final safe = seconds < 0 ? 0 : seconds;
    final minutes = safe ~/ 60;
    final remainder = safe % 60;
    return '$minutes:${remainder.toString().padLeft(2, '0')}';
  }

  Map<String, dynamic>? _topDamagePlayer() {
    final players = encounter.players
        .where(
          (player) =>
              ((player['totalDamage'] as num?) ?? 0).toDouble() > 0,
        )
        .map((player) => Map<String, dynamic>.from(player))
        .toList(growable: true)
      ..sort((a, b) {
        final left = ((a['totalDamage'] as num?) ?? 0).toDouble();
        final right = ((b['totalDamage'] as num?) ?? 0).toDouble();
        return right.compareTo(left);
      });
    return players.isEmpty ? null : players.first;
  }

  @override
  Widget build(BuildContext context) {
    final topPlayer = _topDamagePlayer();
    final title = _historyTitle(encounter);
    final sceneName = _historySceneName(encounter);
    final sceneParts = <String>[
      if (encounter.mapId > 0 && sceneName == null)
        'Map ${encounter.mapId}',
      if (encounter.channelId > 0) 'Channel ${encounter.channelId}',
      if (encounter.lineId > 0) 'Line ${encounter.lineId}',
      if (encounter.phase > 0) 'Phase ${encounter.phase}',
    ];

    return Card(
      clipBehavior: Clip.antiAlias,
      child: InkWell(
        onTap: () {
          Navigator.of(context).push(
            MaterialPageRoute<void>(
              builder: (_) => EncounterHistoryDetailView(
                encounter: encounter,
              ),
            ),
          );
        },
        child: Padding(
          padding: const EdgeInsets.fromLTRB(16, 14, 8, 14),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Padding(
                padding: EdgeInsets.only(top: 3),
                child: Icon(Icons.history_rounded),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      title,
                      style: const TextStyle(
                        fontWeight: FontWeight.w800,
                        fontSize: 16,
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      '${_formatDate(encounter.endedAt)}'
                      ' • ${_formatDuration(encounter.durationSeconds)}'
                      ' • ${_historyReasonLabel(encounter.reason)}',
                    ),
                    if (sceneParts.isNotEmpty) ...[
                      const SizedBox(height: 3),
                      Text(sceneParts.join(' • ')),
                    ],
                    if (topPlayer != null) ...[
                      const SizedBox(height: 6),
                      Text(
                        'Top DPS: ${topPlayer['name'] ?? 'Unknown'}'
                        ' • ${_historyFormatNumber(
                          (topPlayer['totalDamage'] as num?) ?? 0,
                        )}',
                        style: const TextStyle(fontWeight: FontWeight.w600),
                      ),
                    ],
                  ],
                ),
              ),
              IconButton(
                tooltip: 'Delete encounter',
                onPressed: onDelete,
                icon: const Icon(Icons.delete_outline_rounded),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class EncounterHistoryDetailView extends StatelessWidget {
  const EncounterHistoryDetailView({
    required this.encounter,
    super.key,
  });

  final LiteEncounterHistory encounter;

  @override
  Widget build(BuildContext context) {
    return DefaultTabController(
      length: 3,
      child: Scaffold(
        appBar: AppBar(
          title: Text(_historyTitle(encounter)),
          bottom: const TabBar(
            tabs: [
              Tab(text: 'DPS'),
              Tab(text: 'Healing'),
              Tab(text: 'Tanking'),
            ],
          ),
        ),
        body: TabBarView(
          children: [
            _HistoryMetricList(
              players: encounter.players,
              totalKey: 'totalDamage',
              rateKey: 'dps',
              emptyMessage: 'No damage recorded',
            ),
            _HistoryMetricList(
              players: encounter.players,
              totalKey: 'totalHealing',
              rateKey: 'hps',
              emptyMessage: 'No healing recorded',
            ),
            _HistoryMetricList(
              players: encounter.players,
              totalKey: 'totalTaken',
              rateKey: 'takenDps',
              emptyMessage: 'No damage taken recorded',
            ),
          ],
        ),
      ),
    );
  }
}

class _HistoryMetricList extends StatelessWidget {
  const _HistoryMetricList({
    required this.players,
    required this.totalKey,
    required this.rateKey,
    required this.emptyMessage,
  });

  final List<Map<String, dynamic>> players;
  final String totalKey;
  final String rateKey;
  final String emptyMessage;

  @override
  Widget build(BuildContext context) {
    final ranked = players
        .where(
          (player) => ((player[totalKey] as num?) ?? 0).toDouble() > 0,
        )
        .map((entry) => Map<String, dynamic>.from(entry))
        .toList(growable: true)
      ..sort((a, b) {
        final left = ((a[totalKey] as num?) ?? 0).toDouble();
        final right = ((b[totalKey] as num?) ?? 0).toDouble();
        return right.compareTo(left);
      });

    if (ranked.isEmpty) {
      return Center(child: Text(emptyMessage));
    }

    final groupTotal = ranked.fold<double>(
      0,
      (sum, player) =>
          sum + ((player[totalKey] as num?) ?? 0).toDouble(),
    );

    return ListView.separated(
      padding: const EdgeInsets.all(14),
      itemCount: ranked.length,
      separatorBuilder: (_, __) => const SizedBox(height: 5),
      itemBuilder: (context, index) {
        final player = ranked[index];
        final total = ((player[totalKey] as num?) ?? 0).toDouble();
        final rate = ((player[rateKey] as num?) ?? 0).toDouble();
        final percent = groupTotal > 0 ? total / groupTotal * 100 : 0.0;
        final isMe = player['isMe'] == true;
        final rawName = (player['name'] as String?)?.trim();
        final name = rawName == null || rawName.isEmpty ? 'Unknown' : rawName;
        final specialization =
            (player['className'] as String?)?.trim() ?? '';

        return Container(
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
          decoration: BoxDecoration(
            color: isMe
                ? Theme.of(context)
                    .colorScheme
                    .primaryContainer
                    .withValues(alpha: 0.45)
                : Theme.of(context)
                    .colorScheme
                    .surfaceContainerHighest
                    .withValues(alpha: 0.55),
            borderRadius: BorderRadius.circular(10),
          ),
          child: Row(
            children: [
              SizedBox(
                width: 32,
                child: Text(
                  '${index + 1}.',
                  style: const TextStyle(fontWeight: FontWeight.w700),
                ),
              ),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      '${isMe ? '★ ' : ''}$name',
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(fontWeight: FontWeight.w700),
                    ),
                    if (specialization.isNotEmpty)
                      Text(
                        specialization,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: Theme.of(context).textTheme.bodySmall,
                      ),
                  ],
                ),
              ),
              const SizedBox(width: 8),
              Text(
                '${_historyFormatNumber(total)} '
                '(${_historyFormatNumber(rate)})',
                style: const TextStyle(
                  fontWeight: FontWeight.w700,
                  fontFeatures: [FontFeature.tabularFigures()],
                ),
              ),
              const SizedBox(width: 10),
              SizedBox(
                width: 42,
                child: Text(
                  '${percent.toStringAsFixed(percent < 1 ? 1 : 0)}%',
                  textAlign: TextAlign.right,
                  style: const TextStyle(
                    fontWeight: FontWeight.w700,
                    fontFeatures: [FontFeature.tabularFigures()],
                  ),
                ),
              ),
            ],
          ),
        );
      },
    );
  }
}

String _historyFormatNumber(num number) {
  final value = number.toDouble().abs();

  if (value >= 1000000000) {
    final scaled = value / 1000000000;
    return '${scaled < 100 ? scaled.toStringAsFixed(1) : scaled.toStringAsFixed(0)}B';
  }
  if (value >= 1000000) {
    final scaled = value / 1000000;
    return '${scaled < 100 ? scaled.toStringAsFixed(1) : scaled.toStringAsFixed(0)}M';
  }
  if (value >= 1000) {
    final scaled = value / 1000;
    return '${scaled < 100 ? scaled.toStringAsFixed(1) : scaled.toStringAsFixed(0)}K';
  }
  return value.toStringAsFixed(0);
}
