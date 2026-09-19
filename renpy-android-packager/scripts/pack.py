#!/usr/bin/env python3
"""
Main Ren'Py Android packager.

Usage:  pack.py <game_path> <renpy_sdk_path> [options]

Options:
  --org-name <name>       Organization name for keystore (default: "A Ren'Py Creator")
  --fg-icon <file>        Foreground icon PNG (432x432, transparent)
  --bg-icon <file>        Background icon PNG (432x432, opaque)
  --skip-key              Skip keystore check, don't generate

Output: JSON with build result.
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from _common import (
    ICON_FOREGROUND,
    ICON_BACKGROUND,
    find_renpy_launcher,
    read_text_best_effort,
)
from gen_key import generate_keystore
from gen_android_json import generate_android_json
from icon_replace import replace_icons


def restore_icon_backups(renpy_path: str) -> list[str]:
    """Restore original icon templates from .bak files after build."""
    restored = []
    templates = os.path.join(renpy_path, "rapt", "templates")
    for name in (ICON_FOREGROUND, ICON_BACKGROUND):
        original = os.path.join(templates, name)
        backup = original + ".bak"
        if os.path.isfile(backup):
            shutil.move(backup, original)
            restored.append(name)
    return restored


def get_file_size(path: str) -> str:
    """Get human-readable file size."""
    size = os.path.getsize(path)
    for unit in ("B", "K", "M", "G"):
        if size < 1024:
            return f"{size:.0f}{unit}"
        size /= 1024
    return f"{size:.1f}T"


def main():
    parser = argparse.ArgumentParser(
        description="Build Ren'Py Android APK"
    )
    parser.add_argument("game_path", help="Path to Ren'Py game directory")
    parser.add_argument("renpy_sdk", help="Path to Ren'Py SDK")
    parser.add_argument(
        "--org-name", default="A Ren'Py Creator",
        help="Organization name for keystore"
    )
    parser.add_argument("--fg-icon", help="Foreground icon PNG (432x432)")
    parser.add_argument("--bg-icon", help="Background icon PNG (432x432)")
    parser.add_argument(
        "--skip-key", action="store_true",
        help="Skip keystore generation"
    )
    args = parser.parse_args()

    if bool(args.fg_icon) != bool(args.bg_icon):
        result = {
            "error": "--fg-icon and --bg-icon must be provided together.",
        }
        print(json.dumps(result))
        sys.exit(1)

    game_path = os.path.abspath(args.game_path)
    renpy_path = os.path.abspath(args.renpy_sdk)

    # Validate inputs
    if not os.path.isdir(os.path.join(game_path, "game")):
        result = {
            "error": f"No 'game/' subdirectory found in {game_path}. "
                     "Is this a Ren'Py project?"
        }
        print(json.dumps(result))
        sys.exit(1)

    launcher = find_renpy_launcher(renpy_path)
    if not os.path.isfile(launcher):
        result = {
            "error": f"Ren'Py launcher not found in {renpy_path}. "
                     "Is this a Ren'Py SDK?"
        }
        print(json.dumps(result))
        sys.exit(1)

    details = {}

    # --- Step 1: Keystores ---
    keystore = os.path.join(game_path, "android.keystore")
    bundle = os.path.join(game_path, "bundle.keystore")

    if args.skip_key:
        details["keys"] = "skipped"
    elif os.path.isfile(keystore) and os.path.isfile(bundle):
        details["keys"] = "already_exist"
    else:
        details["keys"] = generate_keystore(game_path, args.org_name)

    # --- Step 2: android.json ---
    android_json = os.path.join(game_path, "android.json")
    if not os.path.isfile(android_json):
        dirname = os.path.basename(game_path)
        defaults = {
            "name": dirname,
            "icon_name": dirname,
            "package": "unknown.app",
            "heap_size": "3",
            "orientation": "sensorLandscape",
            "update_always": True,
            "store": "none",
        }
        generate_android_json(game_path, defaults)
        details["android_json"] = "generated"
    else:
        details["android_json"] = "already_exists"

    # --- Step 3: Icons ---
    icons_replaced = bool(args.fg_icon and args.bg_icon)

    try:
        if icons_replaced:
            details["icons"] = replace_icons(renpy_path, args.fg_icon, args.bg_icon)
        else:
            details["icons"] = "skipped"

        # --- Step 4: Build ---
        dists = f"{game_path}-dists"
        os.makedirs(dists, exist_ok=True)

        print(json.dumps({
            "status": "building",
            "game": game_path,
            "dists": dists,
        }), file=sys.stderr)

        # Determine how to invoke Ren'Py
        if launcher.endswith(".py"):
            build_cmd = [sys.executable, launcher]
        else:
            build_cmd = [launcher]

        build_cmd += [
            os.path.join(renpy_path, "launcher"),
            "android_build",
            game_path,
            "--destination", dists,
        ]

        # On Windows, renpy.exe is a GUI-subsystem executable; subprocess cannot
        # capture output from it via pipes (no console handles). Redirect to a
        # temporary file and read it back for error reporting.
        if sys.platform == "win32" and launcher.endswith(".exe"):
            log_file = os.path.join(tempfile.gettempdir(), "renpy_build.log")
            with open(log_file, "w", encoding="utf-8") as f:
                build_result = subprocess.run(build_cmd, stdout=f, stderr=subprocess.STDOUT)
            try:
                build_out = read_text_best_effort(log_file)
            except Exception:
                build_out = ""
            build_exit = build_result.returncode
        else:
            build_result = subprocess.run(
                build_cmd, capture_output=True, text=True
            )
            build_out = build_result.stdout + build_result.stderr
            build_exit = build_result.returncode

    finally:
        # --- Restore original icons from .bak (always, even if build threw) ---
        if icons_replaced:
            restored = restore_icon_backups(renpy_path)
            if restored:
                details["icons_restored"] = restored

    # --- Step 5: Find APK ---
    apk = ""
    rapt_bin = os.path.join(renpy_path, "rapt", "bin")
    if os.path.isdir(rapt_bin):
        apk_files = sorted(Path(rapt_bin).glob("*.apk"), key=lambda p: p.stat().st_mtime, reverse=True)
        if apk_files:
            apk = str(apk_files[0])

    if build_exit == 0 and apk:
        apk_size = get_file_size(apk)
        shutil.copy2(apk, dists)
        result = {
            "ok": True,
            "apk": apk,
            "size": apk_size,
            "dists": dists,
            "details": details,
        }
        print(json.dumps(result))
    else:
        # Last 20 lines of output
        lines = build_out.strip().splitlines()
        err_tail = " ".join(lines[-20:])
        result = {
            "error": f"Build failed (exit={build_exit})",
            "tail": err_tail,
        }
        print(json.dumps(result))
        sys.exit(1)


if __name__ == "__main__":
    main()
