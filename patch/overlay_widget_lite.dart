enum _LiteViewMode {
  compact,
  expanded,
}

class OverlayWidget extends StatefulWidget {
  const OverlayWidget({super.key});

  @override
  State<OverlayWidget> createState() => _OverlayWidgetState();
}

class _OverlayWidgetState extends State<OverlayWidget> {
  static const int _maxDisplayedPlayers = 20;
  static const double _compactMinimumWidth = 180;
  static const double _compactMinimumHeight = 56;
  static const double _expandedMinimumWidth = 360;
  static const double _expandedMinimumHeight = 96;
  static const double _maximumWidth = 1200;
  static const double _maximumHeight = 620;

  List<Map<String, dynamic>> _players = const [];
  int _combatTime = 0;
  StreamSubscription? _overlaySubscription;
  _LiteViewMode _viewMode = _LiteViewMode.expanded;
  int _lastResizeRequestMs = 0;

  double _windowX = 8;
  double _windowY = 80;
  Size? _resizeStartSize;
  Offset? _resizeStartPointer;

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

  int get _activePlayerCount {
    return _players
        .where((player) => ((player['total'] as num?) ?? 0) > 0)
        .length;
  }

  String _formatNumber(num number) {
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

  String _formatTime(int seconds) {
    final safeSeconds = seconds < 0 ? 0 : seconds;
    final hours = safeSeconds ~/ 3600;
    final minutes = (safeSeconds % 3600) ~/ 60;
    final remainder = safeSeconds % 60;

    if (hours > 0) {
      return '${hours.toString().padLeft(2, '0')}:'
          '${minutes.toString().padLeft(2, '0')}:'
          '${remainder.toString().padLeft(2, '0')}';
    }

    return '${minutes.toString().padLeft(2, '0')}:'
        '${remainder.toString().padLeft(2, '0')}';
  }

  void _resetEncounter() {
    final sendPort =
        IsolateNameServer.lookupPortByName('overlay_communication_port');
    sendPort?.send('RESET');
  }


List<Map<String, dynamic>> _rankPlayers() {
  final ranked = _players
      .where((player) => ((player['total'] as num?) ?? 0) > 0)
      .map((player) => Map<String, dynamic>.from(player))
      .toList(growable: true)
    ..sort((a, b) {
      final aTotal = ((a['total'] as num?) ?? 0).toDouble();
      final bTotal = ((b['total'] as num?) ?? 0).toDouble();
      final totalComparison = bTotal.compareTo(aTotal);
      if (totalComparison != 0) return totalComparison;

      final aDps = ((a['dps'] as num?) ?? 0).toDouble();
      final bDps = ((b['dps'] as num?) ?? 0).toDouble();
      final dpsComparison = bDps.compareTo(aDps);
      if (dpsComparison != 0) return dpsComparison;

      final aName = (a['name'] as String?) ?? '';
      final bName = (b['name'] as String?) ?? '';
      return aName.compareTo(bName);
    });

  for (var index = 0; index < ranked.length; index++) {
    ranked[index]['_rank'] = index + 1;
  }

  return ranked;
}

  List<Map<String, dynamic>> _selectVisiblePlayers(
    List<Map<String, dynamic>> ranked,
    int limit,
  ) {
    if (ranked.length <= limit) {
      return List<Map<String, dynamic>>.from(ranked, growable: false);
    }

    final visible = ranked.take(limit).toList(growable: true);
    final myIndex = ranked.indexWhere((player) => player['isMe'] == true);

    // Always preserve the local player, even if they are below the normal cut.
    if (myIndex >= limit && visible.isNotEmpty) {
      visible[visible.length - 1] = ranked[myIndex];
    }

    return List<Map<String, dynamic>>.from(visible, growable: false);
  }


int _visibleLimitForMode() {
  return _maxDisplayedPlayers;
}

String _modeLabel() {
  return _viewMode == _LiteViewMode.compact ? 'C' : 'E';
}





double get _minimumWidthForCurrentMode {
  return _viewMode == _LiteViewMode.compact
      ? _compactMinimumWidth
      : _expandedMinimumWidth;
}

double get _minimumHeightForCurrentMode {
  return _viewMode == _LiteViewMode.compact
      ? _compactMinimumHeight
      : _expandedMinimumHeight;
}

Future<void> _resizeOverlay(double width, double height) async {
  final safeWidth = width
      .clamp(_minimumWidthForCurrentMode, _maximumWidth)
      .toInt();
  final safeHeight = height
      .clamp(_minimumHeightForCurrentMode, _maximumHeight)
      .toInt();

  try {
    await FlutterOverlayWindow.resizeOverlay(
      safeWidth,
      safeHeight,
      false,
    );
  } catch (_) {
    // Keep the DPS meter usable even if a device rejects a resize request.
  }
}


void _toggleViewMode() {
  final nextMode = _viewMode == _LiteViewMode.compact
      ? _LiteViewMode.expanded
      : _LiteViewMode.compact;

  setState(() {
    _viewMode = nextMode;
  });

  if (nextMode == _LiteViewMode.compact) {
    // Compact always begins at its true minimum size.
    _resizeOverlay(
      _compactMinimumWidth,
      _compactMinimumHeight,
    );
  } else {
    // Expanded always begins at the requested minimum presentation size.
    _resizeOverlay(360, 180);
  }
}

  void _moveWindow(DragUpdateDetails details) {
    _windowX = (_windowX + details.delta.dx).clamp(0.0, 10000.0);
    _windowY = (_windowY + details.delta.dy).clamp(0.0, 10000.0);

    FlutterOverlayWindow.moveOverlay(
      OverlayPosition(_windowX, _windowY),
    );
  }

  void _startManualResize(
    BuildContext context,
    DragStartDetails details,
  ) {
    _resizeStartSize = MediaQuery.of(context).size;
    _resizeStartPointer = details.globalPosition;

  }

  void _updateManualResize(DragUpdateDetails details) {
    final startSize = _resizeStartSize;
    final startPointer = _resizeStartPointer;
    if (startSize == null || startPointer == null) return;

    final difference = details.globalPosition - startPointer;
    final width =
        (startSize.width + difference.dx)
            .clamp(_minimumWidthForCurrentMode, _maximumWidth);
    final height =
        (startSize.height + difference.dy)
            .clamp(_minimumHeightForCurrentMode, _maximumHeight);

    final now = DateTime.now().millisecondsSinceEpoch;
    if (now - _lastResizeRequestMs < 32) return;

    _lastResizeRequestMs = now;
    _resizeOverlay(width, height);
  }

  void _finishManualResize(DragEndDetails details) {
    _resizeStartSize = null;
    _resizeStartPointer = null;
  }

  Widget _buildHeaderButton({
    required Widget child,
    required VoidCallback onTap,
    double size = 25,
  }) {
    return GestureDetector(
      behavior: HitTestBehavior.opaque,
      onTap: onTap,
      child: SizedBox(
        width: size,
        height: size,
        child: Center(child: child),
      ),
    );
  }

  Widget _buildHeader({
    required double headerHeight,
    required double headerFontSize,
    required int totalPlayers,
  }) {
    final playerLabel = totalPlayers > _maxDisplayedPlayers
        ? '$_maxDisplayedPlayers+'
        : '$totalPlayers';

    return GestureDetector(
      behavior: HitTestBehavior.opaque,
      onPanUpdate: _moveWindow,
      child: Container(
        height: headerHeight,
        padding: const EdgeInsets.only(left: 9, right: 3),
        color: const Color(0xF01B1E24),
        child: Row(
          children: [
            Flexible(
              child: FittedBox(
                fit: BoxFit.scaleDown,
                alignment: Alignment.centerLeft,
                child: Text(
                  'DPS',
                  maxLines: 1,
                  style: TextStyle(
                    color: const Color(0xFF82AEFF),
                    fontWeight: FontWeight.w800,
                    fontSize: headerFontSize,
                    letterSpacing: 0.3,
                  ),
                ),
              ),
            ),
            const SizedBox(width: 6),
            Container(
              constraints: const BoxConstraints(minWidth: 22),
              padding: const EdgeInsets.symmetric(horizontal: 5, vertical: 2),
              decoration: BoxDecoration(
                color: const Color(0x243A86FF),
                borderRadius: BorderRadius.circular(9),
              ),
              child: Text(
                playerLabel,
                textAlign: TextAlign.center,
                style: TextStyle(
                  color: const Color(0xFFAEC8FF),
                  fontWeight: FontWeight.w700,
                  fontSize: (headerFontSize - 2).clamp(9, 13).toDouble(),
                  fontFeatures: const [FontFeature.tabularFigures()],
                ),
              ),
            ),
            const Spacer(),
            Text(
              _formatTime(_combatTime),
              maxLines: 1,
              style: TextStyle(
                color: const Color(0xFFD3D8E3),
                fontWeight: FontWeight.w600,
                fontSize: (headerFontSize - 1).clamp(10, 14).toDouble(),
                fontFeatures: const [FontFeature.tabularFigures()],
              ),
            ),
            const SizedBox(width: 4),
            _buildHeaderButton(
              onTap: _toggleViewMode,
              child: Container(
                constraints: const BoxConstraints(minWidth: 21),
                padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 2),
                decoration: BoxDecoration(
                  color: _viewMode == _LiteViewMode.expanded
                      ? const Color(0x423A86FF)
                      : const Color(0x1FFFFFFF),
                  borderRadius: BorderRadius.circular(5),
                  border: Border.all(
                    color: _viewMode == _LiteViewMode.expanded
                        ? const Color(0x88699DFF)
                        : const Color(0x22FFFFFF),
                    width: 0.7,
                  ),
                ),
                child: Text(
                  _modeLabel(),
                  textAlign: TextAlign.center,
                  style: TextStyle(
                    color: const Color(0xFFDDE6F7),
                    fontWeight: FontWeight.w800,
                    fontSize: (headerFontSize - 2).clamp(9, 12).toDouble(),
                    fontFeatures: const [FontFeature.tabularFigures()],
                  ),
                ),
              ),
            ),
            _buildHeaderButton(
              onTap: _resetEncounter,
              child: Icon(
                Icons.refresh_rounded,
                size: (headerHeight * 0.52).clamp(14, 19).toDouble(),
                color: const Color(0xFFAAB2C2),
              ),
            ),
          ],
        ),
      ),
    );
  }



Color _classColor(String className) {
  switch (className) {
    case 'Stormblade':
    case 'Iaido':
    case 'Moonstrike':
      return const Color(0xFF805AA3);

    case 'Frost Mage':
    case 'Icicle':
    case 'Frostbeam':
      return const Color(0xFF7788D4);

    case 'Twin Striker':
    case 'Formless Expertise':
    case 'Crimson Expertise':
      return const Color(0xFFBA7F12);

    case 'Wind Knight':
    case 'Vanguard':
    case 'Skyward':
      return const Color(0xFF799A9C);

    case 'Verdant Oracle':
    case 'Smite':
    case 'Lifebind':
      return const Color(0xFF639C70);

    case 'Heavy Guardian':
    case 'Earthfort':
    case 'Block':
      return const Color(0xFF7D6033);

    case 'Marksman':
    case 'Wildpack':
    case 'Falconry':
      return const Color(0xFF8E8B47);

    case 'Shield Knight':
    case 'Recovery':
    case 'Shield':
      return const Color(0xFF9C9B75);

    case 'Beat Performer':
    case 'Dissonance':
    case 'Concerto':
      return const Color(0xFF9C5353);

    case 'Lucy':
    case 'Natsu':
      return const Color(0xFFDB8787);

    case 'Dorothy':
      return const Color(0xFFB87552);

    case 'Dark Spirit Dance Ritual Blade':
      return const Color(0xFF8D6A9F);

    default:
      return const Color(0xFF67AEF6);
  }
}

String _expandedIdentity(Map<String, dynamic> player) {
  final rawName = (player['name'] as String?)?.trim();
  final name = (rawName == null || rawName.isEmpty) ? 'Unknown' : rawName;
  final className = (player['className'] as String?)?.trim() ?? '';
  final combatPower = ((player['combatPower'] as num?) ?? 0).toInt();
  final illusionBreakingStrength =
      ((player['illusionBreakingStrength'] as num?) ?? 0).toInt();

  final ownerPrefix = player['isMe'] == true ? '★ ' : '';
  final classPart =
      className.isEmpty || className == 'Unknown' ? '' : ' — $className';

  String scorePart = '';
  if (combatPower > 0 && illusionBreakingStrength > 0) {
    scorePart = ' ($combatPower+$illusionBreakingStrength)';
  } else if (combatPower > 0) {
    // The game may not AOI-sync this Season 3 value for other players.
    scorePart = ' ($combatPower+—)';
  } else if (illusionBreakingStrength > 0) {
    scorePart = ' (—+$illusionBreakingStrength)';
  }

  return '$ownerPrefix$name$classPart$scorePart';
}

String _compactIdentity(Map<String, dynamic> player) {
  final rawName = (player['name'] as String?)?.trim();
  final name = (rawName == null || rawName.isEmpty) ? 'Unknown' : rawName;
  final ownerPrefix = player['isMe'] == true ? '★ ' : '';
  return '$ownerPrefix$name';
}

String _formatContribution(double percentage) {
  if (percentage <= 0) return '0%';
  if (percentage < 1) return '${percentage.toStringAsFixed(1)}%';
  return '${percentage.toStringAsFixed(0)}%';
}

Widget _buildPlayerRow({
  required Map<String, dynamic> player,
  required double maxTotal,
  required double groupTotal,
  required double rowHeight,
  required double columnWidth,
}) {
  final total = ((player['total'] as num?) ?? 0).toDouble();
  final dps = ((player['dps'] as num?) ?? 0).toDouble();
  final ratio = (total / maxTotal).clamp(0.0, 1.0).toDouble();
  final contribution = groupTotal > 0 ? (total / groupTotal * 100.0) : 0.0;
  final isMe = player['isMe'] == true;
  final rank = (player['_rank'] as int?) ?? 0;
  final className = (player['className'] as String?)?.trim() ?? '';
  final classColor = _classColor(className);

  final compact = _viewMode == _LiteViewMode.compact;
  final identity = compact ? _compactIdentity(player) : _expandedIdentity(player);

  final fontSize = compact
      ? (rowHeight * 0.58).clamp(5.6, 7.4).toDouble()
      : (rowHeight * 0.58).clamp(6.2, 8.0).toDouble();
  final rankFontSize = compact
      ? (fontSize - 0.2).clamp(5.3, 7.1).toDouble()
      : (fontSize - 0.2).clamp(5.9, 7.7).toDouble();
  final metricFontSize = compact
      ? (fontSize + 0.05).clamp(5.7, 7.5).toDouble()
      : (fontSize + 0.05).clamp(6.3, 8.1).toDouble();

  final rankWidth = compact
      ? (columnWidth * 0.105).clamp(18.0, 30.0).toDouble()
      : (columnWidth * 0.065).clamp(24.0, 34.0).toDouble();
  final metricWidth = compact
      ? (columnWidth * 0.36).clamp(64.0, 142.0).toDouble()
      : (columnWidth * 0.31).clamp(108.0, 176.0).toDouble();
  final percentageWidth = compact
      ? (columnWidth * 0.12).clamp(24.0, 42.0).toDouble()
      : (columnWidth * 0.075).clamp(32.0, 48.0).toDouble();

  return Padding(
    padding: EdgeInsets.symmetric(
      horizontal: (columnWidth * 0.008).clamp(2.0, 5.0).toDouble(),
      vertical: 0,
    ),
    child: Stack(
      children: [
        Positioned.fill(
          child: DecoratedBox(
            decoration: BoxDecoration(
              color: isMe
                  ? const Color(0x2BFFC857)
                  : const Color(0x121A1E27),
              borderRadius: BorderRadius.circular(2.5),
              border: isMe
                  ? Border.all(
                      color: const Color(0x88FFC857),
                      width: 0.7,
                    )
                  : null,
            ),
          ),
        ),
        Positioned.fill(
          child: FractionallySizedBox(
            alignment: Alignment.centerLeft,
            widthFactor: ratio,
            child: DecoratedBox(
              decoration: BoxDecoration(
                color: isMe
                    ? classColor.withValues(alpha: 0.48)
                    : classColor.withValues(alpha: 0.29),
                borderRadius: BorderRadius.circular(2.5),
              ),
            ),
          ),
        ),
        if (isMe)
          Positioned(
            left: 0,
            top: 1,
            bottom: 1,
            child: Container(
              width: 3,
              decoration: BoxDecoration(
                color: const Color(0xFFFFC857),
                borderRadius: BorderRadius.circular(2),
              ),
            ),
          ),
        Padding(
          padding: EdgeInsets.only(
            left: isMe ? 6 : 4,
            right: 4,
          ),
          child: Row(
            children: [
              SizedBox(
                width: rankWidth,
                child: Text(
                  '${rank.toString().padLeft(2, '0')}.',
                  maxLines: 1,
                  style: TextStyle(
                    color: isMe
                        ? const Color(0xFFFFD978)
                        : const Color(0xFFB0B6C1),
                    fontWeight: FontWeight.w700,
                    fontSize: rankFontSize,
                    height: 1,
                    fontFeatures: const [FontFeature.tabularFigures()],
                  ),
                ),
              ),
              Expanded(
                child: Text(
                  identity,
                  maxLines: 1,
                  softWrap: false,
                  overflow: TextOverflow.ellipsis,
                  style: TextStyle(
                    color: isMe
                        ? const Color(0xFFFFFFFF)
                        : const Color(0xFFE1E4EA),
                    fontWeight: isMe ? FontWeight.w800 : FontWeight.w600,
                    fontSize: fontSize,
                    height: 1,
                  ),
                ),
              ),
              SizedBox(width: compact ? 2 : 5),
              SizedBox(
                width: metricWidth,
                child: FittedBox(
                  fit: BoxFit.scaleDown,
                  alignment: Alignment.centerRight,
                  child: Text(
                    '${_formatNumber(total)} (${_formatNumber(dps)})',
                    maxLines: 1,
                    textAlign: TextAlign.right,
                    style: TextStyle(
                      color: const Color(0xFFF6F7F9),
                      fontWeight: FontWeight.w700,
                      fontSize: metricFontSize,
                      height: 1,
                      fontFeatures: const [FontFeature.tabularFigures()],
                    ),
                  ),
                ),
              ),
              SizedBox(width: compact ? 2 : 5),
              SizedBox(
                width: percentageWidth,
                child: Text(
                  _formatContribution(contribution),
                  maxLines: 1,
                  textAlign: TextAlign.right,
                  style: TextStyle(
                    color: isMe
                        ? const Color(0xFFFFD978)
                        : const Color(0xFFC4CAD5),
                    fontWeight: FontWeight.w700,
                    fontSize: metricFontSize,
                    height: 1,
                    fontFeatures: const [FontFeature.tabularFigures()],
                  ),
                ),
              ),
            ],
          ),
        ),
      ],
    ),
  );
}

Widget _buildPlayerList({
  required List<Map<String, dynamic>> players,
  required double maxTotal,
  required double groupTotal,
  required double rowHeight,
  required double columnWidth,
  required double availableHeight,
}) {
  final contentHeight = rowHeight * players.length;
  final shouldScroll = contentHeight > availableHeight + 1;

  return RepaintBoundary(
    child: ListView.builder(
      padding: const EdgeInsets.symmetric(vertical: 1.5),
      physics: shouldScroll
          ? const ClampingScrollPhysics()
          : const NeverScrollableScrollPhysics(),
      itemCount: players.length,
      itemExtent: rowHeight,
      itemBuilder: (context, index) {
        return _buildPlayerRow(
          player: players[index],
          maxTotal: maxTotal,
          groupTotal: groupTotal,
          rowHeight: rowHeight,
          columnWidth: columnWidth,
        );
      },
    ),
  );
}




Widget _buildMeterBody({
  required BoxConstraints constraints,
  required List<Map<String, dynamic>> visiblePlayers,
  required double maxTotal,
  required double groupTotal,
}) {
  final width = constraints.maxWidth.isFinite ? constraints.maxWidth : 540.0;
  final height = constraints.maxHeight.isFinite ? constraints.maxHeight : 130.0;
  final compact = _viewMode == _LiteViewMode.compact;

  // Fixed readable row heights. ListView provides scrolling at every size.
  final rowHeight = compact ? 10.0 : 11.0;

  if (visiblePlayers.isEmpty) {
    return Center(
      child: FittedBox(
        fit: BoxFit.scaleDown,
        child: Text(
          'Waiting for combat…',
          style: TextStyle(
            color: const Color(0xFF8B93A3),
            fontWeight: FontWeight.w500,
            fontSize: (height * 0.10).clamp(8.0, 12.0).toDouble(),
          ),
        ),
      ),
    );
  }

  return _buildPlayerList(
    players: visiblePlayers,
    maxTotal: maxTotal,
    groupTotal: groupTotal,
    rowHeight: rowHeight,
    columnWidth: width,
    availableHeight: height,
  );
}

  @override
  Widget build(BuildContext context) {
    final ranked = _rankPlayers();
    final visiblePlayers = _selectVisiblePlayers(
      ranked,
      _visibleLimitForMode(),
    );
    final maxTotal = ranked.isEmpty
        ? 1.0
        : ((ranked.first['total'] as num?) ?? 1)
            .toDouble()
            .clamp(1.0, double.infinity)
            .toDouble();
    final groupTotal = ranked.fold<double>(
      0.0,
      (sum, player) =>
          sum + ((player['total'] as num?) ?? 0).toDouble(),
    );

    return Material(
      color: Colors.transparent,
      child: LayoutBuilder(
        builder: (context, outerConstraints) {
          final width = outerConstraints.maxWidth.isFinite
              ? outerConstraints.maxWidth
              : 400.0;
          final height = outerConstraints.maxHeight.isFinite
              ? outerConstraints.maxHeight
              : 150.0;
          final headerHeight =
              (height * 0.15).clamp(26.0, 33.0).toDouble();
          final headerFontSize =
              (headerHeight * 0.36).clamp(9.5, 12.5).toDouble();

          return Container(
            decoration: BoxDecoration(
              color: const Color(0xE6121418),
              border: Border.all(
                color: const Color(0x663A86FF),
                width: 1,
              ),
              borderRadius: BorderRadius.circular(7),
              boxShadow: const [
                BoxShadow(
                  color: Color(0x42000000),
                  blurRadius: 8,
                  offset: Offset(0, 2),
                ),
              ],
            ),
            clipBehavior: Clip.antiAlias,
            child: Stack(
              children: [
                Column(
                  children: [
                    _buildHeader(
                      headerHeight: headerHeight,
                      headerFontSize: headerFontSize,
                      totalPlayers: ranked.length,
                    ),
                    Expanded(
                      child: LayoutBuilder(
                        builder: (context, bodyConstraints) {
                          return _buildMeterBody(
                            constraints: bodyConstraints,
                            visiblePlayers: visiblePlayers,
                            maxTotal: maxTotal,
                            groupTotal: groupTotal,
                          );
                        },
                      ),
                    ),
                  ],
                ),
                Positioned(
                  right: 0,
                  bottom: 0,
                  child: GestureDetector(
                    behavior: HitTestBehavior.opaque,
                    onPanStart: (details) =>
                        _startManualResize(context, details),
                    onPanUpdate: _updateManualResize,
                    onPanEnd: _finishManualResize,
                    child: SizedBox(
                      width: (width * 0.055).clamp(20.0, 30.0).toDouble(),
                      height: (height * 0.09).clamp(20.0, 30.0).toDouble(),
                      child: Align(
                        alignment: Alignment.bottomRight,
                        child: Padding(
                          padding: const EdgeInsets.all(3),
                          child: Icon(
                            Icons.south_east,
                            size: 15,
                            color: const Color(0x66FFFFFF),
                          ),
                        ),
                      ),
                    ),
                  ),
                ),
              ],
            ),
          );
        },
      ),
    );
  }
}
