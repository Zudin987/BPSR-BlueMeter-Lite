# Building BlueMeter Lite

BlueMeter Lite is maintained as a patch kit on top of BlueMeter Mobile.

## Reproducible inputs

The v1.2.0 build is pinned to:

```text
BlueMeter Mobile: 3c9d757cc0fd67971faf18447638c08044fb9b7c
Flutter:          3.44.7
Java:             17
App version:      1.2.0+19
```

The workflow checks out the exact upstream commit rather than whatever happens to be the latest `main` branch.

## Normal GitHub Actions build

Use **Actions → Build BlueMeter Lite APK → Run workflow**.

The normal workflow:

1. checks out the pinned upstream commit
2. applies the Lite patch
3. verifies the patched version
4. builds split APKs
5. verifies APK signatures when signing secrets exist
6. uploads APK and corresponding-source artifacts for 30 days

## Signed GitHub Release

Use **Actions → Publish BlueMeter Lite Release → Run workflow** only after completing [SIGNING-SETUP.md](SIGNING-SETUP.md).

The release workflow defaults to:

```text
Tag:        v1.2.0
Draft:      true
Prerelease: false
```

It creates permanent Release assets:

- `BlueMeter-Lite-v1.2.0-arm64-v8a.apk`
- `BlueMeter-Lite-v1.2.0-armeabi-v7a.apk`
- `BlueMeter-Lite-v1.2.0-x86_64.apk`
- `BlueMeter-Lite-v1.2.0-source.zip`
- `SHA256SUMS.txt`
- `SIGNING-CERT-SHA256.txt`

Review the draft release, then publish it manually.

## Local Windows build

Requirements:

- Git
- Python 3
- Flutter 3.44.7
- Java 17
- Android SDK configured for Flutter

Run:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\build-local.ps1
```

When `private-signing/bluemeter-lite-release.jks` and `private-signing/key.properties` exist, the local build uses the permanent release key. Otherwise it falls back to debug signing.

## Architecture

- `arm64-v8a` — most modern Android phones
- `armeabi-v7a` — older 32-bit ARM devices
- `x86_64` — emulators and uncommon x86 Android devices

## AGPL corresponding source

Every public APK release must include the exact patched source used to build it. The release workflow removes private signing material before creating the source archive.
