#!/usr/bin/env python3
"""
Check Ren'Py Android build environment.

Usage:  check_env.py [--renpy <path>] [--config <config.json>]

Checks: JDK version (≥21), Android SDK, Ren'Py SDK existence.
Output: JSON with status per check.
"""

import argparse
import json
import os
import re
import subprocess
import sys

from _common import (
    detect_jdk,
    find_renpy_launcher,
    get_config_path,
    read_config,
    read_text_best_effort,
)


def check_android_sdk(renpy_path: str) -> tuple[bool, str]:
    """Check if Android SDK is available under Ren'Py rapt directory."""
    sdk_path = os.path.join(renpy_path, "rapt", "Sdk")
    # On Windows, sdkmanager is a .bat file, on Linux/macOS it has no extension
    sdkmanager_names = ["sdkmanager", "sdkmanager.bat"]
    bin_dir = os.path.join(sdk_path, "cmdline-tools", "latest", "bin")
    if os.path.isdir(sdk_path):
        for name in sdkmanager_names:
            if os.path.isfile(os.path.join(bin_dir, name)):
                return True, sdk_path

    # Try sdk.txt reference
    sdk_txt = os.path.join(renpy_path, "rapt", "sdk.txt")
    if os.path.isfile(sdk_txt):
        try:
            sdk_dir = read_text_best_effort(sdk_txt).strip()
            if os.path.isdir(sdk_dir):
                return True, sdk_dir
        except Exception:
            pass

    return False, ""


def main():
    parser = argparse.ArgumentParser(
        description="Check Ren'Py Android build environment"
    )
    parser.add_argument("--renpy", help="Path to Ren'Py SDK")
    parser.add_argument(
        "--config", default=None,
        help="Path to config.json (default: scripts/config.json, fallback ./config.json)"
    )
    args = parser.parse_args()

    renpy_path = args.renpy or ""

    # Determine config path: try explicit, then script-relative, then CWD fallback
    config_path = args.config
    if not config_path:
        config_path = get_config_path()
        if not os.path.isfile(config_path):
            cwd_config = os.path.join(os.getcwd(), "config.json")
            if os.path.isfile(cwd_config):
                config_path = cwd_config

    config = read_config(config_path)
    if not renpy_path and config.get("renpy_versions"):
        versions = config["renpy_versions"]
        default = config.get("default_renpy_version")
        if default and default in versions:
            renpy_path = versions[default]
        else:
            renpy_path = next(iter(versions.values()))
    jdk_path_from_config = config.get("jdk_path", "")

    # JDK check
    if jdk_path_from_config:
        if os.path.isfile(jdk_path_from_config):
            # Old config: stored javac.exe path directly
            javac = jdk_path_from_config
            jdk_path = os.path.dirname(os.path.dirname(os.path.realpath(javac)))
        elif os.path.isdir(jdk_path_from_config):
            # New config: stored JDK root directory
            jdk_path = jdk_path_from_config
            javac = os.path.join(
                jdk_path, "bin", "javac" + (".exe" if sys.platform == "win32" else "")
            )
        else:
            javac = ""
        if javac and os.path.isfile(javac):
            try:
                out = subprocess.check_output(
                    [javac, "-version"], stderr=subprocess.STDOUT, text=True
                )
                m = re.search(r"\d+", out)
                jdk_ver = int(m.group()) if m else None
            except Exception:
                jdk_ver = None
        else:
            jdk_ver = None
    else:
        jdk_path, jdk_ver = detect_jdk()

    jdk_ok = jdk_ver is not None and jdk_ver >= 21

    # Ren'Py SDK check (use find_renpy_launcher from _common)
    renpy_ok = False
    renpy_script = ""
    if renpy_path:
        script = find_renpy_launcher(renpy_path)
        if os.path.isfile(script):
            renpy_ok = True
            renpy_script = script

    # Android SDK check
    sdk_ok = False
    sdk_dir = ""
    if renpy_ok:
        sdk_ok, sdk_dir = check_android_sdk(renpy_path)

    result = {
        "jdk_ok": jdk_ok,
        "jdk_version": str(jdk_ver) if jdk_ver else "",
        "jdk_path": jdk_path,
        "renpy_ok": renpy_ok,
        "renpy_path": renpy_path,
        "renpy_script": renpy_script,
        "sdk_ok": sdk_ok,
        "sdk_path": sdk_dir,
        "all_ok": jdk_ok and renpy_ok and sdk_ok,
    }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
