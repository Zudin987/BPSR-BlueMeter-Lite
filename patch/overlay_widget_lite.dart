enum _LiteViewMode {
  compact,
  expanded,
}

enum _LiteMeterType {
  damage,
  healing,
  tanking,
}

class OverlayWidget extends StatefulWidget {
  const OverlayWidget({super.key});

  @override
  State<OverlayWidget> createState() => _OverlayWidgetState();
}

class _OverlayWidgetState extends State<OverlayWidget> {
  static const int _maxDisplayedPlayers = 20;
  static const double _compactMinimumWidth = 180;
  static const double _compactMinimumHeight = 80;
  static const double _expandedMinimumWidth = 360;
  static const double _expandedMinimumHeight = 96;
  static const double _maximumWidth = 1200;
  static const double _maximumHeight = 620;

  static const String _prefMode = 'lite_overlay_mode';
  static const String _prefWidth = 'lite_overlay_width';
  static const String _prefHeight = 'lite_overlay_height';
  static const String _prefX = 'lite_overlay_x';
  static const String _prefY = 'lite_overlay_y';
  static const String _prefLocked = 'lite_overlay_locked';
  static const String _prefMeterType = 'lite_overlay_meter_type';

  List<Map<String, dynamic>> _players = const [];
  int _combatTime = 0;
  StreamSubscription? _overlaySubscription;
  _LiteViewMode _viewMode = _LiteViewMode.expanded;
  _LiteMeterType _meterType = _LiteMeterType.damage;
  bool _isLocked = false;
  int _lastResizeRequestMs = 0;

  double _windowX = 8;
  double _windowY = 80;
  double _windowWidth = 360;
  double _windowHeight = 180;
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

    WidgetsBinding.instance.addPostFrameCallback((_) {
      _restoreLayout();
    });
  }

  @override
  void dispose() {
    _overlaySubscription?.cancel();
    super.dispose();
  }


Future<void> _restoreLayout() async {
  try {
    final prefs = await SharedPreferences.getInstance();
    final savedMode = prefs.getString(_prefMode);
    final mode = savedMode == 'compact'
        ? _LiteViewMode.compact
        : _LiteViewMode.expanded;

    final minimumWidth = mode == _LiteViewMode.compact
        ? _compactMinimumWidth
        : _expandedMinimumWidth;
    final minimumHeight = mode == _LiteViewMode.compact
        ? _compactMinimumHeight
        : _expandedMinimumHeight;
    final defaultWidth = mode == _LiteViewMode.compact ? 180.0 : 360.0;
    final defaultHeight = mode == _LiteViewMode.compact ? 80.0 : 180.0;

    // The overlay isolate reports the overlay window's dimensions, not the
    // phone's full display. Do not use that view to clamp screen coordinates.
    final width = (prefs.getDouble(_prefWidth) ?? defaultWidth)
        .clamp(minimumWidth, _maximumWidth)
        .toDouble();
    final height = (prefs.getDouble(_prefHeight) ?? defaultHeight)
        .clamp(minimumHeight, _maximumHeight)
        .toDouble();

    final x = (prefs.getDouble(_prefX) ?? 8.0)
        .clamp(0.0, 10000.0)
        .toDouble();
    final y = (prefs.getDouble(_prefY) ?? 80.0)
        .clamp(0.0, 10000.0)
        .toDouble();
    final savedMeterType = prefs.getString(_prefMeterType);
    final meterType = switch (savedMeterType) {
      'healing' => _LiteMeterType.healing,
      'tanking' => _LiteMeterType.tanking,
      _ => _LiteMeterType.damage,
    };
    final locked = prefs.getBool(_prefLocked) ?? false;

    if (!mounted) return;

    setState(() {
      _viewMode = mode;
      _meterType = meterType;
      _isLocked = locked;
      _windowX = x;
      _windowY = y;
      _windowWidth = width;
      _windowHeight = height;
    });

    // The main isolate first creates a visible window at a safe position.
    // Restore only after the Android overlay service has fully attached.
    await Future<void>.delayed(const Duration(milliseconds: 650));
    await _resizeOverlay(width, height);
    await FlutterOverlayWindow.moveOverlay(
      OverlayPosition(_windowX, _windowY),
    );
    await _saveLayout();
  } catch (_) {
    // Keep the safe visible startup layout when restoration fails.
  }
}

Future<void> _saveLayout() async {
  try {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(
      _prefMode,
      _viewMode == _LiteViewMode.compact ? 'compact' : 'expanded',
    );
    await prefs.setDouble(_prefWidth, _windowWidth);
    await prefs.setDouble(_prefHeight, _windowHeight);
    await prefs.setDouble(_prefX, _windowX);
    await prefs.setDouble(_prefY, _windowY);
    await prefs.setBool(_prefLocked, _isLocked);
    await prefs.setString(
      _prefMeterType,
      switch (_meterType) {
        _LiteMeterType.damage => 'damage',
        _LiteMeterType.healing => 'healing',
        _LiteMeterType.tanking => 'tanking',
      },
    );
  } catch (_) {
    // Persistence failure must never interrupt the live meter.
  }
}


String get _metricTotalKey {
  return switch (_meterType) {
    _LiteMeterType.damage => 'totalDamage',
    _LiteMeterType.healing => 'totalHealing',
    _LiteMeterType.tanking => 'totalTaken',
  };
}

String get _metricRateKey {
  return switch (_meterType) {
    _LiteMeterType.damage => 'dps',
    _LiteMeterType.healing => 'hps',
    _LiteMeterType.tanking => 'takenDps',
  };
}

String get _meterTitle {
  return switch (_meterType) {
    _LiteMeterType.damage => 'DPS',
    _LiteMeterType.healing => 'Healing',
    _LiteMeterType.tanking => 'Tanking',
  };
}

String get _emptyMeterMessage {
  return switch (_meterType) {
    _LiteMeterType.damage => 'Waiting for damage…',
    _LiteMeterType.healing => 'Waiting for healing…',
    _LiteMeterType.tanking => 'Waiting for damage taken…',
  };
}

Color get _meterAccentColor {
  return switch (_meterType) {
    _LiteMeterType.damage => const Color(0xFF82AEFF),
    _LiteMeterType.healing => const Color(0xFF65D69B),
    _LiteMeterType.tanking => const Color(0xFFFFA86A),
  };
}

Color get _meterAccentSoftColor {
  return switch (_meterType) {
    _LiteMeterType.damage => const Color(0x243A86FF),
    _LiteMeterType.healing => const Color(0x2445B978),
    _LiteMeterType.tanking => const Color(0x24D87839),
  };
}

double _playerMetricTotal(Map<String, dynamic> player) {
  return ((player[_metricTotalKey] as num?) ?? 0).toDouble();
}

double _playerMetricRate(Map<String, dynamic> player) {
  return ((player[_metricRateKey] as num?) ?? 0).toDouble();
}

int get _activePlayerCount {
  return _players.where((player) => _playerMetricTotal(player) > 0).length;
}

Future<void> _setMeterType(_LiteMeterType meterType) async {
  if (_meterType == meterType) return;

  setState(() {
    _meterType = meterType;
  });

  await _saveLayout();
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
      .where((player) => _playerMetricTotal(player) > 0)
      .map((player) => Map<String, dynamic>.from(player))
      .toList(growable: true)
    ..sort((a, b) {
      final totalComparison =
          _playerMetricTotal(b).compareTo(_playerMetricTotal(a));
      if (totalComparison != 0) return totalComparison;

      final rateComparison =
          _playerMetricRate(b).compareTo(_playerMetricRate(a));
      if (rateComparison != 0) return rateComparison;

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

  _windowWidth = safeWidth.toDouble();
  _windowHeight = safeHeight.toDouble();

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


Future<void> _toggleViewMode() async {
  final nextMode = _viewMode == _LiteViewMode.compact
      ? _LiteViewMode.expanded
      : _LiteViewMode.compact;

  setState(() {
    _viewMode = nextMode;
  });

  if (nextMode == _LiteViewMode.compact) {
    await _resizeOverlay(
      _compactMinimumWidth,
      _compactMinimumHeight,
    );
  } else {
    await _resizeOverlay(360, 180);
  }

  await _saveLayout();
}

Future<void> _toggleLock() async {
  setState(() {
    _isLocked = !_isLocked;
  });
  await _saveLayout();
}

  void _moveWindow(DragUpdateDetails details) {
    if (_isLocked) return;

    _windowX = (_windowX + details.delta.dx)
        .clamp(0.0, 10000.0)
        .toDouble();
    _windowY = (_windowY + details.delta.dy)
        .clamp(0.0, 10000.0)
        .toDouble();

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
    _saveLayout();
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


Widget _buildMeterTab({
  required String label,
  required _LiteMeterType type,
  required double height,
  required double fontSize,
}) {
  final selected = _meterType == type;
  final accent = switch (type) {
    _LiteMeterType.damage => const Color(0xFF82AEFF),
    _LiteMeterType.healing => const Color(0xFF65D69B),
    _LiteMeterType.tanking => const Color(0xFFFFA86A),
  };

  return Expanded(
    child: GestureDetector(
      behavior: HitTestBehavior.opaque,
      onTap: () => _setMeterType(type),
      child: Container(
        height: height,
        margin: const EdgeInsets.symmetric(horizontal: 1.5),
        decoration: BoxDecoration(
          color: selected
              ? accent.withValues(alpha: 0.34)
              : const Color(0x1FFFFFFF),
          borderRadius: BorderRadius.circular(4),
          border: Border.all(
            color: selected
                ? accent.withValues(alpha: 0.80)
                : const Color(0x18FFFFFF),
            width: 0.7,
          ),
        ),
        child: Center(
          child: FittedBox(
            fit: BoxFit.scaleDown,
            child: Text(
              label,
              maxLines: 1,
              style: TextStyle(
                color: selected
                    ? const Color(0xFFF4F7FF)
                    : const Color(0xFFB9C0CC),
                fontWeight:
                    selected ? FontWeight.w800 : FontWeight.w600,
                fontSize: fontSize,
                height: 1,
              ),
            ),
          ),
        ),
      ),
    ),
  );
}

Widget _buildMeterTabs({
  required double tabHeight,
  required double tabFontSize,
}) {
  return Container(
    height: tabHeight,
    padding: const EdgeInsets.fromLTRB(3, 2, 3, 2),
    color: const Color(0xE9181B20),
    child: Row(
      children: [
        _buildMeterTab(
          label: 'DPS',
          type: _LiteMeterType.damage,
          height: tabHeight - 4,
          fontSize: tabFontSize,
        ),
        _buildMeterTab(
          label: 'Healing',
          type: _LiteMeterType.healing,
          height: tabHeight - 4,
          fontSize: tabFontSize,
        ),
        _buildMeterTab(
          label: 'Tanking',
          type: _LiteMeterType.tanking,
          height: tabHeight - 4,
          fontSize: tabFontSize,
        ),
      ],
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
    onPanStart: _isLocked ? null : (_) {},
    onPanUpdate: _isLocked ? null : _moveWindow,
    onPanEnd: _isLocked ? null : (_) => _saveLayout(),
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
                _meterTitle,
                maxLines: 1,
                style: TextStyle(
                  color: _meterAccentColor,
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
              color: _meterAccentSoftColor,
              borderRadius: BorderRadius.circular(9),
            ),
            child: Text(
              playerLabel,
              textAlign: TextAlign.center,
              style: TextStyle(
                color: _meterAccentColor.withValues(alpha: 0.90),
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
            onTap: _toggleLock,
            size: 23,
            child: Icon(
              _isLocked
                  ? Icons.lock_rounded
                  : Icons.lock_open_rounded,
              size: (headerHeight * 0.48).clamp(13, 18).toDouble(),
              color: _isLocked
                  ? const Color(0xFFFFD978)
                  : const Color(0xFFAAB2C2),
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
    // Remote Season 3 strength is not guaranteed to be present in game packets.
    // Show only the real Ability Score when remote strength is unavailable.
    scorePart = ' ($combatPower)';
  } else if (illusionBreakingStrength > 0) {
    scorePart = ' ($illusionBreakingStrength)';
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
  final total = _playerMetricTotal(player);
  final rate = _playerMetricRate(player);
  final ratio = (total / maxTotal).clamp(0.0, 1.0).toDouble();
  final contribution = groupTotal > 0 ? (total / groupTotal * 100.0) : 0.0;
  final isMe = player['isMe'] == true;
  final rank = (player['_rank'] as int?) ?? 0;
  final className = (player['className'] as String?)?.trim() ?? '';
  final classColor = _classColor(className);

  final compact = _viewMode == _LiteViewMode.compact;
  final identity =
      compact ? _compactIdentity(player) : _expandedIdentity(player);

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

  final rankStyle = TextStyle(
    color: isMe
        ? const Color(0xFFFFD978)
        : const Color(0xFFB0B6C1),
    fontWeight: FontWeight.w700,
    fontSize: rankFontSize,
    height: 1,
    fontFeatures: const [FontFeature.tabularFigures()],
  );

  final identityStyle = TextStyle(
    color: isMe
        ? const Color(0xFFFFFFFF)
        : const Color(0xFFE1E4EA),
    fontWeight: isMe ? FontWeight.w800 : FontWeight.w600,
    fontSize: fontSize,
    height: 1,
  );

  final metricStyle = TextStyle(
    color: const Color(0xFFF6F7F9),
    fontWeight: FontWeight.w700,
    fontSize: metricFontSize,
    height: 1,
    fontFeatures: const [FontFeature.tabularFigures()],
  );

  final percentageStyle = TextStyle(
    color: isMe
        ? const Color(0xFFFFD978)
        : const Color(0xFFC4CAD5),
    fontWeight: FontWeight.w700,
    fontSize: metricFontSize,
    height: 1,
    fontFeatures: const [FontFeature.tabularFigures()],
  );

  return Padding(
    padding: EdgeInsets.symmetric(
      horizontal: (columnWidth * 0.008).clamp(2.0, 5.0).toDouble(),
      vertical: 0,
    ),
    child: Stack(
      fit: StackFit.expand,
      children: [
        DecoratedBox(
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
        FractionallySizedBox(
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
        if (isMe)
          Positioned(
            left: 0,
            top: 0,
            bottom: 0,
            child: Container(
              width: 2,
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
            crossAxisAlignment: CrossAxisAlignment.center,
            children: [
              SizedBox(
                width: rankWidth,
                height: rowHeight,
                child: Align(
                  alignment: Alignment.centerLeft,
                  child: Text(
                    '${rank.toString().padLeft(2, '0')}.',
                    maxLines: 1,
                    textAlign: TextAlign.left,
                    textHeightBehavior: const TextHeightBehavior(
                      applyHeightToFirstAscent: false,
                      applyHeightToLastDescent: false,
                    ),
                    strutStyle: StrutStyle(
                      fontSize: rankFontSize,
                      height: 1,
                      forceStrutHeight: true,
                    ),
                    style: rankStyle,
                  ),
                ),
              ),
              Expanded(
                child: SizedBox(
                  height: rowHeight,
                  child: Align(
                    alignment: Alignment.centerLeft,
                    child: Text(
                      identity,
                      maxLines: 1,
                      softWrap: false,
                      overflow: TextOverflow.ellipsis,
                      textAlign: TextAlign.left,
                      textHeightBehavior: const TextHeightBehavior(
                        applyHeightToFirstAscent: false,
                        applyHeightToLastDescent: false,
                      ),
                      strutStyle: StrutStyle(
                        fontSize: fontSize,
                        height: 1,
                        forceStrutHeight: true,
                      ),
                      style: identityStyle,
                    ),
                  ),
                ),
              ),
              SizedBox(width: compact ? 2 : 5),
              SizedBox(
                width: metricWidth,
                height: rowHeight,
                child: Align(
                  alignment: Alignment.centerRight,
                  child: FittedBox(
                    fit: BoxFit.scaleDown,
                    alignment: Alignment.centerRight,
                    child: Text(
                      '${_formatNumber(total)} (${_formatNumber(rate)})',
                      maxLines: 1,
                      textAlign: TextAlign.right,
                      textHeightBehavior: const TextHeightBehavior(
                        applyHeightToFirstAscent: false,
                        applyHeightToLastDescent: false,
                      ),
                      strutStyle: StrutStyle(
                        fontSize: metricFontSize,
                        height: 1,
                        forceStrutHeight: true,
                      ),
                      style: metricStyle,
                    ),
                  ),
                ),
              ),
              SizedBox(width: compact ? 2 : 5),
              SizedBox(
                width: percentageWidth,
                height: rowHeight,
                child: Align(
                  alignment: Alignment.centerRight,
                  child: Text(
                    _formatContribution(contribution),
                    maxLines: 1,
                    textAlign: TextAlign.right,
                    textHeightBehavior: const TextHeightBehavior(
                      applyHeightToFirstAscent: false,
                      applyHeightToLastDescent: false,
                    ),
                    strutStyle: StrutStyle(
                      fontSize: metricFontSize,
                      height: 1,
                      forceStrutHeight: true,
                    ),
                    style: percentageStyle,
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
          _emptyMeterMessage,
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
        : _playerMetricTotal(ranked.first)
            .clamp(1.0, double.infinity)
            .toDouble();
    final groupTotal = ranked.fold<double>(
      0.0,
      (sum, player) => sum + _playerMetricTotal(player),
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
          final tabHeight =
              (height * 0.10).clamp(16.0, 22.0).toDouble();
          final tabFontSize =
              (tabHeight * 0.46).clamp(7.0, 10.0).toDouble();

          return Container(
            decoration: BoxDecoration(
              color: const Color(0xE6121418),
              border: Border.all(
                color: _isLocked
                    ? const Color(0x88FFC857)
                    : const Color(0x663A86FF),
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
                    _buildMeterTabs(
                      tabHeight: tabHeight,
                      tabFontSize: tabFontSize,
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
                if (!_isLocked)
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
