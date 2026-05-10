# Tards 卡牌游戏开发 —— 新对话启动上下文

## 一、项目概览

- **项目名称**：Tards TCG（集换式卡牌游戏）
- **技术栈**：Python 3.14 + Tkinter（严禁 Pygame）+ TCP JSON 网络协议
- **根目录**：`C:\Users\34773\Desktop\tards开发库`
- **虚拟环境**：`.venv\Scripts/python.exe`
- **已知环境坑**：Windows PowerShell GBK 编码导致 CLI 乱码；建议写临时 `.py` 文件再执行

## 二、当前工作状态（截至 2026-05-09）

### 2.1 本轮已完成（本次对话）

**冥刻卡包策略卡 — 11张全部完成**
- 9张策略卡补上 `@strategy` 装饰器（导入时签名校验 + 运行时异常保护）
- 补回 `_jiaoshui_effect`、`_bingkuai_effect` 丢失的文档字符串
- 新建 `STRATEGY_MAP`（underworld_effects.py），注册全部11张策略卡
- 实现 **新月**（4T金卡）：全局阴谋-1T + 阴谋每触发2次回收自身到手牌
- 核心引擎扩展：`constants.py` 新增 `EVENT_CONSPIRACY_TRIGGERED`；`game.py` 阴谋触发后自动 emit

**Bug 修复**
- 快速点击数字键/鼠标出牌导致卡牌多次打出 → `_on_hand_card_click` 加 500ms 防抖锁 `_is_playing_card`
- 快速点击拍铃/拉闸导致回合错乱 → `_on_bell` / `_on_brake` 加 500ms 防抖锁
- 拍铃"不出牌惩罚"只扣1次 → 在 `game.py` 每次玩家获得回合时重置 `t_changed_this_round`
- 手牌满时兑换矿物导致上限失效 → `exchange_mineral` 加入上限检查，满则磨牌
- 补全缺失导入：`game.py` 缺 `EVENT_CONSPIRACY_TRIGGERED`；`discrete_effects.py` `_yanhuozhixing_effect` 缺 `get_opponent`
- 热修：`player.py` `draw_card` 中被误替换的 `mineral_card` 变量名恢复为 `card`

**平衡调整**
- 门船穿梭：2T → 1T1I

**GitHub 同步**
- 全部修改已推送到 `WindWillows/Tards.git` `master` 分支
- 最新 commit：`3d878ea`

### 2.2 各卡包状态

| 卡包 | 总数 | 策略卡 | 随从卡 | 状态 |
|------|------|--------|--------|------|
| **离散** | 182 | ~40张已实现 | ~140张已实现 | 基本完成，剩余少量复杂卡 |
| **冥刻** | 163 | **51/51 全部完成** | 10张有效果，102张白板/关键词 | 策略卡完成，随从卡大量待实现 |
| **血契** | 70 | 少量 | 少量 | 大量待实现 |

### 2.3 近期架构变更（必须知晓）

- **拍铃惩罚**：`t_changed_this_round` 在 `action_phase` 开始时（`reset_turn_flags`）和**每次玩家获得回合时**都会重置
- **阴谋触发事件**：`game.py` 阴谋 effect_fn 执行后会 emit `EVENT_CONSPIRACY_TRIGGERED`
- **防抖锁模式**：GUI 输入（出牌/拍铃/拉闸）统一使用 500ms 状态锁防重复提交
- **策略卡 5 参数**：`effect_fn(player, target, game, extras, card)` 第5参数传入 Strategy 实例自身

## 三、核心工作模式（必须严格遵守）

### 3.1 实现新卡牌标准流程
1. 分析效果 → 确定触发时机
2. 检查 `effect_utils.py` 是否已有可用 API
3. 若无可用 API，先扩展工具库，再写卡牌效果
4. 编写 `special_fn`（异象）或 `strategy_fn`（策略）
5. 加上 `@special` 或 `@strategy` 装饰器
6. 在 `card_pools/xxx_effects.py` 中注册到 `SPECIAL_MAP` / `STRATEGY_MAP`
7. 在 `card_pools/xxx.py` 中通过 `register_card()` 注册卡牌

### 3.2 关键规则
- **禁止望文生义**：所有游戏术语有精确定义，不确定时查规则书/代码/问用户
- **禁止自作主张**：不应用其他 TCG 知识推断机制
- **禁止硬编码**：Card effects 必须放在 `effect_fn`/`special_fn` 中，不得在游戏核心循环中检查卡牌名
- **优先更新工具库**：复杂功能先查 `effect_utils.py`，不足时扩展工具库而非写 ad-hoc 代码
- **向后兼容**：原函数注释保留不删除

## 四、关键文件速查

| 文件 | 职责 |
|------|------|
| `card_pools/discrete.py` | 离散卡包 182 张定义 |
| `card_pools/discrete_effects.py` | 离散卡包效果实现 + `STRATEGY_MAP` |
| `card_pools/underworld.py` | 冥刻卡包 163 张定义 |
| `card_pools/underworld_effects.py` | 冥刻卡包效果实现 + `SPECIAL_MAP` + `STRATEGY_MAP` |
| `card_pools/effect_utils.py` | 标准效果工具库（**优先使用**） |
| `tards/player.py` | `Player` 类；`exchange_mineral` 已修复上限检查 |
| `tards/game.py` | `Game` 主引擎；`action_phase` 已修复拍铃惩罚 |
| `tards/constants.py` | 事件常量；已新增 `EVENT_CONSPIRACY_TRIGGERED` |
| `gui_client.py` | GUI；已添加出牌/拍铃/拉闸防抖锁 |
| `AGENTS.md` | Agent 工作规则 |
| `TARDS_GAME_REFERENCE.md` | 完整项目参考文档 |

## 五、常见陷阱

1. **`from .xxx_effects import *`** 只会导入 `__all__` 中的名字。新函数必须加入 `__all__` 和对应 `MAP`。
2. **Pylance 报错「未定义」**：`import *` 导致静态分析失效，不影响运行时。
3. **PowerShell 编码**：CLI 脚本输出中文会乱码，建议写临时 `.py` 文件再执行。
4. **`StrReplaceFile` 慎用 `replace_all`**：确认不会误改其他同名变量（如 `card.move_to` 被误改为 `mineral_card.move_to`）。
5. **新事件常量**：若新增事件类型（如 `EVENT_CONSPIRACY_TRIGGERED`），务必同步添加到使用处的 `import` 列表。

## 六、启动任务建议

**当前最优先任务**：冥刻卡包随从卡（102张白板/仅靠关键词，需判断是否都需要自定义效果）或继续离散卡包收尾。

**注意**：用户在 2026-05-09 表示离散卡包基本完成，本轮重点完成了冥刻策略卡。下一段对话的任务需与用户确认。

---

*生成时间：2026-05-09*
