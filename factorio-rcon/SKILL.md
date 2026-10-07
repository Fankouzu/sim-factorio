---
name: factorio-rcon
description: 接入 Factorio 游戏并读写游戏世界——用命令行启动带 RCON 的服务器，从外部进程执行 Lua 读取/修改游戏状态，或从零创建一张新地图并接管。当用户说「连接 Factorio 游戏 / 让 AI 进入游戏 / 开 RCON / 在游戏里读写 / 创建新地图 / 启动 Factorio 服务器 / 从外部操作游戏」等，或需要让程序/AI 访问 Factorio 世界状态、批量建拆建筑、导出游戏数据时使用。含单机无 RCON、UDP/TCP 端口、命令前缀静默失败、auto_pause 语义等实测坑位。详细参考见 references/。
agent_created: true
---

# Factorio RCON 接入

让外部进程（AI / 脚本）**真的进入** Factorio 世界：读状态、写实体、建新图。

> 本文件是最短流程 + 索引。细节按需读 `references/`，不要一次性全读。

---

## 0. 三条铁律（先记住，能省 90% 调试时间）

1. **单机模式没有 RCON。** GUI 点「开多人游戏」**也不会**开 RCON。必须用**命令行** `--rcon-port` 启动服务器。
2. **游戏流量走 UDP**（默认 34197），**RCON 走 TCP**（默认 25575）。用 TCP 探游戏端口会**误报关闭**。
3. **每条 Lua 命令必须带前缀** `/c` 或 `/silent-command`。不带 → 服务器**静默返回空字符串，不报错**。

---

## 1. 最短流程

```bash
BIN="/path/to/factorio"        # 见 references/setup.md §1
WORK=/tmp/fct                  # 沙箱工作目录

# ① 建工作目录 + 两个配置文件（内容见 references/setup.md §2-3）
mkdir -p $WORK/{config,saves} $WORK/root/{mods,script-output}
# 写 $WORK/config/config.ini          → write-data=$WORK/root（必须绝对路径）
# 写 $WORK/config/server-settings.json → allow_commands="true"

# ② 创建新地图（纯原版；空 mod 目录）
"$BIN" --create $WORK/saves/w.zip \
       --config $WORK/config/config.ini \
       --mod-directory $WORK/root/mods

# ③ 启动服务器（必须后台托管，见 §4）
"$BIN" --start-server $WORK/saves/w.zip \
       --config $WORK/config/config.ini \
       --mod-directory $WORK/root/mods \
       --server-settings $WORK/config/server-settings.json \
       --port 34197 --rcon-port 25575 --rcon-password yourpass

# ④ 等端口就绪（别用固定 sleep）
for i in $(seq 1 120); do nc -z 127.0.0.1 25575 && break; sleep 1; done

# ⑤ 用 RCON 发命令
RCON_PORT=25575 RCON_PWD=yourpass \
  python3 scripts/rcon.py '/c rcon.print("tick="..game.tick)'
```

**接已有存档**：把 ② 换成 `cp <存档>.zip $WORK/saves/w.zip`，**绝不动原档**。

---

## 2. 命令前缀与返回

| 输入 | 返回 |
|---|---|
| `rcon.print("x")`（无前缀） | **空字符串，无报错**（静默消失） |
| `/c rcon.print("x")` | `x` |
| `/silent-command rcon.print("x")` | `x`（不刷屏，**AI 首选**） |

- **只有 `rcon.print()` 的输出能回传 RCON**；`game.print()` 只进玩家聊天栏。
- 非 Lua 命令同样可用：`/server-save`、`/quit`、`/players`、`/help`。

### ★ 空返回的三种可能（实测，极易误判）

收到**空字符串**时，可能是：

1. **命令没带前缀**；
2. **Lua 运行时报错了** —— 报错**既不回传 RCON，也不写日志**，完全静默；
3. 命令执行了但确实没产出任何 print。

**定位方法：用 `pcall` 把业务代码包起来，自己捕获错误。**

```lua
/c local ok,err=pcall(function()
     -- 你的业务代码
     rcon.print("tick="..game.tick)
   end)
   if not ok then rcon.print("ERR: "..tostring(err)) end
```

> 常见触发例：`game.active_mods` **不存在**（2.0 里用 `script.active_mods`）；
> 访问 nil 字段、对无效实体调方法，都会静默失败。
> **写不确定的 API 时一律用 pcall 包一层。**

---

## 3. 读写游戏世界（Lua 起步包）

```lua
-- 世界状态
game.tick                  -- 当前刻（60 tick = 1 秒）
game.speed                 -- 速度倍率
game.tick_paused           -- 是否暂停
#game.connected_players    -- 在线人数
game.surfaces              -- 所有星球/表面

-- 查实体
local s = game.surfaces["nauvis"]
local silos = s.find_entities_filtered{ name = "rocket-silo" }
local near  = s.find_entities_filtered{ area = {{x-20,y-20},{x+20,y+20}} }

-- 写实体
local e = s.create_entity{ name="iron-chest", position={0,0}, force="player" }
e.destroy()

-- 导出到磁盘（落 <write-data>/script-output/）
helpers.write_file("dump.json", helpers.table_to_json(data), false)
```

⚠️ **`create_entity` 坐标吸附到 0.5 网格**：给 `{0,0}` 读回是 `(0.5, 0.5)`，正常。
⚠️ **只有 `helpers.write_file()`，没有 `game.write_file()`**。
⚠️ **`game.speed = 0` 报错**，用 `0.01` 或 `game.tick_paused = true`。

---

## 4. 长驻进程的工程细节

服务器是**长驻进程**，启动方式决定它活不活得下来：

- ❌ `nohup "$BIN" ... &` —— 实测**会被 SIGHUP 带走**（日志 `Received SIGHUP, shutting down`），
  且退出前会**把地图存回存档**（副本被污染，下次启动前要重新 `cp`）。
- ✅ 用执行环境的 **background 任务机制**托管（前台 exec，不加 `&`）。
- **启动后必须验证**：`pgrep -fl factorio` + `lsof -nP -iTCP:25575 -sTCP:LISTEN`。
  **别只看日志说"启动成功"**。

**收尾**：`/server-save` 保存 → `/quit` 正常关服（保存后退出）。

---

## 5. `auto_pause: true` 的真实语义（易误判）

没人在线时：**世界暂停（tick 几乎不动），但服务器进程和 RCON 端口照常活着**。
连续读 `game.tick` 只涨 1~2 格（那几格还是发 RCON 命令时被唤醒跑的），`paused=false`、`speed=1`。

**这不是掉线。** 想读"稳定状态"就保持 `true`；想观测产线动态设 `false`（但服务器不会凭空推进世界）。

---

## 6. ★ 安全红线

1. **永远用副本。** 接玩家存档先 `cp`，再 `--start-server <副本>`。**不碰原档一个字节**——
   注意 `auto_pause` 也可能让服务器**保存**，一旦保存原档就被改写。
2. **端口别撞。** 先查 `lsof -nP -iTCP:25575` / `-iUDP:34197`，选空闲端口。
3. **mod 别污染。** `--mod-directory` 指向**复制出来的**目录，不软链玩家真实 mod 目录
   （游戏会往里写 `mod-list.json`）。
4. **写操作前想清楚。** RCON 的 Lua 权限**完整**：能造、能删、能改任何东西。
5. **报数必报时刻。** 存档是"会跑的表"，每个数字绑定在某个 tick 上。
   读关键数量要**抢在载入第一帧**或先冻结（`game.speed = 0.01`）。
   **别拿 A 时刻的现象推 B 时刻的原因。**

---

## 7. 参考文档索引

| 文件 | 内容 |
|---|---|
| `references/setup.md` | 找可执行文件、config.ini、server-settings.json 完整模板、mod 目录、地图生成参数 |
| `references/protocol.md` | RCON 报文格式（小端）、认证、客户端源码说明、命令参数全表 |
| `references/pitfalls.md` | 8 条实测坑详解 + 排障清单 |

**配套脚本**：`scripts/rcon.py` —— 零依赖 RCON 客户端（标准库 socket + struct）。

```bash
RCON_HOST=127.0.0.1 RCON_PORT=25575 RCON_PWD=yourpass \
  python3 scripts/rcon.py \
  '/c rcon.print("tick="..game.tick)' \
  '/c for _,s in pairs(game.surfaces) do rcon.print(s.name) end'
```

---

## 8. 版本

实测环境：**Factorio 2.0.77**（build 84539, mac-arm64, Steam）。协议与命令行在 2.x 通用。
