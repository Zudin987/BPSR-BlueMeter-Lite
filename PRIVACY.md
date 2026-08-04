# Privacy Policy

_Last updated: 2026-08-04_

BlueMeter Lite is an unofficial, open-source Android DPS overlay for Blue Protocol: Star Resonance.

## Data processed

To calculate live combat statistics, the app locally processes network packets belonging to supported BPSR Android clients. Parsed information can include:

- player names and identifiers
- profession or specialization
- Ability Score and Illusion-Breaking Strength
- damage values and encounter timing

## Local processing

Combat data is processed on the Android device.

BlueMeter Lite adds no:

- user accounts
- advertisements
- analytics
- cloud synchronization
- project-operated relay or collection server

The game continues communicating with its original servers. BlueMeter Lite forwards the selected game app's traffic to its original destination.

## Storage

The app stores lightweight encounter summaries locally on the phone so users can review DPS, Healing and Tanking data in the control app. These summaries can include player names, specializations, totals, per-second values, scene information and encounter timing.

Encounter history is not uploaded or synchronized. Entries older than seven days are deleted automatically, and users can delete individual entries or all history manually.

Overlay mode, selected meter, size, position, movement lock and auto-reset lock are also stored locally so the layout can be restored.

Temporary live combat values can remain in memory while the app and meter service are running.

## Android permissions

- **VPN service:** locally captures and forwards supported BPSR traffic
- **Display over other apps:** displays the DPS overlay above the game
- **Foreground service and notification:** keeps the local capture service visibly active
- **Package visibility:** checks whether a supported BPSR client is installed

Only installed supported BPSR packages are added to the VPN allow-list.

## Maintenance and contact

BlueMeter Lite is provided as-is. Routine support, feedback processing and diagnosis are not planned.
