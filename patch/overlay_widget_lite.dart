class OverlayWidget extends StatefulWidget {
  const OverlayWidget({super.key});

  @override
  State<OverlayWidget> createState() => _OverlayWidgetState();
}

class _OverlayWidgetState extends State<OverlayWidget> {
  List<Map<String, dynamic>> _players = const [];
  int _combatTime = 0;
  StreamSubscription? _overlaySubscription;

  @override
  void initState() {
    super.initState();
    _overlaySubscription = FlutterOverlayWindow.overlayListener.listen((event) {
      if (!mounted || event is! Map) return;

      final rawPlayers = event['players'];
      final rawCombatTime = event['combatTime'];

      setState(() {
        if (rawPlayers is List) {
          _players = rawPlayers
              .whereType<Map>()
              .map((entry) => Map<String, dynamic>.from(entry))
              .toList(growable: false);
        }
        if (rawCombatTime is num) {
          _combatTime = rawCombatTime.toInt();
        }
      });
    });
  }

  @override
  void dispose() {
    _overlaySubscription?.cancel();
    super.dispose();
  }

  String _formatNumber(num number) {
    if (number >= 1000000000) {
      return '${(number / 1000000000).toStringAsFixed(2)}b';
    }
    if (number >= 1000000) {
      final value = number / 1000000;
      return '${value < 100 ? value.toStringAsFixed(2) : value.toStringAsFixed(1)}m';
    }
    if (number >= 1000) {
      final value = number / 1000;
      return '${value < 100 ? value.toStringAsFixed(2) : value.toStringAsFixed(1)}k';
    }
    return number.toStringAsFixed(0);
  }

  String _formatTime(int seconds) {
    final minutes = seconds ~/ 60;
    final remainder = seconds % 60;
    return '${minutes.toString().padLeft(2, '0')}:'
        '${remainder.toString().padLeft(2, '0')}';
  }

  void _resetEncounter() {
    final sendPort =
        IsolateNameServer.lookupPortByName('overlay_communication_port');
    sendPort?.send('RESET');
  }

  @override
  Widget build(BuildContext context) {
    final ranked = _players
        .where((player) => ((player['total'] as num?) ?? 0) > 0)
        .toList(growable: false)
      ..sort((a, b) {
        final aDps = ((a['dps'] as num?) ?? 0).toDouble();
        final bDps = ((b['dps'] as num?) ?? 0).toDouble();
        return bDps.compareTo(aDps);
      });

    final count = ranked.length > 8 ? 8 : ranked.length;
    final double maxDps = count > 0
        ? ((ranked.first['dps'] as num?) ?? 1)
            .toDouble()
            .clamp(1.0, double.infinity)
            .toDouble()
        : 1.0;

    return Material(
      color: Colors.transparent,
      child: Container(
        decoration: BoxDecoration(
          color: const Color(0xE6121418),
          border: Border.all(color: const Color(0x553A86FF), width: 1),
          borderRadius: BorderRadius.circular(6),
        ),
        clipBehavior: Clip.antiAlias,
        child: Column(
          children: [
            Container(
              height: 28,
              padding: const EdgeInsets.only(left: 9, right: 4),
              color: const Color(0xF01B1E24),
              child: Row(
                children: [
                  const Text(
                    'DPS',
                    style: TextStyle(
                      color: Color(0xFF75A7FF),
                      fontWeight: FontWeight.w700,
                      fontSize: 12,
                    ),
                  ),
                  const Spacer(),
                  Text(
                    _formatTime(_combatTime),
                    style: const TextStyle(
                      color: Color(0xFFCED4E0),
                      fontSize: 11,
                      fontFeatures: [FontFeature.tabularFigures()],
                    ),
                  ),
                  const SizedBox(width: 4),
                  IconButton(
                    onPressed: _resetEncounter,
                    padding: EdgeInsets.zero,
                    constraints: const BoxConstraints.tightFor(
                      width: 25,
                      height: 25,
                    ),
                    icon: const Icon(
                      Icons.refresh,
                      size: 15,
                      color: Color(0xFFAAB2C2),
                    ),
                  ),
                ],
              ),
            ),
            Expanded(
              child: count == 0
                  ? const Center(
                      child: Text(
                        'Waiting for combat…',
                        style: TextStyle(
                          color: Color(0xFF8B93A3),
                          fontSize: 11,
                        ),
                      ),
                    )
                  : ListView.builder(
                      padding: const EdgeInsets.symmetric(vertical: 2),
                      physics: const NeverScrollableScrollPhysics(),
                      itemCount: count,
                      itemExtent: 23,
                      itemBuilder: (context, index) {
                        final player = ranked[index];
                        final dps = ((player['dps'] as num?) ?? 0).toDouble();
                        final double ratio =
                            (dps / maxDps).clamp(0.0, 1.0).toDouble();
                        final isMe = player['isMe'] == true;
                        final name = (player['name'] as String?)?.trim();
                        final displayName =
                            (name == null || name.isEmpty) ? 'Unknown' : name;

                        return Padding(
                          padding: const EdgeInsets.symmetric(
                            horizontal: 4,
                            vertical: 1,
                          ),
                          child: Stack(
                            children: [
                              Positioned.fill(
                                child: FractionallySizedBox(
                                  alignment: Alignment.centerLeft,
                                  widthFactor: ratio,
                                  child: DecoratedBox(
                                    decoration: BoxDecoration(
                                      color: isMe
                                          ? const Color(0x4D3A86FF)
                                          : const Color(0x263A86FF),
                                      borderRadius: BorderRadius.circular(3),
                                    ),
                                  ),
                                ),
                              ),
                              Padding(
                                padding:
                                    const EdgeInsets.symmetric(horizontal: 5),
                                child: Row(
                                  children: [
                                    SizedBox(
                                      width: 18,
                                      child: Text(
                                        '${index + 1}',
                                        style: const TextStyle(
                                          color: Color(0xFF7F8796),
                                          fontSize: 10,
                                        ),
                                      ),
                                    ),
                                    Expanded(
                                      child: Text(
                                        displayName,
                                        maxLines: 1,
                                        overflow: TextOverflow.ellipsis,
                                        style: TextStyle(
                                          color: isMe
                                              ? const Color(0xFFFFFFFF)
                                              : const Color(0xFFD5DAE4),
                                          fontWeight: isMe
                                              ? FontWeight.w700
                                              : FontWeight.w500,
                                          fontSize: 11,
                                        ),
                                      ),
                                    ),
                                    const SizedBox(width: 5),
                                    Text(
                                      _formatNumber(dps),
                                      textAlign: TextAlign.right,
                                      style: const TextStyle(
                                        color: Color(0xFFFFFFFF),
                                        fontWeight: FontWeight.w700,
                                        fontSize: 11,
                                        fontFeatures: [
                                          FontFeature.tabularFigures(),
                                        ],
                                      ),
                                    ),
                                  ],
                                ),
                              ),
                            ],
                          ),
                        );
                      },
                    ),
            ),
          ],
        ),
      ),
    );
  }
}
