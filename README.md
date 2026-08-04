<div align="center">

# BlueMeter Lite

**A lightweight Android DPS overlay for Blue Protocol: Star Resonance.**

No PC required. Runs directly on your Android device.

[![Build](https://github.com/Zudin987/BPSR-BlueMeter-Lite/actions/workflows/build-apk.yml/badge.svg)](https://github.com/Zudin987/BPSR-BlueMeter-Lite/actions/workflows/build-apk.yml)
[![License: AGPL-3.0](https://img.shields.io/badge/license-AGPL--3.0-blue.svg)](LICENSE)
![Platform](https://img.shields.io/badge/platform-Android-green.svg)

[**Download the latest APK**](https://github.com/Zudin987/BPSR-BlueMeter-Lite/releases/latest)

</div>

## Screenshots

### Compact mode

Compact mode keeps the ranking, player name, total damage, DPS and contribution percentage in a small window.

<img src="docs/screenshots/bluemeter-lite-compact.png" alt="BlueMeter Lite compact overlay" width="520">

### Expanded mode

Expanded mode adds the detected specialization, Ability Score and Illusion-Breaking Strength.

<img src="docs/screenshots/bluemeter-lite-expanded.png" alt="BlueMeter Lite expanded overlay" width="760">

## Features

- Live ranking by total damage
- Current DPS shown beside total damage
- Group damage contribution percentage
- Compact and Expanded overlay modes
- Detected profession or specialization
- Ability Score and Illusion-Breaking Strength
- Gold star and highlight for the local player
- One-column list with vertical scrolling
- Movable and manually resizable overlay
- Manual encounter reset
- Up to 20 displayed damage dealers
- Android-only local capture with no PC relay

BlueMeter Lite intentionally focuses on the live meter. It does not include skill breakdowns, timelines, encounter history, healing tabs, target analysis, radar or boss-timer tools.

## Download and install

1. Open the [latest GitHub release](https://github.com/Zudin987/BPSR-BlueMeter-Lite/releases/latest).
2. Download the APK marked **arm64-v8a**. This is the correct build for most modern Android phones.
3. Install the APK.
4. Open **BlueMeter Lite**.
5. Grant **Display over other apps** permission.
6. Tap **Start DPS Meter** and approve Android's VPN request.
7. Launch BPSR and enter combat.

Android displays a VPN indicator and a foreground-service notification while the meter is active.

## Overlay controls

| Control | Action |
|---|---|
| `C` | Switch to Compact mode at `180 × 80` |
| `E` | Switch to Expanded mode at `360 × 180` |
| Header drag | Move the overlay |
| Bottom-right handle | Resize the overlay |
| Reset icon | Reset the current encounter |

The player list always stays in one column. Resize the window vertically and scroll when more rows are available.

## Display format

Compact:

```text
01. ★ MrHard                         2.8M (79.9K)   23%
```

Expanded:

```text
01. ★ MrHard — Frostbeam (49632+2250)   2.8M (77.8K)   19%
```

The values in parentheses after a player name are:

```text
Ability Score + Illusion-Breaking Strength
```

The values after total damage are:

```text
Total Damage (DPS)
```

## Supported Android clients

| Region/client | Android package |
|---|---|
| HaoPlay SEA | `sea.haoplay.game.gp.bpsr` |
| A Plus Japan / Global | `com.bpsr.apj` |
| Taiwan / Hong Kong / Macau | `tw.haoplay.game.gp.xhgm` |
| X.D. regional client | `asia.xdg.game.gp.bpsr` |

Only installed supported BPSR packages are added to the Android VPN allow-list.

## Privacy and network behaviour

BlueMeter Lite processes supported BPSR traffic locally on the phone and forwards it to the game's original destination. The project does not operate a relay server and does not require an account.

BlueMeter Lite does not add advertising, analytics or cloud synchronization. See [PRIVACY.md](PRIVACY.md) for details.

## Troubleshooting

### The game has no internet after starting the meter

Stop BlueMeter Lite, reopen it and start the meter again. Also confirm that your installed BPSR client is listed under [Supported Android clients](#supported-android-clients).

### A player's class or scores are missing

Some information appears only after the relevant player or combat packet is received. Enter combat or wait until the player uses a specialization-specific skill.

### The APK will not install over an older build

Uninstall the older beta build, then install the new APK. Stable release signing should prevent this after the official 1.0 release.

### The overlay is too small

Switch modes with `C` or `E`, then use the bottom-right resize handle.

For unresolved problems, open a [bug report](https://github.com/Zudin987/BPSR-BlueMeter-Lite/issues/new/choose).

## Building from source

This repository is a reproducible patch kit based on BlueMeter Mobile. The build workflow clones the upstream source, records its revision, applies the Lite patch and builds split Android APKs.

See [BUILDING.md](BUILDING.md) for GitHub Actions and local build instructions.

## Credits

- [BlueMeter Mobile](https://github.com/jbourny/bluemetermobile) by jbourny and contributors — upstream Android meter
- [BPSR-ZDPS](https://github.com/Blue-Protocol-Source/BPSR-ZDPS) — protocol, profession and attribute reference
- Blue Protocol: Star Resonance and related names belong to their respective owners

This is an unofficial community project and is not affiliated with Bandai Namco, HaoPlay, A Plus Japan, X.D. Global, Bokura or the official game developers and publishers.

## License

BlueMeter Lite is distributed under the [GNU Affero General Public License v3.0](LICENSE).

Modified APK distributions must make their complete corresponding source available, including the Lite patch and the upstream revision used for the build. See [LICENSE-NOTICE.md](LICENSE-NOTICE.md).
