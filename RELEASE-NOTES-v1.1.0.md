# BlueMeter Lite v1.1.0

The second stable release of BlueMeter Lite, by MrEz.

## Important upgrade notice

**v1.1.0 is the first release signed with BlueMeter Lite's permanent release key.**

Users who installed v1.0.0 must:

1. uninstall BlueMeter Lite v1.0.0
2. install v1.1.0

This is a one-time signing migration. Future releases can install normally over v1.1.0 as long as the permanent key is preserved.

## What's new

- Remembers Compact/Expanded mode, overlay size, screen position and lock state
- Adds a lock button that disables both dragging and resizing
- Detects the installed BPSR regional client before starting
- Shows a clear message when no supported client is installed
- Opens the control application in portrait
- Keeps the in-game overlay rotation-aware
- Adds an About screen with privacy, AGPL license and upstream revision
- Adds `by MrEz` creator credit

## Reliability fixes

- Force-recreates stale or invisible overlays before starting the VPN
- Restores saved layouts only after the Android overlay is attached
- Restores header dragging while unlocked
- Keeps drag and resize disabled while locked
- Corrects remote Illusion-Breaking Strength parsing
- Uses current Season 3 strength IDs and corrected specialization names

## Reproducible release

This release is built from:

```text
BlueMeter Mobile: 3c9d757cc0fd67971faf18447638c08044fb9b7c
Flutter:          3.44.7
App version:      1.1.0+18
```

The release includes APK checksums, the signing-certificate SHA-256 fingerprint and complete corresponding source.

## Which APK to download

Most modern Android phones:

```text
BlueMeter-Lite-v1.1.0-arm64-v8a.apk
```

Other builds are provided for older 32-bit ARM devices and x86_64 Android environments.

## Supported clients

- HaoPlay SEA
- A Plus Japan / Global
- Taiwan / Hong Kong / Macau
- X.D. regional client

## Maintenance status

BlueMeter Lite is feature-complete and provided as-is. Routine support and feature development are not planned.
