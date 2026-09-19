---
name: renpy-android-packager
description: Automates Ren'Py Android APK building from CLI. Triggers when user mentions Ren'Py packaging, android build, APK export, exporting Ren'Py games to mobile, or "renpy 打包". Persists paths and SDK versions as JSON config for reuse.
---

# Ren'Py Android Packager

Build Ren'Py visual novels into Android APKs via CLI scripts. All scripts accept arguments and print a JSON result on stdout, with progress on stderr — no Ren'Py GUI needed.

## When to trigger

Use whenever the user wants to:
- Build a Ren'Py game for Android
- Package/export a Ren'Py project as APK
- Set up Ren'Py Android build environment
- Manage Ren'Py SDK versions for building

## First-run: Initialize config

### Interactive mode (recommended for first-time users)

Run with no arguments — it will ask you everything:

```bash
python3 scripts/init_config.py
```

When guiding the user: "Enter the Ren'Py SDK path (you can configure multiple versions — you'll be asked how many at the start)."

It will:
1. Ask **how many Ren'Py SDK versions** you want to configure
2. For each: ask for the **SDK path**, then auto-detect the version number (from folder name → full path → `renpy/vc_version.py` → `doc/index.html` → `doc/changelog.html`)
3. If version cannot be detected, prompt you to type it manually
4. If multiple versions: ask which one to use as **default**
5. Auto-detect OS and JDK version (no manual input needed)
6. Write `config.json` to `scripts/config.json` (script-relative path)

### CLI mode (for automation)

```bash
scripts/init_config.py --renpy <path-to-renpy-sdk> --version-label "<version-label>"
```

Pass `--renpy` to skip all interactive prompts. Add more versions later by running again with a new `--renpy --version-label` pair.

## Pre-build: Check environment

```bash
scripts/check_env.py --renpy <path-to-renpy-sdk>
```

Returns JSON with `all_ok`, `jdk_ok`, `renpy_ok`, `sdk_ok` booleans. Fix any failing checks before building.

## Per-build workflow

### Step 1: Ask user for SDK version
If config.json has multiple `renpy_versions`, ask which version to use. Map their choice to the SDK path.

### Step 2: Ask for game path
Verify `<game_path>/game/` exists.

### Step 3: Handle keystores (confirmation)
Check if `<game>/android.keystore` and `<game>/bundle.keystore` exist.

**If missing:** ask confirmation:
> "Keystores are missing. Will auto-generate with `--org-name "My Studio"`. Change the org name? (y/N)"

If **y**: further ask:
  - **a) Auto-generate**: prompt for org name, then pass `--org-name "<name>"` to pack.py
  - **b) Provide existing**: ask for path to existing `android.keystore`, copy it (and `bundle.keystore` if also provided) into `<game>/`, then call `pack.py --skip-key`
If **N** or enter: proceed with the default (`--org-name "A Ren'Py Creator"`).

### Step 4: Handle android.json (confirmation)
If `<game>/android.json` is missing, ask confirmation:
> "android.json is missing. Will use defaults (package: unknown.app, orientation: sensorLandscape, heap_size: 3 GB). Customize? (y/N)"

If **y**: ask for fields one by one with descriptions:
  - **name**: App display name — any string, e.g. `"My Game"`
  - **icon_name**: Short label for the icon — any string, e.g. `"MG"`
  - **package**: Android package ID — must contain a dot, lowercase only, e.g. `"com.studio.gamename"`
  - **heap_size**: Heap size in GB — integer, typically 2-4, e.g. `"3"`
  - **orientation**: Screen orientation — one of: `"sensorLandscape"` (landscape, auto-rotate), `"portrait"`, or `"sensor"` (both)
  - **update_always**: Rebuild project every time — `true` or `false`
  - **store**: Target store — one of: `"none"`, `"google"`, `"amazon"`, `"all"`
Then write the JSON directly to `<game>/android.json` (use `bash` to write — `write_file` may be restricted by the sandbox). pack.py will see the file exists and skip auto-generation.
If **N** or enter: proceed, pack.py will generate defaults.

### Step 5: Ask about icons
"Need to change the app icon?" If yes, get foreground PNG (432×432 transparent) + background PNG (432×432 opaque).

### Step 6: Run the pack script

```bash
python3 scripts/pack.py "/path/to/game" "/path/to/renpy-sdk" \
  --org-name "My Studio" \
  --fg-icon "/path/to/fg.png" \
  --bg-icon "/path/to/bg.png"
```

Use `--skip-key` if keystores already exist. Use `--fg-icon`/`--bg-icon` only if user provided icons — they must be passed together, a single one is rejected.

After the build finishes (success or failure), `pack.py` automatically restores the original icon templates from their `.bak` backups, so the SDK is left clean.

Output: `{"ok": true, "apk": "...", "size": "580M", "dists": "..."}` on success, or `{"error": "..."}` on failure.

## Cross-platform notes

- **Python command**: Examples use `python3` (Linux/macOS). On Windows or systems where `python3` is unavailable, use `python` instead. The agent will adapt automatically.

## Windows notes

- **Chinese characters in JSON args**: Passing Chinese JSON strings as cmdline arguments in PowerShell may cause encoding issues. Use the `--file` option instead:
  ```bash
  python3 scripts/gen_android_json.py /path/to/game --file /path/to/input.json
  ```
  Write the JSON to a file with utf-8 encoding first, then pass the file path.
- **sdkmanager.bat**: The Android SDK's `sdkmanager` is `sdkmanager.bat` on Windows. This is handled automatically by `check_env.py`.
- **renpy.exe GUI subsystem**: On Windows, `renpy.exe` is a GUI application. `pack.py` redirects build output to a temporary file and reads it back for error reporting.

## Error handling — CRITICAL

- If `pack.py` returns an error with `"tail"` field: read the error tail. If it mentions game script errors (`.rpy`, `.py` files), **DO NOT read or modify any game files**. Report the error to user and ask if they want help.
- If the error is environment-related (JDK, SDK, Gradle): suggest fixes.
- **Never** read files inside `<game>/game/` without explicit user permission.

## Script reference

| Script | Purpose | Input |
|--------|---------|-------|
| `init_config.py` | Auto-detect env, create config.json | `--renpy --version-label` |
| `check_env.py` | Validate JDK/AndroidSDK/Ren'Py | `--renpy` |
| `pack.py` | Full build pipeline (all steps) | `<game> <renpy>` + flags |
| `gen_key.py` | Generate android.keystore keys | `<game> <org_name>` |
| `gen_android_json.py` | Create android.json from JSON | `<game> <json>` |
| `icon_replace.py` | Replace icon templates | `<renpy> <fg> <bg>` |
