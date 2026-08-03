# Validation status

Checked on 2026-08-04:

- Patch script passes Python syntax checking.
- Patch script passes a structural smoke test against the current upstream markers.
- Replacement `TcpProxy.kt` passes Kotlin syntax/type checking with Android and packet stubs.
- GitHub Actions workflow parses as valid YAML.
- Hidden `.github/workflows` files are included in the ZIP.

Not yet completed:

- Full Flutter/Gradle APK build in this environment.
- Installation on a physical Android device.
- Live BPSR protocol test.
- Measured ping, CPU, memory, and battery comparison.

The GitHub workflow is intended to perform the first complete APK build. Device
testing is still required before calling this a stable release.
