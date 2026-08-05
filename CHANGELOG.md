# Changelog

All notable user-facing changes to BlueMeter Lite are documented here.

## [1.4.0] - 2026-08-05

### Performance

- Aligned the main overlay bridge with the two-second overlay renderer
- Skipped unchanged payload creation and cross-isolate transfer
- Stopped visible redraws during combat inactivity
- Cached player ranking and formatted metric text
- Limited the live overlay to 20 rows while preserving full encounter history
- Pruned cached Illusion-Breaking Strength values to active encounter players

### Encounter history

- Added local seven-day DPS, Healing, and Tanking encounter history
- Captured dungeon and map names from exact `WorldNtf.EnterScene` data
- Read `AttrSceneBasicId` instead of guessing protobuf integer fields
- Prevented player UIDs from being stored as map IDs
- Preserved the encounter's scene when leaving or changing maps

### Automatic reset

- Added supported map, channel, line, dungeon, wipe, and phase resets
- Added an independent Auto Reset Lock
- Prevented duplicate history saves from grouped transition signals

### Build and maintenance

- Added generated-source validation for location and performance patches
- Pinned the upstream source and Flutter version
- Removed obsolete local-build packaging
- Updated v1.4.0 documentation

## [1.3.2] - 2026-08-05

- Improved map and dungeon transition handling
- Improved encounter-history saving during resets and shutdown

## [1.3.1] - 2026-08-04

- Added reliable map, line, channel, and dungeon transition resets

## [1.3.0] - 2026-08-04

- Added automatic reset controls and seven-day encounter history

## [1.2.0] - 2026-08-04

- Added DPS, Healing, and Tanking meters

## [1.1.0] - 2026-08-04

- Added saved overlay layout, multi-region detection, permanent signing, and
  automated release builds

## [1.0.0] - 2026-08-04

- Initial lightweight Android combat-meter release
