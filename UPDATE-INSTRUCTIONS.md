# BlueMeter Lite v0.4 — App icon + compact/expanded modes

Replace these items in the GitHub repository:

- `patch/overlay_widget_lite.dart`
- `patch/apply_lite_patch.py`
- everything inside `patch/android_icons/`

A commit under `patch/**` starts the APK build automatically.

## Overlay modes

Tap the header mode button to switch:

- `C` = Compact
- `E` = Expanded

### Compact mode
Shows:

`01. ★ MrHard    101.31K (12.39K)    95%`

Compact mode keeps:
- rank
- owner star
- colored class bar
- total damage
- DPS in parentheses
- percentage

Compact mode hides:
- class name
- ability score
- season strength

### Expanded mode
Shows:

`01. ★ MrHard — Frost Mage (49632+2250)    101.31K (12.39K)    95%`

## Icon

The uploaded portrait is now used as the Android launcher icon by copying
generated PNG files into the standard Android mipmap folders.

## APK version

`1.5.0+8`
