# 效果实现模板

## 卡牌描述用语速查

| 描述用语 | 含义 | 实现方式 |
|---------|------|---------|
| **"具有"** | 一般为**光环效果（aura）**，动态实时更新 | `provide_aura_attack/keywords/max_health` |
| **"获得"** | 一般为**永久效果**，持续到游戏结束 | `buff_minion(permanent=True)` / `gain_keyword(permanent=True)` |
| **"直到回合结束"** | 临时效果 | `gain_keyword(permanent=False)` / `give_temp_buff_until_turn_end` |
| **"目标"**（策略卡） | 可能包含**玩家（主角）和异象** | 使用自定义 `targets_fn` 返回异象+玩家列表 |
| **"或"**（抉择） | 玩家二选一 | `game.request_choice()` |

## 标准函数签名

```python
# 异象部署效果
@special
def _xxx_special(minion, player, game, extras=None):
    """文档字符串：描述卡牌效果。"""
    ...

# 策略打出效果
@strategy
def _xxx_strategy(player, target, game, extras=None):
    """文档字符串：描述卡牌效果。"""
    ...
```

**@special 装饰器自动检查：**
- 参数必须包含 `minion`, `player`, `game`, `extras`
- `extras` 必须有默认值 `=None`
- 函数必须有文档字符串

**运行时自动行为：**
- 检查 `minion.is_alive()`，死亡时跳过
- 打印 `[效果触发] 函数名 (异象名)` 日志

## 模板 1：部署指向效果

异象部署时指向 1 个场上目标：

```python
# discrete.py 中注册
register_card(
    name="末影螨",
    cost_str="1I",
    card_type=CardType.MINION,
    # ...
    targets_fn=target_friendly_positions,          # 第一阶段：选部署位置
    extra_targeting_stages=[(target_any_minion, 1, False)],  # 第二阶段：选目标
    special_fn=_moyiren_special,
)

# xxx_effects.py 中实现
@special
def _moyiren_special(minion, player, game, extras=None):
    """部署：对1个异象造成1点伤害。"""
    if not extras:
        return
    target = extras[0]
    if not target or not target.is_alive():
        return
    deal_damage_to_minion(target, 1, minion, game)
```

## 模板 2：亡语效果

```python
@special
def _ehan_special(minion, player, game, extras=None):
    """恶魂：亡语：将1张'恶魂之泪'加入手牌。"""
    def _dr(m, p, b):
        give_card_by_name(p, "恶魂之泪", reason="恶魂亡语")
    add_deathrattle(minion, _dr)
```

## 模板 3：回合开始/结束触发

```python
@special
def _liudu_special(minion, player, game, extras=None):
    """流髑：回合开始：随机冰冻1个敌方异象。"""
    def on_turn_start(g, event_data, source):
        if not minion.is_alive():
            return
        enemies = [m for m in all_enemy_minions(g, player) if m.is_alive()]
        if enemies:
            target = random.choice(enemies)
            gain_keyword(target, "冰冻")
    minion.on_turn_start = on_turn_start
```

## 模板 4：抉择效果

```python
@strategy
def _tansuo_strategy(player, target, game, extras=None):
    """探索：抉择：将1张'丛林神殿'或'沙漠神殿'加入手牌。"""
    choice = game.request_choice(
        player, ["丛林神殿", "沙漠神殿"],
        title="探索：选择一张牌加入手牌"
    )
    if choice:
        add_card_to_hand_by_name(choice, player)
    return True
```

## 模板 5：动态效果注入（延迟到回合结束）

```python
from card_pools.effect_utils import add_turn_end_effect

@special
def _xxx_special(minion, player, game, extras=None):
    """部署：本回合结束时，本异象获得+1/+1。"""
    def on_turn_end(g, event_data, source):
        if minion.is_alive():
            buff_minion(minion, 1, 1)
    add_turn_end_effect(game, minion, on_turn_end)
```

## 模板 6：EventBus 事件监听

```python
from card_pools.effect_utils import add_event_listener

@special
def _shujia_special(minion, player, game, extras=None):
    """书架：受到伤害时，将1张'书'加入手牌。"""
    def on_damaged(g, event_data, source):
        if event_data.get("target") is minion and minion.is_alive():
            give_card_by_name(player, "书", reason="书架受伤")
    add_event_listener(game, EVENT_DAMAGED, on_damaged)
```

## 模板 7：手牌目标 + 场上目标（两阶段指向）

```python
# discrete.py 中注册
register_card(
    name="命名牌",
    cost_str="1T",
    card_type=CardType.STRATEGY,
    targets_fn=target_hand_minions,                # 第一阶段：选手牌中的异象
    extra_targeting_stages=[(target_any_minion, 1, False)],  # 第二阶段：选场上异象
    effect_fn=_mingmingpai_strategy,
)

# xxx_effects.py 中实现
@strategy
def _mingmingpai_strategy(player, target, game, extras=None):
    """选择1张手牌中的异象，使场上的1个异象获得'也算作是本异象'。抽1张牌。"""
    if not target or not hasattr(target, "name"):
        return False
    if not extras or len(extras) < 1:
        return False
    board_minion = extras[0]
    if not board_minion or not board_minion.is_alive():
        return False
    set_alias(board_minion, target.name)
    draw_cards(player, 1, game)
    return True
```

## 模板 8：临时 BUFF（直到回合结束）

```python
from card_pools.effect_utils import give_temp_buff_until_turn_end

@strategy
def _xxx_strategy(player, target, game, extras=None):
    """使1个异象获得+2攻击力直到回合结束。"""
    if not target or not target.is_alive():
        return False
    give_temp_buff_until_turn_end(target, atk_delta=2, hp_delta=0)
    return True
```

## 模板 9：全局部署限制

```python
from card_pools.effect_utils import add_deploy_restriction

@special
def _wuzhu_special(minion, player, game, extras=None):
    """疣猪：双方无法部署花费不大于4T的异象。"""
    def restriction(p, card):
        from tards.cards import MinionCard
        if isinstance(card, MinionCard) and card.cost.t <= 4:
            return False
        return True
    add_deploy_restriction(game, restriction)
```

## 常用 effect_utils API 速查

| 函数 | 用途 |
|------|------|
| `deal_damage_to_minion(target, damage, source, game)` | 标准伤害（含坚韧/替换/事件） |
| `deal_damage_to_player(player, damage, source, game)` | 对玩家造成伤害 |
| `destroy_minion(minion, game)` | 消灭异象（触发亡语） |
| `summon_token(game, name, owner, position, ...)` | 召唤 token |
| `buff_minion(minion, atk_delta, hp_delta, permanent=True)` | 修改攻击力/生命值 |
| `gain_keyword(minion, keyword, value, permanent=True)` | 赋予关键词 |
| `remove_keyword(minion, keyword)` | 移除关键词 |
| `add_deathrattle(minion, fn)` | 动态添加亡语 |
| `return_minion_to_hand(minion, game)` | 返回手牌（满则弃置） |
| `copy_card_to_hand(source_card, owner, game, cost_modifier)` | 复制加入手牌 |
| `draw_cards(player, amount, game)` | 抽牌 |
| `draw_cards_of_type(player, amount, card_type, game)` | 抽指定类型牌 |
| `give_card_by_name(player, name, reason)` | 按名字加入手牌 |
| `add_card_to_hand_by_name(name, player)` | 同上（旧版） |
| `shuffle_into_deck(card, player)` | 洗入牌库 |
| `place_at_deck_top(card, player)` | 置牌库顶 |
| `place_at_deck_bottom(card, player)` | 置牌库底 |
| `initiate_combat(attacker, defender, game)` | 发起对战 |
| `move_minion(minion, new_pos, game)` | 移动异象 |
| `swap_minions(m1, m2, game)` | 交换位置 |
| `transform_minion_to(minion, target_name, game)` | 变形为指定异象 |
| `add_event_listener(game, event_type, fn)` | 注册事件监听 |
| `add_turn_start_effect(game, minion, fn)` | 注入回合开始效果 |
| `add_turn_end_effect(game, minion, fn)` | 注入回合结束效果 |
| `delay_to_turn_end(game, fn)` | 延迟到回合结束 |
| `delay_to_next_turn(game, fn)` | 延迟到下一回合 |
| `add_deploy_restriction(game, fn)` | 全局部署限制 |
| `set_alias(minion, name)` | 使异象"也算作是"某名字 |
| `conditional_effect(condition, effect_fn)` | 条件执行 |
| `all_friendly_minions(game, player)` | 所有友方存活异象 |
| `all_enemy_minions(game, player)` | 所有敌方存活异象 |
| `get_adjacent_positions(pos, board)` | 相邻位置 |
| `get_frontmost_enemy(col, owner, board, attacker)` | 指定列最前敌方异象 |
| `is_enemy(m1, m2)` | 判断敌对关系 |
| `silence_minion(minion)` | 沉默异象 |
| `heal_minion(minion, amount)` | 治疗异象 |
| `heal_player(player, amount)` | 治疗玩家 |
| `discard_card(player, card)` | 弃置手牌 |
| `remove_top_of_deck(player, amount)` | 移除牌库顶牌 |
| `peek_deck_top(player, amount)` | 查看牌库顶 |


## 模板 10：伤害阈值替换与免疫

```python
from card_pools.effect_utils import (
    add_lose_hp_instead_of_damage,
    add_even_damage_immunity,
    add_min_hp_protection,
    add_damage_cap,
)

@special
def _yao_special(minion, player, game, extras=None):
    """鹞：受到伤害时，改为失去1点HP。"""
    # 无条件：任何伤害都改为 lose 1HP
    add_lose_hp_instead_of_damage(minion, condition_fn=None, lose_amount=1)

@special
def _biyi_special(minion, player, game, extras=None):
    """避役：受到不小于4的单次伤害时，改为失去1点HP。"""
    add_lose_hp_instead_of_damage(
        minion,
        condition_fn=lambda damage: damage >= 4,
        lose_amount=1,
    )

@special
def _hu_special(minion, player, game, extras=None):
    """狐：免疫偶数伤害。"""
    add_even_damage_immunity(minion)

@special
def _yixue_special(minion, player, game, extras=None):
    """蚁穴：场上有昆虫时，HP无法降至1以下。"""
    add_min_hp_protection(minion, min_hp=1)
```

> ⚠️ `add_lose_hp_instead_of_damage` 的实现原理：注册一个 `damage_replacement`，在 filter 中调用 `lose_hp()`，然后 replace_fn 返回 0 取消原伤害。原伤害事件链不会触发。

## 模板 11：部署计数检查

```python
from card_pools.effect_utils import (
    get_deploy_count_this_turn,
    is_first_deploy_this_turn,
    is_only_deploy_this_turn,
)

@special
def _tiaozhu_special(minion, player, game, extras=None):
    """跳蛛：结算阶段开始时，若本回合只部署了本异象，获得迅捷。"""
    def on_phase_start(g, event_data, source):
        if event_data.get("phase") != g.PHASE_RESOLVE:
            return
        if not minion.is_alive():
            return
        if is_only_deploy_this_turn(g, player, minion):
            gain_keyword(minion, "迅捷")
            print(f"  {minion.name} 本回合唯一部署，获得迅捷")
    minion.on_phase_start = on_phase_start

@special
def _wujing_special(minion, player, game, extras=None):
    """鼯鼱：必须是本轮部署的第一个异象。"""
    # 部署限制在部署时检查
    # 若本回合已有部署，special_fn 中可返回提示（但实际限制应在 condition_fn 中）
    pass
```

> 部署限制建议通过 `add_deploy_restriction` 或 `condition_fn` 实现，而非在 `special_fn` 中事后检查。

## 模板 12：每回合伤害累计查询

```python
from card_pools.effect_utils import get_damage_dealt_to_player_this_turn

@special
def _muque_special(minion, player, game, extras=None):
    """木鹊：回合结束，若本回合对手受到伤害累计不小于3，你获得1B。"""
    def on_turn_end(g, event_data, source):
        if not minion.is_alive():
            return
        opponent = game.p1 if player == game.p2 else game.p1
        total = get_damage_dealt_to_player_this_turn(g, opponent)
        if total >= 3:
            player.b_point += 1
            print(f"  木鹊：对手本回合受到 {total} 点伤害，{player.name} 获得1B")
    minion.on_turn_end = on_turn_end
```

## 模板 13：伤害重定向与替伤

```python
from card_pools.effect_utils import (
    redirect_adjacent_damage_to_self,
    add_pre_fatal_damage_heal,
)

@special
def _shelang_special(minion, player, game, extras=None):
    """猞猁：相邻异象受到伤害时，改为由本异象承受。"""
    redirect_adjacent_damage_to_self(minion)

@special
def _chaodong_special(minion, player, game, extras=None):
    """嘲鸫：友方异象受到致命伤害前，先获得+1HP。"""
    add_pre_fatal_damage_heal(minion, heal_amount=1)
```

> `redirect_adjacent_damage_to_self` 通过注册 `damage_replacement` 实现。当相邻友方受伤时，对 minion 造成等量伤害，并将原目标的伤害替换为 0。

## 模板 14：跨回合目标记忆

```python
from card_pools.effect_utils import (
    remember_target,
    get_remembered_target,
    clear_remembered_target,
)

@special
def _zhuiliezhe_special(minion, player, game, extras=None):
    """追猎者：部署指向一个不处于本列的异象。亡语：将其消灭。"""
    if not extras:
        return
    target = extras[0]
    remember_target(minion, target, key="zhuilie")

    def _dr(m, p, b):
        t = get_remembered_target(m, key="zhuilie")
        if t and hasattr(t, "is_alive") and t.is_alive():
            destroy_minion(t, b.game_ref if hasattr(b, "game_ref") else None)
            print(f"  追猎者亡语：消灭 {t.name}")
    add_deathrattle(minion, _dr)

@special
def _ankang_special(minion, player, game, extras=None):
    """鮟鱇：回合结束指向一个异象。回合开始消灭指向异象。"""
    def on_turn_end(g, event_data, source):
        if not minion.is_alive():
            return
        # 需要玩家手动选择目标——这里简化，随机选敌方异象
        enemies = all_enemy_minions(g, player)
        if enemies:
            target = random.choice(enemies)
            remember_target(minion, target, key="ankang")
            print(f"  鮟鱇记住了目标 {target.name}")

    def on_turn_start(g, event_data, source):
        t = get_remembered_target(minion, key="ankang")
        if t and t.is_alive():
            destroy_minion(t, g)
            print(f"  鮟鱇消灭记住了的目标 {t.name}")
        clear_remembered_target(minion, key="ankang")

    minion.on_turn_end = on_turn_end
    minion.on_turn_start = on_turn_start
```

## 模板 15：复制异象召唤

```python
from card_pools.effect_utils import summon_copy_of

@special
def _que_special(minion, player, game, extras=None):
    """雀：部署时复制加入战场。回合结束再复制加入战场。"""
    # 寻找空位
    from tards.board import Board
    for pos in [(r, c) for r in player.get_friendly_rows() for c in range(Board.SIZE)]:
        if pos not in game.board.minion_place:
            summon_copy_of(minion, pos, game)
            break
```

## 模板 16：弃置与磨牌事件监听

```python
from card_pools.effect_utils import on_card_discarded, on_card_milled

@special
def _shiyishu_special(minion, player, game, extras=None):
    """食蚁兽：被弃掉或从卡组移除时，改为加入战场。"""
    def on_discard(card):
        if card.source_card and card.source_card.name == "食蚁兽":
            # 将自身加入战场...
            pass

    def on_mill(card):
        if card.source_card and card.source_card.name == "食蚁兽":
            pass

    on_card_discarded(player, on_discard, game)
    on_card_milled(player, on_mill, game)
```

> 食蚁兽的效果需要监听自己被弃掉/被磨的事件。实际实现中可能需要通过 `remember_target` 或卡牌 ID 来精确匹配。

## 模板 17：兴奋机制

```python
from card_pools.effect_utils import add_excitement

@special
def _zongxiong_special(minion, player, game, extras=None):
    """棕熊：具有兴奋——攻击消灭异象后再攻击一次。"""
    add_excitement(minion)
```

> "兴奋"定义：若因攻击消灭了一个异象，则再攻击一次。`add_excitement` 通过监听 `AFTER_DAMAGE` 事件实现。

## 模板 18：全局地形覆盖

```python
from card_pools.effect_utils import override_terrain, clear_terrain_override

@special
def _kun_special(minion, player, game, extras=None):
    """鲲：平地均算作水路。"""
    # 将所有非水路列覆盖为水路
    for r in range(5):
        for c in range(4):  # 0-3 列原先是陆地
            override_terrain(game, (r, c), "水路")
    print("  鲲：所有平地均被视为水路")
```

> `board.py` 的 `is_valid_deploy` 和 `move_minion` 已集成 `_is_water_at()`，优先查询地形覆盖。

## 模板 19：无法被异象选中

```python
from card_pools.effect_utils import set_untargetable_by_minions

@special
def _13haohaizi_special(minion, player, game, extras=None):
    """13号孩子：无法被异象选中（策略仍可以）。"""
    set_untargetable_by_minions(minion, active=True)
```

> `resolve_phase` 中攻击目标选择时会自动过滤 `_untargetable_by_minions` 异象，攻击落空转打英雄。

## 模板 20：全局攻击禁止

```python
from card_pools.effect_utils import add_attack_restriction

@special
def _cilu_special(minion, player, game, extras=None):
    """雌鹿：攻击力最高的敌方异象无法攻击。"""
    def restriction(m):
        if m.owner == player:
            return False
        enemies = all_enemy_minions(game, player)
        if not enemies:
            return False
        highest = max(enemies, key=lambda x: x.current_attack)
        return m is highest

    add_attack_restriction(game, restriction)
```

> 攻击限制在回合结束时自动清理。`resolve_phase` 中攻击前会检查 `can_minion_attack()`。

## 模板 21：伤害来源查询

```python
from card_pools.effect_utils import (
    get_last_damage_source,
    get_last_damage_type,
    get_last_damage_amount,
)

@special
def _haozhu_special(minion, player, game, extras=None):
    """豪猪：受到伤害后，对伤害来源造成等量伤害。"""
    def on_after_damage(event):
        if event.data.get("target") is not minion:
            return
        source = get_last_damage_source(minion)
        amount = get_last_damage_amount(minion)
        if source and source.is_alive() and amount > 0:
            deal_damage_to_minion(source, amount, minion, game)
            print(f"  豪猪反弹 {amount} 点伤害给 {source.name}")

    add_event_listener(game, EVENT_AFTER_DAMAGE, on_after_damage)

@special
def _shuishiyan_special(minion, player, game, extras=None):
    """水螅岩：亡语：若是由于异象效果被消灭，改为在回合结束时成长。"""
    def _dr(m, p, b):
        source_type = get_last_damage_type(m)
        if source_type == "effect":
            print(f"  水螅岩因异象效果被消灭，改为在回合结束时成长")
            # 注册延迟成长...
        else:
            print(f"  水螅岩非异象效果消灭，正常死亡")
    add_deathrattle(minion, _dr)
```


## 新增 API 速查（冥刻包扩展）

### 伤害控制
| 函数 | 用途 |
|------|------|
| `add_lose_hp_instead_of_damage(minion, condition_fn, lose_amount)` | 伤害改为 lose_hp（不触发任何效果） |
| `add_even_damage_immunity(minion)` | 偶数伤害→0 |
| `add_min_hp_protection(minion, min_hp)` | HP 不低于某值 |
| `add_damage_cap(minion, cap)` | 单次伤害上限 |

### 部署与战场追踪
| 函数 | 用途 |
|------|------|
| `get_deployed_this_turn(game, player)` | 本回合已部署列表（按顺序） |
| `get_deploy_count_this_turn(game, player)` | 本回合部署数量 |
| `is_first_deploy_this_turn(game, player)` | 是否尚未部署 |
| `is_only_deploy_this_turn(game, player, minion)` | 某异象是否是唯一部署 |

### 伤害累计
| 函数 | 用途 |
|------|------|
| `get_damage_dealt_to_player_this_turn(game, player)` | 玩家本回合受到的伤害累计 |

### 伤害重定向与替伤
| 函数 | 用途 |
|------|------|
| `redirect_adjacent_damage_to_self(minion)` | 替相邻友方承受伤害 |
| `add_pre_fatal_damage_heal(minion, heal_amount)` | 致命伤害前治疗 |

### 目标记忆
| 函数 | 用途 |
|------|------|
| `remember_target(minion, target, key)` | 记住目标 |
| `get_remembered_target(minion, key)` | 获取记忆（自动检测死亡） |
| `clear_remembered_target(minion, key)` | 清除记忆 |

### 复制召唤
| 函数 | 用途 |
|------|------|
| `summon_copy_of(minion, position, game, modifiers)` | 复制指定异象到指定位置 |

### 事件监听扩展
| 函数 | 用途 |
|------|------|
| `on_card_discarded(player, callback, game)` | 监听弃置事件 |
| `on_card_milled(player, callback, game)` | 监听磨牌事件 |
| `add_excitement(minion)` | 攻击消灭后再攻击一次 |

### 全局效果
| 函数 | 用途 |
|------|------|
| `override_terrain(game, position, terrain_type)` | 覆盖格子地形 |
| `clear_terrain_override(game, position)` | 清除地形覆盖 |
| `get_terrain_at(game, position)` | 查询当前地形 |
| `set_untargetable_by_minions(minion, active)` | 无法被异象选中 |
| `is_untargetable_by_minions(minion)` | 查询无法被选中状态 |
| `add_attack_restriction(game, condition_fn)` | 全局攻击限制 |
| `clear_attack_restrictions(game)` | 清除攻击限制 |
| `can_minion_attack(minion, game)` | 检查是否被禁止攻击 |

### 伤害来源追踪
| 函数 | 用途 |
|------|------|
| `get_last_damage_source(minion)` | 最近一次伤害来源异象 |
| `get_last_damage_type(minion)` | 伤害类型（combat/strategy/effect） |
| `get_last_damage_amount(minion)` | 实际伤害数值 |
| `clear_last_damage_source(minion)` | 清除记录 |

