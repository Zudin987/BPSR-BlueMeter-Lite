# BlueMeter Lite v0.2 UI update

Replace these files in the GitHub repository:

- `patch/overlay_widget_lite.dart`
- `patch/apply_lite_patch.py`
- `README.md`

Uploading either file under `patch/` triggers the APK workflow automatically.

## New overlay behaviour

- Auto mode is enabled by default.
- 1–5 detected players: compact single-column window.
- 6–10 detected players: larger party window.
- 11–20 detected players: two-column raid window.
- Auto height follows the number of active players, avoiding a large empty box
  during solo testing.
- Tap the `A / 5 / 10 / 20 / ↔` button to cycle Auto, Compact, Party, Raid,
  and return from custom size.
- Drag the bottom-right handle for arbitrary resizing.
- Drag the header to move the overlay.
- Font, row height, rank width, name width, and DPS width adapt to the actual
  overlay dimensions.
- Up to 20 players are shown. If more are parsed, the top players remain visible
  and the local player is preserved even when outside the normal cut.
- Narrow custom windows use a scrollable one-column list.
- Wide raid windows use two columns to avoid 20 tiny rows.
- No blur, animation, icons per player, skill details, or charts were added.

## Design references

The layout follows common damage-meter patterns:

- proportional background bars
- fixed right-aligned tabular DPS values
- highlighted local player
- compact number formatting
- adjustable visible-player count
- responsive layouts for party and raid sizes

The implementation stays intentionally DPS-only to retain the Lite project's
low CPU, memory, and battery goals.
