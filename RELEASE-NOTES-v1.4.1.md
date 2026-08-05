# BlueMeter Lite v1.4.1

A maintenance release that finalizes the v1.4 performance and encounter-history
updates.

## Fixed

- Dungeon and map names now use the exact `WorldNtf.EnterScene` scene data used
  by ZDPS.
- Reads `AttrSceneBasicId` from typed scene attributes instead of guessing
  integer fields.
- Prevents player UIDs from being treated as map IDs.
- Keeps the encounter's original scene when leaving a dungeon or changing maps.
- Makes the final performance patch detect the generated source indentation
  correctly during GitHub Actions builds.

## Performance

- Aligns the main overlay bridge and visible renderer to a two-second interval.
- Continues processing damage, healing, and tanking packets between visible
  updates.
- Skips rebuilding and transferring an overlay payload when combat totals and
  player information have not changed.
- Stops unnecessary redraws outside active combat.
- Reuses cached player sorting and formatted metric text.
- Limits the live overlay to 20 rows while retaining every detected player in
  encounter history.
- Removes stale Illusion-Breaking Strength cache entries between encounters.

## Encounter history

- Stores local DPS, Healing, and Tanking summaries for seven days.
- Shows confirmed dungeon and map names when the scene exists in the ZDPS
  catalog.
- Keeps complete encounter data even when only 20 players are rendered live.
- Existing old entries saved without a valid scene ID cannot be renamed
  automatically.

## Notes

- The two-second visible refresh does not intentionally skip combat packets.
  Cumulative totals continue to use captured data.
- Newly added game scenes may temporarily show a generic label until their name
  is added to the scene catalog.
- Future BPSR protocol changes may require another compatibility update.

## Version

`1.4.1+24`
