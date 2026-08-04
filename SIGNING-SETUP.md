# Permanent Android signing setup

Complete this once before publishing v1.1.0.

> [!CAUTION]
> The signing key is the app's permanent identity. Losing it prevents normal future updates. Publishing a different key requires users to uninstall again.

## 1. Generate the key locally

From the repository root in PowerShell:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\generate-release-keystore.ps1
```

This creates a local, Git-ignored folder:

```text
private-signing/
├── bluemeter-lite-release.jks
├── key.properties
└── github-secrets.txt
```

Do not upload any of these files.

## 2. Back it up

Copy the entire `private-signing` folder to at least two secure locations, such as:

- an encrypted USB drive kept offline
- an encrypted password-manager attachment or encrypted archive

Keep the password file together with the key backup, but never in the public repository.

## 3. Add four GitHub Actions secrets

Open the repository:

```text
Settings
→ Secrets and variables
→ Actions
→ New repository secret
```

Open `private-signing/github-secrets.txt` locally and create:

```text
ANDROID_KEYSTORE_BASE64
ANDROID_KEYSTORE_PASSWORD
ANDROID_KEY_ALIAS
ANDROID_KEY_PASSWORD
```

Copy only the value after each `=`.

## 4. Test the signed build

Run:

```text
Actions
→ Build BlueMeter Lite APK
→ Run workflow
```

Download the `arm64-v8a` APK and test it.

Because v1.0.0 used the upstream debug certificate, uninstall v1.0.0 before installing the new permanently signed build. This one-time migration is expected.

## 5. Never regenerate the key

All releases from v1.1.0 onward must use this exact `.jks` file and the same four secret values.
