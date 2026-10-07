# sim-factorio

Factorio 自动化 / AI 接入相关的技能包集合。

## 技能列表

| 技能 | 说明 |
|---|---|
| [`factorio-rcon`](./factorio-rcon/) | 接入 Factorio 游戏并读写世界：命令行启动带 RCON 的服务器，从外部进程执行 Lua 读取/修改游戏状态，或从零创建新地图并接管。 |

## 安装

把技能目录拷进你的 agent 技能目录即可：

```bash
# 用户级（跨项目可用）
cp -r factorio-rcon ~/.workbuddy/skills/

# 或项目级
cp -r factorio-rcon <项目>/.workbuddy/skills/
```

技能目录结构遵循通用规范：

```
factorio-rcon/
├── SKILL.md              # 技能定义（frontmatter: name / description）
├── scripts/
│   └── rcon.py           # 零依赖 RCON 客户端
└── references/
    ├── setup.md          # 环境准备与配置模板
    ├── protocol.md       # 协议格式与命令行全表
    └── pitfalls.md       # 实测坑位与排障清单
```

## 快速验证

```bash
BIN="/path/to/factorio"        # 见 factorio-rcon/references/setup.md
WORK=/tmp/fct
mkdir -p $WORK/{config,saves} $WORK/root/{mods,script-output}

# 1) 创建一张新地图
"$BIN" --create $WORK/saves/w.zip \
       --config $WORK/config/config.ini \
       --mod-directory $WORK/root/mods

# 2) 起服务器（带 RCON；需先写好 config.ini 与 server-settings.json）
"$BIN" --start-server $WORK/saves/w.zip \
       --config $WORK/config/config.ini \
       --mod-directory $WORK/root/mods \
       --server-settings $WORK/config/server-settings.json \
       --port 34197 --rcon-port 25575 --rcon-password yourpass

# 3) 发命令
RCON_PORT=25575 RCON_PWD=yourpass \
  python3 factorio-rcon/scripts/rcon.py '/c rcon.print("tick="..game.tick)'
```

三条铁律：**单机没 RCON，要命令行起服；游戏走 UDP、RCON 走 TCP；命令必带 `/c`，不带就静默消失。**

## 环境

实测于 **Factorio 2.0.77**（build 84539, mac-arm64, Steam）。RCON 协议与命令行在 2.x 通用。

## 许可

以各技能目录内说明为准。
