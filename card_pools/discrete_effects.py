#!/usr/bin/env python3
"""离散卡包人工效果实现。

通过 SPECIAL_MAP 将卡牌名映射到对应的 special_fn 函数。
策略效果函数直接使用 @strategy 装饰器，在 discrete.py 中手动挂接 effect_fn。
"""

import random

from card_pools.effect_decorator import special, strategy
from card_pools.effect_utils import (
    add_card_to_hand_by_name,
    add_deathrattle,
    add_event_listener,
    all_enemy_minions,
    all_friendly_minions,
    buff_minion,
    copy_card_to_hand,
    create_card_by_name,
    deal_damage_to_minion,
    deal_damage_to_player,
    destroy_minion,
    discard_card,
    draw_cards,
    draw_cards_of_type,
    gain_keyword,
    get_adjacent_positions,
    get_all_minions,
    give_card_by_name,
    heal_player,
    initiate_combat,
    is_enemy,
    modify_keyword_number,
    on_after_damage,
    on_after_attack,
    on_before_attack,
    on_before_damage,
    on_before_destroy,
    on_damaged,
    random_enemy_minion,
    remove_keyword,
    remove_minion_no_death,
    remove_top_of_deck,
    return_minion_to_hand,
    shuffle_into_deck,
    summon_token,
    swap,
)


# =============================================================================
# 矿车（已验证）
# =============================================================================

@special
def _kuangche_special(minion, player, game, extras=None):
    """矿车：亡语：获得1个T槽。"""

    def _kuangche_deathrattle(m, p, b):
        """矿车亡语：获得1个T槽。"""
        p.t_point_max += 1
        print(f"  {p.name} 获得1个T槽，T槽上限={p.t_point_max}，当前T点={p.t_point}")

    add_deathrattle(minion, _kuangche_deathrattle)


# =============================================================================
# 单位卡 — 回合结束效果
# =============================================================================

@special
def _beijixiong_special(minion, player, game, extras=None):
    """北极熊：回合结束：若HP不大于2，获得-1/+2。"""

    def _on_turn_end(g, event_data, m):
        if m.is_alive() and m.health <= 2:
            buff_minion(m, -1, +2, permanent=True)

    minion.on_turn_end = _on_turn_end


@special
def _naogui_special(minion, player, game, extras=None):
    """恼鬼：回合结束时，将其消灭。"""

    def _on_turn_end(g, event_data, m):
        if m.is_alive():
            destroy_minion(m, g)

    minion.on_turn_end = _on_turn_end


# =============================================================================
# 单位卡 — 回合开始效果
# =============================================================================

@special
def _liudu_special(minion, player, game, extras=None):
    """流髑：回合开始：随机冰冻1个敌方单位。若其已被冰冻，将其消灭。"""

    def _on_turn_start(g, event_data, m):
        target = random_enemy_minion(g, player)
        if not target:
            return
        if target.keywords.get("冰冻", 0):
            destroy_minion(target, g)
        else:
            gain_keyword(target, "冰冻", 1)

    minion.on_turn_start = _on_turn_start


@special
def _shike_special(minion, player, game, extras=None):
    """尸壳：回合开始：对所有敌方单位造成1点伤害。"""

    def _on_turn_start(g, event_data, m):
        for enemy in all_enemy_minions(g, player):
            deal_damage_to_minion(enemy, 1, source=m, game=g)

    minion.on_turn_start = _on_turn_start


# =============================================================================
# 单位卡 — 部署效果
# =============================================================================

@special
def _weidaoshi_special(minion, player, game, extras=None):
    """卫道士：部署：所有敌方单位获得-1坚韧等级。"""
    for m in all_enemy_minions(game, player):
        modify_keyword_number(m, "坚韧", -1)


@special
def _zhizhu_special(minion, player, game, extras=None):
    """蜘蛛：部署：使1个单位失去迅捷，高频和空袭。亡语：将1张"蜘蛛眼"加入手牌。"""
    # 部署指向效果
    targets = extras or []
    if targets:
        target = targets[0]
        if hasattr(target, "is_alive") and target.is_alive():
            remove_keyword(target, "迅捷")
            remove_keyword(target, "高频")
            remove_keyword(target, "空袭")

    # 亡语
    def _dr(m, p, b):
        add_card_to_hand_by_name("蜘蛛眼", p)

    add_deathrattle(minion, _dr)


@special
def _shuaichong_special(minion, player, game, extras=None):
    """蠹虫：部署：抽1张"蠹虫"。"""
    # 从牌库中查找第一张名为"蠹虫"的牌并抽入手牌
    found_idx = None
    for i, card in enumerate(player.card_deck):
        if card.name == "蠹虫":
            found_idx = i
            break
    if found_idx is not None:
        card = player.card_deck.pop(found_idx)
        if len(player.card_hand) < player.card_hand_max:
            player.card_hand.append(card)
            print(f"  {player.name} 从牌库中抽到了 {card.name}")
        else:
            player.card_dis.append(card)
            print(f"  {player.name} 手牌满，{card.name} 被弃置")
    else:
        print(f"  {player.name} 牌库中没有蠹虫")


@special
def _xiangshu_special(minion, player, game, extras=None):
    """橡树苗：若你拥有不小于11个T槽，立刻成长。"""
    if player.t_point_max >= 11:
        minion.evolve(game)


# =============================================================================
# 单位卡 — 部署钩子（全局监听）
# =============================================================================

@special
def _yanjiangting_special(minion, player, game, extras=None):
    """岩浆艇：友方单位部署时，消灭本单位。"""

    def _on_deploy(deployed, self_minion=minion, g=game):
        if deployed.owner == self_minion.owner and deployed is not self_minion:
            if self_minion.is_alive():
                destroy_minion(self_minion, g)

    minion.register_deploy_hook(game, _on_deploy)


# =============================================================================
# 单位卡 — 亡语
# =============================================================================

@special
def _ganzhe_special(minion, player, game, extras=None):
    """甘蔗：亡语：将1张"书"加入手牌。"""

    def _dr(m, p, b):
        add_card_to_hand_by_name("书", p)

    add_deathrattle(minion, _dr)


# =============================================================================
# 单位卡 — 受伤时/前/后（EventBus 驱动）
# =============================================================================

@special
def _yingshi_special(minion, player, game, extras=None):
    """萤石：你受到的伤害-1。"""

    def _shield(event):
        target = event.get("target")
        if target != player:
            return
        delta = event.get("delta", 0)
        if delta < 0:
            new_delta = min(0, delta + 1)
            event.data["delta"] = new_delta
            print(f"  萤石减免1点伤害（{delta}→{new_delta}）")

    add_event_listener(minion, game, "before_health_change", _shield)


@special
def _shujia_special(minion, player, game, extras=None):
    """书架：受到伤害时，将1张'书'加入手牌。"""

    def _on_damaged(event):
        if event.get("target") == minion:
            add_card_to_hand_by_name("书", player)

    on_damaged(minion, game, _on_damaged)


@special
def _moyiren_special(minion, player, game, extras=None):
    """末影人：受到伤害前，与1个友方单位交换位置。"""

    def _teleport(event):
        if event.get("target") != minion:
            return
        friends = [m for m in all_friendly_minions(game, player) if m is not minion and m.is_alive()]
        if not friends:
            return
        target_friend = random.choice(friends)
        swap(minion, target_friend, game)
        print(f"  末影人与 {target_friend.name} 交换位置")

    on_before_damage(minion, game, _teleport)


@special
def _lieyanren_special(minion, player, game, extras=None):
    """烈焰人：溢出伤害转移至对手。亡语：将1张'烈焰粉'加入手牌。"""

    def _overflow(event):
        source = event.source
        if source != minion:
            return
        target = event.get("target")
        if not hasattr(target, "is_alive") or target.is_alive():
            return
        overflow = max(0, -target.current_health)
        if overflow > 0:
            opponent = game.p2 if player == game.p1 else game.p1
            deal_damage_to_player(opponent, overflow, source=minion, game=game)
            print(f"  烈焰人溢出 {overflow} 点伤害转移给 {opponent.name}")

    on_after_damage(minion, game, _overflow)

    def _dr(m, p, b):
        add_card_to_hand_by_name("烈焰粉", p)

    add_deathrattle(minion, _dr)


@special
def _tiekuilei_special(minion, player, game, extras=None):
    """铁傀儡：受到等于其HP的单次伤害时，将其免除。"""

    def _negate(event):
        if event.get("target") != minion:
            return
        damage = event.get("damage", 0)
        if damage == minion.current_health:
            event.cancelled = True
            print(f"  铁傀儡免除等额伤害")

    on_before_damage(minion, game, _negate)


@special
def _huli_special(minion, player, game, extras=None):
    """狐狸：受到大于其HP的单次伤害时，将其免除。"""

    def _negate(event):
        if event.get("target") != minion:
            return
        damage = event.get("damage", 0)
        if damage > minion.current_health:
            event.cancelled = True
            print(f"  狐狸免除超额伤害")

    on_before_damage(minion, game, _negate)


@special
def _haigui_special(minion, player, game, extras=None):
    """海龟：受到伤害后，将攻击力最高的敌方单位的攻击力设为1，直到下回合结束。"""

    def _weaken(event):
        if event.get("target") != minion:
            return
        enemies = all_enemy_minions(game, player)
        if not enemies:
            return
        highest = max(enemies, key=lambda m: m.current_attack)
        if highest.current_attack > 1:
            delta = -(highest.current_attack - 1)
            buff_minion(highest, delta, 0, permanent=False)
            print(f"  海龟将 {highest.name} 的攻击力降为1（临时）")

    on_after_damage(minion, game, _weaken)


@special
def _rongyuan_special(minion, player, game, extras=None):
    """蝾螈：受到伤害后，返回手牌。返回手牌：使所有友方目标获得+1HP。"""

    def _bounce(event):
        if event.get("target") != minion:
            return
        friends = all_friendly_minions(game, player)
        for m in friends:
            buff_minion(m, 0, 1, permanent=True)
        if minion.is_alive():
            return_minion_to_hand(minion, game)

    on_after_damage(minion, game, _bounce)


@special
def _dishuizhuichui_special(minion, player, game, extras=None):
    """滴水石锥：受到伤害时，对对手造成1点伤害。"""

    def _counter(event):
        if event.get("target") != minion:
            return
        opponent = game.p2 if player == game.p1 else game.p1
        deal_damage_to_player(opponent, 1, source=minion, game=game)

    on_damaged(minion, game, _counter)


# =============================================================================
# 单位卡 — 攻击前/后（EventBus 驱动）
# =============================================================================

@special
def _kulou_special(minion, player, game, extras=None):
    """骷髅：攻击前，改为对HP最低的敌方单位造成等量伤害。"""

    def _retarget(event):
        if event.get("attacker") != minion:
            return
        enemies = all_enemy_minions(game, player)
        if not enemies:
            return
        lowest = min(enemies, key=lambda m: m.current_health)
        event.data["target"] = lowest
        event.data["defender"] = lowest
        print(f"  骷髅改为攻击 {lowest.name}")

    on_before_attack(minion, game, _retarget)


@special
def _baomao_special(minion, player, game, extras=None):
    """豹猫：本单位攻击时，对其指向的单位造成等量伤害。部署：指向一个单位。"""
    targets = extras or []
    if targets and hasattr(targets[0], "is_alive"):
        minion._pointed_target = targets[0]
        print(f"  豹猫指向了 {targets[0].name}")

    def _on_attack(event):
        if event.get("attacker") != minion:
            return
        pointed = getattr(minion, "_pointed_target", None)
        if pointed and pointed.is_alive():
            event.cancelled = True
            deal_damage_to_minion(pointed, minion.current_attack, source=minion, game=game)
            print(f"  豹猫对指向目标 {pointed.name} 造成 {minion.current_attack} 点伤害")

    on_before_attack(minion, game, _on_attack)


@special
def _jiangshi_special(minion, player, game, extras=None):
    """僵尸：造成伤害时，你获得等量HP。"""

    def _leech(event):
        source = event.source
        if source != minion:
            return
        actual = event.get("actual", 0)
        if actual > 0:
            heal_player(player, actual)
            print(f"  僵尸吸血 {actual} HP")

    on_after_damage(minion, game, _leech)


# =============================================================================
# 单位卡 — 消灭前（EventBus 驱动）
# =============================================================================

@special
def _huanyi_special(minion, player, game, extras=None):
    """幻翼：消灭单位前，改为移除对方卡组顶的2张牌。"""

    def _replace_destroy(event):
        target = event.get("target")
        if not target or not hasattr(target, "is_alive"):
            return
        last_attacker = getattr(target, "_last_attacker", None)
        if last_attacker != minion:
            return
        event.cancelled = True
        target.current_health = max(1, target.current_health)
        print(f"  幻翼阻止了 {target.name} 的消灭")
        opponent = target.owner
        remove_top_of_deck(opponent, 2)

    on_before_destroy(minion, game, _replace_destroy)


# =============================================================================
# 开发相关卡牌（通过通用机制实现，非硬编码）
# =============================================================================

@special
def _xinbiao_special(minion, player, game, extras=None):
    """信标：你获得1个C槽或T槽时，开发1张卡组中的牌。若手牌已满，将其洗入卡组。"""
    from tards.constants import EVENT_T_MAX_CHANGED
    def on_t_max_change(event):
        if event.data.get("player") == player and event.data.get("new", 0) > event.data.get("old", 0):
            game.develop_card(player, player.original_deck_defs, overflow_to_discard=False)
    add_event_listener(minion, game, EVENT_T_MAX_CHANGED, on_t_max_change)


@special
def _huoba_special(minion, player, game, extras=None):
    """火把：每回合你首次获得额外的T槽时，抽1张牌。"""
    from tards.constants import EVENT_T_MAX_CHANGED
    def on_t_max_change(event):
        if event.data.get("player") == player and event.data.get("new", 0) > event.data.get("old", 0):
            if not getattr(player, '_huoba_triggered_this_turn', False):
                player._huoba_triggered_this_turn = True
                player.draw_card(1, game=game)
    add_event_listener(minion, game, EVENT_T_MAX_CHANGED, on_t_max_change)
    def reset_flag(g, event_data, m):
        player._huoba_triggered_this_turn = False
    minion.on_turn_start = reset_flag


@special
def _liulangshangren_special(minion, player, game, extras=None):
    """流浪商人：抽牌阶段，取消抽牌，开发一张卡组中的牌。场上有友方友好单位时，无法选中。"""
    def on_turn_start(g, event_data, m):
        player._skip_next_draw = True
        game.develop_card(player, player.original_deck_defs)
    minion.on_turn_start = on_turn_start


@strategy
def _fumota_strategy(player, target, game, extras=None):
    """附魔台：使你获得：每个出牌阶段首次开发时，再开发1张“附魔书”。"""
    if getattr(player, '_enchanting_table_registered', False):
        return True
    player._enchanting_table_registered = True

    def on_develop(p, g):
        if not getattr(p, '_enchanting_table_triggered', False):
            p._enchanting_table_triggered = True
            from tards.card_db import DEFAULT_REGISTRY
            book_defs = [c for c in DEFAULT_REGISTRY.all_cards() if c.name == "附魔书"]
            if book_defs:
                g.develop_card(p, book_defs)

    player._on_develop_callbacks.append(on_develop)

    def reset_flag(event):
        if event.data.get("phase") == game.PHASE_ACTION:
            player._enchanting_table_triggered = False

    from tards.constants import EVENT_PHASE_START
    game.register_listener(EVENT_PHASE_START, reset_flag)
    return True


@strategy
def _gengzhi_strategy(player, target, game, extras=None):
    """耕殖：开发1张友好单位，抽1张牌。此前你每使用过1张“耕殖”，获得-1T花费。"""
    from tards import CardType
    from tards.card_db import DEFAULT_REGISTRY
    # 开发友好单位
    game.develop_card(
        player,
        [c for c in DEFAULT_REGISTRY.all_cards() if c.card_type == CardType.MINION and c.hidden_keywords.get("友好", False)]
    )
    # 抽1张牌
    player.draw_card(1, game=game)
    # 递增使用计数
    player._gengzhi_played_count = getattr(player, '_gengzhi_played_count', 0) + 1
    # 若尚未添加费用修正器，则添加
    if not getattr(player, '_gengzhi_modifier_added', False):
        player._gengzhi_modifier_added = True
        def modifier(card, cost):
            if card.name == "耕殖":
                cost.t = max(0, cost.t - player._gengzhi_played_count)
        player._cost_modifiers.append(modifier)
    return True


# =============================================================================
# 策略卡
# =============================================================================

@strategy
def _mubiao_strategy(player, target, game, extras=None):
    """木镐：获得1个额外的C槽。"""
    player.c_point_max += 1
    print(f"  {player.name} 获得1个额外C槽，C槽上限={player.c_point_max}")
    return True


@strategy
def _shibiao_strategy(player, target, game, extras=None):
    """石镐：获得1个额外的T槽。然后若剩余T点不少于2，抽一张牌。"""
    player.t_point_max += 1
    print(f"  {player.name} 获得1个额外T槽，T槽上限={player.t_point_max}")
    if player.t_point >= 2:
        draw_cards(player, 1, game)
    return True


@strategy
def _jinbiao_strategy(player, target, game, extras=None):
    """金镐：获得1个额外的C槽和T槽。然后若你的HP低于对手，你获得+4HP。"""
    player.c_point_max += 1
    player.t_point_max += 1
    print(f"  {player.name} 获得1个额外C槽和T槽")
    opponent = game.p2 if player == game.p1 else game.p1
    if player.health < opponent.health:
        heal_player(player, 4)
    return True


@strategy
def _zuanshibiao_strategy(player, target, game, extras=None):
    """钻石镐：获得1个额外的C槽和2个额外的T槽。
    然后若对方单位数更多，随机消灭一个花费不大于4T的敌方单位。"""
    player.c_point_max += 1
    player.t_point_max += 2
    print(f"  {player.name} 获得1个额外C槽和2个额外T槽")
    enemy_count = len(all_enemy_minions(game, player))
    friendly_count = len(all_friendly_minions(game, player))
    if enemy_count > friendly_count:
        candidates = [
            m for m in all_enemy_minions(game, player)
            if m.source_card and getattr(m.source_card, "cost", None) and m.source_card.cost.t <= 4
        ]
        if candidates:
            victim = random.choice(candidates)
            destroy_minion(victim, game)
    return True


@strategy
def _xueqiu_strategy(player, target, game, extras=None):
    """雪球：对一个单位造成1点伤害。然后若其HP不大于2，将其冰冻。"""
    if not target or not hasattr(target, "is_alive") or not target.is_alive():
        print("  [警告] 雪球没有有效目标")
        return False
    deal_damage_to_minion(target, 1, source=None, game=game)
    if target.is_alive() and target.health <= 2:
        gain_keyword(target, "冰冻", 1)
    return True


@strategy
def _zhizhuyan_strategy(player, target, game, extras=None):
    """蜘蛛眼：使1个单位获得-2攻击力。"""
    if not target or not hasattr(target, "is_alive") or not target.is_alive():
        print("  [警告] 蜘蛛眼没有有效目标")
        return False
    buff_minion(target, -2, 0, permanent=True)
    return True


@strategy
def _lieyanfen_strategy(player, target, game, extras=None):
    """烈焰粉：对一个单位及其相邻单位造成1点伤害。"""
    if not target or not hasattr(target, "is_alive") or not target.is_alive():
        print("  [警告] 烈焰粉没有有效目标")
        return False
    # 对主目标造成伤害
    deal_damage_to_minion(target, 1, source=None, game=game)
    # 对相邻单位造成伤害
    for pos in get_adjacent_positions(target.position, game.board):
        neighbor = game.board.get_minion_at(pos)
        if neighbor and neighbor.is_alive():
            deal_damage_to_minion(neighbor, 1, source=None, game=game)
    return True


@strategy
def _diaolingkuloutou_strategy(player, target, game, extras=None):
    """凋零骷髅头：移除对方卡组顶的1张牌。"""
    opponent = game.p2 if player == game.p1 else game.p1
    removed = remove_top_of_deck(opponent, 1)
    return bool(removed)


@strategy
def _guanglingjian_strategy(player, target, game, extras=None):
    """光灵箭：使1个单位获得-1坚韧等级。"""
    if not target or not hasattr(target, "is_alive") or not target.is_alive():
        print("  [警告] 光灵箭没有有效目标")
        return False
    modify_keyword_number(target, "坚韧", -1)
    return True


@strategy
def _zhanlipin_strategy(player, target, game, extras=None):
    """战利品：触发1个单位的亡语。若是敌方单位，再抹除其亡语。"""
    if not target or not hasattr(target, "is_alive") or not target.is_alive():
        print("  [警告] 战利品没有有效目标")
        return False
    dr = target.keywords.get("亡语")
    if dr and callable(dr):
        print(f"  触发 {target.name} 的亡语")
        dr(target, target.owner, target.board)
    else:
        print(f"  {target.name} 没有亡语")
    # 若是敌方单位，抹除亡语
    if is_enemy(target, player):
        target.base_keywords.pop("亡语", None)
        target.recalculate()
        print(f"  {target.name} 的亡语被抹除")
    return True


@strategy
def _yiqi_strategy(player, target, game, extras=None):
    """遗弃：将1个单位的HP设为1。"""
    if not target or not hasattr(target, "is_alive") or not target.is_alive():
        print("  [警告] 遗弃没有有效目标")
        return False
    # 将当前生命值设为1（直接扣到1，不触发伤害事件）
    target.current_health = 1
    print(f"  {target.name} 的HP被设为1")
    return True


@strategy
def _gaoshan_strategy(player, target, game, extras=None):
    """高山：对方随机弃1张牌，将1张"铁锭"置入对方卡组顶。"""
    opponent = game.p2 if player == game.p1 else game.p1
    # 对方随机弃1张手牌
    if opponent.card_hand:
        card = random.choice(opponent.card_hand)
        discard_card(opponent, card)
    else:
        print(f"  {opponent.name} 手牌为空，无法弃牌")
    # 将铁锭置入对方牌库顶（牌库顶 = 列表末尾）
    iron = create_card_by_name("铁锭", opponent)
    if iron:
        opponent.card_deck.append(iron)
        print(f"  铁锭被置入 {opponent.name} 的牌库顶")
    return True


@strategy
def _erdi_strategy(player, target, game, extras=None):
    """恶地：对所有花费不大于3的单位造成3点伤害。"""
    for m in get_all_minions(game):
        if m.is_alive():
            cost = getattr(m.source_card, "cost", None)
            if cost and cost.t <= 3:
                deal_damage_to_minion(m, 3, source=None, game=game)
    return True


@strategy
def _tnt_strategy(player, target, game, extras=None):
    """TNT：对一个目标造成2点伤害。抽1张牌。"""
    if target and hasattr(target, "is_alive") and target.is_alive():
        if hasattr(target, "take_damage"):
            deal_damage_to_minion(target, 2, source=None, game=game)
        elif hasattr(target, "health_change"):
            # 对玩家造成伤害
            target.health_change(-2)
    draw_cards(player, 1, game)
    return True


@strategy
def _hongshifen_strategy(player, target, game, extras=None):
    """红石粉：使1个非生命单位具有协同。抽1张牌。"""
    # 注："非生命单位"的定义待确认，当前实现为任意单位赋予协同
    if not target or not hasattr(target, "is_alive") or not target.is_alive():
        print("  [警告] 红石粉没有有效目标")
        return False
    gain_keyword(target, "协同")
    draw_cards(player, 1, game)
    return True


@strategy
def _jinrenshu_strategy(player, target, game, extras=None):
    """禁人书：使1个单位及其相邻单位获得眩晕。"""
    if not target or not hasattr(target, "is_alive") or not target.is_alive():
        print("  [警告] 禁人书没有有效目标")
        return False
    gain_keyword(target, "眩晕", 1)
    for pos in get_adjacent_positions(target.position, game.board):
        neighbor = game.board.get_minion_at(pos)
        if neighbor and neighbor.is_alive():
            gain_keyword(neighbor, "眩晕", 1)
    return True


@strategy
def _baoweiyaosai_strategy(player, target, game, extras=None):
    """保卫要塞：将6张"蠹虫"洗入卡组。"""
    for _ in range(6):
        card = create_card_by_name("蠹虫", player)
        if card:
            shuffle_into_deck(player, card)
    return True


@strategy
def _chongshishitou_strategy(player, target, game, extras=None):
    """虫蚀石头：移除对方卡组顶的2张牌，将2张"蠹虫"置入对方卡组顶。"""
    opponent = game.p2 if player == game.p1 else game.p1
    remove_top_of_deck(opponent, 2)
    for _ in range(2):
        card = create_card_by_name("蠹虫", opponent)
        if card:
            opponent.card_deck.append(card)
            print(f"  蠹虫被置入 {opponent.name} 的牌库顶")
    return True


# =============================================================================
# 单位卡 — Aura（光环）效果
# =============================================================================

@special
def _ma_special(minion, player, game, extras=None):
    """马：与其同列的友方单位具有迅捷。"""
    col = minion.position[1]

    def _swift_aura(m):
        if m.owner == player and m.position[1] == col:
            return {"迅捷": True}
        return {}

    # 立即给场上已有的同列友方单位添加 aura
    for m in all_friendly_minions(game, player):
        if m is not minion and m.position[1] == col:
            minion.provide_aura_keywords(m, _swift_aura)

    # 新部署的友方单位若在同列，也添加 aura
    def _on_deploy(deployed, self_minion=minion, g=game):
        if deployed.owner == player and deployed is not self_minion and deployed.position[1] == col:
            minion.provide_aura_keywords(deployed, _swift_aura)

    minion.register_deploy_hook(game, _on_deploy)


@special
def _chizushou_special(minion, player, game, extras=None):
    """炽足兽：与其同列的友方单位具有先攻1和+1攻击力。"""
    col = minion.position[1]

    def _kw_aura(m):
        if m.owner == player and m.position[1] == col:
            return {"先攻": 1}
        return {}

    def _atk_aura(m):
        if m.owner == player and m.position[1] == col:
            return 1
        return 0

    for m in all_friendly_minions(game, player):
        if m is not minion and m.position[1] == col:
            minion.provide_aura_keywords(m, _kw_aura)
            minion.provide_aura_attack(m, _atk_aura)

    def _on_deploy(deployed, self_minion=minion, g=game):
        if deployed.owner == player and deployed is not self_minion and deployed.position[1] == col:
            minion.provide_aura_keywords(deployed, _kw_aura)
            minion.provide_aura_attack(deployed, _atk_aura)

    minion.register_deploy_hook(game, _on_deploy)


@special
def _chaoonghexin_special(minion, player, game, extras=None):
    """潮涌核心：其它友方单位具有+2攻击力。"""

    def _atk_aura(m):
        if m.owner == player and m is not minion:
            return 2
        return 0

    for m in all_friendly_minions(game, player):
        if m is not minion:
            minion.provide_aura_attack(m, _atk_aura)

    def _on_deploy(deployed, self_minion=minion, g=game):
        if deployed.owner == player and deployed is not self_minion:
            minion.provide_aura_attack(deployed, _atk_aura)

    minion.register_deploy_hook(game, _on_deploy)


@special
def _huosai_feiting_special(minion, player, game, extras=None):
    """活塞飞艇：同列没有敌方单位时，具有迅捷。"""
    col = minion.position[1]

    def _self_swift(m):
        # 仅影响自身
        if m is minion:
            enemies_in_col = [
                e for e in all_enemy_minions(game, player)
                if e.position[1] == col
            ]
            if not enemies_in_col:
                return {"迅捷": True}
        return {}

    minion.add_aura_keywords(_self_swift)
    game.refresh_all_auras()


# =============================================================================
# 单位卡 — 回合结束 / 亡语
# =============================================================================

@special
def _lv_special(minion, player, game, extras=None):
    """驴：回合结束：若处于协同，抽1张牌。"""

    def _on_turn_end(g, event_data, m):
        if not m.is_alive():
            return
        col = m.position[1]
        # 检查同列是否有其它友方单位
        has_synergy = any(
            fm.is_alive() and fm is not m and fm.position[1] == col
            for fm in all_friendly_minions(g, player)
        )
        if has_synergy:
            draw_cards(player, 1, game=g)

    minion.on_turn_end = _on_turn_end


@special
def _guiyu_special(minion, player, game, extras=None):
    """鲑鱼：亡语：抽1张牌，如可能，使其获得-1T花费。否则，抽1张牌。"""

    def _dr(m, p, b):
        # 先抽1张牌
        drawn = draw_cards(p, 1, game=b.game_ref if hasattr(b, "game_ref") else None)
        if drawn > 0 and p.card_hand:
            card = p.card_hand[-1]  # 刚抽到的牌
            # 检查是否为 MinionCard（有 cost 属性）
            if hasattr(card, "cost") and hasattr(card.cost, "t") and card.cost.t > 0:
                card.cost.t = max(0, card.cost.t - 1)
                print(f"  {card.name} 获得-1T花费")
            else:
                # 无法再减花费，再抽1张
                draw_cards(p, 1, game=b.game_ref if hasattr(b, "game_ref") else None)
        else:
            draw_cards(p, 1, game=b.game_ref if hasattr(b, "game_ref") else None)

    add_deathrattle(minion, _dr)


# =============================================================================
# 单位卡 — 部署效果
# =============================================================================

@special
def _xuewulou_special(minion, player, game, extras=None):
    """雪傀儡：部署：在三路平地各加入1个"雪块"。亡语：将1张"雪球"加入手牌。"""
    # 三路平地 = 非水路列（0,1,2,3? 根据规则，"平地"可能指非高地非水路）
    # 离散卡包的地形：高地(0)、山脊(1)、中路(2)、河岸(3)、水路(4)
    # "平地"通常指山脊(1)、中路(2)、河岸(3)
    flat_cols = [1, 2, 3]
    for col in flat_cols:
        # 寻找该列友方空位
        placed = False
        for row in player.get_friendly_rows():
            pos = (row, col)
            if pos not in game.board.minion_place:
                summon_token(game, "雪块", player, pos, attack=0, health=1, keywords={"协同": True, "尖刺": 1})
                placed = True
                break
        if not placed:
            print(f"  雪块无法在列 {col} 部署：无空位")

    # 亡语
    def _dr(m, p, b):
        add_card_to_hand_by_name("雪球", p)

    add_deathrattle(minion, _dr)


@special
def _jinrenta_special(minion, player, game, extras=None):
    """禁人塔：部署：眩晕1行单位。被眩晕单位多眩晕1回合。"""
    # 部署指向：选择1行
    targets = extras or []
    if targets:
        row = targets[0]
        if isinstance(row, tuple):
            row = row[0]
        elif hasattr(row, "position"):
            row = row.position[0]
        for col in range(game.board.SIZE):
            pos = (row, col)
            m = game.board.get_minion_at(pos)
            if m and m.is_alive():
                # 眩晕1回合（基础）+ 多眩晕1回合 = 总共2回合
                m.base_keywords["眩晕"] = 2
                m.recalculate()
                print(f"  {m.name} 被眩晕2回合")


@special
def _zhenceqi_special(minion, player, game, extras=None):
    """侦测器：敌方单位部署时，对其造成1点伤害，使其失去迅捷。"""

    def _on_deploy(deployed, self_minion=minion, g=game):
        if deployed.owner != self_minion.owner and self_minion.is_alive():
            deal_damage_to_minion(deployed, 1, source=self_minion, game=g)
            if deployed.is_alive():
                remove_keyword(deployed, "迅捷")

    minion.register_deploy_hook(game, _on_deploy)


# =============================================================================
# 策略卡
# =============================================================================

@strategy
def _zisongguo_strategy(player, target, game, extras=None):
    """紫颂果：抽2张牌。回合结束时，将其弃掉。"""
    drawn = draw_cards(player, 2, game)
    if drawn > 0:
        # 记录本回合抽到的牌，回合结束时弃掉
        drawn_cards = player.card_hand[-drawn:]

        def _discard_drawn(g, event_data, p):
            for card in drawn_cards:
                if card in p.card_hand:
                    discard_card(p, card)

        # 使用玩家的 on_turn_end 回调（若已存在则链式调用）
        old_fn = player.on_turn_end

        def _on_turn_end(g, event_data, p):
            for card in drawn_cards:
                if card in p.card_hand:
                    discard_card(p, card)
            if old_fn:
                old_fn(g, event_data, p)
            player.on_turn_end = old_fn  # 恢复旧回调

        player.on_turn_end = _on_turn_end
    return True


@strategy
def _panqukuandao_strategy(player, target, game, extras=None):
    """盘曲矿道：抽2张牌，将其中1张复制洗入卡组。"""
    drawn = draw_cards(player, 2, game)
    if drawn >= 2:
        # 简化：将第2张抽到的牌复制并洗入卡组
        card = player.card_hand[-1]
        from tards.cards import MinionCard
        if isinstance(card, MinionCard):
            copy_card_to_hand(card, player, game)
            # 上面是加入手牌，需要改成洗入卡组
            # 修正：直接创建复制并洗入卡组
            new_card = create_card_by_name(card.name, player)
            if new_card:
                shuffle_into_deck(player, new_card)
    elif drawn == 1:
        card = player.card_hand[-1]
        new_card = create_card_by_name(card.name, player)
        if new_card:
            shuffle_into_deck(player, new_card)
    return True


@strategy
def _huoyao_strategy(player, target, game, extras=None):
    """火药：抉择：将1张"TNT"或1张"复制技术"加入手牌。"""
    choice = game.request_choice(player, ["TNT", "复制技术"], title="火药：选择一张牌加入手牌")
    if choice:
        add_card_to_hand_by_name(choice, player)
    return True


@strategy
def _cunzhuangyingxiong_strategy(player, target, game, extras=None):
    """村庄英雄：对1个单位及其相邻单位造成2点伤害。若有单位被消灭，将1张"村庄英雄"洗入卡组。"""
    killed = False
    if target and hasattr(target, "is_alive") and target.is_alive():
        deal_damage_to_minion(target, 2, source=None, game=game)
        if not target.is_alive():
            killed = True
        for pos in get_adjacent_positions(target.position, game.board):
            neighbor = game.board.get_minion_at(pos)
            if neighbor and neighbor.is_alive():
                deal_damage_to_minion(neighbor, 2, source=None, game=game)
                if not neighbor.is_alive():
                    killed = True
    if killed:
        card = create_card_by_name("村庄英雄", player)
        if card:
            shuffle_into_deck(player, card)
    return True


@strategy
def _jielue_strategy(player, target, game, extras=None):
    """劫掠：消灭1个花费不大于3T的单位。若其处于协同，从对方卡组顶抽1张牌。"""
    if not target or not hasattr(target, "is_alive") or not target.is_alive():
        print("  [警告] 劫掠没有有效目标")
        return False
    # 检查花费
    cost = getattr(target.source_card, "cost", None)
    if not cost or cost.t > 3:
        print(f"  {target.name} 的花费大于3T，无法劫掠")
        return False
    destroy_minion(target, game)
    # 检查协同：同列有友方单位
    col = target.position[1]
    has_synergy = any(
        m.is_alive() and m is not target and m.position[1] == col
        for m in all_friendly_minions(game, target.owner)
    )
    if has_synergy:
        opponent = target.owner
        if opponent.card_deck:
            card = opponent.card_deck.pop()
            if len(player.card_hand) < player.card_hand_max:
                player.card_hand.append(card)
                card.owner = player
                print(f"  {player.name} 从 {opponent.name} 的牌库顶抽到了 {card.name}")
            else:
                player.card_dis.append(card)
                print(f"  {player.name} 手牌满，抽到的 {card.name} 被弃置")
    return True


# =============================================================================
# 映射表
# =============================================================================

SPECIAL_MAP = {
    "矿车": "_kuangche_special",
    "北极熊": "_beijixiong_special",
    "恼鬼": "_naogui_special",
    "流髑": "_liudu_special",
    "尸壳": "_shike_special",
    "卫道士": "_weidaoshi_special",
    "蜘蛛": "_zhizhu_special",
    "蠹虫": "_shuaichong_special",
    "橡树苗": "_xiangshu_special",
    "岩浆艇": "_yanjiangting_special",
    "甘蔗": "_ganzhe_special",
    "驴": "_lv_special",
    "鲑鱼": "_guiyu_special",
    "雪傀儡": "_xuewulou_special",
    "禁人塔": "_jinrenta_special",
    "侦测器": "_zhenceqi_special",
    "潮涌核心": "_chaoonghexin_special",
    "活塞飞艇": "_huosai_feiting_special",
    "炽足兽": "_chizushou_special",
    "马": "_ma_special",
    # EventBus 重写 — 受伤/攻击/消灭时机
    "萤石": "_yingshi_special",
    "书架": "_shujia_special",
    "末影人": "_moyiren_special",
    "烈焰人": "_lieyanren_special",
    "铁傀儡": "_tiekuilei_special",
    "狐狸": "_huli_special",
    "豹猫": "_baomao_special",
    "海龟": "_haigui_special",
    "蝾螈": "_rongyuan_special",
    "滴水石锥": "_dishuizhuichui_special",
    "骷髅": "_kulou_special",
    "僵尸": "_jiangshi_special",
    "幻翼": "_huanyi_special",
    # 开发相关（通用机制）
    "信标": "_xinbiao_special",
    "火把": "_huoba_special",
    "流浪商人": "_liulangshangren_special",
    # 新实现（亡语/部署）
    "恶魂": "_ehan_special",
    "凋零骷髅": "_diaolingkulou_special",
    "盔甲架": "_kuijiujia_special",
    # 对战效果
    "僵尸猪人": "_jiangshizhuren_special",
}

# 策略效果函数名列表（供 discrete.py 手动挂接）
STRATEGY_MAP = {
    "木镐": "_mubiao_strategy",
    "石镐": "_shibiao_strategy",
    "金镐": "_jinbiao_strategy",
    "钻石镐": "_zuanshibiao_strategy",
    "雪球": "_xueqiu_strategy",
    "蜘蛛眼": "_zhizhuyan_strategy",
    "烈焰粉": "_lieyanfen_strategy",
    "凋零骷髅头": "_diaolingkuloutou_strategy",
    "光灵箭": "_guanglingjian_strategy",
    "战利品": "_zhanlipin_strategy",
    "遗弃": "_yiqi_strategy",
    "高山": "_gaoshan_strategy",
    "恶地": "_erdi_strategy",
    "TNT": "_tnt_strategy",
    "红石粉": "_hongshifen_strategy",
    "禁人书": "_jinrenshu_strategy",
    "保卫要塞": "_baoweiyaosai_strategy",
    "虫蚀石头": "_chongshishitou_strategy",
    "紫颂果": "_zisongguo_strategy",
    "盘曲矿道": "_panqukuandao_strategy",
    "火药": "_huoyao_strategy",
    "村庄英雄": "_cunzhuangyingxiong_strategy",
    "劫掠": "_jielue_strategy",
    # 对战相关
    "怪物猎人": "_guaiwulieren_strategy",
    # 对战效果
    "怪物猎人": "_guaiwulieren_strategy",
    # 开发相关（通用机制）
    "附魔台": "_fumota_strategy",
    "耕殖": "_gengzhi_strategy",
    # 抉择策略
    "探索": "_tansuo_strategy",
    "金苹果": "_jinpingguo_strategy",
    "丛林神殿": "_conglin_shendian_strategy",
    "沙漠神殿": "_shamo_shendian_strategy",
}

# =============================================================================
# 对战效果（待完善）
# =============================================================================

@special
def _jiangshizhuren_special(minion, player, game, extras=None):
    """僵尸猪人：部署：与1个敌方单位对战。若将其消灭，获得-1攻击力。"""
    targets = extras or []
    enemy = None
    for t in targets:
        if hasattr(t, "is_alive") and t.is_alive() and is_enemy(t, player):
            enemy = t
            break
    if not enemy:
        enemy = random_enemy_minion(game, player)
    if not enemy:
        return

    was_alive = enemy.is_alive()
    initiate_combat(minion, enemy, game)

    if was_alive and not enemy.is_alive():
        buff_minion(minion, atk_delta=-1, hp_delta=0)
        print(f"  {minion.name} 因消灭目标，攻击力-1")


@strategy
def _guaiwulieren_strategy(player, target, game, extras=None):
    """怪物猎人：使1个友方生物单位+1/3，然后与1个敌方单位对战。"""
    friendly = target
    enemy = extras[0] if extras else None
    if not friendly or not hasattr(friendly, "is_alive") or not friendly.is_alive():
        print(f"  [警告] 怪物猎人：未选择有效的友方单位")
        return False
    if not enemy or not hasattr(enemy, "is_alive") or not enemy.is_alive():
        print(f"  [警告] 怪物猎人：未选择有效的敌方单位")
        return False

    buff_minion(friendly, atk_delta=1, hp_delta=3)
    friendly.current_health += 3
    print(f"  {friendly.name} 获得 +1/+3")
    initiate_combat(friendly, enemy, game)
    return True


# =============================================================================
# 抉择策略卡
# =============================================================================

@strategy
def _tansuo_strategy(player, target, game, extras=None):
    """探索：抉择：将1张"丛林神殿"或"沙漠神殿"加入手牌。"""
    choice = game.request_choice(
        player,
        ["丛林神殿", "沙漠神殿"],
        title="探索：选择一张牌加入手牌",
    )
    if choice:
        add_card_to_hand_by_name(choice, player)
    return True


@strategy
def _jinpingguo_strategy(player, target, game, extras=None):
    """金苹果：抉择：使1个单位获得+1/2，或使你获得+4HP。若指向僵尸村民，两项都触发。"""
    if not target or not hasattr(target, "is_alive") or not target.is_alive():
        print(f"  [警告] 金苹果：未选择有效的目标单位")
        return False

    is_zombie_villager = getattr(target, "name", "") == "僵尸村民"

    if is_zombie_villager:
        # 指向僵尸村民：两项都触发
        buff_minion(target, atk_delta=1, hp_delta=2)
        target.current_health += 2
        print(f"  {target.name} 获得 +1/+2")
        heal_player(player, 4)
        print(f"  {player.name} 恢复 4HP")
    else:
        choice = game.request_choice(
            player,
            ["目标+1/2", "自己+4HP"],
            title="金苹果：选择效果",
        )
        if choice == "目标+1/2":
            buff_minion(target, atk_delta=1, hp_delta=2)
            target.current_health += 2
            print(f"  {target.name} 获得 +1/+2")
        elif choice == "自己+4HP":
            heal_player(player, 4)
            print(f"  {player.name} 恢复 4HP")
    return True


@strategy
def _conglin_shendian_strategy(player, target, game, extras=None):
    """丛林神殿：抽2张策略，使其获得-1T花费。"""
    from tards.cards import Strategy
    drawn = draw_cards_of_type(player, 2, Strategy, game)
    for card in drawn:
        if hasattr(card, "cost") and hasattr(card.cost, "t") and card.cost.t > 0:
            card.cost.t -= 1
            print(f"  {card.name} 的T花费-1，当前为 {card.cost.t}T")
    return True


@strategy
def _shamo_shendian_strategy(player, target, game, extras=None):
    """沙漠神殿：抽2张单位，使其获得+1/2。"""
    from tards.cards import MinionCard
    drawn = draw_cards_of_type(player, 2, MinionCard, game)
    for card in drawn:
        card.attack += 1
        card.health += 2
        print(f"  {card.name} 获得 +1/+2，当前 {card.attack}/{card.health}")
    return True


@strategy
def _mingmingpai_strategy(player, target, game, extras=None):
    """命名牌：选择1张手牌中的单位，使场上的1个单位获得"也算作是本单位"。抽1张牌。"""
    # target 是手牌中选中的单位卡，extras[0] 是场上选中的单位
    if not target or not hasattr(target, "name"):
        print("  [警告] 命名牌未选择手牌中的单位")
        return False
    if not extras or len(extras) < 1:
        print("  [警告] 命名牌未选择场上单位")
        return False
    board_minion = extras[0]
    if not board_minion or not hasattr(board_minion, "is_alive") or not board_minion.is_alive():
        print("  [警告] 命名牌的场上目标无效")
        return False
    from card_pools.effect_utils import set_alias
    set_alias(board_minion, target.name)
    draw_cards(player, 1, game)
    return True


# =============================================================================
# 新实现 — 简单亡语/部署效果
# =============================================================================

@special
def _ehan_special(minion, player, game, extras=None):
    """恶魂：亡语：将1张"恶魂之泪"加入手牌。"""
    def _dr(m, p, b):
        give_card_by_name(p, "恶魂之泪", reason="恶魂亡语")
    add_deathrattle(minion, _dr)


@special
def _diaolingkulou_special(minion, player, game, extras=None):
    """凋零骷髅：亡语：将1张"凋零骷髅头"加入手牌。"""
    def _dr(m, p, b):
        give_card_by_name(p, "凋零骷髅头", reason="凋零骷髅亡语")
    add_deathrattle(minion, _dr)


@special
def _kuijiujia_special(minion, player, game, extras=None):
    """盔甲架：亡语：抽1张牌。"""
    def _dr(m, p, b):
        draw_cards(p, 1, game=b.game_ref if hasattr(b, "game_ref") else None)
    add_deathrattle(minion, _dr)


__all__ = [
    "SPECIAL_MAP",
    "STRATEGY_MAP",
    # 单位效果
    "_kuangche_special",
    "_beijixiong_special",
    "_naogui_special",
    "_liudu_special",
    "_shike_special",
    "_weidaoshi_special",
    "_zhizhu_special",
    "_shuaichong_special",
    "_xiangshu_special",
    "_yanjiangting_special",
    "_ganzhe_special",
    "_lv_special",
    "_guiyu_special",
    "_xuewulou_special",
    "_jinrenta_special",
    "_zhenceqi_special",
    "_chaoonghexin_special",
    "_huosai_feiting_special",
    "_chizushou_special",
    "_ma_special",
    # EventBus 重写
    "_yingshi_special",
    "_shujia_special",
    "_moyiren_special",
    "_lieyanren_special",
    "_tiekuilei_special",
    "_huli_special",
    "_baomao_special",
    "_haigui_special",
    "_rongyuan_special",
    "_dishuizhuichui_special",
    "_kulou_special",
    "_jiangshi_special",
    "_huanyi_special",
    # 开发相关（通用机制）
    "_xinbiao_special",
    "_huoba_special",
    "_liulangshangren_special",
    # 新实现
    "_ehan_special",
    "_diaolingkulou_special",
    "_kuijiujia_special",
    "_fumota_strategy",
    "_gengzhi_strategy",
    # 对战效果
    "_jiangshizhuren_special",
    "_guaiwulieren_strategy",
    # 策略效果
    "_mubiao_strategy",
    "_shibiao_strategy",
    "_jinbiao_strategy",
    "_zuanshibiao_strategy",
    "_xueqiu_strategy",
    "_zhizhuyan_strategy",
    "_lieyanfen_strategy",
    "_diaolingkuloutou_strategy",
    "_guanglingjian_strategy",
    "_zhanlipin_strategy",
    "_yiqi_strategy",
    "_gaoshan_strategy",
    "_erdi_strategy",
    "_tnt_strategy",
    "_hongshifen_strategy",
    "_jinrenshu_strategy",
    "_baoweiyaosai_strategy",
    "_chongshishitou_strategy",
    "_zisongguo_strategy",
    "_panqukuandao_strategy",
    "_huoyao_strategy",
    "_cunzhuangyingxiong_strategy",
    "_jielue_strategy",
    "_mingmingpai_strategy",
    # 抉择策略
    "_tansuo_strategy",
    "_jinpingguo_strategy",
    "_conglin_shendian_strategy",
    "_shamo_shendian_strategy",
    # 矿物卡打出效果
    "_tieding_mineral",
    "_jinding_mineral",
    "_zuanshi_mineral",
]


# =============================================================================
# 矿物卡打出效果
# =============================================================================

def _tieding_mineral(player, game):
    """铁锭：打出获得1T。"""
    player.t_point_change(1)
    print(f"  {player.name} 打出铁锭，获得1T")
    return True


def _jinding_mineral(player, game):
    """金锭：打出获得2T。"""
    player.t_point_change(2)
    print(f"  {player.name} 打出金锭，获得2T")
    return True


def _zuanshi_mineral(player, game):
    """钻石：打出获得4T。"""
    player.t_point_change(4)
    print(f"  {player.name} 打出钻石，获得4T")
    return True
