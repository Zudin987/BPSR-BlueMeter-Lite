# BlueMeter Lite v0.5 update

Replace these GitHub files:

1. `patch/overlay_widget_lite.dart`
2. `patch/apply_lite_patch.py`
3. `.github/workflows/build-apk.yml`

## Changes

- Always one column, regardless of player count or overlay width.
- The vertical player list scrolls whenever all rows do not fit.
- Compact mode can be manually reduced to 180 px wide.
- Expanded mode still has a 360 px minimum width.
- Compact automatic widths are now 300, 340, and 390 px.
- Expanded 11–20 player mode is 720 px wide, one column, and scrollable.
- Compact font and fixed column allocations adapt better at very narrow widths.
- `actions/upload-artifact@v7` removes the Node.js 20 warning.

## Version

`1.6.0+9`
