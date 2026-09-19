#!/usr/bin/env python3
"""
Replace Ren'Py Android icon templates.

Usage:  icon_replace.py <renpy_sdk_path> <foreground_png> <background_png>

Backs up originals as .bak, then copies new foreground/background
into rapt/templates/.
"""

import json
import os
import shutil
import sys

from _common import ICON_FOREGROUND, ICON_BACKGROUND


def replace_icons(renpy_path: str, fg_path: str, bg_path: str) -> dict:
    """Replace icon templates in Ren'Py SDK, backing up originals as .bak.

    Returns a dict with ok/error key and optional details.
    """
    templates = os.path.join(renpy_path, "rapt", "templates")
    if not os.path.isdir(templates):
        return {"error": f"Templates directory not found: {templates}"}

    if not os.path.isfile(fg_path):
        return {"error": f"Foreground icon not found: {fg_path}"}
    if not os.path.isfile(bg_path):
        return {"error": f"Background icon not found: {bg_path}"}

    fg_target = os.path.join(templates, ICON_FOREGROUND)
    bg_target = os.path.join(templates, ICON_BACKGROUND)

    details = []

    # Backup and replace foreground. The backup is written only once: if an
    # earlier run was interrupted before restoring, the existing .bak still
    # holds the SDK's original template and must not be overwritten.
    if os.path.isfile(fg_target) and not os.path.isfile(fg_target + ".bak"):
        shutil.copy2(fg_target, fg_target + ".bak")
        details.append("backed up foreground")
    shutil.copy2(fg_path, fg_target)
    details.append("replaced foreground")

    # Backup and replace background (same rule as the foreground).
    if os.path.isfile(bg_target) and not os.path.isfile(bg_target + ".bak"):
        shutil.copy2(bg_target, bg_target + ".bak")
        details.append("backed up background")
    shutil.copy2(bg_path, bg_target)
    details.append("replaced background")

    return {"ok": True, "details": ", ".join(details)}


def main():
    if len(sys.argv) < 4:
        print(json.dumps({
            "error": (
                "Usage: icon_replace.py <renpy_sdk_path> "
                "<foreground_png> <background_png>"
            )
        }))
        sys.exit(1)

    renpy = sys.argv[1]
    fg = sys.argv[2]
    bg = sys.argv[3]
    result = replace_icons(renpy, fg, bg)

    if "error" in result:
        print(json.dumps(result))
        sys.exit(1)
    print(json.dumps(result))


if __name__ == "__main__":
    main()
