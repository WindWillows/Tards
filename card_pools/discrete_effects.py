#!/usr/bin/env python3
"""离散卡包人工效果实现。

通过 SPECIAL_MAP 将卡牌名映射到对应的 special_fn 函数。
策略效果函数直接使用 @strategy 装饰器，在 discrete.py 中手动挂接 effect_fn。
"""

import random

from tards import Pack, Rarity, CardType
from tards.targets import target, target_mix
from tards.cards import Minion, MineralCard
from tards.player import Player
from card_pools.effect_decorator import special, strategy
from card_pools.effect_utils import (
    ENCHANTED_BOOK_POOL,
    get_enchanted_book_definitions,
    add_card_to_hand_by_name,
    add_deathrattle,
    add_event_listener,
    all_enemy_minions,
    all_friendly_minions,
    auto_attack,
    buff_minion,
    copy_card_to_hand,
    create_card_by_name,
    deal_damage_to_minion,
    discover_from_deck_top,
    deal_damage_to_player,
    destroy_minion,
    discard_card,
    draw_cards,
    draw_cards_of_type,
    empty_positions,
    gain_keyword,
    get_adjacent_positions,
    get_all_minions,
    give_card_by_name,
    heal_player,
    initiate_combat,
    is_enemy,
    modify_keyword_number,
    nearest_enemy_minion,
    on,
    on_after_damage,
    on_after_attack,
    on_before_attack,
    on_before_damage,
    on_before_destroy,
    on_damaged,
    on_turn_end,
    on_turn_start,
    random_enemy_minion,
    remove_keyword,
    remove_minion_no_death,
    remove_top_of_deck,
    return_minion_to_hand,
    search_deck,
    shuffle_into_deck,
    summon_token,
    swap,
    was_minion_deployed_this_turn,
    convert_cost_to_t,
)

@special
def _diaoyugan_special(minion, player, game, extras=None):
    """钓鱼竿：回合结束：将1张"书"加入手牌。"""

    def _on_turn_end(event):
        if not minion.is_alive():
            return
        give_card_by_name(player, "书", reason="钓鱼竿效果")

    on_turn_end(minion, game, _on_turn_end)


@special
def _gou_special(minion, player, game, extras=None):
    """狗：处于协同时，具有+1攻击力。亡语：同列友方异象立刻攻击1次。"""

    def aura_fn(m):
        if m is not minion:
            return 0
        if not minion.is_alive():
            return 0
        col = minion.position[1] if minion.position else -1
        if col < 0:
            return 0
        friendlies = [m2 for m2 in game.board.get_minions_in_column(col, friendly_to=player)
                      if m2 is not minion and m2.is_alive()]
        return 1 if friendlies else 0

    minion.add_aura_attack(aura_fn)

    def _dr(m, p, b):
        from card_pools.effect_utils import perform_attack_action
        col = m.position[1] if m.position else -1
        if col < 0:
            return
        friends = [m2 for m2 in b.get_minions_in_column(col, friendly_to=p)
                   if m2 is not m and m2.is_alive()]
        g = b.game_ref
        if not g:
            return
        for friend in friends:
            perform_attack_action(friend, g)

    add_deathrattle(minion, _dr)


@special
def _yang_special(minion, player, game, extras=None):
    """羊：回合结束：若其为本回合唯一部署的友方异象，抽1张牌，将其花费改为0T。"""
    from card_pools.effect_utils import minions_deployed_this_turn

    def _on_turn_end(event):
        if not minion.is_alive():
            return
        if minions_deployed_this_turn(game, player) != 1:
            return
        if not was_minion_deployed_this_turn(game, minion):
            return
        before = len(player.card_hand)
        player.draw_card(1, game=game)
        after = len(player.card_hand)
        if after > before:
            drawn = player.card_hand[-1]
            if hasattr(drawn, 'cost') and drawn.cost:
                drawn.cost.t = 0
                print(f"  {drawn.name} 的花费变为 0T")

    on_turn_end(minion, game, _on_turn_end)


@special
def _zhu_special(minion, player, game, extras=None):
    """猪：部署：指向1个异象，为其承担伤害。"""
    targets = extras or []
    if not targets:
        return True
    protected = targets[0]
    if not hasattr(protected, "is_alive") or not protected.is_alive():
        return True

    print(f"  {minion.name} 开始为 {protected.name} 承担伤害")

    def redirect(event):
        if getattr(minion, "_zhu_redirecting", False):
            return
        target = event.data.get("target")
        if target is not protected:
            return
        damage = event.data.get("damage", 0)
        if damage <= 0:
            return
        if not minion.is_alive():
            return
        event.cancelled = True
        event.data["damage"] = 0
        print(f"  {protected.name} 本应受到 {damage} 点伤害，由 {minion.name} 承担")
        minion._zhu_redirecting = True
        try:
            source = event.data.get("source_minion")
            minion.take_damage(damage, source_minion=source)
        finally:
            minion._zhu_redirecting = False

    on_before_damage(minion, game, redirect)
    return True


@special
def _yangtuo_special(minion, player, game, extras=None):
    """羊驼：受到其伤害的异象获得-1攻击力。然后若其攻击力为0，将其消灭。"""

    def on_dmg(event):
        source = event.data.get("source_minion")
        if source is not minion:
            return
        target = event.data.get("target")
        if not target or not hasattr(target, "is_alive") or not target.is_alive():
            return
        target.gain_attack(-1, permanent=True)
        print(f"  {target.name} 受到羊驼伤害，攻击力变为 {target.attack}")
        if target.attack <= 0:
            print(f"  {target.name} 攻击力为0，被消灭")
            destroy_minion(target, game)

    on_after_damage(minion, game, on_dmg)


@special
def _yingwu_special(minion, player, game, extras=None):
    """鹦鹉：结算阶段开始：将出牌阶段对方使用的首张策略的复制加入手牌。"""
    from tards.cards import Strategy

    def on_card_played(event):
        source_player = event.data.get("player")
        if source_player is player:
            return
        card = event.data.get("card")
        if not card or not isinstance(card, Strategy):
            return
        if getattr(minion, "_yingwu_copied_this_turn", False):
            return
        minion._yingwu_target_card = card
        minion._yingwu_copied_this_turn = True

    on("card_played", on_card_played, game, minion)

    def on_phase_start(event):
        if event.data.get("phase") != game.PHASE_RESOLVE:
            return
        if not minion.is_alive():
            return
        target_card = getattr(minion, "_yingwu_target_card", None)
        if target_card:
            copied = Strategy(
                name=target_card.name,
                cost=target_card.cost.copy(),
                effect_fn=target_card.effect_fn,
                targets=target_card.targets,
                on_turn_start=getattr(target_card, "on_turn_start", None),
                on_turn_end=getattr(target_card, "on_turn_end", None),
                on_phase_start=getattr(target_card, "on_phase_start", None),
                on_phase_end=getattr(target_card, "on_phase_end", None),
            )
            if len(player.card_hand) < player.card_hand_max:
                player.card_hand.append(copied)
            else:
                player.card_dis.append(copied)
            print(f"  {player.name} 获得 {target_card.name} 的复制")
            minion._yingwu_target_card = None
        minion._yingwu_copied_this_turn = False

    on("phase_start", on_phase_start, game, minion)


@special
def _hetun_special(minion, player, game, extras=None):
    """河豚：亡语：造成等同于其受到过伤害总和的伤害，随机分配至所有敌方异象。"""
    minion._hetun_damage_taken = 0

    def on_after_damage(event):
        if event.data.get("target") is not minion:
            return
        actual = event.data.get("actual", 0)
        if actual > 0:
            minion._hetun_damage_taken += actual

    on("after_damage", on_after_damage, game, minion)

    def _hetun_deathrattle(m, p, b):
        total = getattr(m, "_hetun_damage_taken", 0)
        if total <= 0:
            return
        g = b.game_ref
        enemies = [mm for mm in b.minion_place.values() if mm.owner != p and mm.is_alive()]
        if not enemies:
            return
        for _ in range(total):
            alive_enemies = [mm for mm in enemies if mm.is_alive()]
            if not alive_enemies:
                break
            target = random.choice(alive_enemies)
            deal_damage_to_minion(target, 1, source=m, game=g)

    add_deathrattle(minion, _hetun_deathrattle)


@special
def _cunmin_special(minion, player, game, extras=None):
    """村民：每回合每种矿物被首次兑换时，获得1T。"""
    minion._cunmin_exchanged = set()
    minion._cunmin_turn = -1

    def on_mineral_exchanged(event):
        if not minion.is_alive():
            return
        exch_player = event.data.get("player")
        if exch_player is not player:
            return
        card = event.data.get("card")
        if not card or not hasattr(card, "mineral_type"):
            return
        mineral_type = card.mineral_type
        current_turn = game.current_turn
        if current_turn != minion._cunmin_turn:
            minion._cunmin_exchanged.clear()
            minion._cunmin_turn = current_turn
        if mineral_type not in minion._cunmin_exchanged:
            minion._cunmin_exchanged.add(mineral_type)
            player.t_point += 1
            print(f"  {player.name} 的村民触发：首次兑换 {mineral_type}，获得1T")

    on("mineral_exchanged", on_mineral_exchanged, game, minion)


@special
def _youzhu_special(minion, player, game, extras=None):
    """疣猪：双方无法部署花费不大于4T的异象。"""
    def _restriction(p, card):
        from tards.cards import MinionCard
        if not isinstance(card, MinionCard):
            return True
        if not minion.is_alive():
            return True
        if card.cost.t <= 4:
            return False
        return True

    game._global_deploy_restrictions.append(_restriction)


@special
def _zhuling_special(minion, player, game, extras=None):
    """猪灵：每回合首次使用金锭时，随机将1张掉落物加入手牌。"""
    minion._zhuling_used_gold = False

    def on_card_played(event):
        if not minion.is_alive():
            return
        source_player = event.data.get("player")
        if source_player is not player:
            return
        card = event.data.get("card")
        if not card or not hasattr(card, "mineral_type") or card.mineral_type != "G":
            return
        if minion._zhuling_used_gold:
            return
        minion._zhuling_used_gold = True
        from card_pools.effect_utils import DROP_POOL
        if DROP_POOL:
            drop_def = random.choice(DROP_POOL)
            drop_card = drop_def.to_game_card(player)
            if len(player.card_hand) < player.card_hand_max:
                player.card_hand.append(drop_card)
            else:
                player.card_dis.append(drop_card)
            print(f"  {player.name} 的猪灵触发：获得 {drop_card.name}")
        else:
            print(f"  {player.name} 的猪灵触发：掉落物卡池为空")

    on("card_played", on_card_played, game, minion)

    def _zhuling_turn_start(event):
        if not minion.is_alive():
            return
        minion._zhuling_used_gold = False

    on_turn_start(minion, game, _zhuling_turn_start)


@special
def _zhulingmanbing_special(minion, player, game, extras=None):
    """猪灵蛮兵：友方友好异象无法被选中。"""

    def _is_friendly_friendly(m):
        return "友好" in getattr(m, "tags", []) and m.owner == player

    def _apply_protection():
        for m in player.minions_on_board:
            if _is_friendly_friendly(m):
                m._untargetable_by_minions = True

    def _remove_protection():
        for m in player.minions_on_board:
            if _is_friendly_friendly(m):
                m._untargetable_by_minions = False

    def filter_fn(target, source):
        if not minion.is_alive():
            return False
        if hasattr(target, "is_alive") and not target.is_alive():
            return False
        if _is_friendly_friendly(target):
            return True
        return False

    entry = {"filter": filter_fn, "reason": "猪灵蛮兵", "once": False}
    game._target_protections.append(entry)
    _apply_protection()

    def on_deployed(event):
        if not minion.is_alive():
            return
        new_m = event.data.get("minion")
        if new_m and new_m.owner == player and "友好" in getattr(new_m, "tags", []):
            new_m._untargetable_by_minions = True

    on("deployed", on_deployed, game, minion)

    def _cleanup(event):
        if getattr(event, "cancelled", False):
            return
        _remove_protection()
        try:
            game._target_protections.remove(entry)
        except ValueError:
            pass

    on("before_destroy", _cleanup, game, minion)


@special
def _zhulinggongbing_special(minion, player, game, extras=None):
    """猪灵弓兵：一回合内，此前每攻击过目标1次，对其攻击力-1。每消灭1个异象，将1张"光灵箭"加入手牌。"""
    minion._gongbing_attack_count = {}
    minion._gongbing_prev_penalty = 0

    def _pre_attack(gb, target):
        from tards.cards import Minion
        if not isinstance(target, Minion):
            return
        # 清除之前的修正
        prev = getattr(gb, "_gongbing_prev_penalty", 0)
        gb.temp_attack_bonus -= prev
        # 计算新修正
        count = gb._gongbing_attack_count.get(target, 0)
        penalty = -count
        gb.temp_attack_bonus += penalty
        gb._gongbing_prev_penalty = penalty
        gb.recalculate()

    if not hasattr(minion, "_pre_attack_fns"):
        minion._pre_attack_fns = []
    minion._pre_attack_fns.append(_pre_attack)

    def _after_attack(event):
        gb = event.data.get("attacker")
        target = event.data.get("target")
        if gb is not minion:
            return
        if isinstance(target, Minion):
            gb._gongbing_attack_count[target] = gb._gongbing_attack_count.get(target, 0) + 1

    on("after_attack", _after_attack, game, minion)

    def _on_turn_start(event):
        if not minion.is_alive():
            return
        minion._gongbing_attack_count.clear()
        prev = getattr(minion, "_gongbing_prev_penalty", 0)
        if prev != 0:
            minion.temp_attack_bonus += prev
            minion._gongbing_prev_penalty = 0
            minion.recalculate()

    on_turn_start(minion, game, _on_turn_start)

    def _on_after_damage(event):
        if event.data.get("source_minion") is not minion:
            return
        target = event.data.get("target")
        if not target or not isinstance(target, Minion):
            return
        if target.current_health <= 0 and not getattr(target, "_pending_death", False):
            from tards.card_db import DEFAULT_REGISTRY
            glj_def = DEFAULT_REGISTRY.get("光灵箭")
            if glj_def:
                glj = glj_def.to_game_card(player)
                if len(player.card_hand) < player.card_hand_max:
                    player.card_hand.append(glj)
                else:
                    player.card_dis.append(glj)
                print(f"  {player.name} 获得光灵箭")

    on("after_damage", _on_after_damage, game, minion)


@special
def _cunmin2_special(minion, player, game, extras=None):
    """刌民：友方每有1个敌对异象和中立异象，具有+1攻击力。"""

    def _cunmin_attack_aura(m):
        if not m.is_alive():
            return 0
        count = sum(
            1 for mm in m.owner.minions_on_board
            if "敌对" in getattr(mm, "tags", []) or "中立" in getattr(mm, "tags", [])
        )
        return count

    if not hasattr(minion, "_aura_attack_fns"):
        minion._aura_attack_fns = []
    minion._aura_attack_fns.append(_cunmin_attack_aura)
    minion.recalculate()

    def _refresh(event):
        if minion.is_alive():
            minion.recalculate()

    on("deployed", _refresh, game, minion)
    on("death", _refresh, game, minion)

    def _cleanup(event):
        if getattr(event, "cancelled", False):
            return
        if _cunmin_attack_aura in getattr(minion, "_aura_attack_fns", []):
            minion._aura_attack_fns.remove(_cunmin_attack_aura)
            minion.recalculate()

    on("before_destroy", _cleanup, game, minion)


@special
def _qianyingbei_special(minion, player, game, extras=None):
    """潜影贝：敌方异象受到1点伤害后，在回合结束时返回手牌。"""
    minion._qianying_targets = set()

    def on_after_damage(event):
        if not minion.is_alive():
            return
        target = event.data.get("target")
        if not isinstance(target, Minion):
            return
        if target.owner == player:
            return
        actual = event.data.get("actual", 0)
        if actual >= 1:
            minion._qianying_targets.add(target)

    on("after_damage", on_after_damage, game, minion)

    def _qianying_turn_end(event):
        if not minion.is_alive():
            return
        targets = list(minion._qianying_targets)
        minion._qianying_targets.clear()
        for t in targets:
            if t.is_alive() and t.position in game.board.minion_place and game.board.minion_place[t.position] is t:
                return_minion_to_hand(t, game)

    on_turn_end(minion, game, _qianying_turn_end)


@special
def _huanmozhe_special(minion, player, game, extras=None):
    """唤魔者：回合开始：将1张精灵异象加入战场，使其具有迅捷。场上有精灵异象时，无法选中。"""

    def _has_spirit_on_board():
        return any(
            "精灵" in getattr(m, "tags", [])
            for m in game.board.minion_place.values()
            if m is not minion
        )

    def _update_untargetable():
        if not minion.is_alive():
            return
        minion._untargetable_by_minions = _has_spirit_on_board()

    def _summon_spirit():
        from tards.card_db import DEFAULT_REGISTRY, CardType
        from card_pools.effect_utils import empty_positions
        spirits = [
            c for c in DEFAULT_REGISTRY.all_cards()
            if hasattr(c, "tags") and "精灵" in c.tags
            and hasattr(c, "card_type") and c.card_type == CardType.MINION
            and c.name != "唤魔者"
        ]
        if not spirits:
            print("  [警告] 没有可用的精灵异象")
            return
        spirit_def = random.choice(spirits)
        spirit_card = spirit_def.to_game_card(player)
        empties = empty_positions(player, game.board)
        if not empties:
            print(f"  {player.name} 战场已满，无法召唤精灵")
            return
        target_pos = empties[0]
        if not game.board.is_valid_deploy(target_pos, player, spirit_card):
            print(f"  {target_pos} 无法部署 {spirit_card.name}")
            return
        ok = spirit_card.effect(player, target_pos, game)
        if ok:
            summoned = game.board.get_minion_at(target_pos)
            if summoned:
                summoned.keywords["迅捷"] = True
                print(f"  {summoned.name} 获得迅捷")

    def _huanmo_turn_start(event):
        if not minion.is_alive():
            return
        _summon_spirit()
        _update_untargetable()

    on_turn_start(minion, game, _huanmo_turn_start)

    def on_deployed(event):
        _update_untargetable()

    on("deployed", on_deployed, game, minion)

    def on_death(event):
        _update_untargetable()

    on("death", on_death, game, minion)

    # 策略指向保护
    def _huanmo_filter(target, source):
        if target is not minion:
            return False
        if not minion.is_alive():
            return False
        return _has_spirit_on_board()

    def _register_protection():
        game._target_protections.append({
            "filter": _huanmo_filter,
            "reason": "唤魔者",
            "once": False,
        })

    _register_protection()
    _update_untargetable()


@special
@special
def _haitun_special(minion, player, game, extras=None):
    """海豚：部署：展示卡组顶的3张牌，选择1张加入手牌，另2张置入卡组底。"""
    discover_from_deck_top(player, 3, game, title="海豚：选择1张牌加入手牌")


@special
def _jielueduizhang_special(minion, player, game, extras=None):
    """劫掠队长：回合结束：若本回合对手受到的伤害不小于3，使对手失去2点HP。"""
    from card_pools.effect_utils import damage_dealt_to_players_this_turn, get_opponent

    def on_phase_end(event):
        if event.data.get("phase") != game.PHASE_RESOLVE:
            return
        if not minion.is_alive():
            return
        opponent = get_opponent(game, player)
        damage = damage_dealt_to_players_this_turn(game, opponent)
        if damage >= 3:
            opponent.health_change(-2)
            print(f"  {opponent.name} 失去2点HP（本回合受到 {damage} 点伤害）")

    on("phase_end", on_phase_end, game, minion)


@special
def _jiangshicunmin_special(minion, player, game, extras=None):
    """僵尸村民：部署：将1张'金苹果'置入卡组顶。被'金苹果'指向时，抽1张牌，使你的所有手牌获得-1T花费。"""

    # 部署：将金苹果置入卡组顶
    from tards.card_db import DEFAULT_REGISTRY
    jpg_def = DEFAULT_REGISTRY.get("金苹果")
    if jpg_def:
        jpg_card = jpg_def.to_game_card(player)
        player.card_deck.insert(0, jpg_card)
        print(f"  {player.name} 将金苹果置入卡组顶")

    # 标记自身，供金苹果策略检测
    minion._jiangshicunmin_bonus = True


@special
def _moyingxiang_special(minion, player, game, extras=None):
    """末影箱：你每在手牌已满时抽1张牌，对一个随机敌方目标造成2点伤害。"""

    def on_milled(event):
        if event.data.get("player") is not player:
            return
        if not minion.is_alive():
            return
        target = random_enemy_minion(game, player)
        if target:
            deal_damage_to_minion(target, 3, source=minion, game=game)
            print(f"  末影箱对 {target.name} 造成3点伤害（手牌已满时抽牌）")
        else:
            opponent = game.p2 if player == game.p1 else game.p1
            deal_damage_to_player(opponent, 3, source=minion, game=game)
            print(f"  末影箱对 {opponent.name} 造成3点伤害（手牌已满时抽牌）")

    on("milled", on_milled, game, minion)


@special
def _qianxingzhe_special(minion, player, game, extras=None):
    """潜行者：部署：消灭1个与本异象距离最近的异象。"""

    target = nearest_enemy_minion(minion, game)
    if target:
        destroy_minion(target, game)
        print(f"  潜行者消灭了距离最近的 {target.name}")
    else:
        print("  潜行者：场上没有敌方异象")


@special
def _jiangshijiqishi_special(minion, player, game, extras=None):
    """僵尸鸡骑士：部署：如可能，移除卡组顶的一张友好单位。若如此做，获得迅捷和先攻1。"""
    from tards.cards import MinionCard

    found = None
    # 从卡组顶（列表末尾）向下寻找第一张友好异象
    for i in range(len(player.card_deck) - 1, -1, -1):
        card = player.card_deck[i]
        if isinstance(card, MinionCard) and "友好" in getattr(card, "tags", []):
            found = card
            del player.card_deck[i]
            print(f"  僵尸鸡骑士移除了卡组顶的友好异象 {card.name}")
            break

    if found:
        gain_keyword(minion, "迅捷", game)
        modify_keyword_number(minion, "先攻", 1)
        print("  僵尸鸡骑士获得迅捷和先攻1")
    else:
        print("  僵尸鸡骑士：卡组顶没有友好异象")


@special
def _kuloumaqishi_special(minion, player, game, extras=None):
    """骷髅马骑士：部署：你的手牌具有+1T花费，直到下回合结束。"""

    def modifier(card, cost):
        cost.t += 1

    player._cost_modifiers.append(modifier)
    print("  骷髅马骑士：所有手牌+1T花费")

    deployed_turn = game.current_turn

    def on_phase_end(event):
        if event.data.get("phase") != game.PHASE_RESOLVE:
            return
        if not minion.is_alive():
            return
        if game.current_turn <= deployed_turn:
            return  # 本回合结算阶段结束，不移除
        if modifier in player._cost_modifiers:
            player._cost_modifiers.remove(modifier)
            print("  骷髅马骑士效果结束：手牌花费恢复")

    on("phase_end", on_phase_end, game, minion)


@special
def _zhizhuqishi_special(minion, player, game, extras=None):
    """蜘蛛骑士：友方策略造成的伤害+1。"""

    def on_before_damage(event):
        if not minion.is_alive():
            return
        if getattr(game, "_current_strategy_player", None) is not player:
            return
        event.data["damage"] = event.data.get("damage", 0) + 1

    on("before_damage", on_before_damage, game, minion)


@special
def _diyuchuansongmen_special(minion, player, game, extras=None):
    """地狱传送门：友方异象被消灭时，改为将其洗入卡组。"""

    def on_before_destroy(event):
        if not minion.is_alive():
            return
        victim = event.data.get("minion")
        if victim is None:
            return
        if victim.owner is not player:
            return
        # 阻止默认消灭流程
        event.cancelled = True
        # 从场上移除（不触发亡语）
        game.board.remove_minion(victim.position)
        # 将对应卡牌洗入卡组
        card = create_card_by_name(victim.name, player)
        if card:
            shuffle_into_deck(player, card)
            print(f"  地狱传送门将 {victim.name} 洗入卡组")
        else:
            print(f"  地狱传送门：无法为 {victim.name} 创建卡牌")
        # 若受害者是传送门自己，清理监听器
        if victim is minion:
            game.history.unlisten_by_owner(minion)

    on("before_destroy", on_before_destroy, game, minion)


@special
def _chuan_special(minion, player, game, extras=None):
    """船：其上异象被消灭时，抽1张牌。"""

    def on_before_destroy(event):
        if not minion.is_alive():
            return
        victim = event.data.get("minion")
        if victim is None:
            return
        # 检查受害者是否位于本船的上方
        under = game.board.cell_underlay.get(victim.position)
        if under is not minion:
            return
        draw_cards(player, 1, game)
        print(f"  船上的 {victim.name} 被消灭，{player.name} 抽1张牌")

    on("before_destroy", on_before_destroy, game, minion)


@special
def _tntpao_special(minion, player, game, extras=None):
    """TNT炮：攻击异象前，先造成等同于目标部署花费的伤害。"""

    def _pre_attack(attacker, target):
        if not isinstance(target, Minion):
            return
        cost = target.source_card.cost
        damage = cost.t + cost.c + cost.b + cost.s + cost.ct + sum(cost.minerals.values())
        if damage > 0:
            deal_damage_to_minion(target, damage, source=minion, game=game)
            print(f"  TNT炮对 {target.name} 造成了 {damage} 点部署花费伤害（攻击前）")

    if not hasattr(minion, "_pre_attack_fns"):
        minion._pre_attack_fns = []
    minion._pre_attack_fns.append(_pre_attack)


@special
def _shanhun_special(minion, player, game, extras=None):
    """善魂：部署：指向1个异象。亡语：使其+2/2。"""

    target = None
    if extras:
        target = extras[0]

    if target and isinstance(target, Minion) and target.is_alive():
        minion._shanhun_target = target
        print(f"  善魂指向了 {target.name}")

        def _dr(m, p, b):
            t = getattr(m, "_shanhun_target", None)
            if t and t.is_alive():
                t.gain_attack(2, permanent=True)
                t.gain_health_bonus(2, permanent=True)
                t.current_health += 2
                print(f"  善魂的亡语使 {t.name} +2/+2")

        add_deathrattle(minion, _dr)
    else:
        print("  善魂：未指向有效异象")


@special
def _banxiangou_special(minion, player, game, extras=None):
    """绊线钩：受到伤害前，每有1个友方"绊线钩"与之同行或同列，对1个随机敌方目标造成1次1点伤害。"""

    def on_before_damage(event):
        if not minion.is_alive():
            return
        victim = event.data.get("target")
        if victim is not minion:
            return
        r, c = minion.position
        count = 0
        for m in all_friendly_minions(game, player):
            if m.name == "绊线钩" and (m.position[0] == r or m.position[1] == c):
                count += 1
        if count > 0:
            print(f"  绊线钩受到伤害，同行/同列有 {count} 个友方绊线钩")
        for _ in range(count):
            enemies = all_enemy_minions(game, player)
            opponent = game.p2 if player == game.p1 else game.p1
            candidates = enemies + [opponent]
            if candidates:
                target = random.choice(candidates)
                if isinstance(target, Minion):
                    deal_damage_to_minion(target, 1, source=minion, game=game)
                else:
                    deal_damage_to_player(target, 1, source=minion, game=game)
                print(f"  绊线钩对 {target.name} 造成1点伤害")

    on("before_damage", on_before_damage, game, minion)


def _xiangshu_evolve(minion, player, game):
    """橡树：成长时，获得1个C槽，抽1张牌。"""
    player.c_point_max += 1
    draw_cards(player, 1, game)
    print(f"  橡树成长：{player.name} 获得1个C槽并抽1张牌")


@special
def _yinyuehe_special(minion, player, game, extras=None):
    """音乐盒：对方每回合打出的第一张手牌花费翻倍。"""
    from card_pools.effect_utils import cards_played_this_turn, get_opponent

    opponent = get_opponent(game, player)

    def modifier(card, cost):
        if cards_played_this_turn(game, opponent) == 0:
            cost.t *= 2
            print(f"  音乐盒使 {card.name} 的T花费翻倍")

    opponent._cost_modifiers.append(modifier)
    print("  音乐盒：对方首张手牌T花费翻倍")

    def on_phase_end(event):
        if event.data.get("phase") != game.PHASE_RESOLVE:
            return
        if not minion.is_alive() and modifier in opponent._cost_modifiers:
            opponent._cost_modifiers.remove(modifier)
            print("  音乐盒效果移除")

    on("phase_end", on_phase_end, game, minion)


@special
def _zhong_special(minion, player, game, extras=None):
    """钟：友方异象造成1点战斗伤害时，改为造成3点伤害。"""

    def on_before_damage(event):
        if not minion.is_alive():
            return
        source = event.data.get("source_minion")
        if source is None or source.owner is not player:
            return
        if not event.data.get("is_combat_damage"):
            return
        if event.data.get("damage") == 1:
            event.data["damage"] = 3
            print(f"  钟使 {source.name} 的战斗伤害从1点变为3点")

    on("before_damage", on_before_damage, game, minion)


@special
def _diaolingpaota_special(minion, player, game, extras=None):
    """凋灵炮塔：溢出伤害转移至对手。回合结束：若你的手牌数不小于6，随机攻击1个敌方异象。"""

    def on_after_damage(event):
        if not minion.is_alive():
            return
        source = event.data.get("source_minion")
        if source is not minion:
            return
        target = event.data.get("target")
        if target is None or not hasattr(target, "current_health"):
            return
        overflow = max(0, -target.current_health)
        if overflow > 0:
            opponent = game.p2 if player == game.p1 else game.p1
            deal_damage_to_player(opponent, overflow, source=minion, game=game)
            print(f"  凋灵炮塔的溢出伤害 {overflow} 点转移至 {opponent.name}")

    def on_phase_end(event):
        if event.data.get("phase") != game.PHASE_RESOLVE:
            return
        if not minion.is_alive():
            return
        if len(player.card_hand) < 6:
            return
        target = random_enemy_minion(game, player)
        if target and target.is_alive():
            print(f"  凋灵炮塔随机攻击 {target.name}")
            minion.attack_target(target)
        else:
            print("  凋灵炮塔：场上没有敌方异象可攻击")

    on("after_damage", on_after_damage, game, minion)
    on("phase_end", on_phase_end, game, minion)


@special
def _huosaichengchui_special(minion, player, game, extras=None):
    """活塞城槌：无法选中攻击力不大于本异象的异象。

    即：攻击时跳过攻击力 <= 自身的敌方异象，选择下一个合法目标。
    """

    def _filter(target):
        return target.current_attack > minion.current_attack

    minion._attack_target_filter = _filter
    print("  活塞城槌：攻击时跳过攻击力不大于自身的异象")


@special
def _dungouji_special(minion, player, game, extras=None):
    """盾构机：无法攻击对手。每消灭1个异象，抽1张牌。"""

    def on_before_attack(event):
        if not minion.is_alive():
            return
        if event.data.get("attacker") is not minion:
            return
        target = event.data.get("target")
        if isinstance(target, Player):
            event.cancelled = True
            print("  盾构机无法攻击对手")

    def on_after_damage(event):
        if not minion.is_alive():
            return
        source = event.data.get("source_minion")
        if source is not minion:
            return
        target = event.data.get("target")
        if target and hasattr(target, "current_health") and target.current_health <= 0:
            draw_cards(player, 1, game)
            print(f"  盾构机消灭异象，{player.name} 抽1张牌")

    on("before_attack", on_before_attack, game, minion)
    on("after_damage", on_after_damage, game, minion)


@special
def _shuimuqiang_special(minion, player, game, extras=None):
    """水幕墙：部署：使所有友方异象获得防空。受到非生命异象或策略造成的伤害时，将其设为0点。"""

    # 部署：所有友方异象获得防空
    for m in all_friendly_minions(game, player):
        if m.is_alive():
            gain_keyword(m, "防空")
    print("  水幕墙使所有友方异象获得防空")

    def on_before_damage(event):
        if not minion.is_alive():
            return
        victim = event.data.get("target")
        if victim is not minion:
            return
        source = event.data.get("source_minion")
        source_type = event.data.get("source_type", "")
        is_non_living = source and hasattr(source, "tags") and "非生命" in getattr(source, "tags", [])
        is_strategy = (source is None and getattr(game, "_current_strategy_player", None) is not None) or source_type == "strategy"
        if is_non_living or is_strategy:
            event.data["damage"] = 0
            print("  水幕墙将受到的非生命/策略伤害设为0")

    on("before_damage", on_before_damage, game, minion)


@special
def _modichuan_special(minion, player, game, extras=None):
    """末地船：非迅捷友方异象部署时，获得-1HP和迅捷。"""

    def on_deployed(event):
        if not minion.is_alive():
            return
        deployed = event.data.get("minion")
        if deployed is None or deployed.owner is not player:
            return
        if "迅捷" in deployed.keywords:
            return
        if deployed.current_health > 0:
            deployed.current_health -= 1
            print(f"  末地船使 {deployed.name} 获得-1HP")
        gain_keyword(deployed, "迅捷")
        print(f"  末地船使 {deployed.name} 获得迅捷")

    on("deployed", on_deployed, game, minion)


@special
def _modishuijing_special(minion, player, game, extras=None):
    """末地水晶：友方目标受到对方策略效果时，改为由本异象承受。亡语：若是被策略效果消灭，对所有敌方目标造成2点伤害。"""

    def on_before_damage(event):
        if not minion.is_alive():
            return
        if getattr(game, "_end_crystal_redirecting", False):
            return
        victim = event.data.get("target")
        if victim is minion:
            return
        if victim is None:
            return
        # 检查是否是友方目标
        if hasattr(victim, "owner") and victim.owner is not player:
            return
        if isinstance(victim, Player) and victim is not player:
            return
        # 检查来源是否是敌方策略
        source_type = event.data.get("source_type", "")
        is_strategy = (event.data.get("source_minion") is None and getattr(game, "_current_strategy_player", None) is not None) or source_type == "strategy"
        if not is_strategy:
            return
        strategy_player = getattr(game, "_current_strategy_player", None)
        if strategy_player is None or strategy_player == player:
            return
        # 重定向
        damage = event.data.get("damage", 0)
        if damage > 0:
            event.data["damage"] = 0
            game._end_crystal_redirecting = True
            try:
                deal_damage_to_minion(minion, damage, source=None, game=game)
            finally:
                game._end_crystal_redirecting = False
            print(f"  末地水晶代替 {getattr(victim, 'name', str(victim))} 承受 {damage} 点策略伤害")

    def on_after_damage(event):
        if event.data.get("target") is minion:
            source_type = event.data.get("source_type", "")
            is_strategy = (event.data.get("source_minion") is None and getattr(game, "_current_strategy_player", None) is not None) or source_type == "strategy"
            actual = event.data.get("actual", 0)
            if actual > 0:
                if is_strategy:
                    minion._killed_by_strategy = True
                else:
                    minion._killed_by_strategy = False

    on("before_damage", on_before_damage, game, minion)
    on("after_damage", on_after_damage, game, minion)

    # 亡语
    def _dr(m, p, b):
        if getattr(m, "_killed_by_strategy", False):
            opponent = game.p2 if player == game.p1 else game.p1
            for enemy in all_enemy_minions(game, player):
                if enemy.is_alive():
                    deal_damage_to_minion(enemy, 2, source=m, game=game)
            deal_damage_to_player(opponent, 2, source=m, game=game)
            print("  末地水晶亡语：被策略消灭，对所有敌方目标造成2点伤害")

    add_deathrattle(minion, _dr)


@special
def _loudoukuanche_special(minion, player, game, extras=None):
    """漏斗矿车：部署：抽1张花费不大于4T的异象。亡语：将其加入本异象所在的位置。"""
    from tards.cards import MinionCard

    drawn = None
    for i in range(len(player.card_deck) - 1, -1, -1):
        card = player.card_deck[i]
        if isinstance(card, MinionCard) and card.cost.t <= 4:
            drawn = card
            del player.card_deck[i]
            player.card_hand.append(card)
            print(f"  漏斗矿车抽到 {card.name}")
            break

    if drawn:
        minion._loudoukuanche_card = drawn

    def _dr(m, p, b):
        card = getattr(m, "_loudoukuanche_card", None)
        if card and card in p.card_hand:
            p.card_hand.remove(card)
            pos = m.position
            if pos and pos not in game.board.minion_place:
                original_b = card.cost.b
                card.cost.b = 0
                try:
                    card.effect(p, pos, game)
                    print(f"  漏斗矿车亡语：将 {card.name} 部署到 {pos}")
                finally:
                    card.cost.b = original_b
            else:
                print(f"  漏斗矿车位置被占用，{card.name} 被弃置")
                p.card_dis.append(card)
        else:
            print("  漏斗矿车：抽到的异象已不在手牌中")

    add_deathrattle(minion, _dr)


@special
def _nvwu_special(minion, player, game, extras=None):
    """女巫：部署：使一个目标流失2点HP。如果因此消灭了目标，本异象获得：
    '结算阶段开始时，对一个目标造成2点伤害（在出牌阶段由玩家决定）。
    如果因此消灭了目标，本异象具有无法选中直到结算阶段结束。'
    """

    # 部署时：从 extras 获取玩家选择的目标
    target = extras[0] if extras else None
    if target and hasattr(target, "current_health"):
        target.current_health -= 2
        print(f"  女巫使 {target.name} 流失2点HP")
        if target.current_health <= 0:
            target.minion_death()
            minion._nvwu_active = True
            print("  女巫激活持续效果")

    def on_phase_start(event):
        if not getattr(minion, "_nvwu_active", False):
            return
        phase = event.data.get("phase")

        if phase == game.PHASE_ACTION:
            # 行动阶段：玩家选择结算阶段目标
            if not minion.is_alive():
                return
            from tards.targeting import TargetingRequest

            enemies = all_enemy_minions(game, player)
            opponent = game.p2 if player == game.p1 else game.p1

            def scope_fn(p, board):
                return enemies + [opponent]

            req = TargetingRequest()
            req.source = minion
            req.scope_fn = scope_fn
            req.count = 1
            req.prompt = "女巫：选择结算阶段目标"
            req.deciding_player = player
            t = game.targeting_system.request_target(req)
            if t is not None:
                minion._nvwu_target = t
            else:
                minion._nvwu_target = None

        elif phase == game.PHASE_RESOLVE:
            # 结算阶段：对预选目标造成2点伤害
            if not minion.is_alive():
                return
            t = getattr(minion, "_nvwu_target", None)
            if t and hasattr(t, "is_alive"):
                if t.is_alive():
                    from card_pools.effect_utils import deal_damage_to_minion
                    deal_damage_to_minion(t, 2, source=minion, game=game)
                    # take_damage 内部在 HP<=0 时调用 minion_death（延迟执行），
                    # 此时直接检查血量或 _pending_death 判断是否消灭
                    if t.current_health <= 0 or getattr(t, "_pending_death", False):
                        witch_reason = f"女巫无法选中_{id(minion)}"
                        entry = {
                            "filter": lambda target, source: target is minion and minion.is_alive(),
                            "reason": witch_reason,
                            "once": False,
                        }
                        game._target_protections.append(entry)
                        print("  女巫获得无法选中")
            elif isinstance(t, Player):
                from card_pools.effect_utils import deal_damage_to_player
                deal_damage_to_player(t, 2, source=minion, game=game)
                print(f"  女巫使 {t.name} 受到2点伤害")

    def on_phase_end(event):
        if event.data.get("phase") == game.PHASE_RESOLVE:
            # 精确清理本女巫的无法选中（避免误伤其他女巫）
            witch_reason = f"女巫无法选中_{id(minion)}"
            game._target_protections = [
                p for p in game._target_protections
                if p.get("reason") != witch_reason
            ]

    on("phase_start", on_phase_start, game, minion)
    on("phase_end", on_phase_end, game, minion)


@special
def _zhongshengmao_special(minion, player, game, extras=None):
    """重生锚：友方其它非回响异象具有'亡语：将本异象的回响加入手牌。'友方回响异象的花费设为1G。"""

    def _dr_factory(target_name):
        def _dr(m, p, b):
            card = create_card_by_name(target_name, p)
            if card:
                if len(p.card_hand) < p.card_hand_max:
                    p.card_hand.append(card)
                    print(f"  {target_name} 的亡语：将回响加入手牌")
                else:
                    p.card_dis.append(card)
                    print(f"  {target_name} 的亡语：手牌已满，回响被弃置")
        return _dr

    def _aura_fn(target):
        if target is minion:
            return {}
        if "回响" in target.keywords:
            return {}
        return {"亡语": _dr_factory(target.name)}

    def _apply_aura(target):
        if target is not minion and target.is_alive() and "回响" not in target.keywords:
            minion.provide_aura_keywords(target, _aura_fn)

    # 部署时给所有友方非回响异象上光环
    for m in all_friendly_minions(game, player):
        _apply_aura(m)

    # 新部署的友方异象也上光环
    def on_deployed(event):
        if not minion.is_alive():
            return
        deployed = event.data.get("minion")
        if deployed and deployed.owner == player:
            _apply_aura(deployed)

    on("deployed", on_deployed, game, minion)

    # 回响异象花费设为1G
    def modifier(card, cost):
        if card.keywords.get("回响", False):
            cost.t = 1
            cost.c = cost.b = cost.s = 0
            cost.ct = 0
            cost.minerals = {}

    player._cost_modifiers.append(modifier)
    print("  重生锚：回响异象花费设为1G")

    def on_before_destroy(event):
        if event.data.get("minion") is minion:
            if modifier in player._cost_modifiers:
                player._cost_modifiers.remove(modifier)
                print("  重生锚花费修正效果移除")

    on("before_destroy", on_before_destroy, game, minion)


@special
def _shashoutu_special(minion, player, game, extras=None):
    """杀手兔：结算阶段不攻击。出牌阶段，敌方异象首次部署时，本异象攻击1次。"""

    minion._skip_resolve_attack = True

    def on_phase_start(event):
        if event.data.get("phase") == game.PHASE_ACTION:
            minion._enemy_deployed_this_action = False

    def on_deployed(event):
        if not minion.is_alive():
            return
        if getattr(minion, "_enemy_deployed_this_action", False):
            return
        if game.current_phase != game.PHASE_ACTION:
            return
        deployed = event.data.get("minion")
        if deployed is None or deployed.owner == player:
            return
        minion._enemy_deployed_this_action = True
        auto_attack(minion, game)

    on("phase_start", on_phase_start, game, minion)
    on("deployed", on_deployed, game, minion)


@special
def _shouweizhe_special(minion, player, game, extras=None):
    """守卫者：对对手造成伤害后，消灭本异象。"""

    def on_after_damage(event):
        if not minion.is_alive():
            return
        source = event.data.get("source_minion")
        if source is not minion:
            return
        target = event.data.get("target")
        if isinstance(target, Player) and event.data.get("actual", 0) > 0:
            destroy_minion(minion, game)
            print("  守卫者对对手造成伤害后自我消灭")

    on("after_damage", on_after_damage, game, minion)


@special
def _toast_special(minion, player, game, extras=None):
    """Toast_：攻击异象后，若目标未被消灭，获得-1HP并攻击1次。"""

    def on_after_attack(event):
        if event.data.get("attacker") is not minion:
            return
        target = event.data.get("target")
        if not isinstance(target, Minion):
            return
        if target.is_alive():
            minion.current_health -= 1
            print(f"  Toast_ 获得-1HP")
            if minion.current_health <= 0:
                minion.minion_death()
            elif minion.is_alive():
                minion.attack_target(target)
                print(f"  Toast_ 再次攻击 {target.name}")

    on("after_attack", on_after_attack, game, minion)


@special
def _jielueshou_special(minion, player, game, extras=None):
    """劫掠兽：部署：眩晕其它所有异象。异象进入战场时，获得-1HP和-1坚韧等级。"""

    # 部署时眩晕其它所有异象
    for m in list(game.board.minion_place.values()):
        if m is minion:
            continue
        if m.is_alive():
            m.base_keywords["眩晕"] = 1
            m.recalculate()
            print(f"  {m.name} 被眩晕1回合")

    # 全局部署钩子：异象进入战场时 -1HP 和 -1坚韧
    def _on_deploy(deployed, self_minion=minion, g=game):
        if deployed is self_minion:
            return
        if not self_minion.is_alive():
            return
        if deployed.is_alive():
            deployed.current_health -= 1
            modify_keyword_number(deployed, "坚韧", -1)
            print(f"  {deployed.name} 进入战场，获得-1HP和-1坚韧")

    minion.register_deploy_hook(game, _on_deploy)


@special
def _nishiz_special(minion, player, game, extras=None):
    """溺尸：部署：失去1T。对异象造成伤害时，弃掉对方花费最低的1张手牌。"""

    # 部署时失去1T
    player.t_point = max(0, player.t_point - 1)
    print(f"  {player.name} 失去1T")

    def on_after_damage(event):
        if event.data.get("source_minion") is not minion:
            return
        target = event.data.get("target")
        if not isinstance(target, Minion):
            return
        opponent = target.owner
        if not opponent.card_hand:
            return
        # 找到花费最低的手牌（比较 t + ct）
        cheapest = min(
            opponent.card_hand,
            key=lambda c: getattr(getattr(c, 'cost', None), 't', 0) + getattr(getattr(c, 'cost', None), 'ct', 0)
        )
        discard_card(opponent, cheapest)

    on("after_damage", on_after_damage, game, minion)


@special
@special
def _dongxuezhizhu_special(minion, player, game, extras=None):
    """洞穴蜘蛛：部署：将1个异象的攻击力设为1。亡语：将1张"蜘蛛眼"加入手牌。"""
    from tards.targeting import TargetingRequest

    def scope(p, b):
        return [m for m in b.minion_place.values() if m.is_alive()]

    req = TargetingRequest()
    req.source = minion
    req.scope_fn = scope
    req.prompt = "洞穴蜘蛛：选择1个异象将其攻击力设为1"
    req.deciding_player = player
    t = game.targeting_system.request_target(req)
    if t is None:
        return False
    if isinstance(t, Minion) and t.is_alive():
        t.base_attack = 1
        t.perm_attack_bonus = 0
        t.temp_attack_bonus = 0
        if hasattr(t, '_aura_attack_fns'):
            t._aura_attack_fns.clear()
        t.recalculate()
        print(f"  {t.name} 的攻击力被设为1")

    def _deathrattle(m, p, b):
        from tards.card_db import DEFAULT_REGISTRY
        zzy_def = DEFAULT_REGISTRY.get("蜘蛛眼")
        if zzy_def:
            zzy = zzy_def.to_game_card(p)
            if len(p.card_hand) < p.card_hand_max:
                p.card_hand.append(zzy)
            else:
                p.card_dis.append(zzy)
            print(f"  {p.name} 获得蜘蛛眼")

    add_deathrattle(minion, _deathrattle)
    return True


@special
def _kuangche_special(minion, player, game, extras=None):
    """矿车：亡语：获得1个T槽。"""

    def _kuangche_deathrattle(m, p, b):
        """矿车亡语：获得1个T槽。"""
        p.t_point_max += 1
        print(f"  {p.name} 获得1个T槽，T槽上限={p.t_point_max}，当前T点={p.t_point}")

    add_deathrattle(minion, _kuangche_deathrattle)



@special
def _moyingman_special(minion, player, game, extras=None):
    """末影螨：部署：对1个异象造成1点伤害。"""
    from tards.targeting import TargetingRequest

    def scope(p, b):
        return [m for m in b.minion_place.values() if m.is_alive()]

    req = TargetingRequest()
    req.source = minion
    req.scope_fn = scope
    req.prompt = "末影螨：选择1个异象造成1点伤害"
    req.deciding_player = player
    t = game.targeting_system.request_target(req)
    if t is None:
        return False
    if hasattr(t, "is_alive") and t.is_alive():
        deal_damage_to_minion(t, 1, source=minion, game=game)
    return True


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



@special
def _liudu_special(minion, player, game, extras=None):
    """流髑：回合开始：随机冰冻1个敌方异象。若其已被冰冻，将其消灭。"""

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
    """尸壳：回合开始：对所有敌方异象造成1点伤害。"""

    def _on_turn_start(g, event_data, m):
        for enemy in all_enemy_minions(g, player):
            deal_damage_to_minion(enemy, 1, source=m, game=g)

    minion.on_turn_start = _on_turn_start



@special
def _weidaoshi_special(minion, player, game, extras=None):
    """卫道士：部署：所有敌方异象获得-1坚韧等级。"""
    for m in all_enemy_minions(game, player):
        modify_keyword_number(m, "坚韧", -1)


@special
def _zhizhu_special(minion, player, game, extras=None):
    """蜘蛛：部署：使1个异象失去迅捷，高频和空袭。亡语：将1张"蜘蛛眼"加入手牌。"""
    from tards.targeting import TargetingRequest

    def scope(p, b):
        return [m for m in b.minion_place.values() if m.is_alive()]

    req = TargetingRequest()
    req.source = minion
    req.scope_fn = scope
    req.prompt = "蜘蛛：选择1个异象移除迅捷/高频/空袭"
    req.deciding_player = player
    t = game.targeting_system.request_target(req)
    if t is None:
        return False
    if hasattr(t, "is_alive") and t.is_alive():
        remove_keyword(t, "迅捷")
        remove_keyword(t, "高频")
        remove_keyword(t, "空袭")

    # 亡语
    def _dr(m, p, b):
        add_card_to_hand_by_name("蜘蛛眼", p)

    add_deathrattle(minion, _dr)
    return True


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



@special
def _yanjiangting_special(minion, player, game, extras=None):
    """岩浆艇：友方异象部署时，消灭本异象。"""

    def _on_deploy(deployed, self_minion=minion, g=game):
        if deployed.owner == self_minion.owner and deployed is not self_minion:
            if self_minion.is_alive():
                destroy_minion(self_minion, g)

    minion.register_deploy_hook(game, _on_deploy)


@special
def _ganzhe_special(minion, player, game, extras=None):
    """甘蔗：亡语：将1张"书"加入手牌。"""

    def _dr(m, p, b):
        add_card_to_hand_by_name("书", p)

    add_deathrattle(minion, _dr)


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


def _moyingzhenzhu_targets(player, board):
    """末影珍珠合法目标：友方存活且处于陆地（非水路）的异象。"""
    return [
        m for m in board.minion_place.values()
        if m.is_alive()
        and hasattr(m, "owner") and m.owner == player
        and hasattr(m, "board") and m.board is not None
        and not m.board._is_water_at(m.position)
    ]


@strategy
def _moyingzhenzhu_effect(player, target, game, extras=None):
    """末影珍珠：指向2个同阵营陆地异象，交换它们的位置。

    目标选择在 effect_fn 内部完成，不依赖 targets_fn / extra_targeting_stages。
    玩家取消时返回 False，由 play_fn() 自动回滚费用与卡牌。
    """
    from tards.targeting import TargetingRequest

    # 第一次指向请求
    req1 = TargetingRequest()
    req1.source = player
    req1.scope_fn = _moyingzhenzhu_targets
    req1.prompt = "末影珍珠：选择第一个陆地异象"
    req1.deciding_player = player
    a = game.targeting_system.request_target(req1)
    if a is None:
        return False

    # 第二次指向请求（排除已选）
    def scope2(p, b):
        return [m for m in _moyingzhenzhu_targets(p, b) if m is not a]

    req2 = TargetingRequest()
    req2.source = player
    req2.scope_fn = scope2
    req2.prompt = "末影珍珠：选择第二个陆地异象"
    req2.deciding_player = player
    b = game.targeting_system.request_target(req2)
    if b is None:
        return False

    # 校验
    if not hasattr(a, "is_alive") or not hasattr(b, "is_alive"):
        print("  末影珍珠：目标必须是异象")
        return False
    if not a.is_alive() or not b.is_alive():
        print("  末影珍珠：目标已死亡")
        return False
    if a.owner != player or b.owner != player:
        print("  末影珍珠：目标必须是同阵营异象")
        return False
    if not hasattr(a, "board") or a.board is None or a.board._is_water_at(a.position):
        print("  末影珍珠：目标必须是陆地异象")
        return False
    if not hasattr(b, "board") or b.board is None or b.board._is_water_at(b.position):
        print("  末影珍珠：目标必须是陆地异象")
        return False

    swap(a, b, game)
    return True


@special
def _moyiren_special(minion, player, game, extras=None):
    """末影人：受到伤害前，与1个友方异象交换位置。亡语：将1张'末影珍珠'加入手牌。"""

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

    def _dr(m, p, b):
        add_card_to_hand_by_name("末影珍珠", p)

    add_deathrattle(minion, _dr)


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
    """海龟：受到伤害后，将攻击力最高的敌方异象的攻击力设为1，直到下回合结束。"""

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
# 异象卡 — 攻击前/后（EventBus 驱动）
# =============================================================================

@special
def _kulou_special(minion, player, game, extras=None):
    """骷髅：攻击前，改为对HP最低的敌方异象造成等量伤害。"""

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
    """豹猫：本异象攻击时，对其指向的异象造成等量伤害。部署：指向一个异象。"""
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
    """僵尸：具有两栖。部署在高地时变化为尸壳，部署在水路时变化为溺尸。
    否则：造成伤害时，你获得等量HP。"""
    pos = minion.position
    if pos:
        r, c = pos
        transform_name = None
        if c == 0:
            transform_name = "尸壳"
        elif game.board._is_water_at(pos):
            transform_name = "溺尸"

        if transform_name:
            from card_pools.effect_utils import remove_minion_no_death, summon_minion_by_name
            remove_minion_no_death(minion, game)
            summon_minion_by_name(game, transform_name, player, pos)
            return

    # 非变形情况：吸血
    def _leech(event):
        source = event.source
        if source != minion:
            return
        actual = event.get("actual", 0)
        if actual > 0:
            heal_player(player, actual)
            print(f"  僵尸吸血 {actual} HP")

    on_after_damage(minion, game, _leech)



@special
def _huanyi_special(minion, player, game, extras=None):
    """幻翼：消灭异象前，改为移除对方卡组顶的2张牌。"""

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
    """流浪商人：抽牌阶段，取消抽牌，开发一张卡组中的牌。场上有友方友好异象时，无法选中。"""
    def on_turn_start(g, event_data, m):
        player._skip_next_draw = True
        game.develop_card(player, player.original_deck_defs)
    minion.on_turn_start = on_turn_start


@strategy
def _shu_strategy(player, target, game, extras=None):
    """书：开发1张"附魔书"。"""
    book_defs = get_enchanted_book_definitions()
    if book_defs:
        game.develop_card(player, book_defs)
    return True


@strategy
def _fumota_strategy(player, target, game, extras=None):
    """附魔台：使你获得：每个出牌阶段首次开发时，再开发1张“附魔书”。"""
    if getattr(player, '_enchanting_table_registered', False):
        return True
    player._enchanting_table_registered = True

    def on_develop(p, g):
        if not getattr(p, '_enchanting_table_triggered', False):
            p._enchanting_table_triggered = True
            book_defs = get_enchanted_book_definitions()
            if book_defs:
                g.develop_card(p, book_defs)

    player._on_develop_callbacks.append(on_develop)

    def reset_flag(event):
        if event.data.get("phase") == game.PHASE_ACTION:
            player._enchanting_table_triggered = False

    from tards.constants import EVENT_PHASE_START
    game.history.listen(EVENT_PHASE_START, reset_flag)
    return True


@strategy
def _gengzhi_strategy(player, target, game, extras=None):
    """耕殖：开发1张友好异象，抽1张牌。此前你每使用过1张“耕殖”，获得-1T花费。"""
    from tards import CardType
    from tards.card_db import DEFAULT_REGISTRY
    # 开发友好异象
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
    然后若对方异象数更多，随机消灭一个花费不大于4T的敌方异象。"""
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
    """雪球：对一个异象造成1点伤害。然后若其HP不大于2，将其冰冻。"""
    if not target or not hasattr(target, "is_alive") or not target.is_alive():
        print("  [警告] 雪球没有有效目标")
        return False
    deal_damage_to_minion(target, 1, source=None, game=game)
    if target.is_alive() and target.health <= 2:
        gain_keyword(target, "冰冻", 1)
    return True


@strategy
def _zhizhuyan_strategy(player, target, game, extras=None):
    """蜘蛛眼：使1个异象获得-2攻击力。"""
    if not target or not hasattr(target, "is_alive") or not target.is_alive():
        print("  [警告] 蜘蛛眼没有有效目标")
        return False
    buff_minion(target, -2, 0, permanent=True)
    return True


@strategy
def _lieyanfen_strategy(player, target, game, extras=None):
    """烈焰粉：对一个异象及其相邻异象造成1点伤害。"""
    if not target or not hasattr(target, "is_alive") or not target.is_alive():
        print("  [警告] 烈焰粉没有有效目标")
        return False
    # 对主目标造成伤害
    deal_damage_to_minion(target, 1, source=None, game=game)
    # 对相邻异象造成伤害
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
    """光灵箭：使1个异象获得-1坚韧等级。"""
    if not target or not hasattr(target, "is_alive") or not target.is_alive():
        print("  [警告] 光灵箭没有有效目标")
        return False
    modify_keyword_number(target, "坚韧", -1)
    return True


@strategy
def _zhanlipin_strategy(player, target, game, extras=None):
    """战利品：触发1个异象的亡语。若是敌方异象，再抹除其亡语。"""
    if not target or not hasattr(target, "is_alive") or not target.is_alive():
        print("  [警告] 战利品没有有效目标")
        return False
    dr = target.keywords.get("亡语")
    if dr and callable(dr):
        print(f"  触发 {target.name} 的亡语")
        dr(target, target.owner, target.board)
    else:
        print(f"  {target.name} 没有亡语")
    # 若是敌方异象，抹除亡语
    if is_enemy(target, player):
        target.base_keywords.pop("亡语", None)
        target.recalculate()
        print(f"  {target.name} 的亡语被抹除")
    return True


@strategy
def _fuxing_effect(player, target, game, extras=None):
    """复兴：使你获得：你不因抽牌而获得手牌时，将其复制加入手牌，使其花费+1。"""
    import copy

    # 记录已处理的手牌ID（避免重复触发）
    processed_ids = {id(c) for c in player.card_hand}

    def _on_phase_end(event):
        # 只在结算阶段结束时检查
        if event.data.get("phase") != game.PHASE_RESOLVE:
            return

        for card in list(player.card_hand):
            cid = id(card)
            if cid in processed_ids:
                continue
            processed_ids.add(cid)

            # 跳过抽牌获得的卡
            if getattr(card, "_acquired_by_draw", False):
                continue

            # 非抽牌获得：复制并+1T
            copied = copy.copy(card)
            if copied.keywords:
                copied.keywords = copied.keywords.copy()
            copied.cost = copy.copy(card.cost)
            copied.cost.t += 1

            if len(player.card_hand) < player.card_hand_max:
                player.card_hand.append(copied)
                copied.move_to("hand", game)
                print(f"  复兴：复制 {card.name} 加入手牌，花费+1T")
                processed_ids.add(id(copied))
            else:
                player.card_dis.append(copied)
                copied.move_to("discard", game)
                print(f"  复兴：手牌已满，{card.name} 的复制被弃置")

    from card_pools.effect_utils import on
    on("phase_end", _on_phase_end, game, minion=None)
    print("  复兴：效果已激活")
    return True


@strategy
def _yiqi_strategy(player, target, game, extras=None):
    """遗弃：将1个异象的HP设为1。"""
    if not target or not hasattr(target, "is_alive") or not target.is_alive():
        print("  [警告] 遗弃没有有效目标")
        return False
    # 清除临时最大生命值加成
    target.temp_max_health_bonus = 0
    # 调整永久加成使最大生命值变为1
    delta = 1 - target.health
    if delta != 0:
        target.gain_health_bonus(delta, permanent=True)
    # 将当前生命值也设为1（不触发伤害事件）
    target.current_health = 1
    target.recalculate()
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
def _yulin_effect(player, target, game, extras=None):
    """雨林：使1个异象获得亡语：随机消灭1个距离不大于3的敌方异象。"""
    if not target or not hasattr(target, "is_alive") or not target.is_alive():
        print("  雨林：未选择目标")
        return True

    def _deathrattle(minion, owner, board):
        import random
        g = board.game_ref
        if not g:
            return
        # 找距离不大于3的敌方异象
        candidates = []
        for pos, m in board.minion_place.items():
            if m.is_alive() and m.owner != minion.owner:
                dist = abs(pos[0] - minion.position[0]) + abs(pos[1] - minion.position[1])
                if dist <= 3:
                    candidates.append(m)
        if candidates:
            chosen = random.choice(candidates)
            destroy_minion(chosen, g)
            print(f"  雨林亡语：{minion.name} 消灭 {chosen.name}")
        else:
            print(f"  雨林亡语：{minion.name} 范围内没有敌方异象")

    add_deathrattle(target, _deathrattle)
    print(f"  雨林：{target.name} 获得亡语")
    return True


@strategy
def _xueyuan_effect(player, target, game, extras=None):
    """雪原：对1行异象造成等同于此行异象数的伤害。"""
    # 让玩家选择横行
    rows = ["第0行", "第1行", "第2行", "第3行", "第4行"]
    choice = game.request_choice(player, rows, title="雪原：选择1个横行")
    if choice < 0:
        print("  雪原：未选择")
        return True

    chosen_row = choice  # 0-4

    # 统计该行上的存活异象
    targets = [m for pos, m in game.board.minion_place.items()
               if pos[0] == chosen_row and m.is_alive()]

    count = len(targets)
    if count == 0:
        print(f"  雪原：第{chosen_row}行没有异象")
        return True

    # 对每个异象造成 count 点伤害
    for m in targets:
        if m.is_alive():
            deal_damage_to_minion(m, count, source=None, game=game)
            print(f"  雪原：对 {m.name} 造成{count}点伤害")

    return True


@strategy
def _erdi_strategy(player, target, game, extras=None):
    """恶地：对所有花费不大于3的异象造成3点伤害。"""
    # 筛选全场花费折算后不大于3的存活异象
    targets = []
    for pos, m in game.board.minion_place.items():
        if m.is_alive():
            source = getattr(m, "source_card", None)
            if source:
                cost_value = convert_cost_to_t(source.cost) + source.cost.ct
                if cost_value <= 3:
                    targets.append((pos, m))

    # 按列从高地(0)到水路(4)，同列内按行从小到大排序
    targets.sort(key=lambda x: (x[0][1], x[0][0]))

    for pos, m in targets:
        if m.is_alive():
            deal_damage_to_minion(m, 3, source=None, game=game)
            print(f"  恶地：对 {m.name}({pos}) 造成3点伤害")

    return True


@strategy
def _fuzhijishu_effect(player, target, game, extras=None):
    """复制技术：抉择：将1张"轰击"或1张"制导技术"加入手牌。"""
    choice = game.request_choice(
        player,
        ["轰击", "制导技术"],
        title="复制技术：抉择",
    )
    if choice == 0:
        add_card_to_hand_by_name("轰击", player, game)
    elif choice == 1:
        add_card_to_hand_by_name("制导技术", player, game)
    return True


@strategy
def _c418_effect(player, target, game, extras=None):
    """C418：对方手牌具有+2花费，直到下一个出牌阶段结束。"""
    opponent = game.p2 if player == game.p1 else game.p1

    # 修改对方当前手牌费用+2T
    modified_cards = []
    for card in opponent.card_hand:
        card.cost.t += 2
        modified_cards.append(card)

    trigger_turn = game.current_turn + 1

    def _on_phase_end(event):
        if event.data.get("phase") != game.PHASE_ACTION:
            return
        if game.current_turn < trigger_turn:
            return
        # 恢复费用
        for card in modified_cards:
            if card in opponent.card_hand:
                card.cost.t -= 2
        print(f"  C418效果结束：{opponent.name} 手牌费用恢复")
        # 注销自己
        game.history.unlisten(listener_id)

    listener_id = on("phase_end", _on_phase_end, game, minion=None)
    print(f"  C418：{opponent.name} 手牌费用+2T，直到回合{trigger_turn}出牌阶段结束")
    return True


@strategy
def _shitiyaji_effect(player, target, game, extras=None):
    """实体挤压：指向1个异象，使其下一个出牌阶段开始时受到4点伤害并获得眩晕。"""
    if not target or not hasattr(target, "is_alive") or not target.is_alive():
        print("  实体挤压：未选择目标")
        return True

    def _on_phase_start(g, event_data, m):
        if event_data.get("phase") != g.PHASE_ACTION:
            return
        if m is not target:
            return
        if not m.is_alive():
            return
        # 只触发一次
        m.on_phase_start = None
        # 先伤害
        deal_damage_to_minion(m, 4, game=g)
        print(f"  实体挤压：{m.name} 受到4点伤害")
        # 后眩晕
        gain_keyword(m, "眩晕")
        print(f"  实体挤压：{m.name} 获得眩晕")

    target.on_phase_start = _on_phase_start
    print(f"  实体挤压：{target.name} 将在下一个出牌阶段开始时受到伤害和眩晕")
    return True


@strategy
def _zhenzhuta_effect(player, target, game, extras=None):
    """珍珠塔：开发4张卡组中的牌，将其花费设为4T。"""
    from tards.cost import Cost

    def _set_cost_4t(card):
        card.cost = Cost(t=4)

    for i in range(4):
        result = game.develop_card(
            player,
            player.original_deck_defs,
            count=3,
            modify_fn=_set_cost_4t,
            return_card=True,
        )
        if result:
            print(f"  珍珠塔：开发第{i+1}张 {result.name}，花费设为4T")
        else:
            print(f"  珍珠塔：开发第{i+1}张失败")

    return True


@strategy
def _zhidaojishu_effect(player, target, game, extras=None):
    """制导技术：抉择：将1张"矢量炮"或1张"珍珠塔"加入手牌。"""
    choice = game.request_choice(
        player,
        ["矢量炮", "珍珠塔"],
        title="制导技术：抉择",
    )
    if choice == 0:
        add_card_to_hand_by_name("矢量炮", player, game)
    elif choice == 1:
        add_card_to_hand_by_name("珍珠塔", player, game)
    return True


@strategy
@strategy
def _hongji_effect(player, target, game, extras=None):
    """轰击：消灭1个受伤异象，将1张"TNT炮"加入手牌。"""
    from tards.targeting import TargetingRequest

    def scope(p, b):
        return [m for m in b.minion_place.values() if m.is_alive() and m.current_health < m.health]

    req = TargetingRequest()
    req.source = player
    req.scope_fn = scope
    req.prompt = "轰击：选择1个受伤异象"
    req.deciding_player = player
    t = game.targeting_system.request_target(req)
    if t is None:
        return False
    if not hasattr(t, "is_alive") or not t.is_alive():
        print("  轰击：目标无效")
        return True
    if t.current_health >= t.health:
        print("  轰击：目标未受伤")
        return True

    destroy_minion(t, game)
    add_card_to_hand_by_name("TNT炮", player, game)
    print(f"  轰击：将 TNT炮 加入手牌")
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
    """红石粉：使1个非生命异象具有协同。抽1张牌。"""
    # 注："非生命异象"的定义待确认，当前实现为任意异象赋予协同
    if not target or not hasattr(target, "is_alive") or not target.is_alive():
        print("  [警告] 红石粉没有有效目标")
        return False
    gain_keyword(target, "协同")
    draw_cards(player, 1, game)
    return True


@strategy
def _jinrenshu_strategy(player, target, game, extras=None):
    """禁人书：使1个异象及其相邻异象获得眩晕（持续到回合结束）。"""
    if not target or not hasattr(target, "is_alive") or not target.is_alive():
        print("  [警告] 禁人书没有有效目标")
        return False
    gain_keyword(target, "眩晕", permanent=False)
    for pos in get_adjacent_positions(target.position, game.board):
        neighbor = game.board.get_minion_at(pos)
        if neighbor and neighbor.is_alive():
            gain_keyword(neighbor, "眩晕", permanent=False)
    return True


_ehanglei_targets = target_mix(target("minion"), target("player", enemy=True))


@strategy
def _ehanglei_strategy(player, target, game, extras=None):
    """恶魂之泪：对1个目标造成2点伤害。对方随机弃1张牌。"""
    from tards.cards import Minion

    if isinstance(target, Minion):
        deal_damage_to_minion(target, 2, source=None, game=game)
    elif hasattr(target, "health_change"):
        deal_damage_to_player(target, 2, source=None, game=game)
    else:
        print("  [警告] 恶魂之泪目标无效")
        return False

    # 对方随机弃1张牌
    opponent = game.p2 if player == game.p1 else game.p1
    if opponent.card_hand:
        import random
        discarded = random.choice(opponent.card_hand)
        discard_card(opponent, discarded)

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
# 异象卡 — Aura（光环）效果
# =============================================================================

@special
def _ma_special(minion, player, game, extras=None):
    """马：与其同列的友方异象具有迅捷。"""
    col = minion.position[1]

    def _swift_aura(m):
        if m.owner == player and m.position[1] == col:
            return {"迅捷": True}
        return {}

    # 立即给场上已有的同列友方异象添加 aura
    for m in all_friendly_minions(game, player):
        if m is not minion and m.position[1] == col:
            minion.provide_aura_keywords(m, _swift_aura)

    # 新部署的友方异象若在同列，也添加 aura
    def _on_deploy(deployed, self_minion=minion, g=game):
        if deployed.owner == player and deployed is not self_minion and deployed.position[1] == col:
            minion.provide_aura_keywords(deployed, _swift_aura)

    minion.register_deploy_hook(game, _on_deploy)


@special
def _chizushou_special(minion, player, game, extras=None):
    """炽足兽：与其同列的友方异象具有先攻1和+1攻击力。"""
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
    """潮涌核心：其它友方异象具有+2攻击力。"""

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
    """活塞飞艇：同列没有敌方异象时，具有迅捷。"""
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
# 异象卡 — 回合结束 / 亡语
# =============================================================================

@special
def _lv_special(minion, player, game, extras=None):
    """驴：回合结束：若处于协同，抽1张牌。"""

    def _on_turn_end(g, event_data, m):
        if not m.is_alive():
            return
        col = m.position[1]
        # 检查同列是否有其它友方异象
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
# 异象卡 — 部署效果
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
    """禁人塔：部署：眩晕1行异象。被眩晕异象多眩晕1回合。"""
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
    """侦测器：敌方异象部署时，对其造成1点伤害，使其失去迅捷。"""

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
    """村庄英雄：对1个异象及其相邻异象造成2点伤害。若有异象被消灭，将1张"村庄英雄"洗入卡组。"""
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
    """劫掠：消灭1个花费不大于3T的异象。若其处于协同，从对方卡组顶抽1张牌。"""
    if not target or not hasattr(target, "is_alive") or not target.is_alive():
        print("  [警告] 劫掠没有有效目标")
        return False
    # 检查花费
    cost = getattr(target.source_card, "cost", None)
    if not cost or cost.t > 3:
        print(f"  {target.name} 的花费大于3T，无法劫掠")
        return False
    destroy_minion(target, game)
    # 检查协同：同列有友方异象
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


def _gaolu_draw_trigger(player, game, card):
    """高炉抽取：随机将"铁锭"、"金锭"、"钻石"中的1张加入手牌。"""
    import random
    mineral_names = ["铁锭", "金锭", "钻石"]
    chosen_name = random.choice(mineral_names)
    mineral = create_card_by_name(chosen_name, player)
    if mineral is None:
        print(f"  高炉抽取：无法创建 {chosen_name}")
        return
    if len(player.card_hand) < player.card_hand_max:
        player.card_hand.append(mineral)
        mineral.move_to("hand", game)
        print(f"  高炉抽取：将 {chosen_name} 加入手牌")
    else:
        player.card_dis.append(mineral)
        mineral.move_to("discard", game)
        print(f"  高炉抽取：手牌已满，{chosen_name} 被弃置")


@special
def _kuqideheiyaoshi_special(minion, player, game, extras=None):
    """哭泣的黑曜石：友方回响异象具有"部署：获得+2/2。"""

    def on_deployed(event):
        deployed = event.data.get("minion")
        if deployed is None or deployed.owner != player:
            return
        if not deployed.source_card:
            return
        if not deployed.source_card.keywords.get("回响", False):
            return
        deployed.attack += 2
        deployed.health += 2
        deployed.current_health += 2
        print(f"  哭泣的黑曜石：{deployed.name} 部署时获得 +2/2")

    on("deployed", on_deployed, game, minion)


# =============================================================================
# 映射表
# =============================================================================

SPECIAL_MAP = {
    "矿车": "_kuangche_special",
    "末影螨": "_moyingman_special",
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
    "钓鱼竿": "_diaoyugan_special",
    "驴": "_lv_special",
    "鲑鱼": "_guiyu_special",
    "雪傀儡": "_xuewulou_special",
    "哭泣的黑曜石": "_kuqideheiyaoshi_special",
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
    "狗": "_gou_special",
    "羊": "_yang_special",
    "猪": "_zhu_special",
    "羊驼": "_yangtuo_special",
    "鹦鹉": "_yingwu_special",
    "河豚": "_hetun_special",
    "村民": "_cunmin_special",
    "疣猪": "_youzhu_special",
    "猪灵": "_zhuling_special",
    "猪灵蛮兵": "_zhulingmanbing_special",
    "猪灵弓兵": "_zhulinggongbing_special",
    "刌民": "_cunmin2_special",
    "潜影贝": "_qianyingbei_special",
    "唤魔者": "_huanmozhe_special",
    "劫掠兽": "_jielueshou_special",
    "溺尸": "_nishiz_special",
    "洞穴蜘蛛": "_dongxuezhizhu_special",
    "海豚": "_haitun_special",
    "劫掠队长": "_jielueduizhang_special",
    "僵尸村民": "_jiangshicunmin_special",
    "恶魂": "_ehan_special",
    "凋零骷髅": "_diaolingkulou_special",
    "盔甲架": "_kuijiujia_special",
    # 对战效果
    "僵尸猪人": "_jiangshizhuren_special",
}

@strategy
def _tiegao_effect(player, target, game, extras=None):
    """铁镐：获得2个额外的C槽。回合结束：抽一张牌。（一次性）"""
    player.c_point_max += 2
    print(f"  {player.name} 获得2个额外C槽")

    def on_phase_end(event):
        if event.data.get("phase") != game.PHASE_RESOLVE:
            return
        player.draw_card(1, game=game)
        print(f"  铁镐：{player.name} 回合结束抽1张牌")

    on("phase_end", on_phase_end, game, once=True)
    return True


@strategy
def _duochongsheji_effect(player, target, game, extras=None):
    """多重射击：对所有敌方目标造成2点伤害。"""
    enemy = game.get_opponent(player)
    for minion in all_enemy_minions(game, player):
        if minion.is_alive():
            deal_damage_to_minion(minion, 2, source=None, game=game)
            print(f"  多重射击：对 {minion.name} 造成2点伤害")
    deal_damage_to_player(enemy, 2, source=None, game=game)
    print(f"  多重射击：对 {enemy.name} 造成2点伤害")
    return True


def _huoshi_targets(player, board):
    """火矢目标：所有位于非水路列上的异象（友方+敌方）。"""
    return [m for pos, m in board.minion_place.items() if not board._is_water_at(pos)]


@strategy
@strategy
def _huoshi_effect(player, target, game, extras=None):
    """火矢：使1个陆地异象获得+4攻击力。"""
    from tards.targeting import TargetingRequest

    def scope(p, b):
        return [m for m in b.minion_place.values() if m.is_alive() and not b._is_water_at(m.position)]

    req = TargetingRequest()
    req.source = player
    req.scope_fn = scope
    req.prompt = "火矢：选择1个陆地异象"
    req.deciding_player = player
    t = game.targeting_system.request_target(req)
    if t is None:
        return False
    if not isinstance(t, Minion):
        print("  火矢：目标必须是异象")
        return False
    if game.board._is_water_at(t.position):
        print("  火矢：目标必须是陆地异象")
        return False
    t.attack += 4
    print(f"  火矢：{t.name} 获得 +4 攻击力")
    return True


def _hengsao_targets(player, board):
    """横扫之刃目标：所有在场异象（通过选择异象来选定其所在行）。"""
    return [m for m in board.minion_place.values() if m.is_alive()]


@strategy
def _hengsao_effect(player, target, game, extras=None):
    """横扫之刃：对1行异象造成3点伤害。"""
    from tards.targeting import TargetingRequest

    def scope(p, b):
        return [m for m in b.minion_place.values() if m.is_alive()]

    req = TargetingRequest()
    req.source = player
    req.scope_fn = scope
    req.prompt = "横扫之刃：选择1个异象（决定目标行）"
    req.deciding_player = player
    t = game.targeting_system.request_target(req)
    if t is None:
        return False
    if not isinstance(t, Minion):
        print("  横扫之刃：目标必须是异象")
        return False
    if not t.is_alive():
        print("  横扫之刃：目标已死亡")
        return False
    row = t.position[0]
    for col in range(game.board.SIZE):
        pos = (row, col)
        m = game.board.get_minion_at(pos)
        if m and m.is_alive():
            deal_damage_to_minion(m, 3, source=None, game=game)
            print(f"  横扫之刃：对 {m.name} 造成3点伤害")
    return True


@strategy
def _erdiao_effect(player, target, game, extras=None):
    """饵钓：将2张"书"加入手牌。"""
    for i in range(2):
        book = create_card_by_name("书", player)
        if book is None:
            print(f"  饵钓：无法创建书")
            continue
        if len(player.card_hand) < player.card_hand_max:
            player.card_hand.append(book)
            book.move_to("hand", game)
            print(f"  饵钓：将书加入手牌")
        else:
            player.card_dis.append(book)
            book.move_to("discard", game)
            print(f"  饵钓：手牌已满，书被弃置")
    return True


@strategy
@strategy
def _zhongcheng_effect(player, target, game, extras=None):
    """忠诚：使1个友方异象获得亡语：将本异象的复制加入手牌。"""
    from tards.targeting import TargetingRequest

    def scope(p, b):
        return [m for m in b.minion_place.values() if m.is_alive() and m.owner == p]

    req = TargetingRequest()
    req.source = player
    req.scope_fn = scope
    req.prompt = "忠诚：选择1个友方异象"
    req.deciding_player = player
    t = game.targeting_system.request_target(req)
    if t is None:
        return False
    if not isinstance(t, Minion):
        print("  忠诚：目标必须是异象")
        return False
    if t.owner != player:
        print("  忠诚：目标必须是友方异象")
        return False

    def _dr(m, p, b):
        copy_card = create_card_by_name(m.name, p)
        if copy_card is None:
            print(f"  {m.name} 的亡语：无法创建复制")
            return
        if len(p.card_hand) < p.card_hand_max:
            p.card_hand.append(copy_card)
            copy_card.move_to("hand", b)
            print(f"  {m.name} 的亡语：将复制加入手牌")
        else:
            p.card_dis.append(copy_card)
            copy_card.move_to("discard", b)
            print(f"  {m.name} 的亡语：手牌已满，复制被弃置")

    add_deathrattle(t, _dr)
    print(f"  忠诚：{t.name} 获得亡语")
    return True


@strategy
def _jitui_effect(player, target, game, extras=None):
    """击退：将1个异象返回其所有者手牌。"""
    if not isinstance(target, Minion):
        print("  击退：目标必须是异象")
        return False
    from tards.auto_effects import return_to_hand
    return_to_hand(target, game, target.owner)
    return True


def _shenhaitansuozhe_targets(player, board):
    """深海探索者主目标：选择效果模式。"""
    return ["+2/2", "造成6点伤害"]


def _shenhaitansuozhe_extra_targets(player, board):
    """深海探索者额外目标：选择水路异象。"""
    return [m for m in board.minion_place.values() if m.is_alive() and board._is_water_at(m.position)]


@strategy
def _shenhaitansuozhe_effect(player, target, game, extras=None):
    """深海探索者：使1个水路异象获得+2/2 或 对其造成6点伤害。"""
    from tards.targeting import TargetingRequest

    # 阶段1：选择效果模式
    req1 = TargetingRequest()
    req1.source = player
    req1.scope_fn = lambda p, b: ["+2/2", "造成6点伤害"]
    req1.prompt = "深海探索者：选择效果模式"
    req1.deciding_player = player
    mode = game.targeting_system.request_target(req1)
    if mode is None:
        return False
    if mode not in ("+2/2", "造成6点伤害"):
        print("  深海探索者：效果模式无效")
        return False

    # 阶段2：选择水路异象
    def water_scope(p, b):
        return [m for m in b.minion_place.values() if m.is_alive() and b._is_water_at(m.position)]

    req2 = TargetingRequest()
    req2.source = player
    req2.scope_fn = water_scope
    req2.prompt = "深海探索者：选择1个水路异象"
    req2.deciding_player = player
    t = game.targeting_system.request_target(req2)
    if t is None:
        return False
    if not isinstance(t, Minion) or not t.is_alive():
        print("  深海探索者：目标无效")
        return False
    if not game.board._is_water_at(t.position):
        print("  深海探索者：目标必须是水路异象")
        return False

    if mode == "+2/2":
        t.attack += 2
        t.health += 2
        t.current_health += 2
        print(f"  深海探索者：{t.name} 获得 +2/2")
    else:
        deal_damage_to_minion(t, 6, source=None, game=game)
        print(f"  深海探索者：对 {t.name} 造成6点伤害")
    return True


@strategy
def _baohu_effect(player, target, game, extras=None):
    """保护：使1个异象获得+0/3 和坚韧1。"""
    if not isinstance(target, Minion):
        print("  保护：目标必须是异象")
        return False
    target.health += 3
    target.current_health += 3
    target.keywords["坚韧"] = target.keywords.get("坚韧", 0) + 1
    target.recalculate()
    print(f"  保护：{target.name} 获得 +0/3 和坚韧1")
    return True


@strategy
def _xiaolv_effect(player, target, game, extras=None):
    """效率：获得1个额外的C槽。"""
    player.c_point_max += 1
    print(f"  {player.name} 获得1个额外C槽")
    return True


@strategy
def _jingyanxiubu_effect(player, target, game, extras=None):
    """经验修补：将手牌抽至6张。获得1个额外的C槽和T槽。使所有友方异象获得+4HP。"""
    # 1. 将手牌抽至6张
    to_draw = max(0, 6 - len(player.card_hand))
    if to_draw > 0:
        player.draw_card(to_draw, game=game)
        print(f"  经验修补：{player.name} 将手牌补至6张")
    # 2. 获得额外槽位
    player.c_point_max += 1
    player.t_point_max += 1
    print(f"  经验修补：{player.name} 获得1个额外C槽和T槽")
    # 3. 友方异象+4HP（含上限）
    for minion in all_friendly_minions(game, player):
        if minion.is_alive():
            minion.health += 4
            minion.current_health += 4
            print(f"  经验修补：{minion.name} 获得 +4HP")
    return True


@strategy
def _kanfa_effect(player, target, game, extras=None):
    """砍伐！：开发1张花费不大于3的非敌对生物异象。将1张"掘进！"加入手牌。"""
    from tards import DEFAULT_REGISTRY, CardType
    # 1. 开发：从全局范围中筛选候选，随机3张3选1加入手牌
    candidates = [
        d for d in DEFAULT_REGISTRY.all_cards()
        if d.card_type == CardType.MINION
        and "生物" in d.tags
        and "敌对" not in d.tags
        and convert_cost_to_t(d.cost) <= 3
    ]
    if candidates:
        game.develop_card(player, candidates)
    else:
        print("  砍伐！：无符合条件的非敌对生物异象")
    # 2. 将掘进！加入手牌
    juejin = create_card_by_name("掘进！", player)
    if juejin:
        if len(player.card_hand) < player.card_hand_max:
            player.card_hand.append(juejin)
            juejin.move_to("hand", game)
            print("  砍伐！：将掘进！加入手牌")
        else:
            player.card_dis.append(juejin)
            juejin.move_to("discard", game)
            print("  砍伐！：手牌已满，掘进！被弃置")
    return True


@strategy
def _juejin_effect(player, target, game, extras=None):
    """掘进！：开发1张花费不小于4的非友好生物异象，使其具有迅捷。"""
    from tards import DEFAULT_REGISTRY, CardType
    candidates = [
        d for d in DEFAULT_REGISTRY.all_cards()
        if d.card_type == CardType.MINION
        and "生物" in d.tags
        and "友好" not in d.tags
        and convert_cost_to_t(d.cost) >= 4
    ]
    if not candidates:
        print("  掘进！：无符合条件的非友好生物异象")
        return True

    def _add_xunjie(card):
        card.keywords["迅捷"] = True
        print(f"  掘进！：{card.name} 获得迅捷")

    game.develop_card(player, candidates, modify_fn=_add_xunjie)
    return True


@strategy
def _tiezhen_effect(player, target, game, extras=None):
    """铁砧：选择并弃掉1张附魔书，将2张复制加入手牌。然后若你有铁锭，抽1张牌。"""
    import copy as _copy
    # 1. 找到手牌中的附魔书
    enchanted_books = [c for c in player.card_hand if c.name in ENCHANTED_BOOK_POOL]
    if not enchanted_books:
        print("  铁砧：手牌中没有附魔书")
        return False
    # 2. 让玩家选择1张（选项含序号以区分同名卡）
    options = [f"{i+1}. {c.name}" for i, c in enumerate(enchanted_books)]
    choice = game.request_choice(player, options, title="铁砧：选择1张附魔书弃掉")
    if not choice:
        print("  铁砧：未选择附魔书")
        return False
    idx = int(choice.split('.')[0]) - 1
    chosen_card = enchanted_books[idx]
    player.discard_card(chosen_card, game, reason="effect")
    # 3. 将2张复制加入手牌
    for i in range(2):
        copied = _copy.copy(chosen_card)
        if copied.keywords:
            copied.keywords = copied.keywords.copy()
        if len(player.card_hand) < player.card_hand_max:
            player.card_hand.append(copied)
            copied.move_to("hand", game)
            print(f"  铁砧：将 {chosen_card.name} 的复制加入手牌")
        else:
            player.card_dis.append(copied)
            copied.move_to("discard", game)
            print(f"  铁砧：手牌已满，{chosen_card.name} 的复制被弃置")
    # 4. 若有铁锭，抽1张牌
    has_tieding = any(c.name == "铁锭" for c in player.card_hand)
    if has_tieding:
        player.draw_card(1, game=game)
        print("  铁砧：有铁锭，抽1张牌")
    return True


@strategy
def _yelian_effect(player, target, game, extras=None):
    """冶炼：移除所有矿物，将3个花费之和等于移除矿物的打出总和的非生命异象加入战场。"""
    from tards import DEFAULT_REGISTRY, CardType, Pack
    from tards.cards import MinionCard, Minion
    import itertools
    import random

    # 1. 从手牌中移除所有矿物
    minerals = [c for c in player.card_hand if isinstance(c, MineralCard)]
    total_value = 0
    for c in minerals:
        total_value += convert_cost_to_t(c.cost) + c.cost.ct
        player.card_hand.remove(c)
        c.move_to("exile", game)
        print(f"  冶炼：移除 {c.name}")
    if not minerals:
        print("  冶炼：手牌中没有矿物")
        return True

    print(f"  冶炼：移除矿物的总费用 = {total_value}")

    # 2. 筛选离散卡包的非生命异象候选池
    candidates = [
        d for d in DEFAULT_REGISTRY.all_cards()
        if d.pack == Pack.DISCRETE
        and d.card_type == CardType.MINION
        and "非生命" in d.tags
    ]
    if len(candidates) < 3:
        print("  冶炼：候选池不足3个非生命异象")
        return True

    # 3. 找所有3个异象组合，使费用之和等于 total_value
    valid_combos = []
    for combo in itertools.combinations(candidates, 3):
        combo_cost = sum(convert_cost_to_t(d.cost) + d.cost.ct for d in combo)
        if combo_cost == total_value:
            valid_combos.append(combo)

    if not valid_combos:
        print(f"  冶炼：找不到3个费用之和为 {total_value} 的非生命异象组合")
        return True

    # 4. 随机选一组，直接放置到随机空位（不触发部署效果）
    chosen_combo = random.choice(valid_combos)
    empties = empty_positions(player, game.board)
    random.shuffle(empties)
    for i, card_def in enumerate(chosen_combo):
        if i >= len(empties):
            print(f"  冶炼：战场已满，无法放置 {card_def.name}")
            break
        pos = empties[i]
        minion_card = card_def.to_game_card(player)
        minion = Minion(
            name=minion_card.name,
            owner=player,
            position=pos,
            attack=minion_card.attack,
            health=minion_card.health,
            source_card=minion_card,
            board=game.board,
            keywords=minion_card.keywords.copy(),
        )
        game.board.place_minion(minion, pos)
        print(f"  冶炼：将 {minion_card.name} 加入战场 ({pos})")
    return True


@strategy
@strategy
def _cuiruotongmeng_effect(player, target, game, extras=None):
    """脆弱同盟：消灭1个友方异象，将2张具有迅捷的"恶魂"加入战场，回合结束时，将其移除。"""
    from tards.cards import MinionCard, Minion
    from tards.cost import Cost
    import random
    from tards.targeting import TargetingRequest

    def scope(p, b):
        return [m for m in b.minion_place.values() if m.is_alive() and m.owner == p]

    req = TargetingRequest()
    req.source = player
    req.scope_fn = scope
    req.prompt = "脆弱同盟：选择1个友方异象消灭"
    req.deciding_player = player
    t = game.targeting_system.request_target(req)
    if t is None:
        return False

    # 1. 消灭友方异象
    if t and hasattr(t, "is_alive") and t.is_alive():
        destroy_minion(t, game)

    # 2. 召唤2个具有迅捷的恶魂
    empties = empty_positions(player, game.board)
    random.shuffle(empties)

    ghasts = []
    for i in range(min(2, len(empties))):
        pos = empties[i]
        card = MinionCard(
            name="恶魂",
            owner=player,
            cost=Cost(t=3),
            targets=lambda p, b: [],
            attack=3,
            health=3,
            keywords={"亡语": True, "迅捷": True},
        )
        minion = Minion(
            name="恶魂",
            owner=player,
            position=pos,
            attack=3,
            health=3,
            source_card=card,
            board=game.board,
            keywords={"亡语": True, "迅捷": True},
        )
        game.board.place_minion(minion, pos)
        minion.summon_turn = game.current_turn
        print(f"  {player.name} 在 {pos} 召唤了恶魂")
        ghasts.append(minion)

    # 3. 回合结束时移除
    def _remove_self(g, event_data, m):
        if m.is_alive():
            remove_minion_no_death(m, g)

    for g in ghasts:
        g.on_turn_end = _remove_self

    return True


@strategy
def _zhengzhuangshangzhen_effect(player, target, game, extras=None):
    """整装上阵：抉择：使所有友方离散异象获得+1/1，或获得+1HP和+1坚韧等级。
    若本回合此前未部署异象，两项都触发。"""
    from tards import Pack
    from card_pools.effect_utils import minions_deployed_this_turn

    # 筛选友方离散异象
    discrete_minions = [
        m for m in all_friendly_minions(game, player)
        if m.is_alive()
        and getattr(getattr(m, "source_card", None), "pack", None) == Pack.DISCRETE
    ]

    if not discrete_minions:
        print("  整装上阵：场上没有友方离散异象")
        return True

    # 检查本回合是否已部署异象
    no_deploy = minions_deployed_this_turn(game, player) == 0

    def apply_buff_a():
        for m in discrete_minions:
            buff_minion(m, atk_delta=1, hp_delta=1, permanent=True)
            m.current_health += 1
            print(f"  整装上阵：{m.name} 获得 +1/1")

    def apply_buff_b():
        for m in discrete_minions:
            buff_minion(m, atk_delta=0, hp_delta=1, permanent=True)
            m.current_health += 1
            modify_keyword_number(m, "坚韧", 1)
            print(f"  整装上阵：{m.name} 获得 +1HP 和 +1坚韧")

    if no_deploy:
        apply_buff_a()
        apply_buff_b()
        print("  整装上阵：本回合未部署异象，两项都触发")
    else:
        choice = game.request_choice(
            player,
            ["所有友方离散异象获得 +1/1", "所有友方离散异象获得 +1HP 和 +1坚韧等级"],
            title="整装上阵：抉择",
        )
        if choice == 0:
            apply_buff_a()
        else:
            apply_buff_b()

    return True


@strategy
def _zhushi_effect(player, target, game, extras=None):
    """蛀蚀：对方抽1张牌，失去与此牌花费相同的T点。若场上有蠹虫，再弃掉此牌。"""
    opponent = game.p2 if player == game.p1 else game.p1

    if not opponent.card_deck:
        print("  蛀蚀：对方牌库已空")
        return True

    # 1. 对方抽1张牌
    drawn_card = opponent.card_deck.pop()
    drawn_card.move_to("hand", game)

    # 处理手牌满的情况（mill）
    if len(opponent.card_hand) >= opponent.card_hand_max:
        drawn_card.move_to("discard", game)
        opponent.card_dis.append(drawn_card)
        print(f"  蛀蚀：{opponent.name} 手牌已满，{drawn_card.name} 被弃置")
        return True

    opponent.card_hand.append(drawn_card)
    print(f"  蛀蚀：{opponent.name} 抽到 {drawn_card.name}")

    # 2. 失去与此牌花费相同的T点
    cost_value = convert_cost_to_t(drawn_card.cost) + drawn_card.cost.ct
    opponent.t = max(0, opponent.t - cost_value)
    print(f"  蛀蚀：{opponent.name} 失去 {cost_value} T点")

    # 3. 若场上有蠹虫，再弃掉此牌
    has_silverfish = any(
        m.is_alive() and m.name == "蠹虫"
        for m in game.board.minion_place.values()
    )
    if has_silverfish:
        opponent.discard_card(drawn_card, game, reason="effect")
        print(f"  蛀蚀：场上有蠹虫，弃掉 {drawn_card.name}")

    return True


@strategy
def _mishi_effect(player, target, game, extras=None):
    """迷失：移除1个异象，将其2张复制置入其所有者卡组顶。"""
    import copy

    if not target or not hasattr(target, "is_alive") or not target.is_alive():
        print("  迷失：未选择目标")
        return True

    # 1. 移除异象（不触发亡语）
    owner = target.owner
    remove_minion_no_death(target, game)

    # 2. 创建2张复制，置入所有者卡组顶
    source_card = getattr(target, "source_card", None)
    if not source_card:
        print("  迷失：目标没有 source_card，无法复制")
        return True

    for i in range(2):
        copied = copy.copy(source_card)
        if copied.keywords:
            copied.keywords = copied.keywords.copy()
        copied.owner = owner
        owner.card_deck.append(copied)
        copied.move_to("deck", game)
        print(f"  迷失：将 {copied.name} 的复制置入 {owner.name} 卡组顶")

    return True


@strategy
def _yuguwajue_effect(player, target, game, extras=None):
    """鱼骨挖掘：开发1张攻击力不大于4的非友好生物异象，将其复制加入战场。"""
    from tards import DEFAULT_REGISTRY, CardType, Pack
    from tards.cards import MinionCard, Minion
    import random

    # 1. 筛选候选池：离散、异象、攻击≤4、非友好、生物
    candidates = [
        d for d in DEFAULT_REGISTRY.all_cards()
        if d.pack == Pack.DISCRETE
        and d.card_type == CardType.MINION
        and getattr(d, "attack", 99) <= 4
        and "友好" not in d.tags
        and "生物" in d.tags
    ]

    if not candidates:
        print("  鱼骨挖掘：找不到符合条件的非友好生物异象")
        return True

    # 2. 随机3选1
    pool = random.sample(candidates, min(3, len(candidates)))
    options = [d.name for d in pool]
    choice = game.request_choice(player, options, title="鱼骨挖掘：开发1张异象")
    if choice < 0 or choice >= len(pool):
        print("  鱼骨挖掘：未选择")
        return True

    chosen_def = pool[choice]

    # 3. 复制加入战场（不触发部署效果）
    empties = empty_positions(player, game.board)
    if not empties:
        print("  鱼骨挖掘：战场已满")
        return True

    pos = random.choice(empties)
    minion_card = chosen_def.to_game_card(player)
    minion = Minion(
        name=minion_card.name,
        owner=player,
        position=pos,
        attack=minion_card.attack,
        health=minion_card.health,
        source_card=minion_card,
        board=game.board,
        keywords=minion_card.keywords.copy() if minion_card.keywords else {},
    )
    game.board.place_minion(minion, pos)
    print(f"  鱼骨挖掘：将 {minion_card.name} 加入战场 ({pos})")
    return True


@strategy
def _chuizhushujing_effect(player, target, game, extras=None, card=None):
    """垂直竖井：抉择：抽1张牌，将一张"垂直竖井"加入对方手牌（费用+1，抽牌数+1），或受到5点伤害。"""
    import copy

    # 获取当前这张卡的抽牌数（击鼓传花递增）
    draw_count = getattr(card, "_chuizhushujing_draw", 1) if card else 1

    choice = game.request_choice(
        player,
        [f"抽{draw_count}张牌，将一张增强的垂直竖井交给对方", "受到5点伤害"],
        title="垂直竖井：抉择",
    )

    if choice == 1:
        deal_damage_to_player(player, 5, game)
        return True

    # 选项A：抽牌 + 传花
    draw_cards(player, draw_count, game)

    opponent = game.p2 if player == game.p1 else game.p1
    if card:
        new_card = copy.copy(card)
        # 费用+1
        from tards.cost import Cost
        new_card.cost = copy.copy(card.cost)
        new_card.cost.t += 1
        # 抽牌数+1
        new_card._chuizhushujing_draw = draw_count + 1
        # 转交给对方
        new_card.owner = opponent
        if len(opponent.card_hand) < opponent.card_hand_max:
            opponent.card_hand.append(new_card)
            new_card.move_to("hand", game)
            print(f"  垂直竖井：将费用+1的垂直竖井交给 {opponent.name}（下回抽{draw_count + 1}张）")
        else:
            opponent.card_dis.append(new_card)
            new_card.move_to("discard", game)
            print(f"  垂直竖井：对方手牌已满，增强的垂直竖井被弃置")
    else:
        print("  垂直竖井：无法获取卡牌实例，传花失败")

    return True


@strategy
def _yiribaqiu_effect(player, target, game, extras=None):
    """一日八秋：抽3张牌，然后若场上有不少于4个友方地狱生物异象，跳过对方的下一个抽牌阶段。"""
    # 1. 抽3张牌
    draw_cards(player, 3, game)

    # 2. 统计友方地狱生物异象数量
    hell_bio_count = 0
    for m in all_friendly_minions(game, player):
        if m.is_alive():
            tags = getattr(m, "tags", [])
            if "地狱" in tags and "生物" in tags:
                hell_bio_count += 1

    # 3. 若不少于4个，跳过对方下一次抽牌
    if hell_bio_count >= 4:
        opponent = game.p2 if player == game.p1 else game.p1
        opponent._skip_next_draw = True
        print(f"  一日八秋：场上有 {hell_bio_count} 个友方地狱生物异象，{opponent.name} 跳过下一次抽牌")
    else:
        print(f"  一日八秋：场上仅有 {hell_bio_count} 个友方地狱生物异象，条件未满足")

    return True


# 策略效果函数名列表（供 discrete.py 手动挂接）
STRATEGY_MAP = {
    "木镐": "_mubiao_strategy",
    "石镐": "_shibiao_strategy",
    "金镐": "_jinbiao_strategy",
    "铁镐": "_tiegao_effect",
    "多重射击": "_duochongsheji_effect",
    "火矢": "_huoshi_effect",
    "横扫之刃": "_hengsao_effect",
    "饵钓": "_erdiao_effect",
    "忠诚": "_zhongcheng_effect",
    "击退": "_jitui_effect",
    "深海探索者": "_shenhaitansuozhe_effect",
    "保护": "_baohu_effect",
    "效率": "_xiaolv_effect",
    "经验修补": "_jingyanxiubu_effect",
    "砍伐！": "_kanfa_effect",
    "掘进！": "_juejin_effect",
    "铁砧": "_tiezhen_effect",
    "冶炼": "_yelian_effect",
    "脆弱同盟": "_cuiruotongmeng_effect",
    "一日八秋": "_yiribaqiu_effect",
    "整装上阵": "_zhengzhuangshangzhen_effect",
    "垂直竖井": "_chuizhushujing_effect",
    "鱼骨挖掘": "_yuguwajue_effect",
    "迷失": "_mishi_effect",
    "蛀蚀": "_zhushi_effect",
    "钻石镐": "_zuanshibiao_strategy",
    "雪球": "_xueqiu_strategy",
    "蜘蛛眼": "_zhizhuyan_strategy",
    "烈焰粉": "_lieyanfen_strategy",
    "凋零骷髅头": "_diaolingkuloutou_strategy",
    "光灵箭": "_guanglingjian_strategy",
    "战利品": "_zhanlipin_strategy",
    "遗弃": "_yiqi_strategy",
    "复兴": "_fuxing_effect",
    "高山": "_gaoshan_strategy",
    "恶地": "_erdi_strategy",
    "雨林": "_yulin_effect",
    "雪原": "_xueyuan_effect",
    "TNT": "_tnt_strategy",
    "复制技术": "_fuzhijishu_effect",
    "轰击": "_hongji_effect",
    "制导技术": "_zhidaojishu_effect",
    "珍珠塔": "_zhenzhuta_effect",
    "实体挤压": "_shitiyaji_effect",
    "C418": "_c418_effect",
    "禁人书": "_jinrenshu_strategy",
    "红石粉": "_hongshifen_strategy",
    "禁人书": "_jinrenshu_strategy",
    "恶魂之泪": "_ehanglei_strategy",
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
    "书": "_shu_strategy",
    "附魔台": "_fumota_strategy",
    "耕殖": "_gengzhi_strategy",
    # 抉择策略
    "探索": "_tansuo_strategy",
    "金苹果": "_jinpingguo_strategy",
    "丛林神殿": "_conglin_shendian_strategy",
    "沙漠神殿": "_shamo_shendian_strategy",
    "金西瓜片": "_jinxiguapian_effect",
    "雷暴": "_leibao_effect",
    "阴雨": "_yinyu_effect",
    "暗夜": "_anye_effect",
    "破袭": "_poxi_effect",
    "火灾": "_huozhai_effect",
    "遗迹机关": "_yiji_jiguan_effect",
    "临界点": "_linjiepoint_effect",
    "药水箭": "_yaoshuijian_effect",
    "熔岩": "_rongyan_effect",
    "充能铁轨": "_chongnengtiegui_effect",
    "调试棒": "_tiaoshibang_effect",
    "门船穿梭": "_menchuanchuansuo_effect",
    "冰霜行者": "_bingshuangxingzhe_effect",
    "耐久": "_naijiu_effect",
    "挖三填一": "_wasan_tianyi_effect",
}

# =============================================================================
# 对战效果（待完善）
# =============================================================================

@special
@special
def _jiangshizhuren_special(minion, player, game, extras=None):
    """僵尸猪人：部署：与1个敌方异象对战。若将其消灭，获得-1攻击力。"""
    from tards.targeting import TargetingRequest

    def scope(p, b):
        return [m for m in b.minion_place.values() if m.is_alive() and m.owner != p]

    req = TargetingRequest()
    req.source = minion
    req.scope_fn = scope
    req.prompt = "僵尸猪人：选择1个敌方异象对战"
    req.deciding_player = player
    enemy = game.targeting_system.request_target(req)
    if enemy is None:
        return False
    if not hasattr(enemy, "is_alive") or not enemy.is_alive():
        return True

    was_alive = enemy.is_alive()
    initiate_combat(minion, enemy, game)

    if was_alive and not enemy.is_alive():
        buff_minion(minion, atk_delta=-1, hp_delta=0)
        print(f"  {minion.name} 因消灭目标，攻击力-1")
    return True


@strategy
@strategy
def _guaiwulieren_strategy(player, target, game, extras=None):
    """怪物猎人：使1个友方生物异象+1/3，然后与1个敌方异象对战。"""
    from tards.targeting import TargetingRequest

    # 阶段1：选择友方异象
    def friendly_scope(p, b):
        return [m for m in b.minion_place.values() if m.is_alive() and m.owner == p]

    req1 = TargetingRequest()
    req1.source = player
    req1.scope_fn = friendly_scope
    req1.prompt = "怪物猎人：选择1个友方异象"
    req1.deciding_player = player
    friendly = game.targeting_system.request_target(req1)
    if friendly is None:
        return False
    if not hasattr(friendly, "is_alive") or not friendly.is_alive():
        print("  怪物猎人：目标无效")
        return False

    # 阶段2：选择敌方异象
    def enemy_scope(p, b):
        return [m for m in b.minion_place.values() if m.is_alive() and m.owner != p]

    req2 = TargetingRequest()
    req2.source = player
    req2.scope_fn = enemy_scope
    req2.prompt = "怪物猎人：选择1个敌方异象对战"
    req2.deciding_player = player
    enemy = game.targeting_system.request_target(req2)
    if enemy is None:
        return False
    if not hasattr(enemy, "is_alive") or not enemy.is_alive():
        print("  怪物猎人：目标无效")
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
    """金苹果：抉择：使1个异象获得+1/2，或使你获得+4HP。若指向僵尸村民，两项都触发。"""
    if not target or not hasattr(target, "is_alive") or not target.is_alive():
        print(f"  [警告] 金苹果：未选择有效的目标异象")
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
    """沙漠神殿：抽2张异象，使其获得+1/2。"""
    from tards.cards import MinionCard
    drawn = draw_cards_of_type(player, 2, MinionCard, game)
    for card in drawn:
        card.attack += 1
        card.health += 2
        print(f"  {card.name} 获得 +1/+2，当前 {card.attack}/{card.health}")
    return True


@strategy
def _mingmingpai_strategy(player, target, game, extras=None):
    """命名牌：选择1张手牌中的异象，使场上的1个异象获得"也算作是本异象"。抽1张牌。"""
    # target 是手牌中选中的异象卡，extras[0] 是场上选中的异象
    if not target or not hasattr(target, "name"):
        print("  [警告] 命名牌未选择手牌中的异象")
        return False
    if not extras or len(extras) < 1:
        print("  [警告] 命名牌未选择场上异象")
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
    """恶魂：本异象造成的伤害无视坚韧效果。亡语：将1张"恶魂之泪"加入手牌。"""
    minion._ignore_toughness = True

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
    # 异象效果
    "_kuangche_special",
    "_moyingman_special",
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
    "_kuqideheiyaoshi_special",
    "_jinrenta_special",
    "_gaolu_draw_trigger",
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
    "_gou_special",
    "_yang_special",
    "_zhu_special",
    "_yangtuo_special",
    "_yingwu_special",
    "_hetun_special",
    "_cunmin_special",
    "_youzhu_special",
    "_zhuling_special",
    "_zhulingmanbing_special",
    "_zhulinggongbing_special",
    "_cunmin2_special",
    "_qianyingbei_special",
    "_huanmozhe_special",
    "_haitun_special",
    "_jielueduizhang_special",
    "_jiangshicunmin_special",
    "_moyingxiang_special",
    "_qianxingzhe_special",
    "_jiangshijiqishi_special",
    "_kuloumaqishi_special",
    "_zhizhuqishi_special",
    "_diyuchuansongmen_special",
    "_chuan_special",
    "_tntpao_special",
    "_shanhun_special",
    "_banxiangou_special",
    "_xiangshu_evolve",
    "_yinyuehe_special",
    "_zhong_special",
    "_diaolingpaota_special",
    "_huosaichengchui_special",
    "_dungouji_special",
    "_shuimuqiang_special",
    "_modichuan_special",
    "_modishuijing_special",
    "_loudoukuanche_special",
    "_nvwu_special",
    "_zhongshengmao_special",
    "_shashoutu_special",
    "_shouweizhe_special",
    "_toast_special",
    "_jielueshou_special",
    "_nishiz_special",
    "_dongxuezhizhu_special",
    "_ehan_special",
    "_diaolingkulou_special",
    "_kuijiujia_special",
    "_diaoyugan_special",
    "_shu_strategy",
    "_fumota_strategy",
    "_gengzhi_strategy",
    # 对战效果
    "_jiangshizhuren_special",
    "_guaiwulieren_strategy",
    # 策略效果
    "_moyingzhenzhu_targets",
    "_moyingzhenzhu_effect",
    "_mubiao_strategy",
    "_shibiao_strategy",
    "_jinbiao_strategy",
    "_tiegao_effect",
    "_duochongsheji_effect",
    "_huoshi_effect",
    "_hengsao_effect",
    "_erdiao_effect",
    "_zhongcheng_effect",
    "_jitui_effect",
    "_shenhaitansuozhe_effect",
    "_baohu_effect",
    "_xiaolv_effect",
    "_jingyanxiubu_effect",
    "_kanfa_effect",
    "_juejin_effect",
    "_tiezhen_effect",
    "_yelian_effect",
    "_cuiruotongmeng_effect",
    "_yiribaqiu_effect",
    "_zhengzhuangshangzhen_effect",
    "_chuizhushujing_effect",
    "_yuguwajue_effect",
    "_mishi_effect",
    "_zhushi_effect",
    "_zuanshibiao_strategy",
    "_xueqiu_strategy",
    "_zhizhuyan_strategy",
    "_lieyanfen_strategy",
    "_diaolingkuloutou_strategy",
    "_guanglingjian_strategy",
    "_zhanlipin_strategy",
    "_yiqi_strategy",
    "_fuxing_effect",
    "_gaoshan_strategy",
    "_erdi_strategy",
    "_yulin_effect",
    "_xueyuan_effect",
    "_tnt_strategy",
    "_fuzhijishu_effect",
    "_hongji_effect",
    "_zhidaojishu_effect",
    "_zhenzhuta_effect",
    "_shitiyaji_effect",
    "_c418_effect",
    "_hongshifen_strategy",
    "_jinrenshu_strategy",
    "_ehanglei_strategy",
    "_ehanglei_targets",
    "_huoshi_targets",
    "_hengsao_targets",
    "_shenhaitansuozhe_targets",
    "_shenhaitansuozhe_extra_targets",
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
    "_qingjinshi_mineral",
    # 策略效果（原 discrete.py 内联 lambda）
    "_fengli_effect",
    "_shiyun_effect",
    "_jingzhuicaiji_effect",
    "_xingyunfangkuai_effect",
    "_yanhuozhixing_effect",
    "_jinxiguapian_effect",
    "_leibao_effect",
    "_yinyu_effect",
    "_anye_effect",
    "_poxi_effect",
    "_huozhai_effect",
    "_yiji_jiguan_effect",
    "_linjiepoint_effect",
    "_yaoshuijian_effect",
    "_rongyan_effect",
    "_chongnengtiegui_effect",
    "_tiaoshibang_effect",
    "_menchuanchuansuo_effect",
    "_bingshuangxingzhe_effect",
    "_naijiu_effect",
    "_wasan_tianyi_effect",
    "_yanhuaqiaochi_effect",
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


def _qingjinshi_mineral(player, game):
    """青金石：打出无事发生。"""
    print(f"  {player.name} 打出青金石，无事发生")
    return True


# =============================================================================
# 原 discrete.py 内联 lambda 迁移（策略效果）
# =============================================================================

def _fengli_effect(player, target, game, extras=None):
    """锋利：对一个异象造成6点伤害。"""
    deal_damage_to_minion(target, 6, game=game)
    return True


def _shiyun_effect(player, target, game, extras=None):
    """时运：抽2张牌。"""
    player.draw_card(2, game=game)
    return True


def _jingzhuicaiji_effect(player, target, game, extras=None):
    """精准采集：开发1张卡组中的牌。"""
    game.develop_card(player, player.original_deck_defs)
    return True


def _xingyunfangkuai_effect(player, target, game, extras=None):
    """幸运方块：开发1张离散金卡异象。"""
    from tards import DEFAULT_REGISTRY
    candidates = [
        c for c in DEFAULT_REGISTRY.all_cards()
        if c.pack == Pack.DISCRETE and c.rarity == Rarity.GOLD and c.card_type == CardType.MINION
    ]
    game.develop_card(player, candidates)
    return True


@strategy
def _bingshuangxingzhe_effect(player, target, game, extras=None):
    """冰霜行者：冰冻1个异象及其相邻异象。抽1张牌。"""
    if not target or not hasattr(target, "is_alive") or not target.is_alive():
        print("  [警告] 冰霜行者：未选择有效的目标异象")
        return False

    # 给目标冰冻1
    gain_keyword(target, "冰冻", 1)
    print(f"  冰霜行者：{target.name} 获得冰冻1")

    # 给相邻异象冰冻1
    for pos in get_adjacent_positions(target.position, game.board):
        m = game.board.get_minion_at(pos)
        if m and m.is_alive():
            gain_keyword(m, "冰冻", 1)
            print(f"  冰霜行者：{m.name}（相邻）获得冰冻1")

    # 抽1张牌
    draw_cards(player, 1, game)
    print(f"  冰霜行者：{player.name} 抽1张牌")
    return True


@strategy
def _naijiu_effect(player, target, game, extras=None):
    """耐久：抽1张牌，你获得+4HP。"""
    draw_cards(player, 1, game)
    print(f"  耐久：{player.name} 抽1张牌")
    heal_player(player, 4)
    print(f"  耐久：{player.name} 获得+4HP")
    return True


@strategy
def _wasan_tianyi_effect(player, target, game, extras=None):
    """挖三填一：移除1个异象。下个抽牌阶段，将其返回战场。其所有者抽1张牌。"""
    if not target or not hasattr(target, "is_alive") or not target.is_alive():
        print("  [警告] 挖三填一：未选择有效的目标异象")
        return False

    original_pos = target.position
    owner = target.owner

    # 从战场移除（不触发亡语）
    remove_minion_no_death(target, game)

    # 其所有者抽1张牌
    draw_cards(owner, 1, game)
    print(f"  挖三填一：{owner.name} 抽1张牌")

    # 注册下个抽牌阶段返回战场
    turn_removed = game.current_turn

    def _on_phase_start(event):
        if event.data.get("phase") != game.PHASE_DRAW:
            return
        if game.current_turn <= turn_removed:
            return  # 跳过当前回合的抽牌阶段

        # 找到合适的位置
        pos = original_pos
        if pos in game.board.minion_place:
            # 原位置被占，找最近的空位
            empties = empty_positions(owner, game.board)
            if empties:
                pos = min(empties, key=lambda p: abs(p[0]-original_pos[0]) + abs(p[1]-original_pos[1]))
            else:
                print(f"  挖三填一：{owner.name} 的区域没有空位，{target.name} 无法返回战场")
                game.history.unlisten(listener_id)
                return

        # 将异象放回战场（不触发部署事件）
        game.board.minion_place[pos] = target
        target.position = pos
        print(f"  挖三填一：{target.name} 返回战场 {pos}")
        game.history.unlisten(listener_id)

    listener_id = on("phase_start", _on_phase_start, game)
    return True


def _yanhuozhixing_effect(player, target, game, extras=None):
    """焰火之星：对1个异象造成6点伤害，溢出伤害随机分配至所有敌方目标。"""
    from card_pools.effect_utils import get_opponent

    if not target or not hasattr(target, "is_alive") or not target.is_alive():
        print("  [警告] 焰火之星：未选择有效的目标异象")
        return False

    actual_damage = deal_damage_to_minion(target, 6, source=None, game=game)
    overflow = 6 - actual_damage

    if overflow > 0:
        print(f"  焰火之星：溢出 {overflow} 点伤害")
        opponent = get_opponent(game, player)
        for _ in range(overflow):
            candidates = [m for m in all_enemy_minions(game, player) if m.is_alive()] + [opponent]
            if candidates:
                t = random.choice(candidates)
                if isinstance(t, Minion):
                    deal_damage_to_minion(t, 1, source=None, game=game)
                else:
                    deal_damage_to_player(t, 1, source=None, game=game)
                print(f"  焰火之星溢出伤害：对 {t.name} 造成1点伤害")

    return True


@strategy
def _jinxiguapian_effect(player, target, game, extras=None):
    """金西瓜片：使1个异象获得：回合开始：获得+1/1。"""
    if not target or not hasattr(target, "is_alive") or not target.is_alive():
        print("  [警告] 金西瓜片：未选择有效的目标异象")
        return False

    def _on_turn_start(event):
        if not target.is_alive():
            return
        buff_minion(target, atk_delta=1, hp_delta=1, permanent=True)
        target.current_health += 1
        print(f"  {target.name} 回合开始：获得+1/+1")

    on_turn_start(target, game, _on_turn_start)
    print(f"  金西瓜片：{target.name} 获得「回合开始：+1/+1」")
    return True


@strategy
@strategy
def _yinyu_effect(player, target, game, extras=None):
    """阴雨：对1个非高地异象造成2点伤害，将其攻击力设为0直到回合结束。"""
    from tards.targeting import TargetingRequest

    def scope(p, b):
        return [m for m in b.minion_place.values() if m.is_alive() and not m.keywords.get("高地", False)]

    req = TargetingRequest()
    req.source = player
    req.scope_fn = scope
    req.prompt = "阴雨：选择1个非高地异象"
    req.deciding_player = player
    t = game.targeting_system.request_target(req)
    if t is None:
        return False
    if not hasattr(t, "is_alive") or not t.is_alive():
        print("  [警告] 阴雨：未选择有效的目标异象")
        return False

    # 造成2点伤害
    deal_damage_to_minion(t, 2, game=game)

    # 若存活，临时将攻击力设为0
    if t.is_alive():
        t.temp_attack_bonus -= t.attack
        t.recalculate()
        print(f"  {t.name} 攻击力被设为0（直到回合结束）")

    return True


@strategy
def _anye_effect(player, target, game, extras=None):
    """暗夜：开发1张离散迅捷异象。然后若你拥有不小于4个T点，对所有敌方目标造成1点伤害。"""
    from tards import DEFAULT_REGISTRY, Pack, CardType

    # 开发1张离散迅捷异象
    candidates = [
        c for c in DEFAULT_REGISTRY.all_cards()
        if c.pack == Pack.DISCRETE and c.card_type == CardType.MINION and c.keywords.get("迅捷")
    ]
    if candidates:
        game.develop_card(player, candidates)
    else:
        print("  暗夜：没有可开发的离散迅捷异象")

    # 若拥有不小于4个T点，对所有敌方目标造成1点伤害
    if player.t_point >= 4:
        opponent = game.p2 if player == game.p1 else game.p1
        for enemy in all_enemy_minions(game, player):
            if enemy.is_alive():
                deal_damage_to_minion(enemy, 1, source=None, game=game)
        deal_damage_to_player(opponent, 1, source=None, game=game)
        print("  暗夜：对所有敌方目标造成1点伤害")

    return True


@strategy
@strategy
def _poxi_effect(player, target, game, extras=None):
    """破袭：使1个友方异象与1个攻击力最低的敌方异象对战。若将其消灭，获得+1HP并重复此流程。"""
    from tards.targeting import TargetingRequest

    def scope(p, b):
        return [m for m in b.minion_place.values() if m.is_alive() and m.owner == p]

    req = TargetingRequest()
    req.source = player
    req.scope_fn = scope
    req.prompt = "破袭：选择1个友方异象"
    req.deciding_player = player
    friendly = game.targeting_system.request_target(req)
    if friendly is None:
        return False
    if not friendly or not hasattr(friendly, "is_alive") or not friendly.is_alive():
        print("  [警告] 破袭：未选择有效的友方异象")
        return False

    while True:
        if not friendly.is_alive():
            break

        enemies = [m for m in all_enemy_minions(game, player) if m.is_alive()]
        if not enemies:
            break

        # 找出攻击力最低的敌方异象
        min_attack = min(m.attack for m in enemies)
        lowest = [m for m in enemies if m.attack == min_attack]

        if len(lowest) == 1:
            enemy = lowest[0]
        else:
            options = [f"{m.name}({m.position[0]},{m.position[1]})" for m in lowest]
            choice = game.request_choice(player, options, title="破袭：选择攻击力最低的敌方异象")
            if choice is None:
                break
            enemy = None
            for m in lowest:
                if f"{m.name}({m.position[0]},{m.position[1]})" == choice:
                    enemy = m
                    break
            if enemy is None:
                break

        if not enemy.is_alive():
            break

        print(f"  破袭：{friendly.name} 与 {enemy.name}({enemy.attack}/{enemy.health}) 对战")
        initiate_combat(friendly, enemy, game)

        if game.check_game_over():
            return True

        # 若敌方被消灭且友方存活，获得+1HP，继续循环
        if not enemy.is_alive() and friendly.is_alive():
            buff_minion(friendly, atk_delta=0, hp_delta=1, permanent=True)
            friendly.current_health += 1
            print(f"  {friendly.name} 消灭 {enemy.name}，获得+1HP")
        else:
            break

    return True


@strategy
def _huozhai_effect(player, target, game, extras=None):
    """火灾：你和对手轮流抽牌至手牌数量为7张，下回合开始时弃掉本次抽到的牌。"""
    opponent = game.p2 if player == game.p1 else game.p1

    drawn_records = []  # [(owner, card), ...]

    def do_draw(p):
        before = set(p.card_hand)
        p.draw_card(1, game=game)
        after = set(p.card_hand)
        new_cards = after - before
        for card in new_cards:
            drawn_records.append((p, card))

    # 轮流抽牌直到双方都达到7张
    while len(player.card_hand) < 7 or len(opponent.card_hand) < 7:
        if len(player.card_hand) < 7:
            do_draw(player)
        if len(opponent.card_hand) < 7:
            do_draw(opponent)
        if len(player.card_hand) >= 7 and len(opponent.card_hand) >= 7:
            break

    if drawn_records:
        print(f"  火灾：本次共抽到 {len(drawn_records)} 张牌")

    # 注册下回合开始时弃牌（跳过当前回合的结算阶段）
    turn_played = game.current_turn

    def _on_phase_start(event, g):
        if event.data.get("phase") != game.PHASE_RESOLVE:
            return
        if game.current_turn <= turn_played:
            return  # 跳过当前回合
        discarded = 0
        for owner, card in drawn_records:
            if card in owner.card_hand:
                owner.discard_card(card, game, reason="火灾效果")
                discarded += 1
        if discarded > 0:
            print(f"  火灾：弃掉 {discarded} 张本次抽到的牌")
        game.history.unlisten(listener_id)

    listener_id = game.history.listen("phase_start", _on_phase_start, priority=0)

    return True


@strategy
def _yiji_jiguan_effect(player, target, game, extras=None):
    """遗迹机关：将2张「绊线钩」加入战场。然后若场上有不多于3个「绊线钩」，对所有目标造成1点伤害。"""
    from tards import DEFAULT_REGISTRY

    card_def = DEFAULT_REGISTRY.get("绊线钩")
    if not card_def:
        print("  [警告] 遗迹机关：找不到绊线钩的定义")
        return False

    # 获取友方区域空位并随机选择最多2个
    empties = empty_positions(player, game.board)
    if not empties:
        print("  遗迹机关：友方区域没有空位")
        return False

    positions = random.sample(empties, min(2, len(empties)))

    for pos in positions:
        card = card_def.to_game_card(player)
        result = card.effect(player, pos, game)
        if result:
            print(f"  遗迹机关：将绊线钩加入战场 {pos}")
        else:
            print(f"  遗迹机关：无法在 {pos} 部署绊线钩")

    # 统计场上绊线钩数量（包括友方和敌方）
    banxian_count = sum(
        1 for m in game.board.minion_place.values()
        if m.name == "绊线钩" and m.is_alive()
    )
    print(f"  遗迹机关：场上有 {banxian_count} 个绊线钩")

    # 若场上不多于3个绊线钩，对所有目标造成1点伤害
    if banxian_count <= 3:
        for m in all_friendly_minions(game, player):
            if m.is_alive():
                deal_damage_to_minion(m, 1, source=None, game=game)
        for m in all_enemy_minions(game, player):
            if m.is_alive():
                deal_damage_to_minion(m, 1, source=None, game=game)
        deal_damage_to_player(player, 1, source=None, game=game)
        opponent = game.p2 if player == game.p1 else game.p1
        deal_damage_to_player(opponent, 1, source=None, game=game)
        print("  遗迹机关：场上绊线钩不多于3个，对所有目标造成1点伤害")

    return True


@strategy
def _linjiepoint_effect(player, target, game, extras=None):
    """临界点：开发1张非生命异象，使其具有绊线钩反击效果。"""
    from tards import DEFAULT_REGISTRY, Pack, CardType

    candidates = [
        c for c in DEFAULT_REGISTRY.all_cards()
        if c.pack == Pack.DISCRETE
        and c.card_type == CardType.MINION
        and "非生命" in c.tags
    ]
    if not candidates:
        print("  临界点：没有可用的非生命异象")
        return False

    def modify_fn(card):
        original_special = card.special

        def _hook_special(minion, player, game, extras=None):
            # 先调用原 special（如果有）
            if original_special:
                import inspect
                sig = inspect.signature(original_special)
                if len(sig.parameters) >= 4:
                    original_special(minion, player, game, extras or [])
                else:
                    original_special(minion, player, game)

            # 注册绊线钩的 before_damage 效果
            def on_before_damage(event):
                if not minion.is_alive():
                    return
                victim = event.data.get("target")
                if victim is not minion:
                    return
                r, c = minion.position
                count = 0
                for m in all_friendly_minions(game, player):
                    if m.name == "绊线钩" and (m.position[0] == r or m.position[1] == c):
                        count += 1
                if count > 0:
                    print(f"  绊线钩效果（临界点）：{minion.name} 受到伤害，同行/同列有 {count} 个友方绊线钩")
                for _ in range(count):
                    enemies = all_enemy_minions(game, player)
                    opponent = game.p2 if player == game.p1 else game.p1
                    candidates = enemies + [opponent]
                    if candidates:
                        t = random.choice(candidates)
                        from tards.cards import Minion
                        if isinstance(t, Minion):
                            deal_damage_to_minion(t, 1, source=minion, game=game)
                        else:
                            deal_damage_to_player(t, 1, source=minion, game=game)
                        print(f"  绊线钩效果（临界点）：{minion.name} 对 {t.name} 造成1点伤害")

            on("before_damage", on_before_damage, game, minion)
            print(f"  临界点：{minion.name} 获得了绊线钩反击效果")

        card.special = _hook_special

    result = game.develop_card(player, candidates, count=3, modify_fn=modify_fn, return_card=True)
    if result:
        print(f"  临界点：开发了 {result.name} 并赋予绊线钩反击效果")
    return result is not None


@strategy
def _yaoshuijian_effect(player, target, game, extras=None):
    """药水箭：使1个异象+1/2，抽1张牌。若指向非生命异象，所有友方非生命异象+2HP。"""
    if not target or not hasattr(target, "is_alive") or not target.is_alive():
        print("  [警告] 药水箭：未选择有效的异象")
        return False

    # +1/2 永久增益
    buff_minion(target, atk_delta=1, hp_delta=2, permanent=True)
    target.current_health += 2
    print(f"  药水箭：{target.name} 获得 +1/+2")

    # 抽1张牌
    draw_cards(player, 1, game)
    print(f"  药水箭：{player.name} 抽1张牌")

    # 若指向非生命异象，所有友方非生命异象+2HP
    if "非生命" in getattr(target, "tags", []):
        for m in all_friendly_minions(game, player):
            if m.is_alive() and "非生命" in getattr(m, "tags", []):
                buff_minion(m, atk_delta=0, hp_delta=2, permanent=True)
                m.current_health += 2
                print(f"  药水箭（非生命加成）：{m.name} 获得+2HP")

    return True


def _yanhuaqiaochi_effect(player, target, game, extras=None):
    """烟花鞘翅：将卡组顶的1张迅捷异象加入战场。"""
    from tards.cards import MinionCard

    empties = empty_positions(player, game.board)
    if not empties:
        print("  烟花鞘翅：友方区域没有空位")
        return False

    # 使用 search_deck 从卡组顶搜索迅捷异象
    candidates = search_deck(player, lambda c: isinstance(c, MinionCard) and c.keywords.get("迅捷"))
    if not candidates:
        print("  烟花鞘翅：卡组中没有迅捷异象")
        return False

    card = candidates[0]
    player.card_deck.remove(card)
    pos = random.choice(empties)
    result = card.effect(player, pos, game)
    if result:
        print(f"  烟花鞘翅：将 {card.name} 加入战场 {pos}")
        return True
    else:
        if len(player.card_hand) < player.card_hand_max:
            player.card_hand.append(card)
            print(f"  烟花鞘翅：部署失败，{card.name} 加入手牌")
        else:
            player.card_dis.append(card)
            print(f"  烟花鞘翅：部署失败且手牌已满，{card.name} 被弃置")
        return False


@strategy
def _menchuanchuansuo_effect(player, target, game, extras=None):
    """门船穿梭：使1个友方异象返回手牌，将其花费设为1I直到回合结束。
    然后若其上回合在场上，使其部署时具有迅捷。
    """
    from tards.targeting import TargetingRequest

    def scope(p, b):
        return [m for m in b.minion_place.values() if m.is_alive() and m.owner == p]

    req = TargetingRequest()
    req.source = player
    req.scope_fn = scope
    req.prompt = "门船穿梭：选择1个友方异象"
    req.deciding_player = player
    t = game.targeting_system.request_target(req)
    if t is None:
        return False
    if not t or not hasattr(t, "is_alive") or not t.is_alive():
        print("  [警告] 门船穿梭：未选择有效的友方异象")
        return False

    was_on_board_last_turn = not was_minion_deployed_this_turn(game, t)

    card = getattr(t, "source_card", None)

    from tards.auto_effects import return_to_hand
    return_to_hand(t, game, player)

    if card:
        # 保存原花费
        from tards.cost import Cost
        original_cost = card.cost
        card.cost = Cost(minerals={"I": 1})
        print(f"  门船穿梭：{card.name} 的花费设为1I")

        # 注册回合结束恢复花费
        turn_set = game.current_turn

        def restore_cost(event):
            if event.data.get("phase") == game.PHASE_RESOLVE:
                card.cost = original_cost
                print(f"  门船穿梭：{card.name} 的花费恢复")
                game.history.unlisten(listener_id)

        listener_id = on("phase_end", restore_cost, game)

        # 若上回合在场上，部署时赋予迅捷
        if was_on_board_last_turn:
            original_special = card.special

            def _swift_special(minion, player, game, extras=None):
                if original_special:
                    import inspect
                    sig = inspect.signature(original_special)
                    if len(sig.parameters) >= 4:
                        original_special(minion, player, game, extras or [])
                    else:
                        original_special(minion, player, game)

                minion.keywords["迅捷"] = True
                minion.recalculate()
                print(f"  门船穿梭：{minion.name} 部署时获得迅捷")

                # 只触发一次，恢复原来的 special
                card.special = original_special

            card.special = _swift_special

    return True


@strategy
def _rongyan_effect(player, target, game, extras=None):
    """熔岩：抉择：对所有后排异象造成4点伤害 或 对对手造成6点伤害。"""
    choice = game.request_choice(
        player,
        ["对所有后排异象造成4点伤害", "对对手造成6点伤害"],
        title="熔岩：选择效果",
    )

    if choice == "对所有后排异象造成4点伤害":
        back_rows = [0, 4]
        for m in get_all_minions(game):
            if m.is_alive() and m.position[0] in back_rows:
                deal_damage_to_minion(m, 4, source=None, game=game)
                print(f"  熔岩：{m.name} 受到4点伤害")
        return True

    elif choice == "对对手造成6点伤害":
        opponent = game.p2 if player == game.p1 else game.p1
        deal_damage_to_player(opponent, 6, source=None, game=game)
        print(f"  熔岩：对 {opponent.name} 造成6点伤害")
        return True

    return False


@strategy
def _chongnengtiegui_effect(player, target, game, extras=None):
    """充能铁轨：移动1个陆地异象。若是友方异象，抽1张牌。"""
    # 获取所有陆地异象
    land_minions = []
    for m in get_all_minions(game):
        if m.is_alive() and not game.board._is_water_at(m.position):
            land_minions.append(m)

    if not land_minions:
        print("  充能铁轨：场上没有陆地异象")
        return False

    # 选择目标异象
    options = [f"{m.name}({m.position[0]},{m.position[1]})" for m in land_minions]
    choice = game.request_choice(player, options, title="充能铁轨：选择要移动的陆地异象")
    if not choice:
        return False

    minion = None
    for m in land_minions:
        if f"{m.name}({m.position[0]},{m.position[1]})" == choice:
            minion = m
            break

    if not minion or not minion.is_alive():
        return False

    # 选择目标位置（该异象所有者友方行内的空位）
    friendly_rows = minion.owner.get_friendly_rows()
    empties = []
    for r in friendly_rows:
        for c in range(game.board.SIZE):
            pos = (r, c)
            if pos == minion.position:
                continue
            if pos not in game.board.minion_place and game.board.target_check(pos):
                is_water = game.board._is_water_at(pos)
                aquatic = minion.keywords.get("水生", False) or minion.keywords.get("两栖", False)
                if is_water and not aquatic:
                    continue
                if not is_water and minion.keywords.get("水生", False):
                    continue
                empties.append(pos)

    if not empties:
        print(f"  充能铁轨：{minion.name} 没有可移动的空位")
        return False

    dest_options = [f"({r},{c})" for r, c in empties]
    dest_choice = game.request_choice(player, dest_options, title=f"充能铁轨：选择 {minion.name} 的目标位置")
    if not dest_choice:
        return False

    dest = None
    for pos in empties:
        if f"({pos[0]},{pos[1]})" == dest_choice:
            dest = pos
            break

    if not dest:
        return False

    # 执行移动
    from card_pools.effect_utils import move
    success = move(minion, dest, game)
    if not success:
        return False

    # 若是友方异象，抽1张牌
    if minion.owner == player:
        draw_cards(player, 1, game)
        print(f"  充能铁轨：移动了友方异象 {minion.name}，抽1张牌")

    return True


@strategy
def _tiaoshibang_effect(player, target, game, extras=None):
    """调试棒：抽1张策略，展示并-1T，赋予其额外效果（打出时抽1张策略，展示并-1T）。"""
    from tards.cards import Strategy

    def _do_debug_effect(p, g, source_name="调试棒"):
        """执行调试效果：抽1张策略，展示并-1T。返回抽到的卡（如有）。"""
        drawn = draw_cards_of_type(p, 1, Strategy, g)
        if not drawn:
            print(f"  {source_name}：没有抽到策略")
            return None
        card = drawn[0]
        print(f"  {source_name}：展示策略 [{card.name}]")
        if hasattr(card, "cost") and hasattr(card.cost, "t") and card.cost.t > 0:
            card.cost.t -= 1
            print(f"  {source_name}：{card.name} 的T花费-1，当前为 {card.cost.t}T")
        return card

    # 主效果：抽1张策略，展示并-1T
    card = _do_debug_effect(player, game)
    if not card:
        return True  # 即使没抽到策略，牌本身已打出

    # 赋予额外效果：打出该策略卡时，额外触发调试效果
    original_effect = card.effect_fn

    def _bonus_effect(p, t, g, ex=None):
        # 执行原效果
        result = True
        if original_effect:
            import inspect
            sig = inspect.signature(original_effect)
            if len(sig.parameters) >= 4:
                result = original_effect(p, t, g, ex or [])
            else:
                result = original_effect(p, t, g)

        # 额外效果
        _do_debug_effect(p, g, source_name="调试棒效果")

        return result if result is not None else True

    card.effect_fn = _bonus_effect
    print(f"  调试棒：{card.name} 获得了额外效果（打出时抽1张策略，展示并-1T）")

    return True


@strategy
def _leibao_effect(player, target, game, extras=None):
    """雷暴：随机消灭2个敌方异象。"""
    enemies = [m for m in all_enemy_minions(game, player) if m.is_alive()]
    if not enemies:
        print("  雷暴：场上没有敌方异象")
        return True

    count = min(2, len(enemies))
    targets = random.sample(enemies, count)
    for m in targets:
        if m.is_alive():
            destroy_minion(m, game)
    print(f"  雷暴：随机消灭了 {count} 个敌方异象")
    return True
