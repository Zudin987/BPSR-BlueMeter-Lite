# BlueMeter Lite v0.9 — Remote Illusion-Breaking Strength fix

Replace these GitHub files:

1. `patch/apply_lite_patch.py`
2. `patch/overlay_widget_lite.dart`

The overlay file is unchanged from v0.8 and is included so the update is
self-contained.

## Actual cause

ZDPS can show Illusion-Breaking Strength for random nearby players because it
processes the attribute collection for nearby entities, not only party data.

BlueMeter has two relevant paths:

1. `SyncNearEntities` for the initial player appearance
2. `SyncNearDeltaInfo` for later incremental updates

The later delta path already handles:

- `AttrSeasonStrength`
- `AttrSeasonStrengthTotal`

The initial appearance path handled name, profession, Ability Score and other
stats, but skipped both Season Strength values. Remote players therefore often
remained at zero unless a later delta resent the attribute.

v0.9 adds both Season Strength cases to the initial nearby-player parser.

## Season 3 IDs

- `11440` — Illusion-Breaking Strength
- `11441` — Illusion-Breaking Strength total

## Existing behaviour retained

- Compact mode `180 × 80`
- Expanded mode `360 × 180`
- vertically centered rows
- one-column scrolling
- session cache for the last non-zero strength value
- Ability Score-only fallback when a specific packet genuinely lacks strength

## Version

`1.10.0+13`
