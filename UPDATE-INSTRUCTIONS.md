# BlueMeter Lite v0.7 — Season 3 and sub-profession correction

Replace these GitHub files:

1. `patch/overlay_widget_lite.dart`
2. `patch/apply_lite_patch.py`

## Season 3 correction

BlueMeter previously treated `12690/12691` as season strength. Those IDs are
season-damage-increase percentage attributes. v0.7 changes the parser to:

- `11440` — Illusion-Breaking Strength
- `11441` — total Illusion-Breaking Strength

If the value is unavailable, Expanded mode shows an em dash instead of a fake
zero, for example: `(49632+—)`.

## Correct base profession names

- Stormblade
- Frost Mage
- Twin Striker
- Wind Knight
- Verdant Oracle
- Dorothy
- Heavy Guardian
- Dark Spirit Dance Ritual Blade
- Marksman
- Shield Knight
- Beat Performer
- Lucy
- Natsu

The previous `Soul Musician` label is corrected to `Beat Performer`.

## ZDPS-style sub-profession detection

A lightweight runtime map detects these specs from distinctive damage skill IDs:

- Iaido / Moonstrike
- Icicle / Frostbeam
- Formless Expertise / Crimson Expertise
- Vanguard / Skyward
- Smite / Lifebind
- Earthfort / Block
- Wildpack / Falconry
- Recovery / Shield
- Dissonance / Concerto

Expanded mode prefers the detected sub-profession. Until a distinctive skill is
seen, it falls back to the base profession name.

## Limitation

Illusion-Breaking Strength is not normally AOI-synced for other nearby players.
It may be available reliably only for the local character. The app therefore
shows `—` when the network stream does not contain the value.

## Version

`1.8.0+11`
