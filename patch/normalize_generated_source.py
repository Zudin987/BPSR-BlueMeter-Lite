#!/usr/bin/env python3
"""Normalize legacy dedented generated Dart blocks before v1.5 patching.

Older Lite patch helpers use textwrap.dedent for inserted class members. Dart
accepts the result because whitespace is not semantic, but exact follow-up patch
anchors become unnecessarily fragile. Normalize only the generated checkout;
the pinned upstream source and historical patch behavior remain untouched.
"""

from __future__ import annotations

import sys
from pathlib import Path


def fail(message: str) -> None:
    raise SystemExit(f"Generated-source normalization failed: {message}")


def indent_region(text: str, start_token: str, end_token: str, label: str) -> str:
    start_token_index = text.find(start_token)
    if start_token_index == -1:
        fail(f"could not locate start of {label}: {start_token}")

    end_token_index = text.find(end_token, start_token_index + len(start_token))
    if end_token_index == -1:
        fail(f"could not locate end of {label}: {end_token}")

    start_line = text.rfind("\n", 0, start_token_index) + 1
    end_line = text.rfind("\n", 0, end_token_index) + 1

    prefix = text[start_line:start_token_index]
    if prefix.startswith("  "):
        return text

    block = text[start_line:end_line]
    normalized = "".join(
        ("  " + line if line.strip() else line)
        for line in block.splitlines(keepends=True)
    )
    return text[:start_line] + normalized + text[end_line:]


def normalize_storage(root: Path) -> None:
    path = root / "lib/core/state/data_storage.dart"
    text = path.read_text(encoding="utf-8")
    text = indent_region(
        text,
        "final Map<Int64, String> _liteSubProfessionNames = {};",
        "void reset({bool resetTimer = true}) {",
        "DataStorage Lite combat block",
    )
    path.write_text(text, encoding="utf-8")


def normalize_main(root: Path) -> None:
    path = root / "lib/main.dart"
    text = path.read_text(encoding="utf-8")

    # apply_lite_patch.py inserts the lightweight overlay bridge with dedent().
    # By the time this script runs, apply_performance_update.py has added the
    # bridge interval immediately before the season-strength cache.
    bridge_start = (
        "static const Duration _liteOverlayBridgeInterval"
        if "static const Duration _liteOverlayBridgeInterval" in text
        else "final Map<String, int> _liteSeasonStrengthCache = {};"
    )
    text = indent_region(
        text,
        bridge_start,
        "Future<void> _onPacketData(dynamic event) async",
        "HomePage Lite overlay bridge",
    )

    # The replacement HomePage service/UI tail is also dedented historically.
    tail_token = "Future<List<String>> _refreshSupportedClients() async"
    tail_index = text.find(tail_token)
    if tail_index == -1:
        fail("could not locate HomePage Lite tail")
    tail_line = text.rfind("\n", 0, tail_index) + 1

    # apply_lite_patch.py intentionally replaces the rest of HomePage and writes
    # one final class-closing brace at EOF. Do not indent that closing brace.
    final_close = text.rfind("\n}")
    if final_close == -1 or final_close < tail_line:
        fail("could not locate final HomePage closing brace")
    final_close += 1

    if not text[tail_line:tail_index].startswith("  "):
        block = text[tail_line:final_close]
        normalized = "".join(
            ("  " + line if line.strip() else line)
            for line in block.splitlines(keepends=True)
        )
        text = text[:tail_line] + normalized + text[final_close:]

    path.write_text(text, encoding="utf-8")


def main() -> None:
    if len(sys.argv) != 2:
        fail("usage: normalize_generated_source.py <upstream-directory>")

    root = Path(sys.argv[1]).resolve()
    normalize_storage(root)
    normalize_main(root)
    print("Normalized legacy Lite generated Dart indentation.")


if __name__ == "__main__":
    main()
