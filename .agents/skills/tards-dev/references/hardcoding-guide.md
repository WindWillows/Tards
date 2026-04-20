# 禁止硬编码 — 改造指南

> 本文件是 AGENTS.md Rule 3 的详细展开版，包含具体案例和改造方案。

## 什么是硬编码

在核心游戏引擎（`game.py`, `player.py`, `board.py`, `cards.py`）中：
- ❌ 检查 `if card.name == "XXX": ...`
- ❌ 检查 `if player._xxx_active: ...`（某张卡牌的私有状态）
- ❌ 在通用流程中写死某张卡的特殊行为

核心引擎只应包含**通用机制**（事件、回调、状态标志）。具体卡牌行为必须在卡牌自己的 `effect_fn` / `special_fn` / `on_turn_start` / `on_turn_end` 或事件监听器中实现。

## 常见违规案例与正确改造

### 案例 1：抽牌阶段检查特定卡牌

❌ **错误**：
```python
# game.py draw_phase 中
for m in board.minion_place.values():
    if m.name == "流浪商人":
        # 特殊处理...
```

✅ **正确**：
```python
# game.py 中提供通用回调列表
class Player:
    _on_draw_callbacks: List[Callable] = []

# 流浪商人的 special_fn 中注册回调
@special
def _liulangshangren_special(minion, player, game, extras=None):
    def on_draw(g, event_data, source):
        # 取消抽牌，改为开发...
    player._on_draw_callbacks.append(on_draw)
```

### 案例 2：开发流程中检查特定状态

❌ **错误**：
```python
# game.py develop_card 中
if player._enchanting_table_active:
    # 再开发一张附魔书
```

✅ **正确**：
```python
# game.py 中遍历通用回调
for cb in player._on_develop_callbacks:
    cb(game, player)

# 附魔台的 strategy_fn 中注册
@strategy
def _fumota_strategy(player, target, game, extras=None):
    player._on_develop_callbacks.append(lambda g, p: g.develop_card(p, [...]))
```

### 案例 3：费用计算中检查特定卡牌

❌ **错误**：
```python
# player.py _get_play_cost 中
if card.name == "耕殖":
    cost.t -= player._gengzhi_count
```

✅ **正确**：
```python
# player.py 中提供通用费用修饰器列表
class Player:
    _cost_modifiers: List[Callable[[Card, Cost], None]] = []

# 耕殖的 strategy_fn 中注册修饰器
@strategy
def _gengzhi_strategy(player, target, game, extras=None):
    def discount(card, cost):
        if getattr(card, 'name', '') == '耕殖':  # 卡牌自己的文件中检查名字 ✅
            cost.t = max(0, cost.t - player._gengzhi_count)
    player._cost_modifiers.append(discount)
```

> 注意：在**卡牌自己的 effect_fn 中**检查 `card.name` 是允许的。禁止的是在**核心引擎**中检查。

### 案例 4：通用事件中检查特定单位

❌ **错误**：
```python
# game.py 某个通用事件中
if m.name == "信标":
    m.owner.develop_card(...)
```

✅ **正确**：
```python
# 信标的 special_fn 中注册 EventBus 监听器
@special
def _xinbiao_special(minion, player, game, extras=None):
    def on_t_changed(g, event_data, source):
        # 当 T 槽变化时触发开发
    add_event_listener(game, EVENT_T_CHANGED, on_t_changed)
```

## 状态变量命名规范

所有由卡牌效果设置的 player/game 级状态变量，**必须带卡牌前缀**，避免冲突：

- ✅ `_songshuqiu_triggered`
- ✅ `_fumota_active`
- ❌ `_triggered`
- ❌ `_flag`
- ❌ `_active`

## 回调闭包绑定规范

使用默认参数绑定，禁止裸闭包捕获循环变量：

- ✅ `def on_damage(m=minion, g=game):`
- ❌ `def on_damage():`（裸闭包，m/g 可能在回调执行时已失效）

## 扩展通用机制的优先级

当某张卡需要一个引擎不支持的机制时，按以下优先级处理：

1. **能否用现有事件实现？** → 注册 EventBus 监听器
2. **能否用现有回调列表实现？** → 追加到 `Player._on_xxx_callbacks`
3. **能否用状态标志实现？** → 添加 `Player._skip_next_draw` 等通用标志
4. **以上都不行？** → 在核心引擎中**添加新的通用机制**（新事件类型 / 新回调列表 / 新状态标志），然后让卡牌使用它

**绝不**：在核心引擎中硬编码该卡牌的名字或特殊分支。
