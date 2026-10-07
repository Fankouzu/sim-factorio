# 环境准备

## 1. 找到可执行文件（`$BIN`）

| 平台 | 典型路径 |
|---|---|
| **macOS（Steam）** | `~/Library/Application Support/Steam/steamapps/common/Factorio/factorio.app/Contents/MacOS/factorio` |
| macOS（官网版） | `/Applications/factorio.app/Contents/MacOS/factorio` |
| **Windows（Steam）** | `C:\Program Files (x86)\Steam\steamapps\common\Factorio\bin\x64\factorio.exe` |
| **Linux（Steam）** | `~/.steam/steam/steamapps/common/Factorio/bin/x64/factorio` |

> ⚠️ **Windows 必须用 `bin/x64/factorio.exe`**，根目录那个是启动器，不接受命令行参数。

验证：`"$BIN" --version` 应输出 `Version: 2.0.xx`。

## 2. 工作目录布局

**给 AI 一个独立沙箱，永远不要直接写玩家的真实数据目录。**

```
$WORK/
├── config/
│   ├── config.ini              # 指向你自己的 write-data
│   └── server-settings.json    # 服务器设置
├── root/                       # ← write-data，游戏写这里
│   ├── mods/
│   └── script-output/          # helpers.write_file() 的输出目录
└── saves/
    └── w.zip                   # 你的地图
```

各平台**默认（真实）**数据目录，仅供定位，**不建议直接写**：

| 平台 | 默认数据目录 |
|---|---|
| macOS | `~/Library/Application Support/factorio` |
| Windows | `%APPDATA%\Factorio` |
| Linux | `~/.factorio` |

## 3. `config/config.ini`（最小可用）

```ini
; version=13
[path]
read-data=__PATH__system-read-data__
write-data=/tmp/fct/root

[general]
locale=auto
```

- `write-data` **必须绝对路径**，且目录要先存在。
- `read-data=__PATH__system-read-data__` 是占位符，照抄，游戏自己解析成安装目录下的 `data/`。

## 4. `config/server-settings.json`（最小可用）

```json
{
  "name": "AI-Server",
  "description": "agent sandbox",
  "tags": [],
  "max_players": 4,
  "visibility": { "public": false, "lan": true },
  "username": "",
  "password": "",
  "token": "",
  "game_password": "",
  "require_user_verification": false,
  "max_upload_in_kilobytes_per_second": 0,
  "max_upload_slots": 5,
  "minimum_latency_in_ticks": 0,
  "ignore_player_limit_for_returning_players": true,
  "allow_commands": "true",
  "autosave_interval": 30,
  "autosave_slots": 5,
  "afk_autokick_interval": 0,
  "auto_pause": true,
  "only_admins_can_pause_the_game": false,
  "autosave_only_on_server": true,
  "non_blocking_saving": false,
  "minimum_segment_size": 25,
  "minimum_segment_size_peer_count": 20,
  "maximum_segment_size": 100,
  "maximum_segment_size_peer_count": 10
}
```

关键字段：

- **`"allow_commands": "true"`** —— 允许控制台命令。**必须是字符串 `"true"`**，布尔 `true` 不生效。
- **`"auto_pause": true`** —— 无人在线时自动暂停（不空推世界）。
  语义详见 `pitfalls.md` §6。
- **`"visibility": { "public": false, "lan": true }`** —— 只在局域网可见（本机连接够用）。

## 5. Mod 目录

| 做法 | 说明 |
|---|---|
| **纯净**（推荐从零学起） | 指向空目录 → 纯原版游戏，无未知 mod 行为干扰 |
| 复用已有 mod | 把 mod 目录**复制**一份，再 `--mod-directory` 指过去 |
| 默认目录 | 不加 `--mod-directory`，用官方默认 |

> ⚠️ **不要直接指向玩家的真实 mod 目录**：游戏会往里写 `mod-list.json`，污染玩家环境。**先复制。**

## 6. 创建新地图（可选参数）

```bash
"$BIN" --create /tmp/fct/saves/w.zip \
       --config /tmp/fct/config/config.ini \
       --mod-directory /tmp/fct/root/mods
```

成功输出末尾 `Done.` + `Goodbye`，生成约 850 KB 原版档。

| 参数 | 作用 |
|---|---|
| `--map-gen-settings FILE` | 地图生成设置（矿量/水/敌人），模板 `data/map-gen-settings.example.json` |
| `--map-settings FILE` | 地图规则（演化/虫群），模板 `data/base/prototypes/map-settings.lua` |
| `--map-gen-seed N` | 固定随机种子（**可复现**，调试很有用） |
| `--preset NAME` | 预设：`default` / `rich-resources` / `marathon` / `death-world` … |

> 💡 **纯净档是最好的实验场**：没有 mod 干扰，读到的数字能和官方 wiki 对上。
