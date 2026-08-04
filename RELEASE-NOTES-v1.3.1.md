# BlueMeter Lite v1.3.1

Fixes automatic encounter reset on map and dungeon transitions.

## Fixed

- Scene data from smaller current-player packets is now accepted
- Scene data from NPCs and other players remains ignored
- Dungeon line ID 0 is preserved
- Entering a dungeon resets the active encounter
- Leaving a dungeon resets the active encounter
- Map, channel, and line changes reset the active encounter
- The previous encounter is archived before new scene IDs are stored

## Version

`1.3.1+21`
