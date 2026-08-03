enum _LiteLayoutMode {
  auto,
  compact,
  party,
  raid,
  custom,
}

class _LiteOverlayPreset {
  const _LiteOverlayPreset(this.width, this.height);

  final int width;
  final int height;
}

class OverlayWidget extends StatefulWidget {
  const OverlayWidget({super.key});

  @override
  State<OverlayWidget> createState() => _OverlayWidgetState();
}

class _OverlayWidgetState extends State<OverlayWidget> {
  static const int _maxDisplayedPlayers = 20;
  static const double _minimumWidth = 280;
  static const double _maximumWidth = 900;
  static const double _minimumHeight = 96;
  static const double _maximumHeight = 620;

  List<Map<String, dynamic>> _players = const [];
  int _combatTime = 0;
  StreamSubscription? _overlaySubscription;
  Timer? _autoResizeTimer;

  _LiteLayoutMode _layoutMode = _LiteLayoutMode.auto;
  int _lastAutoPlayerCount = -1;
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

      _scheduleAutoResize();
    });

    WidgetsBinding.instance.addPostFrameCallback((_) {
      _scheduleAutoResize(immediate: true);
    });
  }

  @override
  void dispose() {
    _autoResizeTimer?.cancel();
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
    switch (_layoutMode) {
      case _LiteLayoutMode.compact:
        return 5;
      case _LiteLayoutMode.party:
        return 10;
      case _LiteLayoutMode.raid:
      case _LiteLayoutMode.auto:
      case _LiteLayoutMode.custom:
        return _maxDisplayedPlayers;
    }
  }

  String _modeLabel() {
    switch (_layoutMode) {
      case _LiteLayoutMode.auto:
        return 'A';
      case _LiteLayoutMode.compact:
        return '5';
      case _LiteLayoutMode.party:
        return '10';
      case _LiteLayoutMode.raid:
        return '20';
      case _LiteLayoutMode.custom:
        return '↔';
    }
  }

  _LiteOverlayPreset _presetForPlayerCount(int count) {
    final safeCount = count.clamp(0, _maxDisplayedPlayers).toInt();

    if (safeCount <= 5) {
      final rows = safeCount == 0 ? 2 : safeCount;
      final height = (42 + rows * 29).clamp(108, 192).toInt();
      return _LiteOverlayPreset(400, height);
    }

    if (safeCount <= 10) {
      final height = (42 + safeCount * 25).clamp(192, 292).toInt();
      return _LiteOverlayPreset(460, height);
    }

    final rowsPerColumn = (safeCount + 1) ~/ 2;
    final height = (42 + rowsPerColumn * 25).clamp(192, 292).toInt();
    return _LiteOverlayPreset(640, height);
  }

  _LiteOverlayPreset _presetForMode(_LiteLayoutMode mode) {
    switch (mode) {
      case _LiteLayoutMode.compact:
        return const _LiteOverlayPreset(400, 192);
      case _LiteLayoutMode.party:
        return const _LiteOverlayPreset(460, 292);
      case _LiteLayoutMode.raid:
        return const _LiteOverlayPreset(640, 292);
      case _LiteLayoutMode.auto:
        return _presetForPlayerCount(_activePlayerCount);
      case _LiteLayoutMode.custom:
        return const _LiteOverlayPreset(400, 192);
    }
  }

  void _scheduleAutoResize({bool immediate = false}) {
    if (_layoutMode != _LiteLayoutMode.auto) return;

    _autoResizeTimer?.cancel();
    _autoResizeTimer = Timer(
      Duration(milliseconds: immediate ? 0 : 650),
      () {
        if (!mounted || _layoutMode != _LiteLayoutMode.auto) return;

        final playerCount = _activePlayerCount;
        final preset = _presetForPlayerCount(playerCount);

        if (playerCount == _lastAutoPlayerCount && !immediate) return;
        _lastAutoPlayerCount = playerCount;
        _resizeOverlay(preset.width.toDouble(), preset.height.toDouble());
      },
    );
  }

  Future<void> _resizeOverlay(double width, double height) async {
    final safeWidth = width.clamp(_minimumWidth, _maximumWidth).toInt();
    final safeHeight = height.clamp(_minimumHeight, _maximumHeight).toInt();

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

  void _cycleLayoutMode() {
    final nextMode = switch (_layoutMode) {
      _LiteLayoutMode.auto => _LiteLayoutMode.compact,
      _LiteLayoutMode.compact => _LiteLayoutMode.party,
      _LiteLayoutMode.party => _LiteLayoutMode.raid,
      _LiteLayoutMode.raid => _LiteLayoutMode.auto,
      _LiteLayoutMode.custom => _LiteLayoutMode.auto,
    };

    setState(() {
      _layoutMode = nextMode;
      _lastAutoPlayerCount = -1;
    });

    if (nextMode == _LiteLayoutMode.auto) {
      _scheduleAutoResize(immediate: true);
    } else {
      final preset = _presetForMode(nextMode);
      _resizeOverlay(preset.width.toDouble(), preset.height.toDouble());
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
    _autoResizeTimer?.cancel();
    _resizeStartSize = MediaQuery.of(context).size;
    _resizeStartPointer = details.globalPosition;

    setState(() {
      _layoutMode = _LiteLayoutMode.custom;
    });
  }

  void _updateManualResize(DragUpdateDetails details) {
    final startSize = _resizeStartSize;
    final startPointer = _resizeStartPointer;
    if (startSize == null || startPointer == null) return;

    final difference = details.globalPosition - startPointer;
    final width =
        (startSize.width + difference.dx).clamp(_minimumWidth, _maximumWidth);
    final height =
        (startSize.height + difference.dy).clamp(_minimumHeight, _maximumHeight);

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
              onTap: _cycleLayoutMode,
              child: Container(
                constraints: const BoxConstraints(minWidth: 21),
                padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 2),
                decoration: BoxDecoration(
                  color: _layoutMode == _LiteLayoutMode.auto
                      ? const Color(0x423A86FF)
                      : const Color(0x1FFFFFFF),
                  borderRadius: BorderRadius.circular(5),
                  border: Border.all(
                    color: _layoutMode == _LiteLayoutMode.auto
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

  Widget _buildPlayerRow({
    required Map<String, dynamic> player,
    required double maxDps,
    required double rowHeight,
    required double columnWidth,
  }) {
    final dps = ((player['dps'] as num?) ?? 0).toDouble();
    final ratio = (dps / maxDps).clamp(0.0, 1.0).toDouble();
    final isMe = player['isMe'] == true;
    final rank = (player['_rank'] as int?) ?? 0;
    final rawName = (player['name'] as String?)?.trim();
    final displayName =
        (rawName == null || rawName.isEmpty) ? 'Unknown' : rawName;

    final fontSize = (rowHeight * 0.44).clamp(9.5, 14.0).toDouble();
    final rankFontSize = (fontSize - 1).clamp(8.5, 12.0).toDouble();
    final dpsFontSize = (fontSize + 0.2).clamp(9.7, 14.2).toDouble();
    final rankWidth = (columnWidth * 0.075).clamp(20.0, 30.0).toDouble();
    final dpsWidth = (columnWidth * 0.27).clamp(58.0, 94.0).toDouble();

    return Padding(
      padding: EdgeInsets.symmetric(
        horizontal: (columnWidth * 0.012).clamp(3.0, 7.0).toDouble(),
        vertical: 1,
      ),
      child: Stack(
        children: [
          Positioned.fill(
            child: DecoratedBox(
              decoration: BoxDecoration(
                color: const Color(0x131A1E27),
                borderRadius: BorderRadius.circular(3),
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
                      ? const Color(0x583A86FF)
                      : const Color(0x293A86FF),
                  borderRadius: BorderRadius.circular(3),
                ),
              ),
            ),
          ),
          if (isMe)
            Positioned(
              left: 0,
              top: 2,
              bottom: 2,
              child: Container(
                width: 2.5,
                decoration: BoxDecoration(
                  color: const Color(0xFF8AB4FF),
                  borderRadius: BorderRadius.circular(2),
                ),
              ),
            ),
          Padding(
            padding: EdgeInsets.symmetric(
              horizontal: (columnWidth * 0.014).clamp(4.0, 8.0).toDouble(),
            ),
            child: Row(
              children: [
                SizedBox(
                  width: rankWidth,
                  child: Text(
                    '$rank',
                    maxLines: 1,
                    style: TextStyle(
                      color: isMe
                          ? const Color(0xFFC9DCFF)
                          : const Color(0xFF7F8796),
                      fontWeight: isMe ? FontWeight.w700 : FontWeight.w500,
                      fontSize: rankFontSize,
                      fontFeatures: const [FontFeature.tabularFigures()],
                    ),
                  ),
                ),
                Expanded(
                  child: Text(
                    displayName,
                    maxLines: 1,
                    softWrap: false,
                    overflow: TextOverflow.ellipsis,
                    style: TextStyle(
                      color: isMe
                          ? const Color(0xFFFFFFFF)
                          : const Color(0xFFD6DBE5),
                      fontWeight:
                          isMe ? FontWeight.w800 : FontWeight.w600,
                      fontSize: fontSize,
                      height: 1,
                    ),
                  ),
                ),
                const SizedBox(width: 5),
                SizedBox(
                  width: dpsWidth,
                  child: FittedBox(
                    fit: BoxFit.scaleDown,
                    alignment: Alignment.centerRight,
                    child: Text(
                      _formatNumber(dps),
                      maxLines: 1,
                      textAlign: TextAlign.right,
                      style: TextStyle(
                        color: const Color(0xFFFFFFFF),
                        fontWeight: FontWeight.w800,
                        fontSize: dpsFontSize,
                        height: 1,
                        fontFeatures: const [FontFeature.tabularFigures()],
                      ),
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
    required double maxDps,
    required double rowHeight,
    required double columnWidth,
    required double availableHeight,
  }) {
    final contentHeight = rowHeight * players.length;
    final shouldScroll = contentHeight > availableHeight + 1;

    return RepaintBoundary(
      child: ListView.builder(
        padding: const EdgeInsets.symmetric(vertical: 2),
        physics: shouldScroll
            ? const ClampingScrollPhysics()
            : const NeverScrollableScrollPhysics(),
        itemCount: players.length,
        itemExtent: rowHeight,
        itemBuilder: (context, index) {
          return _buildPlayerRow(
            player: players[index],
            maxDps: maxDps,
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
    required double maxDps,
  }) {
    final width = constraints.maxWidth.isFinite ? constraints.maxWidth : 400.0;
    final height =
        constraints.maxHeight.isFinite ? constraints.maxHeight : 150.0;
    final useTwoColumns = visiblePlayers.length > 10 && width >= 540;
    final rowsPerColumn = useTwoColumns
        ? (visiblePlayers.length + 1) ~/ 2
        : visiblePlayers.length;
    final safeRowCount = rowsPerColumn == 0 ? 1 : rowsPerColumn;
    final rowHeight =
        (height / safeRowCount).clamp(19.0, 33.0).toDouble();

    if (visiblePlayers.isEmpty) {
      return Center(
        child: FittedBox(
          fit: BoxFit.scaleDown,
          child: Text(
            'Waiting for combat…',
            style: TextStyle(
              color: const Color(0xFF8B93A3),
              fontWeight: FontWeight.w500,
              fontSize: (height * 0.12).clamp(10.0, 14.0).toDouble(),
            ),
          ),
        ),
      );
    }

    if (!useTwoColumns) {
      return _buildPlayerList(
        players: visiblePlayers,
        maxDps: maxDps,
        rowHeight: rowHeight,
        columnWidth: width,
        availableHeight: height,
      );
    }

    final splitIndex = (visiblePlayers.length + 1) ~/ 2;
    final leftPlayers =
        visiblePlayers.sublist(0, splitIndex);
    final rightPlayers =
        visiblePlayers.sublist(splitIndex);

    return Row(
      children: [
        Expanded(
          child: _buildPlayerList(
            players: leftPlayers,
            maxDps: maxDps,
            rowHeight: rowHeight,
            columnWidth: width / 2,
            availableHeight: height,
          ),
        ),
        Container(
          width: 1,
          margin: const EdgeInsets.symmetric(vertical: 4),
          color: const Color(0x20FFFFFF),
        ),
        Expanded(
          child: _buildPlayerList(
            players: rightPlayers,
            maxDps: maxDps,
            rowHeight: rowHeight,
            columnWidth: width / 2,
            availableHeight: height,
          ),
        ),
      ],
    );
  }

  @override
  Widget build(BuildContext context) {
    final ranked = _rankPlayers();
    final visiblePlayers = _selectVisiblePlayers(
      ranked,
      _visibleLimitForMode(),
    );
    final maxDps = ranked.isEmpty
        ? 1.0
        : ((ranked.first['dps'] as num?) ?? 1)
            .toDouble()
            .clamp(1.0, double.infinity)
            .toDouble();

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
              (height * 0.16).clamp(29.0, 38.0).toDouble();
          final headerFontSize =
              (headerHeight * 0.40).clamp(11.5, 15.0).toDouble();

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
                            maxDps: maxDps,
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
