# BlueMeter Lite v1.4.0

Performance-focused update for devices that experienced game FPS loss while the
overlay was active.

## Improved

- Avoids sending unchanged combat payloads to the overlay isolate
- Coalesces UI events before rebuilding the player list
- Skips identical overlay redraws
- Cleans up pending UI timers when the overlay closes
- Retains the existing one-second low-impact refresh interval
- Preserves automatic reset and seven-day encounter history

## Version

`1.4.0+22`
