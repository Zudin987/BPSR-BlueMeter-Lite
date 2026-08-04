# Changelog

All notable user-facing changes to BlueMeter Lite are documented here.

## [Unreleased]

- Prepare stable Android release signing
- Final device compatibility testing
- Publish the first GitHub Release

## [1.0.0] - TBD

### Added

- Live total-damage and DPS ranking
- Group contribution percentages
- Compact and Expanded overlay modes
- Detected professions and specializations
- Ability Score and Illusion-Breaking Strength display
- Local-player star and row highlight
- One-column scrolling list for up to 20 displayed players
- Movable and resizable Android overlay
- Manual encounter reset
- Android launcher icon
- Support for HaoPlay SEA, A Plus Japan/Global, Taiwan/Hong Kong/Macau and X.D. regional clients

### Performance and networking

- BPSR-only Android VPN allow-list
- Queued non-blocking socket writes
- `TCP_NODELAY` on game sockets
- Reduced Kotlin-to-Flutter packet flush frequency
- Removed heavy skill, target, timeline, healing and damage-taken storage from the Lite meter

### Documentation

- Added screenshots, privacy information, build instructions and issue templates
