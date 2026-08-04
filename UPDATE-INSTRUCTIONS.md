# BlueMeter Lite v0.6 update

Replace these GitHub files:

1. `patch/overlay_widget_lite.dart`
2. `patch/apply_lite_patch.py`

## Exact mode-switch sizes

### Compact

When switching from Expanded to Compact, the overlay immediately becomes:

`180 × 56`

This is also the manual minimum size allowed in Compact mode.

Users can then drag the resize handle to make it larger.

### Expanded

When switching from Compact to Expanded, the overlay immediately becomes:

`360 × 180`

Expanded mode keeps a manual minimum width of 360 px and a manual minimum
height of 96 px. The mode switch itself always uses 360 × 180.

## Row density

- Compact row height: 10 px
- Expanded row height: 11 px
- Both are approximately half of the previous v0.5 row heights.
- Font ranges, row padding, and owner markers were reduced to match.
- The player list remains one column and scrollable at every overlay size.

## Behaviour change

Player-count changes no longer automatically resize the overlay. This prevents
the app from overriding the size selected by the user after switching modes or
manually resizing.

## Initial size

A fresh app launch starts in Expanded mode at:

`360 × 180`

## Version

`1.7.0+10`
