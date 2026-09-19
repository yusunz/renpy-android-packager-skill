# Ren'Py Android Packager

把 Ren'Py 视觉小说项目打包成 Android APK 的技能，本体是一组命令行脚本：不依赖 Ren'Py Launcher 的图形界面，全流程可脚本化，脚本结果以 JSON 输出（`pack.py` 的构建进度写 stderr，stdout 只输出结果）。

## 特性

- **纯 CLI 打包**：一条命令跑通 keystore → android.json → 图标 → 构建 → 取产物
- **JSON 输出**：stdout 只有结果 JSON（构建进度走 stderr），可直接被其他程序解析
- **多版本 SDK 管理**：`config.json` 记录「版本号 → 路径」映射，随时切换默认版本
- **环境自检**：一次性检查 JDK（≥ 21）、Ren'Py SDK、Android SDK
- **按需补齐配置**：缺失的 keystore、`android.json` 自动生成，已存在的文件不会被覆盖
- **可换图标**：临时替换 SDK 图标模板，构建结束（包括失败）后自动还原
- **跨平台**：Windows / Linux / macOS

## 目录结构

```
renpy-android-packager-skill/
├─ README.md
├─ .gitignore                      # 忽略本机运行时产物（config.json、__pycache__ 等）
└─ renpy-android-packager/          # 技能本体，安装时复制这一层
   ├─ SKILL.md                      # 技能说明：触发条件、交互流程、脚本参考
   └─ scripts/
      ├─ _common.py                 # 公共函数：JDK 检测、launcher 定位、config 读写
      ├─ init_config.py             # 初始化 / 更新 config.json
      ├─ check_env.py               # 环境自检
      ├─ pack.py                    # 完整打包流程
      ├─ gen_key.py                 # 生成签名用 keystore
      ├─ gen_android_json.py        # 生成 android.json
      └─ icon_replace.py            # 替换 / 备份图标模板
```

## 环境要求

| 依赖 | 要求 | 说明 |
| --- | --- | --- |
| Python | 3.10 或更高 | Windows 上命令用 `python`，Linux/macOS 用 `python3` |
| JDK | 21 或更高 | 需要 `javac`、`keytool` 在 PATH 中（Ren'Py 8.5 的构建设施要求 JDK 21） |
| Ren'Py SDK | 8.x，且带 `rapt` | 需要已安装 Android SDK（见下） |

Android SDK 由 Ren'Py 自己管理，位置是 `<renpy-sdk>/rapt/Sdk`。如果这个目录还不存在，先装一次：打开 Ren'Py Launcher → 选中项目 → 进入 Android 界面 → 点 **Install SDK**，等下载安装完成。`check_env.py` 的 `sdk_ok` 检查的就是这个目录。

## 安装

技能就是 `renpy-android-packager/` 这一层目录：把它整层复制到你所用智能体的技能目录，使 `<技能目录>/renpy-android-packager/SKILL.md` 存在即可，`SKILL.md` 与 `scripts/` 不要拆开。

> 给智能体：要安装的是本仓库的 `renpy-android-packager/` 子目录，不是仓库根目录；技能目录取决于你所在的平台。

各平台的技能目录（其他平台以各自文档为准）：

| 平台 / 环境 | Windows | Linux / macOS |
| --- | --- | --- |
| Codex | `%USERPROFILE%\.codex\skills\` | `~/.codex/skills/` |
| Claude Code | `%USERPROFILE%\.claude\skills\` | `~/.claude/skills/` |
| 部分 agent 环境 | `%USERPROFILE%\.agents\skills\` | `~/.agents/skills/` |

### 方式一：作为智能体技能安装（推荐）

先把仓库克隆到任意位置（GitHub 页面 Code 按钮里就是地址，也可以直接 Download ZIP 解压），然后在仓库目录里把技能复制到上表对应的目录：

```powershell
# Windows PowerShell：<技能目录> 换成上表里对应平台的目标路径
Copy-Item .\renpy-android-packager "<技能目录>\" -Recurse -Force
```

```bash
# Linux / macOS
cp -r ./renpy-android-packager <技能目录>/
```

- 升级时重复执行同一条命令，同名文件会被覆盖。
- 安装完成后新开一个会话即可生效，之后用自然语言描述需求就会触发技能，例如「帮我把 `E:\games\MyGame` 打包成安卓 APK」或「renpy 打包」。

验证安装（`<技能目录>` 同样按上表替换；`all_ok` 为 `true` 说明环境齐备）：

```powershell
# Windows PowerShell
python "<技能目录>\renpy-android-packager\scripts\check_env.py" --renpy "<renpy-sdk>"
```

```bash
# Linux / macOS
python3 <技能目录>/renpy-android-packager/scripts/check_env.py --renpy "<renpy-sdk>"
```

### 方式二：不安装，直接当命令行脚本用

克隆或下载仓库后，按「使用」一节的命令直接调用 `renpy-android-packager/scripts/` 里的脚本即可，不需要复制到技能目录。

## 使用

### 三步走：初始化 → 自检 → 打包

下面命令以仓库根目录为基准；技能装好后脚本位于 `<技能目录>/renpy-android-packager/scripts/`，由智能体调用时无需你手动执行。

#### 第 1 步：初始化配置（`init_config.py`）

交互模式，首次使用推荐：

```bash
python3 renpy-android-packager/scripts/init_config.py     # Windows 用 python
```

脚本会依次询问：要配置几个 Ren'Py SDK 版本 → 每个版本的 SDK 路径（自动从目录名、`renpy/vc_version.py`、`doc/index.html` 等位置识别版本号）→ 多版本时选默认版本；JDK 和操作系统自动检测。结果写入 `scripts/config.json`：

```json
{
  "os": "windows",
  "renpy_versions": {
    "8.5.3": "<renpy-sdk-path>"
  },
  "default_renpy_version": "8.5.3",
  "jdk_path": "<jdk-root>",
  "jdk_version": 21
}
```

CLI 模式（自动化调用，或追加新版本）：

```bash
python3 renpy-android-packager/scripts/init_config.py \
  --renpy "<renpy-sdk>" --version-label "8.5.3"
```

再次运行会与已有 `config.json` 合并，并把新加入的版本设为默认版本。

#### 第 2 步：检查环境（`check_env.py`）

```bash
# 显式指定 SDK
python3 renpy-android-packager/scripts/check_env.py --renpy "<renpy-sdk>"

# 已初始化 config.json 时可省略，默认使用 default_renpy_version
python3 renpy-android-packager/scripts/check_env.py
```

输出示例（路径已省略）：

```json
{
  "jdk_ok": true,
  "jdk_version": "21",
  "jdk_path": "<jdk-root>",
  "renpy_ok": true,
  "renpy_path": "<renpy-sdk>",
  "renpy_script": "<renpy-sdk>/renpy.exe",
  "sdk_ok": true,
  "sdk_path": "<renpy-sdk>/rapt/Sdk",
  "all_ok": true
}
```

`all_ok` 为 `true` 才能顺利打包；有的项是 `false` 时对照「常见问题」处理。

#### 第 3 步：打包（`pack.py`）

```bash
python3 renpy-android-packager/scripts/pack.py "<game-path>" "<renpy-sdk>" \
  --org-name "My Studio" \
  --fg-icon "E:\icons\fg.png" \
  --bg-icon "E:\icons\bg.png"
```

参数：

| 参数 | 必填 | 说明 |
| --- | --- | --- |
| `game_path` | 是 | Ren'Py 游戏目录，内部必须存在 `game/` 子目录 |
| `renpy_sdk` | 是 | Ren'Py SDK 路径 |
| `--org-name` | 否 | 生成 keystore 时写入的组织名（`CN`），默认 `A Ren'Py Creator` |
| `--fg-icon` / `--bg-icon` | 否 | 前景图标（432×432、透明）+ 背景图标（432×432、不透明）PNG，必须成对提供，只给其中一个会直接报错 |
| `--skip-key` | 否 | 跳过 keystore 检查与生成（使用自带签名时用） |

`pack.py` 会按顺序自动完成：

1. **keystore**：`<game>/android.keystore`、`<game>/bundle.keystore` 缺失时用 `keytool` 生成（RSA 2048、有效期 20000 天、别名 `android`、口令 `android`）；已存在则跳过。
2. **android.json**：缺失时写入默认配置——`name` / `icon_name` 取游戏目录名，`package` 为 `unknown.app`，`heap_size` 为 `3`，`orientation` 为 `sensorLandscape`，`update_always` 为 `true`，`store` 为 `none`。想自定义就提前准备好 `android.json`（见下一小节）。
3. **图标**：给了 `--fg-icon` / `--bg-icon` 才执行，把图片复制进 `<renpy-sdk>/rapt/templates/`，原模板先备份为 `.bak`。
4. **构建**：调用 Ren'Py 的 `android_build`，临时产物在 `<renpy-sdk>/rapt/bin/`。
5. **收尾**：从 `.bak` 还原图标模板（失败也会还原），把最新的 APK 复制到 `<game-path>-dists`，最后输出 JSON。

构建开始时会在 stderr 输出一行进度 `{"status": "building", ...}`；stdout 只有最后的结果 JSON，可以直接 `json.loads`。

成功时输出：

```json
{
  "ok": true,
  "apk": "<renpy-sdk>/rapt/bin/<game>.apk",
  "size": "580M",
  "dists": "<game-path>-dists",
  "details": { "keys": "already_exist", "android_json": "already_exists", "icons": "skipped" }
}
```

`details` 记录每一步的处理方式：`keys` 取值 `skipped`（用了 `--skip-key`）、`already_exist`（两个 keystore 都在）或生成结果对象；`android_json` 取值 `generated` 或 `already_exists`；`icons` 取值 `skipped` 或替换结果；替换过图标时还会多一个 `icons_restored` 字段，列出已还原的模板文件名。

失败时输出（`tail` 是构建日志的最后 20 行）：

```json
{ "error": "Build failed (exit=1)", "tail": "<构建日志尾部>" }
```

最终可安装的 APK 就在 `<game-path>-dists` 目录里（例如游戏目录是 `E:\games\MyGame`，产物目录就是 `E:\games\MyGame-dists`）。

### 自定义 android.json

不想用默认值就提前生成 `android.json`（`pack.py` 见到文件存在会直接跳过生成步骤）：

```bash
# 推荐：JSON 先写成 UTF-8 文件，再通过 --file 传入（Windows 上避免命令行编码问题）
python3 renpy-android-packager/scripts/gen_android_json.py "<game-path>" --file "<json-file>"
```

可配置字段：

| 字段 | 说明 | 取值示例 |
| --- | --- | --- |
| `name` | 应用显示名 | `"My Game"` |
| `icon_name` | 图标下方的短标签 | `"MG"` |
| `package` | 包名，需包含点号、全小写 | `"com.studio.mygame"` |
| `heap_size` | 堆大小，字符串形式的 GB 数 | `"3"`（常用 2–4） |
| `orientation` | 屏幕方向 | `"sensorLandscape"` / `"portrait"` / `"sensor"` |
| `update_always` | 每次是否重建工程 | `true` / `false` |
| `store` | 目标商店 | `"none"` / `"google"` / `"amazon"` / `"all"` |

其余字段（`permissions`、`numeric_version`、`include_pil`、`expansion` 等）会与默认值合并，未写的保持默认。

### 单独调用其他脚本

| 脚本 | 用法 | 作用 |
| --- | --- | --- |
| `init_config.py` | `init_config.py [--renpy <path> --version-label <label>]` | 初始化 / 更新 `config.json` |
| `check_env.py` | `check_env.py [--renpy <path>] [--config <file>]` | 环境自检 |
| `pack.py` | `pack.py <game> <renpy> [--org-name ...] [--fg-icon ... --bg-icon ...] [--skip-key]` | 完整打包 |
| `gen_key.py` | `gen_key.py "<game>" "<org name>"` | 只生成 keystore |
| `gen_android_json.py` | `gen_android_json.py "<game>" --file <json>` | 只生成 `android.json` |
| `icon_replace.py` | `icon_replace.py "<renpy>" <fg.png> <bg.png>` | 只替换图标模板（手动调用后需自行从 `.bak` 还原） |

### 在智能体里使用

技能装好后，直接用自然语言提需求即可（触发词见 `SKILL.md` 的 description：Ren'Py 打包、Android 构建、APK 导出等）。智能体按 `SKILL.md` 的流程执行：询问用哪个 SDK 版本 → 校验游戏目录 → 就 keystore、`android.json`、图标逐项与你确认 → 调用脚本 → 汇报 JSON 结果。也可以只让它做子任务，比如「只检查 Ren'Py 安卓构建环境」或「只给这个游戏生成签名」。

## 常见问题

**`python3` 提示找不到命令？**
Windows 上一般只装了 `python`，把命令里的 `python3` 换成 `python` 即可。Linux/macOS 反过来。

**`jdk_ok` 为 `false`？**
没装 JDK 或版本低于 21。装好 JDK 21+ 后确认 `javac -version` 输出 21 以上，并保证 `<jdk>/bin` 在 PATH 中。

**`sdk_ok` 为 `false`？**
Android SDK 没装到 `<renpy-sdk>/rapt/Sdk`。用 Ren'Py Launcher 打开任意项目 → Android 界面 → **Install SDK**，装完重跑 `check_env.py`。

**`keytool not found. Please install JDK 21 or later.`**
生成 keystore 时找不到 `keytool`，同样是 PATH 里缺少 JDK 的 `bin` 目录。

**Windows 下传中文 JSON 参数解析失败？**
不要把中文 JSON 直接放在命令行参数里，写进 UTF-8 文件后用 `gen_android_json.py "<game>" --file "<file>"`。

**想用自己已有的签名？**
把 `android.keystore` 和 `bundle.keystore` 放进游戏目录，然后给 `pack.py` 加 `--skip-key`。注意默认生成的 keystore 口令是公开的 `android`，只能用于本地调试；要上架商店请重新生成并妥善保管（密钥丢失后无法更新已发布的应用）。

**第一次打包很慢？**
首次构建需要下载 Gradle 与 Android 依赖，属正常现象，之后会明显加快。

**失败的 `tail` 里有 `.rpy` / `.py` 报错？**
那是游戏脚本自身的问题，先修脚本。此技能不会自动读取或修改 `<game>/game/` 里的任何文件。

## 备注

- `scripts/config.json` 记录本机路径，`scripts/__pycache__/` 是 Python 缓存，两者都是本机运行时产物，已在仓库的 `.gitignore` 中忽略，不要提交。
- 脚本只会在目标游戏目录写入 keystore、`android.json`，以及写入 `<game-path>-dists` 输出目录，不会改动游戏内容。
- `pack.py` 使用 `--fg-icon` / `--bg-icon` 时会临时改动 Ren'Py SDK 的图标模板，构建结束后（含失败）自动从 `.bak` 还原；`.bak` 只在首次替换时生成，反复运行不会把它覆盖掉，中途强杀进程的话手动把 `rapt/templates/*.png.bak` 改回来即可。
