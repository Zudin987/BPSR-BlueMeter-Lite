# BlueMeter Lite v1.2.0

BlueMeter Lite now includes three lightweight live meters:

- **DPS**
- **Healing**
- **Tanking**

## New meter tabs

Use the tab bar below the overlay header to switch between:

### DPS

Ranks players by:

```text
Total Damage (DPS)   Contribution %
```

### Healing

Ranks players by:

```text
Total Healing (HPS)   Contribution %
```

### Tanking

Ranks players by:

```text
Total Damage Received (Taken Per Second)   Contribution %
```

The selected tab is saved and restored the next time the overlay starts.

## Lightweight by design

This update stores only the totals and separate active-time clocks required for the three live rankings.

It does not add:

- skill breakdowns
- overheal calculation
- mitigation or shielding totals
- deaths
- target breakdowns
- timelines
- encounter history

This keeps the Android app much lighter than a full desktop meter.

## Existing features retained

- Compact and Expanded modes
- one-column scrolling
- local-player star and highlight
- profession, specialization, Ability Score and Illusion-Breaking Strength
- saved position, size, mode and lock state
- drag and resize while unlocked
- lock disables both dragging and resizing
- portrait control app
- supported-client detection
- permanent release signing

## Which APK to download

Most modern Android phones:

```text
BlueMeter-Lite-v1.2.0-arm64-v8a.apk
```

## Upgrade

Users on v1.1.0 can install v1.2.0 normally without uninstalling, because both releases use the same permanent signing key.
