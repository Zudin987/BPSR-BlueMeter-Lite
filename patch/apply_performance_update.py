#!/usr/bin/env python3
"""Deprecated compatibility entry point.

BlueMeter Lite's current overlay already includes the two-second refresh,
idle redraw pause, top-20 rendering, sorting cache, and formatted-number cache.

This file intentionally changes nothing. BlueMeter Lite updates should be
applied by uploading replacement files to GitHub and running the existing
GitHub Actions workflow; no local Python command is required.
"""

from __future__ import annotations


def main() -> None:
    print("No action required.")
    print("The current BlueMeter Lite performance update is already integrated.")
    print("Use GitHub Actions to build the APK.")


if __name__ == "__main__":
    main()
