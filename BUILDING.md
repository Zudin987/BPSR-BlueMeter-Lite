# Building BlueMeter Lite

BlueMeter Lite is maintained as a GitHub Actions patch kit on top of a pinned
BlueMeter Mobile revision.

## Reproducible inputs

```text
BlueMeter Mobile: 3c9d757cc0fd67971faf18447638c08044fb9b7c
Flutter:          3.44.7
Java:             17
App version:      1.4.0+23
```

## Normal APK build

Open **Actions → Build BlueMeter Lite APK → Run workflow**.

GitHub Actions validates the scripts, fetches the pinned upstream source,
applies the Lite, EnterScene, performance, and release-version patches, verifies
the generated source, and builds split APKs.

No local Python, terminal, Flutter installation, or PC build is required.

## Signed GitHub Release

Open **Actions → Publish BlueMeter Lite Release → Run workflow**.

```text
Tag:        v1.4.0
Draft:      true
Prerelease: false
```

The workflow creates architecture-specific APKs, a corresponding-source ZIP,
checksums, and the signing-certificate fingerprint.

## Architecture

- `arm64-v8a` — most modern Android phones
- `armeabi-v7a` — older 32-bit ARM devices
- `x86_64` — emulators and uncommon x86 Android devices

## AGPL corresponding source

Every public APK release includes the exact patched source used for that build.
Private signing files are removed before the source archive is created.
