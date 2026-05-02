---
name: tards-dev
description: |
  Tards 卡牌游戏项目开发专用 skill。用于实现新卡牌、修复卡牌效果、
  理解游戏规则、以及避免硬编码坏习惯。当用户要求：
  (1) 实现/修复某张卡牌的效果，
  (2) 解释某个游戏机制或关键词，
  (3) 修改核心游戏引擎逻辑，
  (4) 调试效果未触发或行为异常，
  (5) 扩展效果工具库时，
  触发本 skill。
---

# Tards 项目开发指南

## 核心原则

1. **不要望文生义**：游戏术语（视野、潜水、移动等）有精确定义，不以日常语义理解。
2. **不要自作主张**：Tards 规则与常规 TCG（炉石/万智/YGO）完全不同，禁止用其他游戏知识推断。
3. **禁止硬编码**：核心引擎（game.py/player.py/board.py/cards.py）中绝不允许出现卡牌名字或特殊分支。
4. **优先扩展工具库**：复杂效果先在 `effect_utils.py` 中实现通用 API，再在卡牌中调用。

## 实现新卡牌的标准流程

```
1. 分析效果 → 确定触发时机（部署/回合开始/回合结束/受伤/亡语/策略打出）
2. 检查 effect_utils.py 是否已有可用 API
3. 若无可用 API，先扩展工具库，再写卡牌效果
4. 编写 special_fn（异象）或 strategy_fn（策略）
5. 加上 @special 或 @strategy 装饰器
6. 在 card_pools/xxx_effects.py 中注册到 SPECIAL_MAP / STRATEGY_MAP
7. 在 card_pools/xxx.py 中通过 register_card() 注册卡牌（或修改现有定义）
8. ~~运行 python demo.py 测试~~（用户指示：不需要测试，直接输出）
```

> **注意**：若用户明确指示"不需要测试，直接输出"，则跳过测试步骤，完成代码后直接汇报成果即可。

## 关键语义映射

| 规则书原文 | 引擎实际时机 | 说明 |
|-----------|------------|------|
| **回合开始** | `EVENT_PHASE_START` + `phase == PHASE_RESOLVE` | 结算阶段开始时触发。禁止用 `EVENT_TURN_START` 或 `on_turn_start` 实现"回合开始"效果。 |
| **回合结束** | `EVENT_PHASE_END` + `phase == PHASE_RESOLVE` | 结算阶段结束时触发。禁止用 `EVENT_TURN_END` 或 `on_turn_end` 实现"回合结束"效果。 |
| **对局开始时** | `Card.on_game_start` 回调 | `Game.start_game()` 在抽初始手牌前扫描并执行。 |
| **弃置** | `Player.discard_card()` 或手牌满磨牌 | 触发 `EVENT_DISCARDED`。正常打出策略卡进入弃牌堆**不触发**。 |
| **打出 / 进入弃牌堆** | `Player.play_card()` → 效果成功 → 移入 discard | **不触发**弃置事件。 |
| **抽取（机制 A）** | `hidden_keywords={"抽取": callback}` | `draw_card()` 直接调用 `callback(player, game, card)`。blood.py 占位符系列使用此方式。 |
| **抽取（机制 B）** | `set_draw_trigger(card, callback)` | 通过 EventBus 调度，`callback(game, event_data, card)`。两种机制并存，签名不同。 |
| **抽牌** | `Player.draw_card()` | 动作本身，不保证触发抽取（若直接 append 到手牌则不会）。 |
| **跳过结算阶段** | `game._skip_resolve_phase = True` | `resolve_phase()` 开头检查，跳过整轮攻击并清空标志。 |
| **双倍血契** | `player._double_blood_gain = True` | 献祭时产血自动翻倍。 |
| **本回合策略卡计数** | `game._strategies_played_this_turn` | 每回合重置，打出策略卡后自动 +1。 |
| **卡位置追踪** | `Card._location` / `move_to()` | 统一追踪卡牌所在区域（deck/hand/discard/board/exile/resolving）。 |
| **卡实例事件监听** | `Card.on(event_type, listener)` / `off_all()` | 卡实例级 EventBus 注册/注销。死亡/离场时应调用 `off_all()`。 |
| **抽取效果设置** | `set_draw_trigger(card, callback)` | 为卡牌绑定抽取触发器，仅 `draw_card()` 入牌时触发。 |
| **策略卡 self 传入** | `effect_fn(player, target, game, extras, card)` | `Strategy.effect()` 通过 `inspect` 检查参数数量。若定义了 5 个参数，第 5 个自动传入 Strategy 实例自身。用于卡实例级监听（如深渊弃置监听）。 |

### 槽位与资源点的区别

**获得槽位（T槽/C槽）≠ 获得资源点。** 增加槽位上限不会自动获得可使用的资源点。

| 效果描述 | 正确实现 | 错误实现 |
|---------|---------|---------|
| "获得1个T槽" | `player.t_point_max += 1` | `player.t_point_max += 1; player.t_point_change(1)` ❌ |
| "获得1个C槽" | `player.c_point_max += 1` | `player.c_point_max += 1; player.c_point_change(1)` ❌ |

- 资源点（`t_point` / `c_point`）在每回合特定阶段由引擎根据上限自动补充。
- 若效果明确说"获得X点T/C"，才使用 `t_point_change(X)` / `c_point_change(X)`。

**核心引擎修改（2026-04-20）**：
- `_EVENT_ATTR_MAP` 已移除 `EVENT_TURN_START` → `on_turn_start` 和 `EVENT_TURN_END` → `on_turn_end` 的映射。
- `minion.on_turn_start` / `minion.on_turn_end` 回调现在仅在**结算阶段**开始/结束时触发。
- `effect_utils.py` 中的 `on_turn_start()` / `on_turn_end()` 函数已改为监听 `phase_start` / `phase_end` 并过滤 `phase == PHASE_RESOLVE`。
- 若某张卡的效果确实需要在**完整回合**开始/结束时触发（目前没有），应使用 `on("turn_start", ...)` 或 `on("turn_end", ...)` 显式注册 EventBus 监听器。

## 指向系统速查

- 所有指向操作统一走 `TargetingRequest` + `process_targeting_request()`。
- 策略卡主目标由 `targets_fn` 返回合法列表。
- 多阶段指向通过 `extra_targeting_stages=[(stage_fn, count, allow_repeat)]` 实现。
- 手牌目标：使用 `target_hand_minions`，GUI 会自动弹出手牌选择。
- **指向玩家**：自定义 `targets_fn` 返回异象列表 + `[game.p1, game.p2]`（如金牙齿策略）。

## 献祭流程速查（2026-04-19 重构后）

```
Game.action_phase() 处理 play 动作时：
  1. 筛选 valid_sacs（存活且 _sacrifice_remaining > 0）
  2. active.b_point += sum(m.keywords.get("丰饶", 1) for m in valid_sacs)  [永久预加]
  3. active.sacrifice_chooser = lambda req, v=valid_sacs: v  [临时注入]
  4. try: active.card_can_play() → active.play_card() → cost.pay()
  5. finally: active.sacrifice_chooser = old_chooser  [恢复选择器]

MinionCard.effect() 内部：
  - request_sacrifice(cost.b) → 消灭目标 → emit EVENT_SACRIFICE
  - 不再操作 b_point！
```

**关键注意**：`card_can_play()` 现在返回 `tuple[bool, str]`，调用时务必取 `[0]` 或解包。

## 测试卡组模式

- `Deck.is_test_deck = True` → `validate()` 跳过所有构筑限制。
- 仅本地可用，联机大厅禁止加载。
- GUI 构筑界面有复选框，save/load 持久化。

## 美术资源接口（2026-04-28 新增）

### AssetManager 使用
```python
from tards.assets import get_asset_manager

am = get_asset_manager()  # 单例，base_path="assets"
am.available()  # Pillow 是否可用且目录存在

# 加载图像（返回 ImageTk.PhotoImage 或 None）
img = am.get_card_face(asset_id, width, height)
img = am.get_card_back("default", width, height)
img = am.get_thumbnail(asset_id, width, height)  # 无缩略图时自动回退到卡面
img = am.get_icon(f"kw_关键词名", size)
img = am.get_board_tile("terrain_enemy", size)
```

**目录约定**（相对于 `assets/`）：
- `cards/faces/{asset_id}.png` — 卡面
- `cards/backs/{asset_id}.png` — 卡背
- `cards/thumbnails/{asset_id}.png` — 缩略图（棋盘/阴谋区）
- `icons/keywords/kw_关键词名.png` — 关键词图标
- `board/tiles/terrain_*.png` — 棋盘地形纹理
- `config.json` — 可选：自定义 asset_id → 路径映射

**零资源兼容**：所有渲染代码必须先检查返回值，为 `None` 时回退到现有文本/几何渲染。禁止因缺少资源文件而报错。

### 注册卡牌时指定资源
```python
register_card(
    name="金牙齿",
    asset_id="jin_yachi",  # 可选，留空则无图像
    asset_back_id="default",  # 可选
    ...
)
```

## GUI 渲染规范

- **手牌**：`tk.Canvas`，尺寸 `BattleFrame.HAND_CARD_WIDTH × HAND_CARD_HEIGHT`（当前 90×120）。图像层叠顺序：卡面图 → 类型角标 → 费用/名称/攻防文字。
- **棋盘异象**：肖像图占格子 70%（56×56），居中显示。边框/阴影/文字覆盖在图像之上。
- **坐标偏移**：棋盘整体有 `BOARD_OFFSET_X/Y` 偏移。所有绘制和点击坐标计算必须考虑偏移。
- **图像引用防 GC**：Tkinter 的 `PhotoImage` 必须保存在 Python 对象属性中（如 `self._minion_image_refs`、`cvs.image`），否则会被垃圾回收导致图像消失。

## 易混淆用语速查（禁止望文生义）

| 用语 | 正确定义 | 常见错误 |
|------|---------|---------|
| **相邻** | 上下左右 **4 格** | 误认为 8 格（那是"周围"） |
| **周围** | 含对角线 **8 格** | 与"相邻"混淆 |
| **弃置 vs 打出进弃牌堆** | 弃置触发 `EVENT_DISCARDED`，打出进弃牌堆**不触发** | 将两者混为一谈 |
| **造成伤害 vs 流失生命** | 前者受坚韧/伤害替换影响，后者用 `lose_hp()` **不受影响** | 在"失去 HP"效果中错误使用 `health_change()` |
| **抽取 vs 抽牌** | 抽取是 `hidden_keywords` 回调，仅在 `draw_card()` 时触发；抽牌是动作 | 直接 append 到手牌后手动调用抽取回调 |
| **获得槽位 vs 获得资源点** | 槽位 = 上限；资源点 = 当前可用值。加上限**不加当前值** | `t_point_max += 1` 后多写一行 `t_point_change(1)` |
| **唯一最高** | 必须有且仅有 **1 个**。并列时 = 不唯一 = **不触发** | 并列时随机选一个执行 |
| **爆掉 vs 磨牌** | 爆掉 = 直接销毁不进任何区域；磨牌 = 手牌满时进弃牌堆 | 混淆两者 |
| **如可能** | 资源/目标不足时**整句跳过**，不报错 | 部分执行或抛出异常 |
| **视野** | 攻击列范围内异象；**不能看破潜水/潜行** | 误认为视野可以选中结算阶段的潜水异象 |
| **潜水/潜行** | **行动阶段**可见可选中；**结算阶段**攻击落空 | 误认为行动阶段不可选中 |
| **移动** | 内部效果回调，**不是玩家行动类型** | 误认为玩家可以主动"移动" |
| **高频** | 攻击多次，每次先攻 -1；**不自带目标选择** | 误认为高频自带视野 |

> **规则**：不确定术语含义时，先查代码实现 → 查 `rules_text.txt` / 规则书 → **问用户**。禁止用其他 TCG 知识推断。

## 参考文件导航

| 文件 | 内容 | 何时读取 |
|------|------|----------|
| [rules-core.md](references/rules-core.md) | 胜利条件、棋盘、回合流程、费用、关键词定义 | 需要理解规则或关键词时 |
| [hardcoding-guide.md](references/hardcoding-guide.md) | 硬编码禁令、常见违规案例、正确改造方案 | 实现效果或修改引擎时 |
| [effect-patterns.md](references/effect-patterns.md) | **标准函数签名 + 21个可复制模板 + 完整 API 速查表**（含伤害控制、部署计数、目标记忆、地形覆盖、攻击限制、伤害来源追踪等） | **编写 special_fn / strategy_fn 时（必读）** |
