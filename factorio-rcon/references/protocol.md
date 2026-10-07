# RCON 协议与命令行参考

## 1. 协议格式

Factorio RCON 实现了 **Source RCON 协议**（与 Minecraft/Source 引擎同款）。所有整数**小端**。

```
[ length : int32 ] [ id : int32 ] [ type : int32 ] [ body : bytes ] [ 0x00 0x00 ]
   4 字节              4 字节        4 字节         变长           2 字节结束符
```

**`length` = 后面所有字节数**（id + type + body + 2 字节结束符），**不含** length 自身。

| type | 含义 |
|---|---|
| `3` | **AUTH**（认证），body = 密码 |
| `2` | **EXECCOMMAND**（执行命令），body = 命令字符串；服务器回包也用 2 |
| `0` | RESPONSE_VALUE（普通响应） |

**认证失败**：服务器回包 **`id = -1`** → 立即判定密码错，不要再发命令。

## 2. 客户端

`scripts/rcon.py` —— 零依赖（标准库 `socket` + `struct`），约 60 行。

```bash
# 环境变量覆盖默认值
RCON_HOST=127.0.0.1 RCON_PORT=25575 RCON_PWD=yourpass \
  python3 scripts/rcon.py 'cmd1' 'cmd2' ...
```

- 默认 `RCON_HOST=127.0.0.1`、`RCON_PORT=25577`、`RCON_PWD=aquilo`（可通过环境变量改）。
- 多条命令**一次连接依次执行**，每条一个响应。
- 命令必须自带前缀（如 `/c ...`），客户端不代加。

**核心实现要点**：

```python
def pack(rid, ptype, body):
    b = body.encode("utf-8") + b"\x00\x00"
    return struct.pack("<iii", 4 + 4 + len(b), rid, ptype) + b

# 认证：send pack(1, 3, PWD)；回包 rid == -1 则失败
# 执行：send pack(i+2, 2, cmd)
# 收包：先读 12 字节头（length/rid/ptype），再读 length-8 字节体
```

## 3. 启动服务器命令行参数全表

（实读自 `--help`，Factorio 2.0.77）

### 服务器启动

| 参数 | 说明 |
|---|---|
| `--start-server FILE` | 启动服务器并加载存档 |
| `--start-server-load-latest` | 启动并加载**最新**存档（免写文件名） |
| `--start-server-load-scenario [MOD/]NAME` | 启动并加载 scenario |
| `--host FILE` / `--host-interactive FILE` | 主持多人游戏 |
| `--until-tick N` | 加载后跑到第 N 刻就停（确定性实验用） |

### RCON 相关

| 参数 | 说明 |
|---|---|
| `--rcon-port N` | **RCON 监听端口（TCP）**。不加 = 没有 RCON |
| `--rcon-bind ADDRESS:PORT` | 绑定指定地址+端口（只本机访问用 `127.0.0.1:25575`） |
| `--rcon-password PWD` | RCON 密码。**必须设**，否则无法认证 |

### 网络

| 参数 | 说明 |
|---|---|
| `--port N` | **游戏**流量端口（**UDP**），默认 34197 |
| `--bind ADDRESS[:PORT]` | 游戏端口绑定地址 |
| `--server-settings FILE` | 服务器设置 JSON |

### 通用

| 参数 | 说明 |
|---|---|
| `-c, --config PATH` | 配置文件（config.ini） |
| `--mod-directory PATH` | mod 目录 |
| `-v, --verbose` | 详细日志 |
| `--no-log-rotation` | 不轮转日志 |

### 地图生成

| 参数 | 说明 |
|---|---|
| `--create FILE` | 创建新地图 |
| `--map-gen-settings FILE` | 生成设置 |
| `--map-settings FILE` | 地图规则 |
| `--map-gen-seed SEED` | 随机种子 |
| `--preset arg` | 生成预设 |
| `--generate-map-preview PATH` | 生成地图预览 PNG（**这是唯一能出图的路径**） |
| `--generate-map-preview-random COUNT` | 随机种子批量预览 |
| `--map-preview-planet PLANET` | 预览指定星球（默认 nauvis） |

### 数据导出（调试利器）

| 参数 | 说明 |
|---|---|
| `--dump-data` | 导出 `data.raw` 为 JSON 到 script-output，然后退出 |
| `--dump-icon-sprites` | 导出所有图标 PNG |
| `--dump-prototype-locale` | 导出所有原型名与描述 |

### 调试 / 性能

| 参数 | 说明 |
|---|---|
| `--benchmark FILE` | 加载存档跑基准测试 |
| `--benchmark-ticks N` | 基准刻数（默认 1000） |
| `--enable-unsafe-lua-debug-api` | 启用 Lua 调试库的不安全函数 |
| `--enable-lua-udp arg` | 启用 `helpers.send_udp()` / `helpers.recv_udp()` |

## 4. 游戏内命令（经 RCON 发送）

| 命令 | 作用 |
|---|---|
| `/c <lua>` | 执行 Lua（会进入命令回显） |
| `/silent-command <lua>` | 执行 Lua（静默，AI 首选） |
| `/server-save` | 保存地图（输出 `Saving the map`） |
| `/quit` | 保存并退出服务器 |
| `/players` | 列出在线玩家 |
| `/help` | 帮助 |

## 5. 玩家如何加入

客户端主菜单 → **多人游戏 → 加入游戏** → 局域网列表里出现 `server-settings.json` 的 `name`；
或直接输 `127.0.0.1:34197`。设了 `game_password` 才需要密码。
