<div align="center">

# BlueMeter Lite

A lightweight Android combat meter for **Blue Protocol: Star Resonance**.

Shows DPS, healing, and damage received directly over the game without requiring a PC.

**Unofficial community project. Not affiliated with the game's developers or publishers.**

</div>

> **TL;DR:** Install the APK, tap **Start DPS Meter**, allow the overlay + Android VPN prompts, then play BPSR. Combat processing stays on your phone.

## What this app does

- Shows **DPS**, **Healing**, and **Tanking** meters.
- Runs as an Android overlay on top of BPSR.
- Uses Android's local VPN feature to observe supported BPSR traffic on the same device.
- Keeps encounter history for up to **7 days**.
- Supports compact/expanded layouts, manual reset, auto-reset lock, and movable/resizable overlay positioning.
- Adds no user account, ads, analytics, cloud sync, or project-operated combat-data server.

## Quick Start — 1, 2, 3

1. **Install and open BlueMeter Lite.**
2. Tap **Start DPS Meter**, then allow **Display over other apps** and approve Android's **VPN** request.
3. Open BPSR and start fighting. The meter appears over the game.

> Android shows a VPN icon while the meter is running. BlueMeter Lite uses a **local VPN** for supported BPSR traffic analysis; it is not a project-operated remote VPN service.

## Overlay buttons

| Button | What it does |
|---|---|
| **DPS / Healing / Tanking** | Switches the current meter. |
| **C** | Compact view. |
| **E** | Expanded view. |
| **Grey auto-reset icon** | Automatic encounter reset is enabled. |
| **Orange crossed auto-reset icon** | Automatic reset is locked/off. |
| **Grey open lock** | Overlay can be moved/resized. |
| **Yellow closed lock** | Overlay position/size is locked. |
| **Reset arrow** | Saves and clears the current encounter. |
| **Drag top bar** | Moves the overlay while unlocked. |
| **Bottom-right handle** | Resizes the overlay while unlocked. |

> **There are two different locks:** the orange control affects encounter auto-reset; the yellow padlock affects only overlay movement/resizing.

The selected meter, view mode, position, size, and lock states are remembered.

## What the three meters mean

- **DPS** — total damage, damage per second, and party share.
- **Healing** — total healing, healing per second, and party share.
- **Tanking** — total damage received, damage received per second, and party share.

Example expanded row:

```text
01. ★ Player — Frostbeam (49,632 + 2,250)  2.8M (79.9K)  23%
```

- `★` marks your detected character.
- `49,632 + 2,250` is Ability Score + Illusion-Breaking Strength.
- `2.8M` is the encounter total for the selected meter.
- `79.9K` is the per-second value.
- `23%` is the share of the group total.

## Encounter history and reset behavior

With automatic reset enabled, BlueMeter Lite can start a new encounter after supported map, channel, dungeon, wipe, or boss-phase changes.

An encounter is saved when an automatic reset happens, you press manual reset, or you stop the meter. History is stored locally on the phone and entries older than **7 days** are deleted automatically.

Some unusual boss phases/wipes may not be detected perfectly; use manual reset when needed.

## Supported Android clients

- HaoPlay SEA
- A Plus Japan / Global
- Taiwan / Hong Kong / Macau
- X.D. regional client

Game/protocol updates can require a BlueMeter Lite update.

## Common problems

<details>
<summary><strong>The overlay does not appear</strong></summary>

1. Stop the meter.
2. Confirm **Display over other apps** is enabled.
3. Start the meter again.

</details>

<details>
<summary><strong>The game has no internet while the meter is running</strong></summary>

Stop the meter, reopen BlueMeter Lite, and start it again. Also confirm the app detects your installed BPSR client.

</details>

<details>
<summary><strong>The overlay is too small or in the wrong place</strong></summary>

Unlock the yellow position padlock, drag the top bar, or resize using the bottom-right handle. Use **C** / **E** for the default compact/expanded sizes.

</details>

<details>
<summary><strong>The APK will not install over v1.0.0</strong></summary>

Uninstall v1.0.0 once, then install the newer version. Builds using the permanent signing key can update normally afterward.

</details>

## Privacy

Combat information is processed locally on your Android device. BlueMeter Lite adds no user account, advertising, analytics, cloud synchronization, or project-operated relay server.

See [PRIVACY.md](PRIVACY.md) for the detailed privacy description.

## Security / repository notes

- Signing keys and passwords are GitHub Actions secrets and are not stored in the repository.
- Normal validation builds use read-only repository permission.
- Generated APKs and build archives belong in Actions/Releases, not in the source tree.
- The build is based on a pinned upstream BlueMeter Mobile commit and publishes corresponding patched source alongside release builds.

## Project information

- [Building from source](BUILDING.md)
- [Signing setup](SIGNING-SETUP.md)
- [Changelog](CHANGELOG.md)
- [Third-party notices](THIRD-PARTY-NOTICES.md)
- [License notice](LICENSE-NOTICE.md)

### Credits and licence

- Modified derivative of **BlueMeter Mobile**, licensed under GNU AGPL v3.
- Uses scene/profession/protocol references from **BPSR-ZDPS**, licensed under MIT.
- This repository is distributed under the [GNU AGPL-3.0 licence](LICENSE).

Blue Protocol: Star Resonance and related names belong to their respective owners.
