#!/usr/bin/env python3
"""Normalize one legacy dedented DataStorage block before v1.5 patching.

apply_lite_patch.py historically inserts its combat block with textwrap.dedent,
while the surrounding upstream class uses two-space indentation. Older releases
accept that Dart syntax, but the v1.5 patch intentionally uses exact anchors.
Normalize only the generated copy; the pinned upstream source is untouched.
"""

from __future__ import annotations

import sys
from pathlib import Path


def fail(message: str) -> None:
    raise SystemExit(f"Generated-source normalization failed: {message}")


def main() -> None:
    if len(sys.argv) != 2:
        fail("usage: normalize_generated_source.py <upstream-directory>")

    path = Path(sys.argv[1]).resolve() / "lib/core/state/data_storage.dart"
    text = path.read_text(encoding="utf-8")

    start_marker = "final Map<Int64, String> _liteSubProfessionNames = {};"
    reset_marker = "void reset({bool resetTimer = true}) {"

    start = text.find(start_marker)
    reset = text.find(reset_marker, start)
    if start == -1 or reset == -1:
        fail("could not locate legacy Lite combat block")

    start_line = text.rfind("\n", 0, start) + 1
    reset_line = text.rfind("\n", 0, reset) + 1

    # If the field line is already class-indented, leave the generated source
    # alone. This makes the normalizer harmless if the base patch is fixed later.
    if text[start_line:start].startswith("  "):
        return

    block = text[start_line:reset_line]
    normalized = "".join(
        ("  " + line if line.strip() else line)
        for line in block.splitlines(keepends=True)
    )

    # Crucially, reset_line itself is not touched. It already comes from the
    # original upstream class with correct indentation.
    text = text[:start_line] + normalized + text[reset_line:]
    path.write_text(text, encoding="utf-8")
    print("Normalized legacy Lite DataStorage combat indentation.")


if __name__ == "__main__":
    main()
