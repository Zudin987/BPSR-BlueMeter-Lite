# BlueMeter Lite v1.4.0

A major performance and encounter-management update for the lightweight Android
BPSR combat meter.

## Performance

- Aligns both sides of the live overlay pipeline to a two-second refresh.
- Continues processing damage, healing, and tanking packets between visible
  updates; the display delay does not intentionally discard combat data.
- Builds and sends a new overlay payload only when combat totals, player
  information, or overlay controls change.
- Stops unnecessary redraws while combat data is unchanged.
- Reuses cached player ranking and formatted metric text.
- Renders up to 20 players live while preserving every detected player in
  encounter history.
- Removes stale Illusion-Breaking Strength cache entries between encounters.

## Encounter history

- Stores local DPS, Healing, and Tanking summaries for seven days.
- Shows confirmed dungeon and map names from the ZDPS scene catalog.
- Registers the exact `WorldNtf.EnterScene` packet and reads
  `AttrSceneBasicId` from typed scene attributes.
- Keeps decoded `SyncContainerData.SceneData` as a fallback.
- Never guesses Social-packet integer fields, preventing player UIDs from being
  mistaken for map IDs.
- Freezes the detected scene when combat begins so leaving the dungeon does not
  rename the completed encounter.

## Automatic encounter reset

- Splits supported encounters on map, channel, line, and dungeon transitions.
- Keeps conservative wipe and boss-phase detection.
- Includes a separate Auto Reset Lock.
- Guards against duplicate history entries from closely grouped signals.

## Build reliability

- Verifies the generated EnterScene processor, history paths, two-second bridge,
  unchanged-payload suppression, top-20 limit, package ID, and release version.
- Keeps the upstream source and Flutter version pinned.
- Release APKs remain signed with the existing permanent key.

## Notes

- Overlay values can update in larger two-second jumps, while cumulative totals
  continue to use captured combat packets.
- A newly added scene may temporarily use a generic reset label until its name
  exists in the scene catalog.
- Existing history entries containing an incorrect UID cannot be repaired.
- Future BPSR protocol changes may require another compatibility update.

## Version

`1.4.0+23`
