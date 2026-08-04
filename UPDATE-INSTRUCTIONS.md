# BlueMeter Lite v0.9.1 — GitHub patch-matcher fix

The v0.9 build failed during `Apply Lite patch` with:

`could not find initial nearby-player Season 3 strength cases`

## Cause

The patch searched for the correct Dart switch cases using an exact text block.
Current upstream has different indentation and no blank line between the
`attrFightPoint` and `attrLevel` cases.

## Fix

v0.9.1 uses a whitespace-tolerant regular expression. It:

1. finds `AttrType.attrFightPoint`
2. accepts any indentation
3. accepts zero or more blank lines
4. inserts the two Season 3 cases
5. preserves the original indentation

The matcher was tested against the current upstream source layout.

## GitHub update

Replace only:

`patch/apply_lite_patch.py`

The overlay file is included unchanged for completeness.

## Version

`1.10.1+14`
