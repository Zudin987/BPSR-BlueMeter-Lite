# v1.1.0 release checklist

## Repository update

Upload or replace:

```text
.github/workflows/build-apk.yml
.github/workflows/release.yml
patch/apply_lite_patch.py
scripts/generate-release-keystore.ps1
README.md
BUILDING.md
SIGNING-SETUP.md
CHANGELOG.md
PRIVACY.md
MAINTENANCE.md
RELEASE-NOTES-v1.1.0.md
REPOSITORY-SETTINGS.md
build-local.ps1
.gitignore
```

Delete:

```text
VALIDATION.md
CONTRIBUTING.md
UPDATE-INSTRUCTIONS.md
```

Suggested commit message:

```text
Prepare signed BlueMeter Lite v1.1.0 release
```

## Signing

1. Run `scripts/generate-release-keystore.ps1` locally.
2. Back up `private-signing/` twice.
3. Add the four GitHub Actions secrets.
4. Never upload the private-signing folder.

## Test build

1. Open **Actions**.
2. Run **Build BlueMeter Lite APK**.
3. Confirm the workflow succeeds.
4. Download the `arm64-v8a` APK.
5. Uninstall v1.0.0.
6. Install and test the new APK:
   - detected client appears
   - Start opens the overlay
   - VPN works
   - drag works while unlocked
   - resize works while unlocked
   - lock disables drag and resize
   - layout returns after restarting
   - DPS and remote season strength appear

## Create the second release

1. Open **Actions**.
2. Run **Publish BlueMeter Lite Release**.
3. Keep:
   - tag: `v1.1.0`
   - draft: `true`
   - prerelease: `false`
4. Wait for the workflow to create a draft release.
5. Open **Releases**.
6. Inspect assets and release notes.
7. Publish the draft.

## Final repository cleanup

Follow `REPOSITORY-SETTINGS.md` and disable Issues.
