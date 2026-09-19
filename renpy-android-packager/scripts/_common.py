"""
Shared utilities for Ren'Py Android Packager scripts.
"""

import locale
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

# Absolute path to the scripts directory
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Icon template filenames (used in pack.py and icon_replace.py)
ICON_FOREGROUND = "android-icon_foreground.png"
ICON_BACKGROUND = "android-icon_background.png"


def read_text_best_effort(path: str) -> str:
    """Read a text file as UTF-8, falling back to the system encoding.

    Files this project writes (config.json, android.json) are always UTF-8,
    while logs written by Ren'Py follow the process locale on Windows. This
    returns readable text for both instead of raising UnicodeDecodeError.
    """
    raw = Path(path).read_bytes()
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return raw.decode(locale.getpreferredencoding(False), errors="replace")


def detect_jdk() -> tuple[str, int | None]:
    """Find javac on PATH and return (jdk_root, major_version)."""
    javac = shutil.which("javac")
    if not javac:
        return ("", None)
    try:
        out = subprocess.check_output(
            [javac, "-version"], stderr=subprocess.STDOUT, text=True
        )
        m = re.search(r"\d+", out)
        ver = int(m.group()) if m else None
    except Exception:
        ver = None
    # Derive JDK root: .../jdk-xx/bin/javac → .../jdk-xx
    jdk_root = os.path.dirname(os.path.dirname(os.path.realpath(javac)))
    return (jdk_root, ver)


def find_renpy_launcher(renpy_path: str) -> str:
    """Find the Ren'Py launcher executable (platform-aware)."""
    # On Windows, prefer .exe over .sh (Git Bash may provide .sh but it's not native)
    if sys.platform == "win32":
        candidates = [
            os.path.join(renpy_path, "renpy.exe"),
            os.path.join(renpy_path, "renpy.py"),
            os.path.join(renpy_path, "renpy.sh"),
        ]
    else:
        candidates = [
            os.path.join(renpy_path, "renpy.sh"),    # Linux/macOS
            os.path.join(renpy_path, "renpy.exe"),   # (unlikely but fallback)
            os.path.join(renpy_path, "renpy.py"),    # Python fallback
        ]
    for c in candidates:
        if os.path.isfile(c):
            # On Linux, ensure .sh launcher is executable
            if sys.platform != "win32" and c.endswith(".sh") and not os.access(c, os.X_OK):
                continue
            return c
    return candidates[0]  # return default, will fail with helpful error


def get_config_path() -> str:
    """Return absolute path to config.json (script-relative)."""
    return os.path.join(SCRIPT_DIR, "config.json")


def read_config(config_path: str | None = None) -> dict:
    """Read config.json. Returns {} on any error (missing, corrupt, etc.)."""
    import json
    path = config_path or get_config_path()
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}
