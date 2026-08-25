# BlueMeter Lite v1.5.0

This release focuses on one rule: keep the meter useful while making its impact
on BPSR as small as practical.

## Performance

- Replaces the native 1 ms polling loop with selector-driven TCP/UDP forwarding.
- The TUN reader wakes the network selector only when game traffic arrives.
- Uses a bounded TUN queue with backpressure instead of dropping game packets.
- Caps reusable packet/buffer pools and expires idle UDP sessions.
- Keys UDP sessions by the complete source/destination four-tuple.
- Removes per-MSS `copyOfRange()` allocations in the TCP proxy.
- Reads TUN packets directly into reusable buffers instead of copying through a
  permanent intermediate read buffer.
- Replaces package-scoped Android packet broadcasts with an in-process bridge to
  Flutter EventChannels.
- Moves packet-batch copies/Flutter delivery outside the native buffer lock.
- Rewrites Dart packet reassembly around reusable storage and read/write offsets.
- Uses `Uint8List.sublistView` for packet/message slices where safe.
- Replaces the permanent overlay polling timer with dirty/event-driven updates.
- Removes the second overlay-side two-second throttle; there is now one visible
  update throttle instead of two stacked delays.
- Reduces wall-clock work in the combat hot path to roughly once per second.
- Stops re-parsing specialization skill IDs after a player's specialization is
  known for the encounter.

## Memory and storage

- Known NPCs no longer become player DPS entries or player-database candidates.
- Combat from not-yet-identified UIDs is held in a small bounded staging cache;
  it is promoted when the UID is confirmed as a player and discarded when it is
  confirmed as a monster.
- Player metadata SQLite writes are coalesced per UID and use one UPSERT after a
  burst of sync updates.
- Player-cache cleanup and encounter-history expiry cleanup run at most daily.
- Removes unused upstream runtime dependencies and unused class-image assets from
  the generated Lite package.

## Reliability

- Adds duplicate/retransmission overlap handling to the local TCP proxy.
- Out-of-order app segments are not forwarded ahead of missing bytes; the proxy
  ACKs the last contiguous sequence so Android can retransmit normally.
- Pooled `Packet` objects clear all parsed fields before reuse so malformed or
  short packets cannot inherit stale metadata.
- Meter stop is non-sticky: Android will not intentionally restart the VPN
  capture service after the user stops it.

## Tests and regression protection

- Adds a 10,000-packet replay test for the low-copy Dart reassembler.
- Adds extreme-fragmentation and stream-reset tests.
- Adds combat-storage tests proving NPCs do not become player DPS entries and
  staged damage is preserved when an unknown UID becomes a player.
- CI now verifies the final generated source and fails if high-impact patterns
  such as the 1 ms polling loop, Android packet broadcasts, `copyOfRange`,
  `BytesBuilder.toBytes()`, permanent overlay polling, or per-write player DB
  existence queries return.

## Core features retained

- Damage / DPS
- Healing / HPS
- Tanking / damage taken
- Compact and expanded overlay
- Encounter history
- Automatic encounter splitting and reset lock
- Player class/sub-profession detection
- Ability Score and Illusion-Breaking Strength display
- Supported regional BPSR Android clients

## Version

`1.5.0+25`
