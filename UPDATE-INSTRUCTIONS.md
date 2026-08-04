# BlueMeter Lite v0.3 — ZDPS-style rows

Replace these two files in the GitHub repository:

- `patch/overlay_widget_lite.dart`
- `patch/apply_lite_patch.py`

A commit under `patch/**` starts the APK build automatically.

## New row format

`★ Username — Class (Ability Score+Season Strength)    Total Damage (DPS)    Share%`

Example:

`01. ★ MrHard — Frost Mage (49632+2250)    101.31K (12.39K)    95%`

## Behaviour

- Rankings and bars are based on total damage.
- DPS is shown in parentheses after total damage.
- Contribution percentage uses total party/raid damage.
- Class comes from `professionId`.
- Ability Score uses `combatPower`.
- Illusion Breaking season strength uses `seasonStrength`.
- The local/owner player gets:
  - a gold star
  - a gold outline and left marker
  - brighter text
  - guaranteed visibility when outside the normal top cut
- Class-colored bars are used without loading icons.
- Font and rows are denser than v0.2.
- Auto widths are larger so the class, score, total, DPS, and percentage fit:
  - 1–5 players: 540 px
  - 6–10 players: 640 px
  - 11–20 players: 980 px in two columns

## APK version

`1.4.0+7`
