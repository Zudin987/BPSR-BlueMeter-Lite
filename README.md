# BlueMeter Lite

A lightweight Android combat meter for **Blue Protocol: Star Resonance**. It shows DPS, healing, and damage received directly over the game without requiring a PC.

> **Unofficial community project.** Not affiliated with the game's developers or publishers.

## Quick start

1. Install and open BlueMeter Lite.
2. Tap **Start DPS Meter**, then allow **Display over other apps** and approve Android's VPN prompt.
3. Open BPSR and start fighting. The meter appears over the game.

BlueMeter Lite uses Android's **local VPN** feature to observe supported BPSR traffic on the same device. It is not a project-operated remote VPN service.

## Features

- **DPS**, **Healing**, and **Tanking** meters.
- Compact and expanded overlay layouts.
- Manual reset plus automatic encounter reset.
- Movable/resizable overlay with a position lock.
- Encounter history kept locally for up to **7 days**.
- No user account, ads, analytics, cloud sync, or project-operated combat-data server.

## Main controls

- **DPS / Healing / Tanking** — switch meter.
- **C / E** — compact or expanded view.
- **Auto-reset icon** — enable or lock automatic encounter reset.
- **Padlock** — allow or prevent moving/resizing the overlay.
- **Reset arrow** — save and clear the current encounter.
- Drag the top bar to move; use the bottom-right handle to resize while unlocked.

The selected meter, view mode, position, size, and lock states are remembered.

## Encounter reset

With automatic reset enabled, BlueMeter Lite can start a new encounter after supported map, channel, dungeon, wipe, or boss-phase changes. Some unusual transitions may not be detected perfectly, so use manual reset when needed.

## Supported Android clients

- HaoPlay SEA
- A Plus Japan / Global
- Taiwan / Hong Kong / Macau
- X.D. regional client

Game or protocol updates can require a BlueMeter Lite update.

## Troubleshooting

- **Overlay missing:** stop the meter, confirm **Display over other apps**, then start again.
- **Game has no internet while running:** stop/reopen the meter and confirm the installed BPSR client is detected.
- **Wrong overlay size/position:** unlock the position padlock, then move/resize it or use **C / E**.
- **Cannot install over v1.0.0:** uninstall v1.0.0 once, then install the newer permanently signed build.

## Privacy and repository safety

Combat information is processed locally on your Android device. See [PRIVACY.md](PRIVACY.md) for details.

Signing secrets are kept in GitHub Actions secrets, and generated APK/build archives belong in Actions or Releases rather than the source tree.

## Project docs

- [Building from source](BUILDING.md)
- [Signing setup](SIGNING-SETUP.md)
- [Changelog](CHANGELOG.md)
- [Third-party notices](THIRD-PARTY-NOTICES.md)
- [License notice](LICENSE-NOTICE.md)

## License and credits

BlueMeter Lite is a modified derivative of **BlueMeter Mobile** and is distributed under the [GNU AGPL-3.0 license](LICENSE). It also uses scene/profession/protocol references from **BPSR-ZDPS** under MIT.

Blue Protocol: Star Resonance and related names belong to their respective owners.
