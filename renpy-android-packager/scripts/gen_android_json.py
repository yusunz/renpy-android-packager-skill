#!/usr/bin/env python3
"""
Generate Ren'Py android.json configuration file.

Usage:  gen_android_json.py <game_path> '<json_args>'

json_args example:
  '{"name":"MyGame","icon_name":"MG","package":"com.example.game","heap_size":"3","orientation":"sensorLandscape","update_always":true,"store":"none"}'
"""

import json
import os
import sys


def generate_android_json(game_path: str, json_input: str | dict) -> dict:
    """Generate android.json from a JSON string or dict. Returns result dict."""
    if isinstance(json_input, dict):
        data = json_input
    else:
        try:
            data = json.loads(json_input)
        except json.JSONDecodeError as e:
            return {"error": f"Invalid JSON: {e}"}

    defaults = {
        "expansion": False,
        "google_play_key": None,
        "google_play_salt": None,
        "include_pil": False,
        "include_sqlite": False,
        "layout": None,
        "numeric_version": 1,
        "permissions": ["VIBRATE", "INTERNET"],
        "source": False,
        "update_icons": True,
        "update_keystores": True,
    }
    defaults.update(data)

    output_file = os.path.join(game_path, "android.json")
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(defaults, f, indent=4, sort_keys=True)

    return {"ok": True, "file": output_file}


def main():
    if len(sys.argv) < 3:
        print(json.dumps({
            "error": "Usage: gen_android_json.py <game_path> '<json_args>'"
        }))
        print(json.dumps({
            "note": "Or: gen_android_json.py <game_path> --file <path> (read JSON from file)"
        }))
        sys.exit(1)

    game_path = sys.argv[1]

    if len(sys.argv) >= 4 and sys.argv[2] == "--file":
        # Read JSON from file (avoids encoding issues with inline args on Windows)
        try:
            with open(sys.argv[3], encoding="utf-8") as f:
                json_input = f.read()
        except Exception as e:
            print(json.dumps({"error": f"Failed to read file: {e}"}))
            sys.exit(1)
    else:
        json_input = sys.argv[2]

    result = generate_android_json(game_path, json_input)

    if "error" in result:
        print(json.dumps(result))
        sys.exit(1)
    print(json.dumps(result))


if __name__ == "__main__":
    main()
