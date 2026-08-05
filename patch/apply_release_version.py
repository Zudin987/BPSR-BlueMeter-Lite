#!/usr/bin/env python3
"""Apply the BlueMeter Lite release version to generated upstream source.

This script is run only by GitHub Actions. No local Python or PC build is
required.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

VERSION_NAME = "1.4.1"
VERSION_CODE = 24


def fail(message: str) -> None:
    raise SystemExit(f"BlueMeter Lite version patch failed: {message}")


def replace_regex_once(
    text: str,
    pattern: str,
    replacement: str,
    label: str,
) -> str:
    updated, count = re.subn(
        pattern,
        replacement,
        text,
        count=1,
        flags=re.MULTILINE,
    )
    if count != 1:
        fail(f"expected one {label}, found {count}")
    return updated


def main() -> None:
    if len(sys.argv) != 2:
        fail("usage: apply_release_version.py <upstream-directory>")

    upstream = Path(sys.argv[1]).resolve()
    pubspec = upstream / "pubspec.yaml"
    main_dart = upstream / "lib/main.dart"

    for required in (pubspec, main_dart):
        if not required.exists():
            fail(f"missing generated source file: {required}")

    pubspec_text = pubspec.read_text(encoding="utf-8")
    pubspec_text = replace_regex_once(
        pubspec_text,
        r"^version:\s*[^\r\n]+$",
        f"version: {VERSION_NAME}+{VERSION_CODE}",
        "pubspec version",
    )
    pubspec.write_text(pubspec_text, encoding="utf-8")

    main_text = main_dart.read_text(encoding="utf-8")
    main_text = replace_regex_once(
        main_text,
        r"^(\s*static const String _liteVersion = )'[^']+';$",
        rf"\g<1>'{VERSION_NAME}';",
        "in-app Lite version",
    )
    main_dart.write_text(main_text, encoding="utf-8")

    print(
        "BlueMeter Lite release version applied: "
        f"{VERSION_NAME}+{VERSION_CODE}"
    )


if __name__ == "__main__":
    main()
