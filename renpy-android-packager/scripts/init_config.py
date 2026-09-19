#!/usr/bin/env python3
"""
Initialize Ren'Py Android packager config.

Usage (CLI mode):     init_config.py --renpy <sdk_path> --version-label <label>
Usage (interactive):  init_config.py  (no args → prompts user)

Output: config.json next to this script (scripts/config.json).

Works on Linux, macOS, and Windows.
"""

import argparse
import json
import os
import platform
import re
import sys
from pathlib import Path

from _common import detect_jdk, get_config_path, read_config


# ── Helpers ──

def detect_os() -> str:
    """Detect operating system."""
    s = platform.system().lower()
    if s == "linux":
        return "linux"
    if s == "darwin":
        return "mac"
    if s == "windows":
        return "windows"
    return s


def extract_version(sdk_path: str) -> str | None:
    """
    Extract Ren'Py version from SDK path using multiple strategies:

    1. Folder name (e.g. "renpy-8.5.3-sdk")
    2. Full path string
    3. renpy/vc_version.py  (version = 'X.Y.Z.....')
    4. doc/index.html  (<...>X.Y.Z Documentation</...>)
    5. doc/changelog.html
    """
    path = Path(sdk_path)

    # 1) Folder name
    ver = _re_in_name(path.name)
    if ver:
        return ver

    # 2) Full path string
    ver = _re_in_name(str(path))
    if ver:
        return ver

    # 3) renpy/vc_version.py
    vc_file = path / "renpy" / "vc_version.py"
    if vc_file.is_file():
        try:
            text = vc_file.read_text(encoding="utf-8")
            m = re.search(r"""^version\s*=\s*['"](\d+\.\d+\.\d+)""", text, re.MULTILINE)
            if m:
                return m.group(1)
        except Exception:
            pass

    # 4) doc/index.html
    ver = _extract_from_html(path / "doc" / "index.html")
    if ver:
        return ver

    # 5) doc/changelog.html
    ver = _extract_from_html(path / "doc" / "changelog.html")
    if ver:
        return ver

    return None


def _re_in_name(text: str) -> str | None:
    m = re.search(r"\d+\.\d+\.\d+", text)
    return m.group(0) if m else None


def _extract_from_html(html_path: Path) -> str | None:
    if not html_path.is_file():
        return None
    try:
        text = html_path.read_text(encoding="utf-8", errors="ignore")
        m = re.search(r"(\d+\.\d+\.\d+)\s*Documentation", text)
        return m.group(1) if m else None
    except Exception:
        return None


def write_config(config: dict, filepath: str | None = None) -> dict:
    """Write config to JSON file."""
    path = filepath or get_config_path()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
    return {
        "ok": True,
        "config": config,
        "file": os.path.abspath(path),
    }


# ── CLI mode ──

def run_cli(args: argparse.Namespace) -> dict:
    """Handle --renpy CLI mode, merging with any existing config."""
    renpy = args.renpy
    label = args.version_label

    if not label and renpy:
        label = extract_version(renpy) or "default"

    os_name = detect_os()
    jdk_path, jdk_ver = detect_jdk()

    # Read existing config and merge
    existing = read_config()
    if existing:
        config = existing
        config["os"] = os_name
        config["renpy_versions"] = config.get("renpy_versions", {})
        config["renpy_versions"][label] = renpy
        config["default_renpy_version"] = label
        config["jdk_path"] = jdk_path
        config["jdk_version"] = jdk_ver
    else:
        config = {
            "os": os_name,
            "renpy_versions": {label: renpy} if renpy and label else {},
            "default_renpy_version": label,
            "jdk_path": jdk_path,
            "jdk_version": jdk_ver,
        }

    result = write_config(config)
    print(json.dumps(result))
    return result


# ── Interactive mode ──

def run_interactive() -> dict:
    """Interactive prompts for first-time setup."""
    print("=" * 42)
    print(" Ren'Py Android Packager — 首次初始化")
    print("=" * 42)
    print()

    os_name = detect_os()
    jdk_path, jdk_ver = detect_jdk()

    # auto-detection summary
    print(f"  检测到操作系统: {os_name}")
    if jdk_path:
        print(f"  检测到 JDK:     {jdk_path} (版本 {jdk_ver})")
    else:
        print("  ⚠  未检测到 JDK，请确保 JDK ≥ 21 已安装")
    print()

    # How many SDKs
    while True:
        sdk_count = input("有几个 Ren'Py SDK 版本需要配置？(1-9): ").strip() or "1"
        if sdk_count.isdigit() and 1 <= int(sdk_count) <= 9:
            sdk_count = int(sdk_count)
            break
        print("请输入 1-9 之间的数字。")

    versions: dict[str, str] = {}

    for i in range(1, sdk_count + 1):
        print()
        print(f"--- 第 {i} 个 SDK ---")

        # Ask for path
        while True:
            sdk_path = input("Ren'Py SDK 路径: ").strip().strip('"').strip("'")
            if os.path.isdir(sdk_path):
                break
            print("路径不存在，请重新输入。")

        # Auto-detect version
        ver = extract_version(sdk_path)
        if ver:
            print(f"  检测到版本号: {ver}")
        else:
            ver = input("未能从路径中识别版本号，请输入 (例如 8.5.3): ").strip() or "default"

        versions[ver] = sdk_path
        print(f"  → {ver}  →  {sdk_path}")

    # Pick default
    print()
    default_label: str = ""
    if len(versions) > 1:
        ver_list = list(versions.keys())
        print("可用版本:")
        for idx, v in enumerate(ver_list, 1):
            print(f"  {idx}) {v}  ({versions[v]})")
        while True:
            choice = input("默认使用哪个版本？(输入编号或版本名): ").strip()
            # try number match
            if choice.isdigit():
                n = int(choice)
                if 1 <= n <= len(ver_list):
                    default_label = ver_list[n - 1]
                    break
            # try name match
            if choice in versions:
                default_label = choice
                break
            print("无效选择，请重试。")
    else:
        default_label = next(iter(versions.keys()))

    config = {
        "os": os_name,
        "renpy_versions": versions,
        "default_renpy_version": default_label,
        "jdk_path": jdk_path,
        "jdk_version": jdk_ver,
    }

    result = write_config(config)
    print()
    print(f"✅ 配置已写入: {result['file']}")
    print(f"   包含 {len(versions)} 个 Ren'Py SDK 版本")
    print(f"   默认版本: {default_label}")
    return result


# ── Entry point ──

def main():
    parser = argparse.ArgumentParser(
        description="Initialize Ren'Py Android packager config",
    )
    parser.add_argument("--renpy", help="Path to Ren'Py SDK")
    parser.add_argument(
        "--version-label",
        help="Version label for the SDK (auto-detected from path if omitted)",
    )
    args = parser.parse_args()

    if args.renpy:
        if not os.path.isdir(args.renpy):
            result = {"error": f"Ren'Py SDK path not found: {args.renpy}"}
            print(json.dumps(result))
            sys.exit(1)
        run_cli(args)
    else:
        run_interactive()


if __name__ == "__main__":
    main()
