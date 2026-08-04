# Privacy Policy

_Last updated: 2026-08-04_

BlueMeter Lite is an unofficial, open-source Android DPS overlay for Blue Protocol: Star Resonance.

## Data processed

To calculate combat statistics, the app locally processes network packets belonging to supported BPSR Android clients. Parsed information can include:

- player names and identifiers
- profession or specialization
- Ability Score and Illusion-Breaking Strength
- damage values and encounter timing

## Local processing

Combat data is processed on the Android device for the live overlay.

BlueMeter Lite does not add:

- user accounts
- advertisements
- analytics
- cloud synchronization
- a project-operated relay or collection server

The game itself continues communicating with its original servers. BlueMeter Lite forwards the selected game app's traffic to its original destination.

## Storage

The Lite interface is designed around the current live encounter. It does not provide a cloud history or account-based combat database.

Temporary values can remain in memory while the app and meter service are running. Stopping the app or resetting the encounter clears the active meter data according to the app's normal behaviour.

## Android permissions

BlueMeter Lite uses:

- **VPN service:** to locally capture and forward traffic from supported BPSR packages
- **Display over other apps:** to show the DPS meter above the game
- **Foreground service and notification:** to keep the local capture service running visibly

Android displays a VPN indicator while the service is active.

## Supported packages

The VPN allow-list is restricted to supported installed BPSR clients. BlueMeter Lite is not intended to capture traffic from unrelated apps.

## Sharing diagnostic information

Do not upload raw packet captures, authentication tokens or other sensitive network data to public GitHub issues.

Screenshots of the DPS overlay and ordinary GitHub Actions logs are generally more appropriate for bug reports.

## Contact

Privacy questions and bug reports can be submitted through the project's GitHub Issues page.
