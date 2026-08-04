# BlueMeter Lite v0.8 update

Replace these GitHub files:

1. `patch/overlay_widget_lite.dart`
2. `patch/apply_lite_patch.py`

## Remote Illusion-Breaking Strength

The app cannot guarantee this value for every other player because the normal
team-member packet provides Ability Score and profession but not Season 3
Illusion-Breaking Strength.

v0.8 therefore:

- shows `(AbilityScore+Strength)` when a real strength value exists
- shows only `(AbilityScore)` when remote strength is unavailable
- no longer displays misleading `+—`
- caches the last non-zero value per player for the current app session if the
  game sends it temporarily

The app does not guess or derive another player's strength.

## Vertical alignment

Every element inside a DPS row now has explicit middle alignment:

- rank
- player identity
- total damage and DPS
- contribution percentage

The rows use centered `Align` widgets, centered Row cross-axis alignment,
forced strut height, and controlled text-height behaviour.

## Compact size

Compact mode now switches to:

`180 × 80`

Its manual minimum height is also 80 px.

Expanded mode remains:

`360 × 180`

## Version

`1.9.0+12`
