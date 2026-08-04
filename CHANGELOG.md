# Changelog

All notable user-facing changes to BlueMeter Lite are documented here.

## [Unreleased]

No routine feature development is planned.

## [1.2.0] - TBD

### Added

- Toggleable DPS, Healing and Tanking tabs
- Total healing, HPS and healing contribution ranking
- Total damage received, taken-per-second and tanking contribution ranking
- Saved selected meter tab
- Separate lightweight active-time clocks for damage, healing and damage received

### Performance

- Stores only totals and meter-specific timestamps
- Does not restore heavy skill, target, timeline, overheal, mitigation or death tracking
- Filters NPC-only entries from the player overlay

## [1.1.0] - 2026-08-04

### Added

- Saved overlay mode, size, position and lock state
- Lock button that disables both moving and resizing
- Supported BPSR client detection before VPN startup
- Clear unsupported-client message
- Portrait control application
- About screen with privacy, license, author and upstream revision
- `by MrEz` creator credit
- Permanent Android release signing support
- Automated draft GitHub Release workflow
- APK checksums and signing-certificate fingerprint assets

### Fixed

- Recreated stale or invisible overlays before VPN startup
- Prevented old saved coordinates from hiding the overlay
- Restored header dragging while unlocked
- Kept resize disabled while locked
- Corrected remote Illusion-Breaking Strength parsing
- Corrected Season 3 attribute IDs and sub-profession mappings
- Centered row text vertically
- Kept the player list in one scrollable column

### Build and release

- Pinned BlueMeter Mobile to a known working commit
- Pinned Flutter to a known working version
- Added exact build metadata to corresponding source
- Added a permanent signed-release workflow

### Upgrade notice

v1.1.0 is the first release signed with BlueMeter Lite's permanent key. Users of v1.0.0 must uninstall once before installing v1.1.0.

## [1.0.0] - 2026-08-04

### Added

- Live total-damage and DPS ranking
- Group contribution percentages
- Compact and Expanded modes
- Profession and specialization detection
- Ability Score and Illusion-Breaking Strength
- Local-player star and row highlight
- One-column scrolling list
- Movable and resizable Android overlay
- Manual encounter reset
- Android launcher icon
- Four supported regional BPSR clients
- BPSR-only local VPN allow-list
- Lightweight packet, storage and overlay pipeline
