## 下一段对话启动提示词

请将以下内容作为系统上下文加载后，再开始与用户对话。

---

**项目**：Tards TCG（Python 3.14 + Tkinter）
**根目录**：`C:\Users\34773\Desktop\tards开发库`
**最新 commit**：`3d878ea`（已推送到 GitHub `WindWillows/Tards.git`）

### 本轮完成的关键工作（2026-05-09）

1. **冥刻卡包 11 张策略卡全部完成**
   - 9 张补上 `@strategy` 装饰器，新建 `STRATEGY_MAP`
   - 实现新月（4T金卡）：阴谋-1T + 每触发2次阴谋回收自身
   - 核心引擎新增 `EVENT_CONSPIRACY_TRIGGERED` 事件（`constants.py` + `game.py`）

2. **Bug 修复**
   - GUI 快速重复点击：出牌/拍铃/拉闸均加 500ms 防抖锁（`_is_playing_card` / `_is_belling` / `_is_braking`）
   - 拍铃不出牌惩罚失效：`game.py` 每次玩家获得回合时重置 `t_changed_this_round`
   - 手牌满兑换矿物上限失效：`player.py` `exchange_mineral` 加入上限检查
   - 补全缺失导入：`game.py` 缺 `EVENT_CONSPIRACY_TRIGGERED`；`discrete_effects.py` 缺 `get_opponent`

3. **平衡调整**：门船穿梭 2T → 1T1I

### 必须记住的规则

- **不要望文生义**、**不要自作主张**、**禁止硬编码**、**优先扩展工具库**
- 策略卡必须加 `@strategy` 装饰器，注册到 `STRATEGY_MAP`
- `StrReplaceFile` 时确认不会误改其他同名变量（上一轮 `card.move_to` 被误改为 `mineral_card.move_to` 导致崩溃）
- 新增事件常量时，务必同步添加到使用处的 `import` 列表
- PowerShell 中文乱码 → 写临时 `.py` 文件再执行

### 各卡包状态

| 卡包 | 总数 | 策略卡 | 随从卡 | 建议优先级 |
|------|------|--------|--------|-----------|
| 离散 | 182 | 基本完成 | 基本完成 | 低 |
| 冥刻 | 163 | **51/51 完成** | 10张有效，102张白板 | **高** |
| 血契 | 70 | 少量 | 少量 | 中 |

### 启动后第一件事

询问用户下一段对话的工作重点。当前没有用户预设的固定任务，需等待用户指令。

---
