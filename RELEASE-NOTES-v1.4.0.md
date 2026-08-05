# BlueMeter Lite v1.4.0

A major performance and encounter-management update for the lightweight Android
BPSR combat meter.

## Performance

- The visible overlay refreshes at most once every two seconds.
- Damage, healing, and tanking packets continue to be processed between visible
  refreshes, so the slower display interval does not intentionally skip combat
  data.
- Stops unnecessary redraws when combat totals have not changed.
- Reuses cached player rankings until the selected meter totals change.
- Caches formatted total and per-second values instead of rebuilding every label.
- Renders up to 20 players in the live overlay while preserving the complete
  player list in encounter history.
- Keeps the local player visible when possible.
- Uses a slower Android packet-to-overlay bridge to reduce CPU and GPU pressure.

## Encounter history

- Stores compact DPS, Healing, and Tanking summaries locally.
- Preserves full encounter data even though the live overlay is limited to 20
  displayed rows.
- Automatically removes history entries older than seven days.
- Saves encounters after supported automatic resets, manual resets, and meter
  shutdown.
- Adds best-effort location naming from the ZDPS scene catalog.
- Registers the exact `WorldNtf.EnterScene` packet used by ZDPS and reads
  `AttrSceneBasicId` from typed scene attributes.
- Keeps decoded `SyncContainerData.SceneData` as a fallback and no longer
  guesses integer fields from Social packets, preventing player UIDs from
  being mistaken for map IDs.
- Freezes the detected scene when combat begins so the destination map does not
  rename the encounter that just ended.

## Automatic encounter reset

- Splits supported encounters on map, channel, line, and dungeon transitions.
- Keeps conservative wipe and boss-phase detection.
- Includes a separate Auto Reset Lock that preserves the meter until a manual
  reset or shutdown.
- Guards against duplicate history entries when several transition signals arrive
  close together.

## Build reliability

- Validates all patch scripts before building.
- Verifies the generated encounter-history paths and safe scene-capture code.
- Confirms the two-second refresh, top-20 display limit, package ID, and release
  version before compiling.
- Keeps the upstream BlueMeter Mobile revision and Flutter version pinned.
- Release APKs remain signed using BlueMeter Lite's existing permanent key.

## Notes

- Overlay values can update in larger two-second jumps, but cumulative totals
  continue to use the captured combat packets.
- Location naming is best-effort and has not been fully field-tested during the
  current game maintenance. Unknown scenes safely fall back to a generic reset
  reason.
- Existing history entries that previously stored an incorrect UID as a map ID
  cannot be repaired automatically.
- A future BPSR protocol update may require another compatibility update.

## Version

`1.4.0+23`
