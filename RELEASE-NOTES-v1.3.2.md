# BlueMeter Lite v1.3.2

This test update replaces SceneData-only reset detection with the primary
signals used by ZDPS.

## Map changes

A full local-player `SyncContainerData` packet is received when a map load
begins. ZDPS starts a new battle immediately on this packet and notes that
ordinary teleports do not trigger it.

BlueMeter Lite now follows that same boundary, with a first-packet startup
guard.

## Dungeon entry

The app now registers:

```text
WorldNtf.SyncDungeonData = 0x17
```

The arrival of that dedicated dungeon snapshot can split the previous
encounter as `new_dungeon`. A three-second duplicate guard prevents both map
and dungeon packets from creating two history entries for one transition.

## Remaining reset work

ZDPS uses more detailed data for:

- phase splitting: dungeon state, objective TargetId, Complete, and Nums
- modern wipe detection: buff IDs 500111, 500112, and 510072
- legacy wipe fallback: actor states plus boss HP reset

Those structures are not yet fully decoded by BlueMeter Mobile. Existing phase
and wipe detection remains heuristic in this test version.

## Version

`1.3.2+22`
