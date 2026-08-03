# BPSR BlueMeter Lite

A lightweight Android-only DPS overlay for **Blue Protocol: Star Resonance**.

This kit applies a small, focused fork on top of
[`jbourny/bluemetermobile`](https://github.com/jbourny/bluemetermobile), then
builds an APK through GitHub Actions.

## Lite design

Included:

- Live DPS ranking
- Player name
- Encounter timer
- Manual reset button
- Adaptive and manually resizable overlay
- Local Android VPN capture
- No PC required

Removed from the active UI/data bridge:

- Boss timer/BPTimer reporting
- Nearby monster radar
- Hunt tools
- Skill breakdown
- Target breakdown
- Timeline graph
- Player detail screen
- Heal/taken tabs
- Overlay themes and detailed configuration panels
- Monster and position serialization

Low-resource changes:

- Overlay updates once per second instead of twice per second
- Only six small fields are sent to the overlay per player
- Up to 20 damage dealers are shown, with automatic party/raid layouts
- No monster, skill, timeline or position data is copied to the overlay isolate
- DPS storage no longer allocates skill, per-target, timeline, healing or damage-taken records
- TCP writes use a pending-write queue instead of assuming a non-blocking
  socket writes the full payload in one call
- TCP_NODELAY is enabled on game sockets
- Kotlin-to-Flutter packet flushing is reduced to once per second

Supported Android game packages:

- `sea.haoplay.game.gp.bpsr` — HaoPlay SEA
- `com.bpsr.apj` — A Plus Japan/global
- `tw.haoplay.game.gp.xhgm` — Taiwan/Hong Kong/Macau
- `asia.xdg.game.gp.bpsr` — X.D. regional client

## Build the APK with GitHub

1. Create a new empty public GitHub repository.
2. Upload the **contents** of this ZIP, including the `.github` folder.
3. Open the repository's **Actions** tab.
4. Choose **Build BlueMeter Lite APK**.
5. Click **Run workflow**.
6. After the build completes, open it and download:
   `bluemeter-lite-apk`.
7. Install the `arm64-v8a` APK on a modern Android phone.

The workflow clones the current upstream BlueMeter source, applies this Lite
patch, builds release APKs, and uploads them as an artifact.

## Use

1. Install the APK.
2. Open **BlueMeter Lite**.
3. Grant **Display over other apps**.
4. Tap **Start DPS Meter**.
5. Approve the Android VPN request.
6. Launch BPSR.

Android will show a VPN indicator and a persistent service notification while
the meter is active. Only installed supported BPSR packages are added to the
VPN allow-list.

## Adaptive overlay

- Auto mode sizes the window for solo, 5-player, 10-player, and 20-player use.
- Wide raid mode splits up to 20 players into two columns.
- The header can move the window and the bottom-right handle can resize it.
- Text and row density adapt to the actual window dimensions.
- The local player is highlighted and remains visible if outside the top 20.

## Ping expectations

The queued socket writer fixes a clear weakness in the upstream proxy:
`SocketChannel.write()` is non-blocking and may write only part of a buffer.
The upstream implementation acknowledged the whole game packet after one write
attempt. Lite queues unsent bytes and finishes them on `OP_WRITE`.

This should reduce avoidable stalls and packet loss, but a local Android
`VpnService` still forwards game traffic in userspace. **Zero additional ping
cannot be guaranteed.** Test normal ping and Lite ping in the same location.

## Important

- This is an experimental community tool.
- It has not been built or tested on a physical phone in this environment.
- Keep the original upstream attribution and AGPL license.
- Publishing a modified APK requires making the corresponding source available
  under AGPL-3.0.
- Game policies and enforcement can change.
