#!/usr/bin/env python3
"""Apply the BlueMeter Lite release version to generated upstream source.

This script is run only by GitHub Actions. No local Python or PC build is
required. The final generated-source cleanup lives here as the last patch step
so PR and release builds analyze the exact same source tree.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

VERSION_NAME = "1.5.0"
VERSION_CODE = 25


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


def cleanup_generated_source(upstream: Path) -> None:
    main_dart = upstream / "lib/main.dart"
    storage_dart = upstream / "lib/core/state/data_storage.dart"

    main_text = main_dart.read_text(encoding="utf-8")

    # The Lite patch removes the upstream features that consumed these imports.
    # Keep flutter/services.dart: it already provides Uint8List for this file.
    for unused_import in (
        "import 'dart:typed_data';\n",
        "import 'package:bluemeter_mobile/core/services/translation_service.dart';\n",
        "import 'core/services/encounter_history_service.dart';\n",
        "import 'package:fixnum/fixnum.dart';\n",
    ):
        main_text = main_text.replace(unused_import, "", 1)

    # The Lite overlay does not support the old heavy player-detail selection
    # path. Remove the two surviving HomePage writes before removing its field.
    main_text, reset_selection_count = re.subn(
        r"\n[ \t]*setState\(\(\) \{\n"
        r"[ \t]*_selectedPlayerUid = null;\n"
        r"[ \t]*\}\);",
        "",
        main_text,
        count=1,
        flags=re.MULTILINE,
    )
    if reset_selection_count != 1:
        fail(
            "expected one legacy selected-player reset write, "
            f"found {reset_selection_count}"
        )

    main_text, set_selection_count = re.subn(
        r"\n[ \t]*setState\(\(\) \{\n"
        r"[ \t]*_selectedPlayerUid = newUid;\n"
        r"[ \t]*\}\);",
        "",
        main_text,
        count=1,
        flags=re.MULTILINE,
    )
    if set_selection_count != 1:
        fail(
            "expected one legacy selected-player assignment, "
            f"found {set_selection_count}"
        )

    main_text = main_text.replace(
        "  String? _selectedPlayerUid; // UID du joueur sélectionné pour affichage de la carte\n",
        "",
        1,
    )

    # This getter belonged to a removed overlay count badge and is no longer used.
    main_text, active_count = re.subn(
        r"\n[ \t]*int get _activePlayerCount \{\n"
        r"[ \t]*return _players\.where\(\(player\) => "
        r"_playerMetricTotal\(player\) > 0\)\.length;\n"
        r"[ \t]*\}\n",
        "\n",
        main_text,
        count=1,
        flags=re.MULTILINE,
    )
    if active_count != 1:
        fail(f"expected one unused active-player getter, found {active_count}")

    main_dart.write_text(main_text, encoding="utf-8")

    storage_text = storage_dart.read_text(encoding="utf-8")

    # Dart 3.12 promotes these nullable method parameters after the explicit
    # guards in the scene/line path, so the legacy assertions are redundant.
    final_warning_replacements = (
        ("      lineId! > 0 &&\n", "      lineId > 0 &&\n"),
        ("    _channelId = channelId!;\n", "    _channelId = channelId;\n"),
        ("    _lineId = lineId!;\n", "    _lineId = lineId;\n"),
    )
    for old, new in final_warning_replacements:
        count = storage_text.count(old)
        if count != 1:
            fail(f"expected one final analyzer cleanup anchor {old.strip()!r}, found {count}")
        storage_text = storage_text.replace(old, new, 1)

    # Keep the pending-combat start-tick `!` operators intact. Those mutable
    # object properties are not promotable through their second comparison.
    storage_dart.write_text(storage_text, encoding="utf-8")


def main() -> None:
    if len(sys.argv) != 2:
        fail("usage: apply_release_version.py <upstream-directory>")

    upstream = Path(sys.argv[1]).resolve()
    pubspec = upstream / "pubspec.yaml"
    main_dart = upstream / "lib/main.dart"
    storage_dart = upstream / "lib/core/state/data_storage.dart"

    for required in (pubspec, main_dart, storage_dart):
        if not required.exists():
            fail(f"missing generated source file: {required}")

    cleanup_generated_source(upstream)

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
    print("Generated Dart analyzer cleanup applied.")


if __name__ == "__main__":
    main()
