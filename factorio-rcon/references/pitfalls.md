# 常见坑（全部实测踩过）

## 坑 1：以为单机能开 RCON

**现象**：游戏正常玩着，连不上 RCON。
**原因**：单机模式**不监听任何端口**。GUI 里点「开多人」也**不会**开 RCON。
**解决**：必须命令行 `--start-server` + `--rcon-port`。

## 坑 2：用 TCP 探游戏端口

**现象**：`nc -z 127.0.0.1 34197` 报 closed，以为服务器没起来。
**原因**：**游戏流量走 UDP**，只有 RCON 走 TCP。
**解决**：用 RCON 端口判断存活（`lsof -nP -iTCP:25575 -sTCP:LISTEN`）；
查游戏端口用 `lsof -nP -iUDP:34197`。

## 坑 3：空返回 —— 缺前缀 or **Lua 报错**（两者现象完全一样）

**现象**：`rcon.py '...'` 输出**空行，没有任何报错**。

**⚠️ 实测确认：Lua 运行时报错时，RCON 同样只返回空字符串，而且既不回传错误、也不写日志，完全静默。**
所以"空返回"有两种成因，**外观无法区分**：

| 成因 | 说明 |
|---|---|
| **A. 缺前缀** | 服务器把它当聊天消息，返回空 |
| **B. Lua 报错** | 例如访问了不存在的字段/方法 |

**两个成因的对照实测**：

| 输入 | 返回 |
|---|---|
| `rcon.print("x")` | 空（缺前缀） |
| `/c rcon.print("x")` | `x` |
| `/c rcon.print("no_field="..tostring(game.active_mods))` | 空（**`game.active_mods` 不存在**，报错被吞） |
| `/c rcon.print("base="..script.active_mods["base"])` | `base=2.0.77`（**正确写法**） |

**解决：用 `pcall` 把业务代码包起来，自己捕获错误。**

```lua
/c local ok,err=pcall(function()
     -- 业务代码
     rcon.print("tick="..game.tick)
   end)
   if not ok then rcon.print("ERR: "..tostring(err)) end
```

**结论：任何不确定的 API 调用都要包 pcall**，否则你只能看到"什么都没有"，无从下手。

## 坑 4：后台进程被 SIGHUP 带走

**现象**：日志显示服务器启动成功，几秒后进程消失、端口关闭。
**原因**：`nohup ... &` 在父 shell 退出时被 SIGHUP 杀死（日志 `Received SIGHUP, shutting down`）。
**额外危害**：退出前会**把地图存回存档** → 如果你在副本上跑，副本被污染（下次要重新 `cp`）。
**解决**：用执行环境的 background 任务机制托管（前台 exec，不加 `&`）。
**验证**：`pgrep -fl factorio` + `lsof -nP -iTCP:25575 -sTCP:LISTEN`。**别只看日志。**

## 坑 5：`game.speed = 0` 报错

**现象**：想暂停游戏，设 0 报错。
**解决**：用 `0.01`（近似暂停）或 `game.tick_paused = true`。

## 坑 6：误判 `auto_pause` 为"掉线"

**现象**：没玩家在线时读 `game.tick`，连续几次只涨 1~2 格，以为连接断了。
**真相**：`auto_pause: true` 时，**世界暂停但进程和 RCON 端口照常活着**；
涨的那 1~2 格是发 RCON 命令时把游戏唤醒跑的。`paused=false`、`speed=1`。
**决策**：
- 要读"稳定状态" → 保持 `true`（世界不会自己跑掉）；
- 要观测产线动态 → 设 `false`，但服务器**不会凭空推进**世界。

## 坑 7：拿沙箱读数当"玩家实机事实"

**真实翻车案例**：沙箱副本被设成 `game.speed=1200` 快进，tick 从 1673 万跑到 2742 万
（**多推 1070 万刻**），箱内物资被消耗殆尽 → 得出"物资断供"的错误结论，而玩家实机里一切正常。

**根因**：**存档是"会跑的表"，不是静态快照。** 每个数字都绑定在**某个 tick** 上。

**规矩**：
- 读关键数量要**抢在载入第一帧**，或**先冻结**（`game.speed = 0.01`）再读；
- **报数必报时刻**：`tick=16781973` 与 `tick=27000000` 是两回事；
- **沙箱永远是副本**，绝不动玩家原档；
- 结论要落到**当时那个 tick**，不能拿"A 时刻的现象"推"B 时刻的原因"。

## 坑 8：`player.selected` 经 RCON 恒为 nil

无法用它判断玩家鼠标指着什么。
**替代**：用坐标距离推断，或直接读实体列表。

## 坑 9：headless 服务器无法截图

无窗口服务端没有渲染管线。多种截图写法**全部返回 OK 但零文件**。
**替代**：用 `helpers.write_file` 导出实体 JSON + tile 网格，自己用 PIL/Canvas 绘制。

## 坑 10：`create_entity` 坐标偏移

给 `{0, 0}`，读回来是 `(0.5, 0.5)`。
**原因**：坐标被吸附到 0.5 网格。**这是正常的**，不是 bug。

---

# 排障清单（连不上时按序查）

```
1. 进程活着吗？        pgrep -fl factorio
2. RCON 端口在听吗？   lsof -nP -iTCP:25575 -sTCP:LISTEN
3. 端口选对了吗？      启动参数 --rcon-port N 与客户端 RCON_PORT 是否一致
4. 密码对吗？          AUTH 回包 id == -1 → 密码错
5. 命令带前缀了吗？    /c 或 /silent-command（不带会静默返回空）
6. 返回空但前缀对？    → **多半是 Lua 报错**，改用 pcall 捕获（坑 3）
7. 用的是 TCP 吗？     RCON 走 TCP；游戏端口走 UDP（别拿 TCP 探游戏口）
8. 读的是副本吗？      原档是否被意外改写（auto_pause 也会保存）
```

---

# 已验证 API 清单（2026-10-07 实测，2.0.77 纯净档）

以下是本文档所有示例的实测结果，可放心照抄：

| 调用 | 实测结果 |
|---|---|
| `game.tick` | ✅ `9` |
| `game.speed` | ✅ `1`；设 `0.01` 成功 |
| `game.tick_paused` | ✅ `false` |
| `#game.connected_players` | ✅ `0`（无人在线） |
| `#game.surfaces` | ✅ `1` |
| `script.active_mods["base"]` | ✅ `2.0.77` |
| `game.active_mods` | ❌ **不存在** → 静默空返回 |
| `surface.create_entity{...}` | ✅ 返回有效实体 |
| `find_entities_filtered{name=}` | ✅ |
| `find_entities_filtered{type=}` | ✅ |
| `find_entities_filtered{area=}` | ✅ |
| `entity.get_inventory(defines.inventory.chest).get_contents()` | ✅ |
| `entity.get_recipe()` | ✅ 无配方返回 nil |
| `entity.destroy()` | ✅ |
| `helpers.write_file(path, data, append)` | ✅ 落 `<write-data>/script-output/` |
| `helpers.table_to_json(t)` | ✅ |
| `defines.inventory.chest` | ✅ `= 1` |
| `defines.direction.north` | ✅ |
| `/server-save` | ✅ 输出 `Saving the map` |
