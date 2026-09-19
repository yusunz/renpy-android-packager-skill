#!/usr/bin/env python3
"""
Generate Ren'Py Android keystore files.

Usage:  gen_key.py <game_path> "<organization_name>"

Output: android.keystore and bundle.keystore in game_path.
"""

import json
import os
import shutil
import subprocess
import sys


def generate_keystore(game_path: str, org_name: str) -> dict:
    """Generate android.keystore and bundle.keystore in game_path.

    Returns a dict with keys: ok/error/warning, and optionally file path.
    """
    if not shutil.which("keytool"):
        return {"error": "keytool not found. Please install JDK 21 or later."}

    keystore = os.path.join(game_path, "android.keystore")
    bundle = os.path.join(game_path, "bundle.keystore")
    results = []

    # Generate android.keystore
    if os.path.isfile(keystore):
        results.append({"warning": f"{keystore} already exists, skipping."})
    else:
        result = subprocess.run([
            "keytool", "-genkey",
            "-keystore", keystore,
            "-alias", "android",
            "-keyalg", "RSA",
            "-keysize", "2048",
            "-keypass", "android",
            "-storepass", "android",
            "-dname", f"CN={org_name}",
            "-validity", "20000",
        ], capture_output=True, text=True)
        if result.returncode != 0:
            return {"error": result.stderr.strip()}
        results.append({"ok": True, "file": keystore})

    # Copy to bundle.keystore
    if os.path.isfile(bundle):
        results.append({"warning": f"{bundle} already exists, skipping."})
    else:
        if not os.path.isfile(keystore):
            return {"error": f"{keystore} was not created, cannot copy."}
        shutil.copy2(keystore, bundle)
        results.append({"ok": True, "file": bundle})

    return {"ok": True, "android": results[0] if results else None, "bundle": results[-1] if results else None}


def main():
    if len(sys.argv) < 3:
        print(json.dumps({
            "error": "Usage: gen_key.py <game_path> <organization_name>"
        }))
        sys.exit(1)

    game_path = sys.argv[1]
    org_name = sys.argv[2]
    result = generate_keystore(game_path, org_name)

    if "error" in result:
        print(json.dumps(result))
        sys.exit(1)
    print(json.dumps(result))


if __name__ == "__main__":
    main()
