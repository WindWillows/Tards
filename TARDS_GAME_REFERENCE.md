# Tards 游戏完整参考文档 & 项目交接手册

> 本文档汇总了《Tards规则书》、三个卡包（离散、冥刻、血契）的设计语言、当前程序实现的每一处细节、已修复的 Bug、以及待办事项。目的是让下一个对话可以在零上下文的情况下快速接手工作。

---

## 一、项目架构与技术栈

- **语言**：Python 3.14（Windows 环境，PowerShell）
- **GUI**：Tkinter（**严禁使用 Pygame**，环境不支持）
- **网络**：TCP + JSON 行协议（`\n` 分隔），基于原始 `socket` 封装 `GameConnection`
- **核心引擎**：`tards/` 目录
  - `game.py` — 回合流程、战斗结算、阶段控制、`Game` 类（含轻量"取消"机制、雕像融合、部署钩子）
  - `player.py` — `Player` 类：资源、手牌、献祭请求、沉浸度增益
  - `cards.py` — `Card` / `MinionCard` / `Strategy` / `Conspiracy` / `MineralCard` / `Minion`
  - `board.py` — `Board` 类：5×5 棋盘、双层细胞（minion_place + cell_underlay）、部署规则、位置查询、跨方移动
  - `effect_queue.py` — `EffectQueue`：确保连锁效果不被中断
  - `targeting.py` — **统一指向模块**：`TargetingRequest`、`TargetPicker`、攻击候选、部署额外目标
  - `auto_effects.py` — 自动化效果辅助函数：`move_enemy_to_friendly`、`swap_units`、`return_to_hand`
  - `net_game.py` — `NetworkDuel`：Host/Client 握手、行动同步、Discover 同步
  - `net_protocol.py` — `GameConnection`、消息序列化/反序列化
  - `card_db.py` — `CardDefinition`、`CardRegistry`、`Pack` 枚举、`CardType`、`Rarity`
  - `deck.py` / `deck_io.py` — `Deck` 类、卡组保存/读取（JSON 格式）
  - `cost.py` — `Cost` 类：T/C/B/S/CT/矿物费用解析与支付
  - `targets.py` — 预设目标选择器（`target_friendly_positions`、`target_none`、`target_any_minion` 等）
  - `constants.py` — 事件类型常量、`GENERAL_KEYWORDS` 列表
- **卡包池**：`card_pools/` 由 `translate_packs.py` 自动生成
  - `discrete.py` — 182 张（离散卡包）
  - `underworld.py` — 164 张（冥刻卡包）
  - `blood.py` — 70 张（血契卡包）
  - 总计 **416** 张卡牌定义
  - `underworld_effects.py` — 冥刻卡包复杂效果手动实现（雕像对 + 5 张特殊卡）
  - `effect_utils.py` — **标准效果工具库**（人工编写 special_fn 必须优先使用）
  - `effect_decorator.py` — **格式校验装饰器** `@special`
- **客户端**：`gui_client.py`（~1500 行）— 主菜单、卡组构筑器、联机大厅、对战界面
- **翻译器**：`translate_packs.py` — 从 `.txt` 卡包文本自动生成 `card_pools/*.py`

---

## 二、核心对战规则（已完整实现）

### 2.1 胜利条件
- 使对手 HP 降至 **0 或以下**。
- 双方 HP **同时** 降至 0 及以下 → **平局**。
- `Game.check_game_over()` 在 `draw_phase`、`action_phase` 循环、以及 `resolve_phase` 中都会被调用。

### 2.2 棋盘布局
- **5 列**：高地(0)、山脊(1)、中路(2)、河岸(3)、水路(4)
- **5 行**：0-1 行为敌方区，2 行为禁行区（双方不可部署/操作），3-4 行为友方区
- **距离**：曼哈顿距离 `|r1-r2| + |c1-c2|`
- **前排**：同列中距离 row=2（中线）更近的异象算前排
- `Board.get_front_minion(col, owner, attacker)` 返回某一列中敌方前排异象，自动过滤潜水/潜行异象（结算阶段）

### 2.3 回合流程
1. **抽牌阶段**（`Game.draw_phase`）
   - 第一回合：先手**跳过**抽牌，后手抽 1 张。
   - 其余回合：后手先抽 1 张，先手后抽 1 张。
   - 双方 T槽 +1（上限默认 10；离散 2 级沉浸度上限改为 8），然后**回满 T点**。
   - 血契 1 级：抽牌阶段开始时，**你失去 1 点 HP，获得 1 S**（流失生命值，不触发"受到伤害时"效果）。
   - 重置冥刻 2 级松鼠兑换标记 `squirrel_exchanged_this_turn = False`。
2. **出牌阶段**（`Game.action_phase`）
   - 先手方在所有**奇数回合**中先行动。
   - 可执行行动类型：
     - `play` — 打出一张手牌（异象部署、策略、矿物、阴谋激活）
     - `bell` — 拍铃：将行动权交给对方
     - `brake` — 拉闸：强制结束自己的出牌阶段
     - `exchange` — 兑换矿物（离散 1 级解锁）
     - `exchange_squirrel` — 兑换松鼠（冥刻 2 级解锁）
     - `set_vision` — 为具有视野的异象预设攻击目标列
     - `set_attack_targets` — 为高频/视野异象预设多个攻击目标
   - 拍铃规则：若本轮次未通过出牌改变过 T 点，拍铃时额外失去 1 T 点。
   - 拉闸规则：一方拉闸后，对方无法再拍铃。
3. **结算阶段**（`Game.resolve_phase`）
   - 对战顺序：**水路(4) → 河岸(3) → 中路(2) → 山脊(1) → 高地(0)**
   - 同列内攻击者排序：**先攻等级降序 → 距离中线升序（`|row-2|`）→ side（0 在前）**
   - **同先攻等级的异象同时攻击**：通过 `EffectQueue.resolve()` 包裹整轮攻击逻辑实现。
   - 异象攻击默认选中敌方前排；若该列无前排，则攻击对手英雄。
   - 结算阶段末尾依次执行：
     - 恢复因 `高频` 临时降低的先攻等级
     - 清理临时 BUFF（`temp_attack_bonus`、`temp_keywords` 等）
     - 冰冻/眩晕/休眠层数衰减（修改源头字典后 `recalculate()`）
     - `成长` 计数器递减与进化触发
     - 清理 `_pending_attack_targets`、`_resolve_target_col`

### 2.4 疲劳伤害（流失生命值）
- 牌库抽空后，第 X 次尝试抽牌时，失去 **X 点 HP**（`draw_fail` 计数器递增）。
- **疲劳属于【流失生命值】**，不受坚韧影响，不触发"受到伤害时"效果（如血契2级）。
- 实现位置：`Player.draw_card()` → `Player.lose_hp()`。

### 2.5 手牌上限
- 默认 **8 张**。
- 离散 1 级沉浸度 → **+1**，即 9 张。
- 手牌满时抽牌/获得卡牌，新卡**直接弃置入弃牌堆**（`card_dis`），不触发任何抽牌效果。

---

## 三、费用系统（已完整实现）

| 符号 | 名称 | 性质 | 实现细节 |
|------|------|------|----------|
| **T** | 通用点数 | 每回合自然获得，回合结束重置为 T槽 值 | `Player.t_point` / `t_point_max` |
| **C** | 兑换槽 | 不会自然增长；离散 2 级上限 4，其余 0 | `Player.c_point` / `c_point_max`；变动请使用 `c_point_change(delta)` |
| **B** | 鲜血 | 通过**献祭**友方异象获得，**回合结束清空** | `Player.b_point`；在 `action_phase` 开头清空 |
| **S** | 血契 | **跨回合保留，无上限** | `Player.s_point` |

### 3.3 流失生命值 vs 受到伤害
| 概念 | 代表表述 | API | 触发伤害替换 | 触发血契2级 | 触发 `player_damage` 事件 |
|------|---------|-----|------------|-----------|------------------------|
| **流失生命值** | "失去X点HP/生命值" | `Player.lose_hp(amount)` | ❌ | ❌ | ❌ |
| **受到伤害** | "造成X点伤害"、受到攻击 | `Player.health_change(-delta)` | ✅ | ✅ | ✅ |

- **疲劳惩罚**、**血契1级沉浸度**、卡牌中的"失去HP"效果均使用 `lose_hp()`。
- **异象攻击英雄**、策略卡"造成伤害"均使用 `health_change()`（或 `Minion.take_damage()` 对异象）。

### 3.1 矿物（离散卡包）
- 铁锭 (I) — 兑换价 **2CT** — 堆叠上限 4 — 打出：获得 **1T**
- 金锭 (G) — 兑换价 **3CT** — 堆叠上限 2 — 打出：获得 **2T**
- 钻石 (D) — 兑换价 **5CT** — 堆叠上限 1 — 打出：获得 **4T**
- 青金石 (M) — 兑换价 **2CT** — 堆叠上限 2 — 打出：无事发生
- **CT 规则**：`XCT` 表示 **X 点费用，每点可以是 1C 或 1T**。
- 支付逻辑：`Cost.pay()` 优先消耗 C，再消耗 T。
- **兑换前提**：玩家必须有**离散 1 级沉浸度**。

### 3.2 鲜血（B）与献祭
- 当你部署一个带有 **B 费用**的异象时，必须**指定若干友方异象进行献祭**。
- 被献祭异象根据其**丰饶等级**产生鲜血（默认丰饶为 1）。
- 支付完部署费用后，**剩余鲜血保留到回合结束**，之后清空。
- **只能在部署需要鲜血的异象时进行献祭**。
- 默认规则：冥刻异象默认具有 **献祭1、丰饶1**。
- **献祭属于"消灭"**，会触发亡语；移除、返回手牌、洗入卡组均不触发。

---

## 四、统一指向模块（Targeting Architecture）

> **核心设计原则**：所有需要玩家"用手指点选"的操作（部署位置、策略目标、场上主动技能、视野/高频攻击预设），**全部通过 `TargetingRequest` + `process_targeting_request()` 统一处理**。GUI 中不再有任何 if/else 分支处理不同卡牌类型的指向逻辑。

### 4.1 核心数据结构

```python
# tards/targeting.py
@dataclass
class TargetingRequest:
    valid_targets: List[Any]       # 可被选中的目标列表
    count: int = 1                  # 需要选择的数量
    allow_repeat: bool = False      # 是否允许重复选择同一目标
    prompt: str = "请选择目标"       # 提示文字
    on_confirm: Callable[[List[Any]], None]  # 确认回调
    on_cancel: Callable[[], None]             # 取消回调
```

`TargetPicker`（在 `gui_client.py` 内）负责收集玩家点击的目标，满足 `count` 后自动触发 `on_confirm`。

### 4.2 指向流程

以**部署一个需要额外目标的异象**为例（如"部署：使一个异象获得恐惧"）：

```
玩家点击手牌
  → _on_hand_card_click()
    → 检查 card.deploy_targets_fn（是否需要额外指向）
      → 需要：构造 TargetingRequest(valid_targets=敌方异象, count=1)
        → process_targeting_request(req)
          → 进入指向模式，高亮 valid_targets
            → 玩家点击目标
              → TargetPicker.select(target) → count 已满足
                → on_confirm([target]) 被调用
                  → _on_deploy_extra_selected(extra_target)
                    → 构造第二个 TargetingRequest(valid_targets=部署位置, count=1)
                      → process_targeting_request(req2)
                        → 玩家点击位置
                          → on_confirm([position])
                            → _submit_play(serial, card, position, extra_targets=[extra_target])
```

### 4.3 目标类型约定

| 目标类型 | 数据类型 | 来源 | 渲染方式 |
|---------|---------|------|---------|
| 棋盘位置 | `tuple(r, c)` | `board.get_empty_positions()` | Canvas 上绘制 oval（椭圆）高亮 |
| 场上异象 | `Minion` 对象 | `board.get_all_minions()` | Canvas 上给异象矩形加边框 |
| 玩家 | `Player` 对象 | `[game.p1, game.p2]` | 信息面板中的玩家标签高亮 |
| 无目标 | `None` | `target_none` | 无需高亮 |

### 4.4 extra_targets 传递约定

所有效果函数统一使用以下签名：

```python
# MinionCard.special 的签名
special_fn(minion, player, game, extras=None)

# Strategy.effect_fn 的签名（通过 inspect 自适应）
effect_fn(player, target, game, extras=None)
```

- **第一个选中的目标** = `target`（主目标）
- **后续选中的目标** = `extra_targets` 列表（按选择顺序）

```python
# 部署时：使一个异象获得恐惧
# target = 部署位置 (r, c)
# extras[0] = 被选中的敌方异象
```

### 4.5 视野与高频攻击的预设目标

- **视野 X**：出牌阶段通过 `set_vision` action 选择攻击列，`minion._resolve_target_col = col`。结算阶段该异象优先攻击该列。
- **高频/三重打击**：出牌阶段通过 `set_attack_targets` action 预设多个攻击目标，`minion._pending_attack_targets = [target1, target2, ...]`。结算阶段按顺序消耗：第 1 次攻击取第 0 个，第 2 次取第 1 个……
- 预设目标耗尽后攻击英雄。
- **潜水/潜行异象**：行动阶段（出牌阶段）**可见且可选中**（策略可以指向它们）；结算阶段**攻击自动落空**。

---

## 五、双层细胞架构（Board 底层）

`Board` 使用双层细胞模型管理棋盘状态：

| 层 | 属性名 | 存储内容 | 行为 |
|---|--------|---------|------|
| 主层 | `minion_place: dict[(r,c) → Minion]` | 场上正常异象 | 碰撞检测、移动、攻击 |
| 底层 | `cell_underlay: dict[(r,c) → Minion]` | 藤蔓、漂浮物 | 依附于主层异象 |

### 5.1 藤蔓（Vine）
- 只能部署在**友方异象**的格子上。
- 藤蔓与宿主共享同一个 `(r, c)`，但藤蔓存储在 `cell_underlay`，宿主在 `minion_place`。
- **替伤机制**：当宿主受到攻击伤害时，`take_damage()` 自动将伤害路由给 `vine_overlay`（如果存在且存活）。
- **共生死亡**：宿主死亡时，藤蔓同步死亡（`minion_death()` 中处理）。
- 玩家只能点击宿主，**不能直接选中藤蔓**。

### 5.2 漂浮物（Float）
- 存储在 `cell_underlay`。
- 允许在其格子上**再部署一个异象**（无视通常的碰撞检测）。
- 受到的伤害由上方异象承受。
- 上方异象死亡/离场后，漂浮物回归 `minion_place` 原位。

### 5.3 跨方移动
- `Board.move_minion(minion, new_pos, allow_cross_side=False)`
- 当 `allow_cross_side=True` 时，允许异象移动到敌方行区域（如"将敌方异象移到友方区域"类效果）。
- `auto_effects.move_enemy_to_friendly()` 会先改变 `minion.owner`，再调用 `move_minion(..., allow_cross_side=True)`。

---

## 六、已实现的核心机制（含代码位置）

### 6.1 开发（Discover）
- 代码入口：`Game.develop_card()`。
- 网络同步：`NetworkDuel._make_discover_provider()`。
- GUI 弹窗：`DiscoverDialog`。
- 离散 3 级沉浸度增益：开发成功后 `player.health_change(1)`。

### 6.2 恐惧（Fear）
- 代码：`Minion.apply_fear()` / `remove_fear()`。
- 视觉：恐惧异象带**紫色粗边框**（`#9c27b0`，3px）。

### 6.3 成长（Evolve）
- 结算阶段触发：`成长 X` 每回合 -1，到 0 时调用 `m.evolve(game)`。
- 进化逻辑：`Minion.evolve()` → `Game.transform_minion()`。

### 6.4 献祭（Sacrifice）
- GUI：`SacrificeDialog`。
- 引擎：`Game.action_phase()` 处理 sacrifices，临时预加鲜血。

### 6.5 阴谋（Conspiracy）与 Bluff
- 激活流程：`BluffDialog` → 目标选择 → `active_conspiracies`。
- 事件监听：`Game.emit_event()` 遍历 `active_conspiracies`。
- **condition_fn 全部 TODO**：当前所有阴谋卡只有框架，没有实际触发条件。

### 6.6 回响（Echo）
- 异象回响：生成 2T/1/1 复制体，`echo_level - 1`。
- 策略回响：`copy.copy` 后 `echo_level - 1`。

### 6.7 效果队列（EffectQueue）
- `queue(name, fn)` — 入队，不在结算中时立即处理。
- `resolve(name, fn)` — 执行主效果 + 处理所有连锁。
- **当前模型为 FIFO 队列，非堆栈**。无法支持 Counterspell 式的"响应并取消原效果"。

### 6.8 异象死亡与亡语
- `Minion.minion_death()` 加入 `EffectQueue`：先移除棋盘 → 派发 `EVENT_DEATH` → 触发亡语。
- 亡语签名：`fn(minion, player, board)`。

### 6.9 雕像拼装（Statue Fusion）
- 5 对雕像（节肢/水肺/尖牙/丰饶/长翅），每组包含一个 `statue_top`（座首）和一个 `statue_bottom`（底座）。
- 检测：`Game._check_statue_pair()` 在 `EVENT_DEPLOY` 后扫描配对。
- 执行：`Game._resolve_statue_fusions()` 在结算阶段结束和回合结束时触发。
- 配对相同 → 本回合结束生效；配对不同 → 下回合结束生效。
- 效果函数在 `underworld_effects.py` 中手动实现。

### 6.10 部署钩子框架（Deploy Hooks）
- `Game.deploy_hooks: List[Callable[[Minion], None]]`
- 异象通过 `Minion.register_deploy_hook(game, fn)` 注册全局部署监听。
- 钩子在新异象部署时自动触发。
- 异象死亡时自动清理自己的钩子。

### 6.11 自动化事件框架
- 事件常量：`EVENT_TURN_START`、`EVENT_TURN_END`、`EVENT_PHASE_START`、`EVENT_PHASE_END`。
- `Game._trigger_auto_effects()` 遍历场上异象、手牌、玩家，触发 `on_turn_start/end`、`on_phase_start/end` 回调。
- 回调签名：`fn(game, event_data, source)`。

### 6.12 轻量"取消"机制
- **设计原则**：不改 EffectQueue FIFO 模型，在状态变更前拦截。
- **伤害替换**：`Game.register_damage_replacement(filter_fn, replace_fn, once=True)`
  - 在 `Minion.take_damage()` 和 `Player.health_change(-delta)` 的**最开头**调用。
  - `replace_fn(damage) → int`，返回 0 表示完全取消。
  - 多个替换按注册顺序依次应用。
- **指向保护**：`Game.protect_target(filter_fn, once=True)`
  - 在 `Strategy.effect()` 执行 `effect_fn` **之前**检查。
  - 被保护时，卡牌正常消耗（进弃牌堆），但效果不执行。
- **限制**：
  - 无法取消无目标的策略（如"抽两张牌"）。
  - 无法做真正的 Counterspell（堆栈响应）。
  - 持续型保护（`once=False`）在回合结束时由 `clear_protections()` 清理。

### 6.13 通用词条实现状态（完整清单）

| 词条 | 实现状态 | 实现细节 |
|------|---------|----------|
| **协同** | ✅ | 部署合法性检查 |
| **独行** | ✅ | 同列友方异象存在时不可部署 |
| **水生/两栖** | ✅ | 水路/陆地部署限制 |
| **高地** | ✅ | `c==0` 部署限制 |
| **亡语** | ✅ | 死亡时触发 `EffectQueue` |
| **丰饶** | ✅ | 献祭时产血数量 |
| **献祭** | ✅ | B费用异象部署时强制献祭 |
| **恐惧** | ✅ | 清除通用词条并加紫色边框 |
| **冰冻** | ✅ | 受战斗伤害削层，归零翻倍；结算阶段结束衰减 |
| **眩晕** | ✅ | 结算阶段无法攻击；结算阶段结束衰减 |
| **休眠** | ✅ | 非迅捷异象部署时默认获得休眠1；结算阶段无法攻击；结算阶段结束衰减 |
| **坚韧** | ✅ | 受到伤害 `-坚韧值` |
| **脆弱** | ✅ | 并入坚韧逻辑：坚韧为0时脆弱使受伤+1（负数坚韧） |
| **重甲** | ✅ | 等价于坚韧 |
| **迅捷** | ✅ | 部署当回合即可攻击 |
| **尖刺** | ✅ | 受战斗伤害后反弹 |
| **高频** | ✅ | 每回合攻击多次，每次先攻-1 |
| **三重打击** | ✅ | 等价于 `高频3` |
| **先攻** | ✅ | 决定攻击顺序与同时攻击分组 |
| **横扫** | ✅ | 对左右相邻列造成伤害 |
| **串击/穿刺/穿透** | ✅ | 对同列所有敌方异象造成伤害 |
| **空袭** | ✅ | 若无敌方防空拦截，直接攻击对手英雄 |
| **防空** | ✅ | 拦截空袭异象；本列敌方异象失去串击/穿刺/穿透 |
| **潜水/潜行** | ✅ | 行动阶段可见可选中；结算阶段攻击自动落空；视野不可看破 |
| **绝缘** | ✅ | 策略卡无法直接以对方绝缘异象为初始目标；AOE策略需手动检查 `game.is_immune()` |
| **视野X** | ✅ | 预设攻击目标列；结算阶段优先攻击该列 |
| **破甲X** | ✅ | 攻击时无视目标X层坚韧 |
| **成长** | ✅ | 回合结束计数器-1，到0时进化；支持罗马数字解析 |
| **回响** | ✅ | 部署/打出后生成弱化复制体或返回手牌 |
| **藤蔓** | ✅ | 双层细胞架构；替伤；共生死亡 |
| **漂浮物** | ✅ | 允许叠放；伤害由上方异象承受 |
| **护盾** | ❌ | 未实现（曾讨论后搁置） |
| **嘲讽** | ❌ | 未实现 |
| **圣盾/护盾** | ❌ | 未实现 |
| **战吼** | ❌ | 未区分"战吼"与"部署时"概念 |
| **沉默** | ❌ | 未实现 |
| **吸血** | ❌ | 未实现 |
| **连击** | ❌ | GUI 中提及但无实际关键词定义 |
| **超杀** | ❌ | 未实现 |
| **冻结**（区别于冰冻）| ❌ | 未实现 |
| **无法攻击** | ❌ | 未作为独立关键词实现 |
| **魔免/法术免疫** | ❌ | 未实现 |
| **复生** | ❌ | 未实现 |
| **剧毒** | ❌ | 未实现 |
| **激励** | ❌ | 无英雄技能系统 |

---

## 七、沉浸度增益实现状态

| 卡包 | 1级 | 2级 | 3级 |
|------|-----|-----|-----|
| **离散** | 开放矿物兑换；手牌上限 +1 | T槽上限 8，C槽上限 4 | 开发时 +1HP |
| **冥刻** | 开局 6 张松鼠牌堆 | 每回合 1T 兑换松鼠（一次） | HP≤20 给「烛烟」；HP≤10 给「大团烛烟」 |
| **血契** | 抽牌阶段 -1HP、+1S | 受到单次 ≥3 伤害时，+3S | 开局洗入 6 张「时刻」 |

---

## 八、网络对战协议（精确 Schema）

### 8.1 连接层
- `GameConnection` 基于原始 TCP socket。
- 消息格式：**单行 JSON + `\n`**。

### 8.2 握手流程
1. `HELLO`：`{"type":"HELLO","name":"玩家A","deck":["火把","萤石",...],"immersion_points":{"离散":2,"冥刻":1}}`
   - `deck` 为完整的 40 张有序卡名列表。
2. Host 发送 `START`：`{"type":"START","first_player_name":"玩家A","seed":123456789}`

### 8.3 行动中继
- `ACTION`：`{"type":"ACTION","action":{...}}`
- `play`：`{"type":"play","serial":1,"target":{"pos":[3,2]},"bluff":false,"sacrifices":[{"pos":[4,2]}],"extra_targets":[{"pos":[2,2]}]}`
  - `extra_targets` 为额外指向目标序列化结果（位置或 player_side）。
- `set_vision`：`{"type":"set_vision","pos":[3,2],"col":4,"targets":[{"pos":[1,2]}]}`
- `set_attack_targets`：`{"type":"set_attack_targets","pos":[3,2],"targets":[{"pos":[1,2]},{"player_side":0}]}`

### 8.4 Discover 同步
- `DISCOVER`：`{"type":"DISCOVER","names":["火把","萤石","信标"],"chosen":"萤石"}`

### 8.5 已知限制
- 无心跳机制，断线只能通过 socket 异常检测。
- 无断线重连。

---

## 九、GUI 客户端架构（gui_client.py）

### 9.1 整体结构
- `TardsApp` — 根应用，管理帧切换
- `MenuFrame` / `DeckBuilderFrame` / `LobbyFrame` / `BattleFrame`
- `LocalDuel` / `NetworkDuel`

### 9.2 对战界面
- 棋盘：500×500 Canvas，5×5 格子。
- 异象渲染：蓝色（己方）、红色（敌方），边框颜色根据状态变化。
- 手牌区：横向 Canvas + Scrollbar。
- 信息面板：HP、T/C/B/S、手牌/卡组/弃牌/阴谋数量。
- 弹窗：`BluffDialog`、`SacrificeDialog`、`DiscoverDialog`。

### 9.3 统一指向交互
- 所有指向操作通过 `process_targeting_request(req)` 进入指向模式。
- `_on_canvas_click()` 在指向模式下将点击委托给 `TargetPicker.select()`。
- 支持多阶段嵌套：部署位置 → 额外目标 → 确认。
- 支持多选和重复选择（通过 `count` 和 `allow_repeat` 控制）。

### 9.4 AI（本地测试）
- `LocalDuel._ai_action()` 是简单随机 AI。
- 优先献祭丰饶值低的友方异象。

---

## 十、卡包翻译器（translate_packs.py）

### 10.1 输入输出
- 输入：`.txt` 文件（离散/冥刻/血契卡包）
- 输出：`card_pools/*.py`

### 10.2 自动生成效果
- **抽牌**：`try_generate_draw_effect()`
- **伤害**：`try_generate_damage_effect()`
- **治疗**：`try_generate_heal_effect()`
- **赋予关键词**：`try_generate_keyword_effect()` — 支持恐惧、冰冻、眩晕、迅捷、坚韧、先攻等
- **开发（Discover）**：`try_generate_develop_effect()`
- **移动/交换/返回手牌**：`try_generate_move_effect()`
- **献祭变形**：`try_generate_sacrifice_transform_effect()`
- **目标推导**：`try_generate_targets_fn()` / `try_generate_deploy_targets_fn()`

### 10.3 未覆盖的复杂效果（需人工实现）
- 消灭、沉默、变形、复制、取消、弃置、洗入牌库、从牌库移除顶牌、召唤/加入战场、抉择、指向/记录、随机、对战、buff/debuff、额外资源槽、回响升级、免疫消灭、恐惧清除、动态亡语附着……

---

## 十一、人工效果编写规范（effect_utils.py + effect_decorator.py）

### 11.1 标准工具库（EffectUtils）

所有人工编写的 `special_fn` / `effect_fn` **必须优先使用** `card_pools/effect_utils.py` 中的标准函数，禁止自行实现底层逻辑。

| 函数 | 用途 |
|------|------|
| `return_minion_to_hand(minion, game)` | 将场上异象返回手牌（满则弃置） |
| `summon_token(game, name, owner, position, ...)` | 在指定位置召唤 token 异象 |
| `deal_damage_to_minion(target, damage, source, game)` | 对异象造成标准伤害（自动触发所有替换/护盾/坚韧） |
| `create_echo_card(source_card, echo_level)` | 创建回响版本卡牌（2T/1/1） |
| `is_enemy(m1, m2)` | 判断是否为敌对关系 |
| `get_adjacent_positions(position, board)` | 获取上下左右相邻位置 |
| `get_frontmost_enemy(column, owner, board, attacker)` | 获取指定列最靠前敌方异象 |
| `transform_minion_to(minion, target_name, game)` | 将异象变形为指定名称新异象 |
| `copy_card_to_hand(source_card, owner, game, cost_modifier)` | 将卡牌复制加入手牌 |
| `add_deathrattle(minion, deathrattle_fn)` | 动态添加亡语效果 |

### 11.2 格式校验装饰器（@special）

```python
from card_pools.effect_decorator import special

@special
def _xxx_special(minion, player, game, extras=None):
    """文档字符串：描述卡牌效果。"""
    ...
```

**自动检查（游戏启动时执行）：**
- 参数必须包含 `minion`、`player`、`game`、`extras`
- `extras` 必须有默认值 `=None`
- 函数必须有文档字符串（否则警告）

**运行时自动行为：**
- 检查 `minion.is_alive()`，死亡时跳过并打印警告
- 打印 `[效果触发] 函数名 (异象名)` 日志

### 11.3 四条铁律

1. **状态变量必须带卡牌前缀**：`_songshuqiu_triggered`，禁止用 `_triggered` / `_flag`。
2. **回调函数必须用默认参数绑定**：`def on_damage(m=minion, g=game):`，禁止裸闭包。
3. **操作前检查异象是否存活**：`if not minion.is_alive(): return`。
4. **每个关键行为必须打印日志**：`print(f" {minion.name} 移动至 {new_pos}")`。

### 11.4 协作开发流程

```
1. 判断触发时机（部署/回合开始/回合结束/受伤/亡语）
2. python tools/gen_effect.py "卡牌名(铁)" "描述" --type <时机> --file <卡包>
3. 将骨架代码粘贴到 card_pools/xxx_effects.py
4. 使用 effect_utils.py 中的工具填空实现
5. 加上 @special 装饰器
6. 更新 SPECIAL_MAP
7. 运行 python demo.py 测试
```

---

## 十二、最近修复的关键 Bug（含根因分析）

| # | Bug 描述 | 根因 | 修复位置 |
|---|----------|------|----------|
| 1 | **献祭弹窗死锁** | 在 tkinter 回调里调用 `Event().wait()` 阻塞主线程 | 将献祭选择提前到 `_on_hand_card_click()`，用模态 `SacrificeDialog` + 回调传值 |
| 2 | **B 费用异象无法出牌** | `card_can_play` 在 `request_sacrifice` 之前检查费用 | 临时预加鲜血，出牌后回滚 |
| 3 | **冰冻/眩晕层数不减** | 直接修改 `self.keywords`，但 `recalculate()` 会覆盖 | 改为从源头字典递减后 `recalculate()` |
| 4 | **平局无结束提示** | `game_over_callback` 只在 `winner` 非 None 时触发 | 改为 `game.game_over` 时触发 |
| 5 | **NetworkDuel.close 死锁** | `close()` 没设置 `_discover_event` | 补充 `self._discover_event.set()` |
| 6 | **T槽增长异常** | 离散 2 级时逻辑先越界再压回 | 直接 `max_t = 8 if discrete_pts >= 2 else 10` |
| 7 | **统一指向模块重构** | GUI 中各种 if/else 分支处理不同指向逻辑，维护困难 | 全部替换为 `TargetingRequest` + `process_targeting_request()` |
| 8 | **extra_targets 标准化** | Strategy 和 MinionCard 的 effect 签名不一致 | 统一为 `(p, t, g, extras=None)`，通过 inspect 兼容旧代码 |
| 9 | **藤蔓替伤失效** | 藤蔓 overlay 未在 `take_damage()` 中正确路由 | 在坚韧计算前优先检查 `vine_overlay` |
| 10 | **潜水可见性矛盾** | 潜水异象在行动阶段不可选中，导致策略无法指向 | 改为行动阶段可见可选中，结算阶段攻击落空 |
| 11 | **献祭后鲜血未正确扣除** | 临时鲜血注入后，`card_can_play` 失败没有回滚 | 在 finally 逻辑中恢复 `sacrifice_chooser` 和 `b_point` |
| 12 | **AI 使用错误卡组** | 本地测试 AI 使用 `make_gui_deck` 而非玩家选择的卡组 | 改为 `deck.to_game_deck(None)` 并同步沉浸度 |
| 13 | **额外目标序列化缺失** | `net_protocol.py` 未处理 `extra_targets` 字段 | 补充 `extra_targets` 的序列化/反序列化 |
| 14 | **attack_target 中 event 为 None 崩溃** | `game.emit_event(EVENT_BEFORE_ATTACK)` 在 `game_over=True` 时返回 `None`，后续直接 `event.get(...)` | `cards.py:attack_target()` 添加 `if event is None: return` 防护 |
| 15 | **underworld_effects.py 变量/参数错误** | 多处 `MinionCard(cost=0, targets="none")` 传错类型；`Minion(card=...)` 参数名错误；`player.minions_on_board` 属性不存在 | 统一改用 `summon_token()` 和 `Cost()`；补充缺失的 `effect_utils` 导入 |

---

## 十三、待实现 / TODO 汇总

### 13.1 引擎层
- [ ] **堆栈响应机制**（高优先级）：将 `EffectQueue` 从 FIFO 队列改为支持 `push_stack()` / `resolve_stack()` 的堆栈模型，实现真正的 Counterspell 式"取消原效果"。
- [ ] **结束阶段（End Phase）**：当前 `run_turn()` 只有抽牌→出牌→结算，结算后直接 `EVENT_TURN_END`，无独立结束阶段。部分卡牌效果（如"回合结束时"）在结算阶段末尾处理。
- [x] **抽取（Draw-trigger）**：~~"抽取：..." 效果在卡被从卡组抽入手牌时触发。`EVENT_DRAW` 已发出但几乎没有响应逻辑。~~ **已实现**：通过 `_trigger_auto_effects` + `_EVENT_SPECIFIC_TARGET` 精确命中被抽卡牌，走 `card.on_drawn` 回调。工具：`set_draw_trigger(card, callback)` / `remove_draw_trigger(card)`。
- [ ] **Tag 系统**（阻塞大量卡牌）：friendly/hostile/neutral/creature/nonliving/hell/fairy 等标签尚未实现，阻塞耕殖/砍伐/掘进等效果。
- [ ] **效果来源追踪**：区分"被策略效果消灭" vs "被战斗消灭"（亡语判断需要）。
- [ ] **英雄技能系统**：完全缺失。
- [ ] **牌库抽空疲劳**：`draw_fail` 计数器已存在，但需确认逻辑完整性。
- [ ] **`Player.minions_on_board` 属性缺失**：`auto_effects.py`（`move_enemy_to_friendly`）和 `underworld_effects.py` 都假设该属性存在，但 `Player.__init__` 从未初始化它。需要补充 `self.minions_on_board = []` 并在异象部署/死亡/移动时同步维护。

### 13.2 卡牌效果层（高优先级）
- `translate_packs.py` 生成的 416 张卡牌中，绝大多数 `special_fn=None` 或 `effect_fn=None`。
- 当前人工实现进度（详见 `COMPLEX_CARDS_INDEX.md`）：
  - 离散包：~20 张已实现（矿车、北极熊、恼鬼、流髑、尸壳、卫道士、蜘蛛、蠹虫、橡树苗、岩浆艇、马、炽足兽、潮涌核心、活塞飞艇等），~90 张 TODO
  - 血契包：5 张已实现（保卫者、巫毒娃娃、天籁人偶、溴化银、亡灵），~55 张 TODO
  - 冥刻包：5 张已实现（烛烟、大团烛烟、猫、白鼬、弱狼），~150 张 TODO
- 需要人工实现的典型效果：消灭、沉默、变形、复制、取消、弃置、洗入牌库、从牌库移除顶牌、召唤/加入战场、抉择、随机选择、即时对战、buff/debuff、额外资源槽、回响升级、免疫消灭、恐惧清除、动态亡语附着……
- **建议**：复杂效果集中到 `card_pools/xxx_effects.py` 手动实现，通过 `SPECIAL_MAP` 映射到生成的 `xxx.py` 中。

### 13.3 阴谋系统
- [ ] **condition_fn 全部 TODO**：所有阴谋卡只有框架，没有实际触发条件。
- 需要实现的常见条件：受到战斗伤害时、打出策略时、异象被消灭时、回合开始时……

### 13.4 场上主动技能
- [ ] "出牌阶段限一次" 类型效果尚未实现。架构已支持（通过 `TargetingRequest`），但无卡牌定义 `active_effect_fn`。

### 13.5 网络层
- [ ] 断线重连 / 心跳机制缺失。
- [ ] `set_attack_targets` 多目标序列化需完整对局测试验证。

### 13.6 GUI 层
- [ ] 弃牌堆 / 卡组详情查看
- [ ] 更丰富的状态提示（光环来源、先攻等级数值）
- [ ] 悔棋 / 撤销（仅限本地测试）
- [ ] 对战日志导出
- [ ] 目标高亮视觉反馈未在 live Tkinter 中充分测试

### 13.7 未实现的关键词
- 护盾、嘲讽、圣盾、战吼、沉默、吸血、连击、超杀、冻结（区别于冰冻）、无法攻击、魔免、复生、剧毒、激励、发现（区别于开发）

---

## 十五、本轮对话（2026-04-17）核心交付

### 15.1 架构/引擎改动
1. **Rule 3 强化**：`game.py` / `player.py` 中所有卡牌名字硬编码（信标、流浪商人、附魔台、耕殖）已全部移除，迁移为 event-driven 实现。
2. **`_trigger_auto_effects` 扩展**：支持 `_EVENT_SPECIFIC_TARGET`，使 `EVENT_DRAW` 等事件可精确命中特定目标，而非遍历全部候选。
3. **献祭流程完善**：
   - 献祭次数限制（`_sacrifice_remaining`）
   - 非变形献祭现在触发 `minion_death()`（正确触发亡语）
   - 献祭免疫标记（`_immune_to_sacrifice`）
   - 冥刻异象注册时自动注入 `"献祭":1`、`"丰饶":1`
4. **恐惧机制**：`board.get_front_minion` 过滤 `_fear_active` 异象。

### 15.2 effect_utils.py 扩展（新增 ~70 函数，11 个分区）
- **延迟效果**：`delay_to_next_turn`、`delay_to_phase_start`、`delay_to_turn_end`
- **状态追踪**：`track_stat`、`increment_stat`、`get_stat`、`track_per_turn`
- **战斗伤害增强/替换**：`augment_combat_damage`、`replace_combat_damage`
- **全局事件钩子**：`on_deploy_global`、`on_sacrifice_global`、`on_draw_global`、`on_turn_start_global` 等
- **批量/AOE**：`damage_all_enemies`、`heal_all_friendly`、`buff_all_friendly`、`destroy_all_enemies`、`silence_all_enemies`
- **更多目标选择器**：`weakest_enemy_minion`、`strongest_enemy_minion`、`nearest_enemy_minion`、`adjacent_friendly_minions` 等
- **条件与组合**：`conditional_effect`、`chain_effects`、`repeat_effect`
- **临时效果**：`give_temp_keyword_until_turn_end`、`give_temp_buff_until_turn_end`、`inject_temporary_deathrattle`
- **牌库操作增强**：`reveal_top_of_deck`、`put_on_top_of_deck`、`put_on_bottom_of_deck`、`search_deck`
- **高级事件包装**：`on_after_deploy`、`on_card_played`、`on_sacrifice`、`on_turn_start`、`on_turn_end`、`on_discarded`、`on_milled`
- **"如可能"条件执行**：`if_possible_then`、`if_resource_then`、`if_has_cards_then`、`if_has_friendly_minions_then`、`if_has_enemy_minions_then`

### 15.3 新实现卡牌
- **blood_effects.py**：保卫者、巫毒娃娃、天籁人偶、溴化银、亡灵（5张）
- **underworld_effects.py**：烛烟、大团烛烟、猫(铁)、白鼬(铁)、弱狼(铁)（5张）+ 雕像座首效果

### 15.4 新文档
- `COMPLEX_CARDS_INDEX.md`：~90 离散、~60 血契、~75 冥刻 TODO 卡，按 11 类困难度分类，标注阻塞架构缺口。

### 15.5 已知遗留问题
- `Player.minions_on_board` 属性未在 `Player.__init__` 中初始化，但 `auto_effects.py` 和 `underworld_effects.py` 都有依赖。
- Tag 系统缺失（friendly/hostile/neutral/creature/nonliving/hell/fairy）。
- 状态追踪框架的基础工具已提供，但尚未与 engine 深度集成（如自动每回合清零）。
- 延迟效果工具基于 EventBus 实现，尚未验证跨多回合的复杂链式延迟。

---

---

## 十四、开发注意事项（保命指南）

1. **不要在 tkinter 主线程回调里调用 `threading.Event().wait()`**
   - 头号卡死原因。所有模态弹窗用 `grab_set()` + 回调函数模式。

2. **修改 `keywords` 时必须修改源头字典**
   - `self.keywords` 是 `recalculate()` 的产物。持久状态写入 `base_keywords` / `perm_keywords` / `temp_keywords`，然后 `recalculate()`。

3. **C 点操作请使用 `player.c_point_change(delta)`**
   - 直接赋值可能突破 `c_point_max` 上限。

4. **网络 action 中的 sacrifices 反序列化可能返回 `tuple`**
   - `Game.action_phase()` 已做过滤：`valid_sacs = [m for m in sacrifices if hasattr(m, "keywords")]`

5. **重新运行 `translate_packs.py` 会覆盖 `card_pools/*.py`**
   - 手动实现的效果必须放在 `xxx_effects.py` + `SPECIAL_MAP` 中，或单独模块。

6. **`make_gui_deck` 仅用于快速演示**
   - 网络对战和本地测试都使用 `deck.to_game_deck(None)`。

7. **所有指向操作统一走 `TargetingRequest`**
   - 禁止在 GUI 中新增 if/else 分支处理不同卡牌的指向逻辑。

8. **人工效果必须使用 `@special` 装饰器和 `effect_utils.py`**
   - 这是团队协作的格式契约。

---

## 十五、文件速查表

| 文件 | 职责 |
|------|------|
| `gui_client.py` | Tkinter GUI、LocalDuel、NetworkDuel 对接、统一指向交互 |
| `tards/game.py` | `Game` 主引擎、回合流程、战斗结算、轻量取消机制、雕像融合 |
| `tards/player.py` | `Player` 状态、资源、手牌操作、沉浸度增益 |
| `tards/cards.py` | `Card` 类型体系、`Minion` 战场逻辑、亡语、藤蔓替伤 |
| `tards/board.py` | 5×5 棋盘、双层细胞、部署规则、跨方移动 |
| `tards/effect_queue.py` | `EffectQueue` 连锁控制（FIFO 队列） |
| `tards/targeting.py` | `TargetingRequest`、`TargetPicker`、攻击候选、部署额外目标 |
| `tards/auto_effects.py` | 自动化效果辅助：移动、交换、返回手牌 |
| `tards/net_game.py` | `NetworkDuel` 网络对战同步 |
| `tards/net_protocol.py` | TCP JSON 协议、序列化/反序列化 |
| `tards/card_db.py` | `CardDefinition`、`CardRegistry`、卡包枚举 |
| `tards/cost.py` | `Cost` 类、费用解析与支付 |
| `tards/targets.py` | 预设目标选择器 |
| `tards/constants.py` | 事件常量、`GENERAL_KEYWORDS` |
| `translate_packs.py` | `.txt` → `card_pools/*.py` 翻译器 |
| `card_pools/discrete.py` | 离散卡包 182 张卡牌定义 |
| `card_pools/underworld.py` | 冥刻卡包 164 张卡牌定义 |
| `card_pools/blood.py` | 血契卡包 70 张卡牌定义 |
| `card_pools/underworld_effects.py` | 冥刻卡包手动效果实现（雕像 + 5 张特殊卡） |
| `card_pools/effect_utils.py` | **标准效果工具库**（人工编写必须使用） |
| `card_pools/effect_decorator.py` | **格式校验装饰器 `@special`** |
| `decks/*.json` | 玩家保存的卡组定义 |
| `TARDS_GAME_REFERENCE.md` | 本文档 |
| `Tards规则书1.0.docx` | 原始规则书 |
| `血契卡包.txt` / `离散卡包.txt` / `冥刻卡包.txt` | 卡包源文本（翻译器输入） |

---

*文档版本：2026-04-17*  
*涵盖规则书 v1.0 + 离散卡包 + 冥刻卡包 v1.0 + 血契卡包 + 程序实现全状态 + 统一指向模块 + 轻量取消机制 + 人工效果协作规范*
