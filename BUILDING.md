# Building BlueMeter Lite

BlueMeter Lite is maintained as a patch kit on top of [BlueMeter Mobile](https://github.com/jbourny/bluemetermobile).

The build process:

1. clones the current upstream source
2. records the upstream Git commit
3. applies `patch/apply_lite_patch.py`
4. builds split Android release APKs
5. uploads the APKs and corresponding patched source

## GitHub Actions

1. Open the repository's **Actions** tab.
2. Select **Build BlueMeter Lite APK**.
3. Choose **Run workflow**.
4. Open the completed run.
5. Download `bluemeter-lite-apk`.
6. Download `bluemeter-lite-patched-source` when preparing a public release.

The workflow also runs automatically when the patch or build workflow changes.

## Local Windows build

Requirements:

- Git
- Python 3
- Flutter stable
- Java 17
- Android SDK configured for Flutter

From PowerShell:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\build-local.ps1
```

The APKs are copied to:

```text
build-output/
```

## APK architecture

Flutter produces split APKs:

- `arm64-v8a` — recommended for most modern Android phones
- `armeabi-v7a` — older 32-bit ARM devices
- `x86_64` — mainly emulators and uncommon x86 Android devices

## Upstream compatibility

The patch targets the current structure of BlueMeter Mobile. An upstream source change can break a patch marker even when BlueMeter Lite itself has not changed.

When that happens, update the patch against the new upstream layout and run the full GitHub Actions build again.

## Release signing

Before publishing 1.0, configure one persistent Android release signing key.

Do not rely on a newly generated CI signing identity for every build. Users must be able to install later releases over the existing app without uninstalling it.

Store the keystore and passwords as protected GitHub Actions secrets. Never commit a private signing key or password to the public repository.

## AGPL source requirement

For every distributed APK, provide the complete corresponding source. The GitHub workflow's patched-source artifact records the upstream revision and contains the generated source used for that build.
