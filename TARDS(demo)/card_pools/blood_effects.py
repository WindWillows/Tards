# 血契卡包人工效果实现
# 由 blood.py 引用

from tards.data.card_db import DEFAULT_REGISTRY
from tards.core.targets import target, target_mix
from card_pools.effect_decorator import special
from card_pools.effect_utils import (
    add_deathrattle,
    add_event_listener,
    buff_minion,
    destroy_minion,
    draw_cards,
    empty_positions,
    give_card_by_name,
    heal_player,
    on_after_attack,
    random_enemy_minion,
    summon_minion_by_name,
)

SPECIAL_MAP = {
    "保卫者": "_baoweizhe_special",
    "巫毒娃娃": "_wuduwawa_special",
    "天籁人偶": "_tianlairenou_special",
    "溴化银": "_xiuhuayin_special",
    "亡灵": "_wangling_special",
    "硫氰化钾": "_liuqinghuajia_special",
    "竹心": "_zhuxin_special",
    "环丁二烯": "_huanderxixi_special",
    "Bishop": "_bishop_special",
    "流明": "_liuming_special",
    "礼堂": "_liting_special",
    "独脚大盗": "_dujiaodadao_special",
    "显影室": "_xianyingshi_special",
    "死灵法师": "_silingfashi_special",
    "云君": "_yunjun_special",
    "无穷小量": "_wuqiongxiaoliang_special",
    "雷金纳德": "_leijinade_special",
    "铁心": "_tiexin_special",
    "阿波罗之卫": "_aboluozhiwei_special",
}

STRATEGY_MAP = {}

__all__ = [
    "SPECIAL_MAP",
    "STRATEGY_MAP",
    "_baoweizhe_special",
    "_wuduwawa_special",
    "_tianlairenou_special",
    "_xiuhuayin_special",
    "_wangling_special",
    "_liuqinghuajia_special",
    "_zhuxin_special",
    "_huanderxixi_special",
    "_bishop_special",
    "_liuming_special",
    "_liting_special",
    "_dujiaodadao_special",
    "_xianyingshi_special",
    "_silingfashi_special",
    "_yunjun_special",
    "_wuqiongxiaoliang_special",
    "_leijinade_special",
    "_yilong_cost_modifier",
    "_yilong_game_start",
    "_tiexin_special",
    "_aboluozhiwei_special",
    "_jiaopian_effect",
    "_peiti_effect",
    "_shuangsheng_bishou_effect",
    "_zhanzheng_heping_effect",
    "_sanbei_icecream_effect",
    "_xuejiang_effect",
    "_xuejiang_draw_trigger",
    "_ziyou_effect",
    "_wuzhi_effect",
    "_xianchu_xinzang_effect",
    "_jisuobuyu_effect",
    "_yongheng_effect",
    "_tansuanya_tie_effect",
    "_jiaojuan_effect",
    "_fusi_effect",
    "_kongju_zhi_effect",
    "_zhongying_effect",
    "_kongju_zhengshe_effect",
    "_chahuo_shuji_effect",
    "_wujiandi_yu_effect",
    "_wangyi_effect",
    "_shenyuan_effect",
    "_yusiwangpo_effect",
    "_guobao_effect",
    "_xuejian_bailian_effect",
    "_xiajian_effect",
    "_shenpan_qianxi_effect",
    "_xuezhi_huaibiao_effect",
    "_dunxiu_zhizhen_effect",
    "_hangou_chilun_effect",
    "_tianxia_wushuang_effect",
    "_weiwei_yuzhui_effect",
    "_zhanweifu1_effect",
    "_zhanweifu2_effect",
    "_zhanweifu3_effect",
    "_zhanweifu4_effect",
    "_qinchen_effect",
    "_yuzhong_effect",
    "_tingwu_effect",
    "_bomu_effect",
    "_rending_effect",
    "_meidan_effect",
    "_zhijianfangcun_special",
    "_erliuhuatan_special",
    "_jiaopian_choice",
    "_peiti_targets",
    "_yongheng_targets",
    "_wangyi_targets",
    "_guobao_cost_modifier",
    "_xuezhi_huaibiao_game_start",
    "target_highland_minion",
    "_zhanweifu1_draw_trigger",
    "_zhanweifu2_draw_trigger",
    "_zhanweifu4_draw_trigger",
    "_tianxiawushuang_effect",
    "_zhadanren_draw_trigger",
    "_shimengmo_special",
    "_budongdian_special",
    "_jupian_special",
    "_xuanchen_special",
    "_sanfuhualu_special",
    "_erliuhuatan_special",
    "_yixi_special",
    "_shuixieshi_cost_modifier",
    "_shuixieshi_game_start",
    "_shuixieshi_draw_trigger",
    "_guankui_effect",
    "_tianxiawushuang_effect",
    "_xuejia_draw_trigger",
    "_xuejia_special",
    "_xuejia_deathrattle",
]






# =============================================================================
# 保卫者：你受到伤害时，本异象获得+1/1
# =============================================================================
@special
def _baoweizhe_special(minion, player, game, extras=None):
    """保卫者：你受到伤害时，本异象获得+1/1。"""
    def _on_player_damage(event):
        target = event.get("target")
        if target != player:
            return
        damage = event.get("damage", 0)
        if damage > 0 and minion.is_alive():
            buff_minion(minion, 1, 1, permanent=True)
            print(f"  保卫者触发：{minion.name} 获得+1/1")

    from tards.constants import EVENT_PLAYER_DAMAGE
    add_event_listener(minion, game, EVENT_PLAYER_DAMAGE, _on_player_damage)


# =============================================================================
# 巫毒娃娃：你每受到1点伤害，获得1S
# =============================================================================
@special
def _wuduwawa_special(minion, player, game, extras=None):
    """巫毒娃娃：你每受到1点伤害，获得1S。"""
    def _on_player_damage(event):
        target = event.get("target")
        if target != player:
            return
        damage = event.get("damage", 0)
        if damage > 0:
            player.s_point += damage
            print(f"  巫毒娃娃触发：{player.name} 获得 {damage}S")

    from tards.constants import EVENT_PLAYER_DAMAGE
    add_event_listener(minion, game, EVENT_PLAYER_DAMAGE, _on_player_damage)


# =============================================================================
# 天籁人偶：受到伤害时，你获得等量HP
# =============================================================================
@special
def _tianlairenou_special(minion, player, game, extras=None):
    """天籁人偶：受到伤害时，你获得等量HP。"""
    def _on_damaged(event):
        if event.get("target") != minion:
            return
        damage = event.get("damage", 0)
        if damage > 0:
            heal_player(player, damage)
            print(f"  天籁人偶触发：{player.name} 恢复 {damage} HP")

    from card_pools.effect_utils import on_damaged
    on_damaged(minion, game, _on_damaged)


# =============================================================================
# 溴化银：攻击后，消灭本异象。亡语：将1张"胶片"加入对方手牌
# =============================================================================
@special
def _xiuhuayin_special(minion, player, game, extras=None):
    """溴化银：攻击后，消灭本异象。亡语：将1张"胶片"加入对方手牌。"""
    # 攻击后消灭
    def _suicide_after_attack(event):
        if event.get("attacker") != minion:
            return
        if minion.is_alive():
            from card_pools.effect_utils import destroy_minion
            destroy_minion(minion, game)
            print(f"  溴化银攻击后自毁")

    on_after_attack(minion, game, _suicide_after_attack)

    # 亡语：将胶片加入对方手牌
    def _dr(m, p, b):
        opponent = game.p1 if p == game.p2 else game.p2
        give_card_by_name(opponent, "胶片", reason="溴化银亡语")

    add_deathrattle(minion, _dr)


# =============================================================================
# 亡灵：无法被异象选中（已有恐惧关键词，此函数仅为占位/无额外效果）
# =============================================================================
@special
def _wangling_special(minion, player, game, extras=None):
    """亡灵：无法被异象选中（已有恐惧关键词）。"""
    # 恐惧关键词已在 keywords 中定义，board.get_front_minion 会自动过滤
    pass


# =============================================================================
# 硫氰化钾：部署：使1个异象获得恐惧。若其已具有恐惧，将其HP设为1点。
# =============================================================================
@special
def _liuqinghuajia_special(minion, player, game, extras=None):
    """硫氰化钾：部署：使1个异象获得恐惧。若其已具有恐惧，将其HP设为1点。"""
    from tards.core.targeting import TargetingRequest
    from tards.cards import Minion

    def scope(p, board):
        return [m for m in board.minion_place.values() if m.is_alive()]

    req = TargetingRequest()
    req.source = minion
    req.scope_fn = scope
    req.prompt = "硫氰化钾：选择1个异象"
    req.deciding_player = player

    target = game.targeting_system.request_target(req)
    if target is None:
        return False

    if not isinstance(target, Minion) or not target.is_alive():
        print("  硫氰化钾：目标无效")
        return False

    if target.keywords.get("恐惧", False):
        target.current_health = 1
        target.current_max_health = 1
        print(f"  硫氰化钾：{target.name} 已具有恐惧，HP 被设为 1")
    else:
        target.apply_fear()
        print(f"  硫氰化钾：{target.name} 获得恐惧")

    return True


# =============================================================================
# 竹心：部署：消灭一个处于协同的敌方异象。
# =============================================================================
@special
def _zhuxin_special(minion, player, game, extras=None):
    """竹心：部署：消灭一个处于协同的敌方异象。

    处于协同指该异象的同列存在其他友方异象（不依赖是否具有“协同”关键词）。
    """
    from tards.core.targeting import TargetingRequest
    from tards.cards import Minion

    def _is_in_synergy(m, board):
        """判断异象是否处于协同（同列有其他存活的友方异象）。"""
        col = m.position[1]
        return any(
            other is not m and other.is_alive()
            for other in board.get_minions_in_column(col, friendly_to=m.owner)
        )

    def scope(p, board):
        return [m for m in board.minion_place.values()
                if m.is_alive() and m.owner != player and _is_in_synergy(m, board)]

    candidates = scope(player, game.board)
    if not candidates:
        print("  竹心：没有处于协同的敌方异象")
        return True

    req = TargetingRequest()
    req.source = minion
    req.scope_fn = scope
    req.prompt = "竹心：选择1个处于协同的敌方异象"
    req.deciding_player = player

    target = game.targeting_system.request_target(req)
    if target is None:
        print("  竹心：取消选择目标")
        return False

    if not isinstance(target, Minion) or not target.is_alive():
        print("  竹心：目标无效")
        return False
    if target.owner == player or not _is_in_synergy(target, game.board):
        print("  竹心：目标不是处于协同的敌方异象")
        return False

    destroy_minion(target, game)
    print(f"  竹心部署：消灭处于协同的 {target.name}")
    return True


# =============================================================================
# 环丁二烯：亡语：使敌方部署的下一个异象获得恐惧。
# =============================================================================
@special
def _huanderxixi_special(minion, player, game, extras=None):
    """环丁二烯：亡语：使敌方部署的下一个异象获得恐惧。"""
    def _dr(m, p, b):
        from tards.constants import EVENT_DEPLOYED
        def _listener(event):
            deployed = event.data.get("minion")
            if deployed and deployed.owner != p and deployed.is_alive():
                deployed.apply_fear()
                print(f"  环丁二烯亡语触发：{deployed.name} 获得恐惧")

        game.history.listen_once(EVENT_DEPLOYED, _listener)
        print(f"  环丁二烯亡语：已注册敌方下一异象恐惧效果")

    add_deathrattle(minion, _dr)


# =============================================================================
# Bishop：结算阶段结束：场上每有1个具有恐惧的异象，你获得1点HP。
# =============================================================================
@special
def _bishop_special(minion, player, game, extras=None):
    """Bishop：结算阶段结束：场上每有1个具有恐惧的异象，你获得1点HP。"""
    def on_turn_end(g, event_data, source=minion):
        if not source.is_alive():
            return
        from card_pools.effect_utils import get_all_minions
        count = sum(1 for m in get_all_minions(g) if m.is_alive() and m.keywords.get("恐惧", False))
        if count > 0:
            heal_player(player, count)
            print(f"  Bishop 触发：场上 {count} 个恐惧异象，{player.name} 恢复 {count} HP")

    minion.on_turn_end = on_turn_end
# =============================================================================
# =============================================================================
# 自动迁移的效果函数
# =============================================================================
def _jiaopian_effect(player, target, game, extras=None):
    """胶片：抉择——对你造成1点伤害 或 移除卡组顶1张到弃牌堆。"""
    from card_pools.effect_utils import deal_damage_to_player

    choice = game.request_choice(player, ["造成1点伤害", "移除卡组顶1张"], title="胶片")
    if choice == "造成1点伤害":
        deal_damage_to_player(player, 1, game=game)
        print(f"  胶片：{player.name} 受到1点伤害")
    elif choice == "移除卡组顶1张":
        if player.card_deck:
            card = player.card_deck.pop()
            player.card_dis.append(card)
            print(f"  胶片：{player.name} 移除卡组顶 [{card.name}] 到弃牌堆")
        else:
            print(f"  胶片：{player.name} 牌库已空")
    else:
        print("  胶片：未选择")
        return False
    return True

def _peiti_effect(player, target, game, extras=None):
    """配体：场上每有1个恐惧异象，使1个纯净异象+1/+1。"""
    from tards.cards import Minion
    from tards.core.targeting import TargetingRequest

    # 统计场上恐惧异象数量
    fear_count = 0
    for m in list(game.board.minion_place.values()) + list(game.board.cell_underlay.values()):
        if m.is_alive() and m.keywords.get("恐惧", False):
            fear_count += 1

    if fear_count == 0:
        print("  配体：场上没有恐惧异象")
        return True

    def scope(p, board):
        return [m for m in board.minion_place.values() if m.is_alive()]

    req = TargetingRequest()
    req.source = player
    req.scope_fn = scope
    req.prompt = "配体：选择1个异象"
    req.deciding_player = player

    target = game.targeting_system.request_target(req)
    if target is None:
        return False
    if not isinstance(target, Minion) or not target.is_alive():
        print("  配体：目标无效")
        return False

    target.gain_attack(fear_count, permanent=True)
    target.gain_health_bonus(fear_count, permanent=True)
    print(f"  配体：{target.name} +{fear_count}/+{fear_count}（场上{fear_count}个恐惧异象）")
    return True

def _shuangsheng_bishou_effect(player, target, game, extras=None, card=None):
    """双生匕首：抽1张牌，获得1S，对1个异象和你造成1点伤害。"""
    from tards.cards import Minion
    from tards.core.targeting import TargetingRequest

    def scope(p, board):
        return [m for m in board.minion_place.values() if m.is_alive()]

    req = TargetingRequest()
    req.source = card or player
    req.scope_fn = scope
    req.prompt = "双生匕首：选择1个异象"
    req.deciding_player = player

    target = game.targeting_system.request_target(req)
    if target is None:
        return False

    player.draw_card(1, game=game)
    player.s_point += 1
    print(f"  双生匕首：{player.name} 获得1S")
    if isinstance(target, Minion) and target.is_alive():
        target.take_damage(1, source_type="strategy")
        print(f"  双生匕首：{target.name} 受到1点伤害")
    player.health_change(-1)
    print(f"  双生匕首：{player.name} 受到1点伤害")
    return True

def _zhanzheng_heping_effect(player, target, game, extras=None):
    """战争即和平：对方抽2张牌，若其手牌≥5，你获得+6HP。"""
    opponent = game.p2 if player == game.p1 else game.p1
    opponent.draw_card(2, game=game)
    print(f"  战争即和平：{opponent.name} 抽2张牌")

    if len(opponent.card_hand) >= 5:
        player.health_max_change(6)
        player.health_change(6)
        print(f"  战争即和平：{opponent.name} 手牌≥5，{player.name} 获得+6HP")
    else:
        print(f"  战争即和平：{opponent.name} 手牌{len(opponent.card_hand)}，不足5张")
    return True


def _sanbei_icecream_effect(player, target, game, extras=None):
    """三倍icecream：双方各抽1张牌。"""
    opponent = game.p2 if player == game.p1 else game.p1
    player.draw_card(1, game=game)
    opponent.draw_card(1, game=game)
    print(f"  三倍icecream：{player.name} 和 {opponent.name} 各抽1张牌")
    return True

def _ziyou_effect(player, target, game, extras=None, card=None):
    """自由即奴役：对异象造成1点伤害，若本回合离开战场，回响加入手牌。"""
    from card_pools.effect_utils import deal_damage_to_minion, create_echo_card
    from tards.cards import Minion
    from tards.core.targeting import TargetingRequest

    def scope(p, board):
        return [m for m in board.minion_place.values() if m.is_alive()]

    req = TargetingRequest()
    req.source = card or player
    req.scope_fn = scope
    req.prompt = "自由即奴役：选择1个异象"
    req.deciding_player = player

    target = game.targeting_system.request_target(req)
    if target is None:
        return False

    if not isinstance(target, Minion) or not target.is_alive():
        print("  自由即奴役：目标不合法")
        return False

    actual_damage = deal_damage_to_minion(target, 1, source=card, game=game)
    if actual_damage <= 0:
        print(f"  自由即奴役：{target.name} 未实际受到伤害")
        return True
    print(f"  自由即奴役：{target.name} 受到1点伤害")

    tracked = target
    sc = getattr(tracked, "source_card", None)
    if not sc:
        print(f"  自由即奴役：{tracked.name} 无源卡，无法生成回响")
        return True

    def _check():
        if not tracked.is_alive():
            echo = create_echo_card(sc, getattr(sc, "echo_level", 1))
            echo.owner = player
            player.add_card_to_hand(echo, game=game, emit_events=False)
            print(f"  自由即奴役：{tracked.name} 已离开战场，回响加入手牌")
        else:
            print(f"  自由即奴役：{tracked.name} 仍存活，无回响")

    game._delayed_effects.append({
        "trigger": "turn_end",
        "turn": game.current_turn,
        "owner": player,
        "fn": _check,
    })
    return True

def _wuzhi_effect(player, target, game, extras=None):
    """无知即力量：将上一个被消灭的异象的复制洗入卡组。"""
    import random
    from tards.cards import MinionCard
    from card_pools.effect_utils import last_died_minion

    last_minion = last_died_minion(game)
    if not last_minion:
        print("  无知即力量：本对局无异象被消灭")
        return True

    sc = getattr(last_minion, "source_card", None)
    if not sc:
        print("  无知即力量：无法找到源卡")
        return True

    copy_card = MinionCard(
        name=sc.name,
        owner=player,
        cost=sc.cost.copy(),
        targets=sc.targets,
        attack=sc.attack,
        health=sc.health,
        special=getattr(sc, "special", None),
        keywords=dict(sc.keywords) if sc.keywords else {},
    )
    copy_card.pack = getattr(sc, "pack", None)

    player.card_deck.append(copy_card)
    random.shuffle(player.card_deck)
    from card_pools.effect_utils import clear_shown_in_deck
    clear_shown_in_deck(player)
    print(f"  无知即力量：{copy_card.name} 的复制洗入卡组")
    return True

def _xianchu_xinzang_effect(player, target, game, extras=None):
    """献出心脏：对所有异象造成2点伤害，每消灭1个获得2S。"""
    from card_pools.effect_utils import deal_damage_to_minion

    all_minions = []
    seen = set()
    for m in list(game.board.minion_place.values()) + list(game.board.cell_underlay.values()):
        if m.is_alive() and id(m) not in seen:
            all_minions.append(m)
            seen.add(id(m))

    killed = 0
    for m in all_minions:
        before_alive = m.is_alive()
        deal_damage_to_minion(m, 2, game=game)
        if before_alive and not m.is_alive():
            killed += 1

    if killed > 0:
        player.s_point += killed * 2
        print(f"  献出心脏：消灭 {killed} 个异象，获得 {killed * 2}S")
    else:
        print(f"  献出心脏：未消灭异象")
    return True

def _jisuobuyu_effect(player, target, game, extras=None):
    """己所不欲：随机将对方1张手牌转换为己所不欲（+2T直到结算阶段结束）。"""
    import random
    opponent = game.p2 if player == game.p1 else game.p1

    if not opponent.card_hand:
        print("  己所不欲：对方手牌为空")
        return True

    original = random.choice(opponent.card_hand)
    opponent.card_hand.remove(original)

    # 创建新卡
    card_def = DEFAULT_REGISTRY.get("己所不欲 己所不欲 勿施于人")
    if not card_def:
        print("  己所不欲：找不到卡牌定义")
        opponent.card_hand.append(original)
        return False

    new_card = card_def.to_game_card(opponent)

    # 临时费用修正 +2T
    def _temp_cost_mod(card, cost):
        cost.t += 2

    new_card._card_cost_modifiers.append(_temp_cost_mod)

    opponent.card_hand.append(new_card)
    print(f"  己所不欲：{opponent.name} 的 [{original.name}] 被转换为 [{new_card.name}]（+2T）")

    # 结算阶段结束时移除修正
    def _cleanup():
        if _temp_cost_mod in getattr(new_card, "_card_cost_modifiers", []):
            new_card._card_cost_modifiers.remove(_temp_cost_mod)
            print(f"  己所不欲：{new_card.name} 的+2T修正已移除")

    game._delayed_effects.append({
        "trigger": "turn_end",
        "turn": game.current_turn,
        "fn": _cleanup,
    })
    return True

def _yongheng_effect(player, target, game, extras=None):
    """永恒奴役：将恐惧异象的复制加入手牌。"""
    from card_pools.effect_utils import copy_card_to_hand
    from tards.cards import Minion
    from tards.core.targeting import TargetingRequest

    def scope(p, board):
        return [m for m in board.minion_place.values() if m.is_alive()]

    req = TargetingRequest()
    req.source = player
    req.scope_fn = scope
    req.prompt = "永恒奴役：选择1个异象"
    req.deciding_player = player

    target = game.targeting_system.request_target(req)
    if target is None:
        return False
    if not isinstance(target, Minion) or not target.is_alive():
        print("  永恒奴役：目标无效")
        return False

    sc = getattr(target, "source_card", None)
    if not sc:
        print("  永恒奴役：找不到源卡")
        return False

    copy_card_to_hand(sc, player, game=game)
    print(f"  永恒奴役：{sc.name} 的复制加入手牌")
    return True

def _tansuanya_tie_effect(player, target, game, extras=None):
    """碳酸亚铁：获得等同于本出牌阶段失去HP的治疗。"""
    from card_pools.effect_utils import health_lost_this_phase

    total_lost = health_lost_this_phase(game, player)
    if total_lost > 0:
        player.health_change(total_lost)
        print(f"  碳酸亚铁：{player.name} 本出牌阶段失去 {total_lost} HP，恢复 {total_lost} HP")
    else:
        print(f"  碳酸亚铁：{player.name} 本出牌阶段未失去HP")
    return True

def _jiaojuan_effect(player, target, game, extras=None):
    """胶卷：将1张胶片加入对方手牌，自己抽1张。"""
    opponent = game.p2 if player == game.p1 else game.p1
    film_def = DEFAULT_REGISTRY.get("胶片")
    if film_def:
        film = film_def.to_game_card(opponent)
        opponent.add_card_to_hand(film, game=game, emit_events=False)
    else:
        print("  胶卷：找不到胶片定义")

    player.draw_card(1, game=game)
    print(f"  胶卷：{player.name} 抽1张牌")
    return True

def _fusi_effect(player, target, game, extras=None):
    """赴死之时：消灭所有攻击力最高的异象，自己拉闸。"""
    from card_pools.effect_utils import destroy_minion

    all_minions = []
    for m in list(game.board.minion_place.values()) + list(game.board.cell_underlay.values()):
        if m.is_alive() and m not in all_minions:
            all_minions.append(m)

    if not all_minions:
        print("  赴死之时：场上无异象")
        player.braked = True
        print(f"  赴死之时：{player.name} 拉闸")
        return True

    max_atk = max(m.current_attack for m in all_minions)
    victims = [m for m in all_minions if m.current_attack == max_atk]

    for m in victims:
        destroy_minion(m, game)
        print(f"  赴死之时：消灭攻击力最高的 {m.name}({max_atk})")

    player.braked = True
    print(f"  赴死之时：{player.name} 拉闸")
    return True

def _kongju_zhi_effect(player, target, game, extras=None):
    """恐惧植入：使1个异象获得恐惧，抽1张牌。"""
    from tards.cards import Minion
    from tards.core.targeting import TargetingRequest

    def scope(p, board):
        return [m for m in board.minion_place.values() if m.is_alive()]

    req = TargetingRequest()
    req.source = player
    req.scope_fn = scope
    req.prompt = "恐惧植入：选择1个异象"
    req.deciding_player = player

    target = game.targeting_system.request_target(req)
    if target is None:
        return False

    if not isinstance(target, Minion) or not target.is_alive():
        print("  恐惧植入：目标不合法")
        return False

    target.keywords["恐惧"] = True
    target.recalculate()
    print(f"  恐惧植入：{target.name} 获得恐惧")

    player.draw_card(1, game=game)
    print(f"  恐惧植入：{player.name} 抽1张牌")
    return True

def _zhongying_effect(player, target, game, extras=None):
    """重影：对方胶片数量翻倍，所有胶片+1T直到结算阶段结束。"""
    opponent = game.p2 if player == game.p1 else game.p1
    film_def = DEFAULT_REGISTRY.get("胶片")

    # 统计现有胶片
    existing_films = [c for c in opponent.card_hand if getattr(c, "name", None) == "胶片"]
    count = len(existing_films)

    if count > 0 and film_def:
        added = 0
        for _ in range(count):
            film = film_def.to_game_card(opponent)
            if not opponent.add_card_to_hand(film, game=game, emit_events=False):
                break
            added += 1
        print(f"  重影：{opponent.name} 的胶片数量翻倍（+{added}张）")
    else:
        print(f"  重影：{opponent.name} 手牌中无胶片")

    # 给所有胶片+1T
    def _temp_cost_mod(card, cost):
        cost.t += 1

    all_films = [c for c in opponent.card_hand if getattr(c, "name", None) == "胶片"]
    for film in all_films:
        film._card_cost_modifiers.append(_temp_cost_mod)
    print(f"  重影：{len(all_films)} 张胶片+1T")

    # 结算阶段结束时移除修正
    def _cleanup():
        for film in all_films:
            if _temp_cost_mod in getattr(film, "_card_cost_modifiers", []):
                film._card_cost_modifiers.remove(_temp_cost_mod)
        print("  重影：胶片+1T修正已移除")

    game._delayed_effects.append({
        "trigger": "turn_end",
        "turn": game.current_turn,
        "fn": _cleanup,
    })
    return True

def _kongju_zhengshe_effect(player, target, game, extras=None):
    """恐惧震慑：冰冻所有恐惧异象，对其造成1点伤害。"""
    from card_pools.effect_utils import deal_damage_to_minion

    victims = []
    for m in list(game.board.minion_place.values()) + list(game.board.cell_underlay.values()):
        if m.is_alive() and m.keywords.get("恐惧", False):
            victims.append(m)

    if not victims:
        print("  恐惧震慑：场上无恐惧异象")
        return True

    for m in victims:
        m.keywords["冰冻"] = True
        m.recalculate()
        deal_damage_to_minion(m, 1, game=game)
        print(f"  恐惧震慑：{m.name} 被冰冻并受到1点伤害")

    return True

def _chahuo_shuji_effect(player, target, game, extras=None):
    """查获书籍：随机将1张对方手牌洗入卡组，自己抽1张。"""
    import random
    opponent = game.p2 if player == game.p1 else game.p1

    if opponent.card_hand:
        card = random.choice(opponent.card_hand)
        opponent.card_hand.remove(card)
        opponent.card_deck.append(card)
        random.shuffle(opponent.card_deck)
        from card_pools.effect_utils import clear_shown_in_deck
        clear_shown_in_deck(opponent)
        print(f"  查获书籍：{opponent.name} 的 [{card.name}] 被洗入卡组")
    else:
        print(f"  查获书籍：{opponent.name} 手牌为空")

    player.draw_card(1, game=game)
    print(f"  查获书籍：{player.name} 抽1张牌")
    return True

def _wujiandi_yu_effect(player, target, game, extras=None):
    """无间地狱：对所有恐惧敌方异象造成等同于场上恐惧异象数的伤害。"""
    from card_pools.effect_utils import deal_damage_to_minion

    # 统计场上恐惧异象数
    fear_count = 0
    for m in list(game.board.minion_place.values()) + list(game.board.cell_underlay.values()):
        if m.is_alive() and m.keywords.get("恐惧", False):
            fear_count += 1

    if fear_count == 0:
        print("  无间地狱：场上无恐惧异象")
        return True

    opponent = game.p2 if player == game.p1 else game.p1
    for m in list(game.board.minion_place.values()) + list(game.board.cell_underlay.values()):
        if m.is_alive() and m.keywords.get("恐惧", False) and m.owner == opponent:
            deal_damage_to_minion(m, fear_count, game=game)
            print(f"  无间地狱：{m.name} 受到 {fear_count} 点伤害")

    return True

def _wangyi_effect(player, target, game, extras=None):
    """王翼弃兵：弃1张牌，消灭1个折算花费不大于此牌的异象。"""
    from card_pools.effect_utils import convert_cost_to_t, destroy_minion
    from tards.core.targeting import TargetingRequest

    # 阶段1：选择手牌中的1张卡弃掉
    def hand_scope(p, board):
        return [c for c in p.card_hand]

    req = TargetingRequest()
    req.source = player
    req.scope_fn = hand_scope
    req.prompt = "王翼弃兵：选择1张手牌弃掉"
    req.deciding_player = player

    target = game.targeting_system.request_target(req)
    if target is None:
        return False
    if target not in player.card_hand:
        print("  王翼弃兵：目标不在手牌中")
        return False

    player.card_hand.remove(target)
    player.card_dis.append(target)
    max_cost = convert_cost_to_t(target.cost)
    print(f"  王翼弃兵：弃掉 [{target.name}]，折算费用 {max_cost}T")

    # 筛选符合条件的异象
    candidates = []
    for m in list(game.board.minion_place.values()) + list(game.board.cell_underlay.values()):
        if m.is_alive():
            sc = getattr(m, "source_card", None)
            if sc and convert_cost_to_t(sc.cost) <= max_cost:
                candidates.append(m)

    if not candidates:
        print("  王翼弃兵：无符合条件的异象")
        return True

    options = [f"{i+1}. {m.name}({convert_cost_to_t(m.source_card.cost)}T)" for i, m in enumerate(candidates)]
    chosen = game.request_choice(player, options, title="王翼弃兵：选择要消灭的异象")
    if not chosen:
        print("  王翼弃兵：未选择目标")
        return True

    idx = int(chosen.split('.')[0]) - 1
    victim = candidates[idx]
    destroy_minion(victim, game)
    print(f"  王翼弃兵：消灭 {victim.name}")
    return True

def _shenyuan_effect(player, target, game, extras=None, card=None):
    """深渊：抽2张牌。被弃掉时：抽2张牌。

    利用新引擎的 Card.on() 注册卡实例级监听器，仅响应该实例自身的弃置事件。
    正常打出进入弃牌堆不会触发 EVENT_DISCARDED，因此不会误触发。
    """
    from tards.constants import EVENT_DISCARDED

    player.draw_card(2, game=game)
    print(f"  深渊：{player.name} 抽2张牌")

    if card is None:
        return True

    def on_discarded(event_data):
        discarded = event_data.get("card")
        if discarded is not card:
            return
        owner = getattr(discarded, "owner", None)
        if owner:
            owner.draw_card(2, game=game)
            print(f"  深渊：被弃掉时，{owner.name} 抽2张牌")
        # 触发后注销，避免重复响应
        card.off_all()

    card.on(EVENT_DISCARDED, on_discarded)
    return True

def _yusiwangpo_effect(player, target, game, extras=None, card=None):
    """鱼死网破：选择并弃1张自己的手牌，对方随机弃2张牌。

    规则确认：
    - 打出时卡已进入临时结算区，不在手牌中。
    - "如可能"原则：没有牌可弃就不弃。
    - 先弃自己的，再弃对方的。
    """
    import random

    # 先弃置自己的1张手牌
    if player.card_hand:
        options = [f"{i+1}. {c.name}" for i, c in enumerate(player.card_hand)]
        chosen = game.request_choice(player, options, "鱼死网破：选择弃1张手牌")
        if chosen:
            idx = int(chosen.split('.')[0]) - 1
            chosen_card = player.card_hand[idx]
            player.discard_card(chosen_card, game, reason="effect")

    # 再弃置对方随机2张手牌
    opponent = game.p2 if player == game.p1 else game.p1
    if opponent.card_hand:
        discard_count = min(2, len(opponent.card_hand))
        to_discard = random.sample(opponent.card_hand, discard_count)
        for c in to_discard:
            opponent.discard_card(c, game, reason="effect")

    return True

def _guobao_effect(player, target, game, extras=None, card=None):
    """过曝！：将2张胶片加入对方手牌，对所有异象造成等同于对方手中胶片数目的伤害。"""
    from tards.data.card_db import DEFAULT_REGISTRY
    from tards.constants import EVENT_DRAW, EVENT_DISCARDED, EVENT_MILLED

    opponent = game.p2 if player == game.p1 else game.p1

    # 将2张胶片加入对方手牌
    jiaopian_def = DEFAULT_REGISTRY.get("胶片")
    if jiaopian_def:
        for _ in range(2):
            jp = jiaopian_def.to_game_card(opponent)
            opponent.add_card_to_hand(jp, game=game, emit_events=False)

    # 对所有异象造成等同于对方手中胶片数目的伤害（包含刚加入的）
    jiaopian_count = sum(1 for c in opponent.card_hand if getattr(c, "name", None) == "胶片")
    if jiaopian_count > 0:
        all_minions = list(game.board.minion_place.values())
        for m in all_minions:
            if m.is_alive():
                m.take_damage(jiaopian_count, source_type="strategy")
        print(f"  过曝！：对方手中有 {jiaopian_count} 张胶片，对所有异象造成 {jiaopian_count} 点伤害")
    else:
        print(f"  过曝！：对方手中没有胶片，不造成伤害")

    return True

def _xuejian_bailian_effect(player, target, game, extras=None, card=None):
    """血溅白练：冰冻所有敌方异象。
    若本回合双方合计使用的策略卡数恰好为3，则额外对所有敌方异象造成3点伤害。
    利用 GameHistory 查询本回合策略使用总数与敌方异象存活状态。
    """
    from card_pools.effect_utils import (
        all_enemy_minions,
        total_strategies_played_this_turn,
        freeze_minion,
        deal_damage_to_minion,
    )

    # 通过日志模块获取所有存活敌方异象
    enemies = all_enemy_minions(game, player)
    if not enemies:
        print("  血溅白练：场上无敌方异象")
        return True

    # 冰冻所有敌方异象
    for m in enemies:
        freeze_minion(m, layers=1)

    # 通过日志模块查询本回合双方合计策略使用数
    # 注意：EVENT_CARD_PLAYED 在 effect 执行后才发射，因此查询结果不含自身，需 +1
    strategy_count = total_strategies_played_this_turn(game) + 1
    print(f"  血溅白练：本回合双方已使用 {strategy_count} 张策略卡（含自身）")

    if strategy_count == 3:
        for m in enemies:
            if m.is_alive():
                deal_damage_to_minion(m, 3, source=None, game=game)
        print("  血溅白练：第3张策略触发，对所有敌方异象造成3点伤害")

    return True

def _xiajian_effect(player, target, game, extras=None, card=None):
    """狭间：将1个异象返回其所有者手牌。冰冻相邻两列的敌方异象。

    手牌满则爆掉（直接销毁，不进弃牌堆）。返回手牌不触发亡语。
    """
    from tards.cards import MinionCard, Minion
    from tards.core.targeting import TargetingRequest

    def scope(p, board):
        return [m for m in board.minion_place.values() if m.is_alive()]

    req = TargetingRequest()
    req.source = card or player
    req.scope_fn = scope
    req.prompt = "狭间：选择1个异象"
    req.deciding_player = player

    target = game.targeting_system.request_target(req)
    if target is None:
        return False

    if not isinstance(target, Minion) or not target.is_alive():
        return False

    minion = target

    owner = minion.owner
    position = minion.position
    col = position[1] if isinstance(position, (list, tuple)) and len(position) >= 2 else 0

    # 1. 将异象从战场移除（remove_minion 不触发亡语）
    game.board.remove_minion(position)

    # 创建原卡复制
    sc = minion.source_card
    new_card = MinionCard(
        name=sc.name,
        owner=owner,
        cost=sc.cost,
        targets=sc.targets,
        attack=sc.attack,
        health=sc.health,
        special=getattr(sc, "special", None),
        keywords=dict(sc.keywords) if hasattr(sc, "keywords") else {},
    )

    # 手牌有空间则加入手牌，否则爆掉（直接销毁，不进弃牌堆）
    owner.add_card_to_hand(new_card, game=game, emit_events=False)

    # 2. 冰冻相邻两列的敌方异象（不包含目标所在列）
    adjacent_cols = []
    if col - 1 >= 0:
        adjacent_cols.append(col - 1)
    if col + 1 < 5:  # BOARD_SIZE
        adjacent_cols.append(col + 1)

    for m in game.board.minion_place.values():
        if m.is_alive() and m.owner != player:
            m_col = m.position[1] if isinstance(m.position, (list, tuple)) and len(m.position) >= 2 else 0
            if m_col in adjacent_cols:
                m.gain_keyword("冰冻", 1, permanent=True)
                print(f"  狭间：{m.name}（列 {m_col}）被冰冻")

    return True

def _shenpan_qianxi_effect(player, target, game, extras=None, card=None):
    """审判前夕：选择手牌中的1张异象，使其花费-2T。你失去1个T槽。

    费用减免为永久，可叠加。下限为0T。
    """
    from tards.cards import MinionCard

    # 筛选手牌中的异象卡
    minion_cards = [c for c in player.card_hand if isinstance(c, MinionCard)]
    if minion_cards:
        options = [f"{i+1}. {c.name}({c.cost})" for i, c in enumerate(minion_cards)]
        chosen = game.request_choice(player, options, "审判前夕：选择手牌中的1张异象")
        if chosen:
            idx = int(chosen.split('.')[0]) - 1
            chosen_card = minion_cards[idx]

            def discount_fn(card, cost):
                cost.t = max(0, cost.t - 2)

            chosen_card._card_cost_modifiers.append(discount_fn)
            print(f"  审判前夕：{chosen_card.name} 的费用-2T")
        else:
            print("  审判前夕：未选择目标")
    else:
        print("  审判前夕：手牌中没有异象卡")

    # 无论是否选到目标，都失去1个T槽
    player.t_point_max_change(-1)
    print(f"  审判前夕：{player.name} 失去1个T槽")
    return True

def _xuezhi_huaibiao_effect(player, target, game, extras=None, card=None):
    """血渍怀表：对你造成3点伤害，对方随机弃1张牌。将1张钝锈指针洗入卡组。"""
    import random

    # 对自己造成3点伤害（普通伤害，非流失生命）
    player.health_change(-3)
    print(f"  血渍怀表：{player.name} 受到3点伤害")

    # 对方随机弃1张手牌
    opponent = game.p2 if player == game.p1 else game.p1
    if opponent.card_hand:
        to_discard = random.choice(opponent.card_hand)
        opponent.discard_card(to_discard, game, reason="effect")

    # 将1张钝锈指针洗入卡组
    from tards.data.card_db import DEFAULT_REGISTRY
    pointer_def = DEFAULT_REGISTRY.get("钝锈指针")
    if pointer_def:
        new_card = pointer_def.to_game_card(player)
        player.card_deck.append(new_card)
        new_card.move_to("deck", game)
        random.shuffle(player.card_deck)
        from card_pools.effect_utils import clear_shown_in_deck
        clear_shown_in_deck(player)
        print(f"  血渍怀表：1张钝锈指针洗入卡组")
    else:
        print(f"  血渍怀表：钝锈指针定义未找到")

    return True

def _dunxiu_zhizhen_effect(player, target, game, extras=None, card=None):
    """钝锈指针：对你造成3点伤害，本轮跳过结算阶段。将1张含垢齿轮洗入卡组。"""
    import random

    # 对自己造成3点伤害
    player.health_change(-3)
    print(f"  钝锈指针：{player.name} 受到3点伤害")

    # 跳过本轮结算阶段
    game._skip_resolve_phase = True
    print(f"  钝锈指针：本轮结算阶段将被跳过")

    # 将1张含垢齿轮洗入卡组
    from tards.data.card_db import DEFAULT_REGISTRY
    gear_def = DEFAULT_REGISTRY.get("含垢齿轮")
    if gear_def:
        new_card = gear_def.to_game_card(player)
        player.card_deck.append(new_card)
        new_card.move_to("deck", game)
        random.shuffle(player.card_deck)
        from card_pools.effect_utils import clear_shown_in_deck
        clear_shown_in_deck(player)
        print(f"  钝锈指针：1张含垢齿轮洗入卡组")
    else:
        print(f"  钝锈指针：含垢齿轮定义未找到")

    return True

def _hangou_chilun_effect(player, target, game, extras=None, card=None):
    """含垢齿轮：对你造成3点伤害，获得'获得血契时，改为获得双倍'。"""
    player.health_change(-3)
    print(f"  含垢齿轮：{player.name} 受到3点伤害")

    player._double_blood_gain = True
    print(f"  含垢齿轮：{player.name} 获得双倍血契")
    return True

def _tianxia_wushuang_effect(player, target, game, extras=None, card=None):
    '''天下无双：随机对1个敌方异象失去1点HP。若场上有敌方异象的HP为偶数，重复此操作。'''
    import random

    opponent = game.p2 if player == game.p1 else game.p1

    while True:
        # 获取敌方存活异象（current_health > 0 防止已触发死亡但尚未移除的异象被重复选中）
        enemy_minions = [m for m in game.board.minion_place.values()
                         if m.is_alive() and m.current_health > 0 and m.owner == opponent]
        if not enemy_minions:
            break

        # 随机选1个失去1点HP
        victim = random.choice(enemy_minions)
        victim.current_health -= 1
        print(f'  天下无双：{victim.name} 失去1点HP')
        if victim.current_health <= 0:
            victim.minion_death()

        # 检查是否仍有敌方异象当前HP为偶数（同样过滤已死亡但尚未移除的异象）
        has_even_hp = any(
            m.is_alive() and m.current_health > 0 and m.current_health % 2 == 0
            for m in game.board.minion_place.values()
            if m.owner == opponent
        )
        if not has_even_hp:
            break

    return True

def _weiwei_yuzhui_effect(player, target, game, extras=None, card=None):
    """巍巍欲坠：对1个高地异象造成6点伤害。若被消灭，将其回响加入手牌。"""
    from card_pools.effect_utils import create_echo_card
    from tards.cards import Minion
    from tards.core.targeting import TargetingRequest

    def scope(p, board):
        return [m for m in board.minion_place.values() if m.is_alive() and m.position[1] == 0]

    req = TargetingRequest()
    req.source = player
    req.scope_fn = scope
    req.prompt = "巍巍欲坠：选择1个高地异象"
    req.deciding_player = player

    target = game.targeting_system.request_target(req)
    if target is None:
        return False
    if not isinstance(target, Minion) or not target.is_alive():
        print("  巍巍欲坠：目标无效")
        return False

    # 验证目标在高地列
    if target.position[1] != 0:
        print("  巍巍欲坠：目标不在高地列")
        return False

    # 造成6点伤害
    target.take_damage(6, source_type="strategy")
    print(f"  巍巍欲坠：{target.name} 受到6点伤害")

    # 若被消灭，将其回响加入手牌
    if not target.is_alive():
        source_card = getattr(target, "source_card", None)
        if source_card:
            echo = create_echo_card(source_card, echo_level=1)
            echo.owner = player
            player.add_card_to_hand(echo, game=game, emit_events=False)

    return True

def _zhanweifu1_effect(player, target, game, extras=None, card=None):
    """阳炎：消灭场上攻击力唯一最高的敌方异象。"""
    opponent = game.p2 if player == game.p1 else game.p1
    enemy_minions = [m for m in game.board.minion_place.values()
                     if m.is_alive() and m.owner == opponent]

    if not enemy_minions:
        print("  阳炎：场上没有敌方异象")
        return True

    # 找出最高攻击力
    max_attack = max(m.attack for m in enemy_minions)
    highest = [m for m in enemy_minions if m.attack == max_attack]

    if len(highest) != 1:
        print(f"  阳炎：最高攻击力({max_attack})的敌方异象有{len(highest)}个，不唯一，无法消灭")
        return True

    victim = highest[0]
    victim.current_health = 0
    victim.minion_death()
    print(f"  阳炎：消灭 {victim.name}")
    return True

def _zhanweifu2_effect(player, target, game, extras=None, card=None):
    """占位符2：使1个异象及其相邻异象获得恐惧。"""
    from tards.cards import Minion
    from tards.core.targeting import TargetingRequest

    def scope(p, board):
        return [m for m in board.minion_place.values() if m.is_alive()]

    req = TargetingRequest()
    req.source = card or player
    req.scope_fn = scope
    req.prompt = "占位符2：选择1个异象"
    req.deciding_player = player

    target = game.targeting_system.request_target(req)
    if target is None:
        return False

    if not isinstance(target, Minion) or not target.is_alive():
        return False

    # 目标自身获得恐惧
    target.apply_fear()

    # 上下左右相邻的异象也获得恐惧
    r, c = target.position[0], target.position[1]
    adjacent_positions = []
    if r - 1 >= 0:
        adjacent_positions.append((r - 1, c))
    if r + 1 < 5:
        adjacent_positions.append((r + 1, c))
    if c - 1 >= 0:
        adjacent_positions.append((r, c - 1))
    if c + 1 < 5:
        adjacent_positions.append((r, c + 1))

    for pos in adjacent_positions:
        m = game.board.get_minion_at(pos)
        if m and m.is_alive():
            m.apply_fear()
            print(f"  占位符2：{m.name}（相邻）获得恐惧")

    return True

def _zhanweifu3_effect(player, target, game, extras=None, card=None):
    """占位符3：抽2张牌。选择1张手牌，将其置入卡组顶。"""
    player.draw_card(2, game=game)

    if player.card_hand:
        options = [f"{i+1}. {c.name}" for i, c in enumerate(player.card_hand)]
        chosen = game.request_choice(player, options, "占位符3：选择1张手牌置入卡组顶")
        if chosen:
            idx = int(chosen.split('.')[0]) - 1
            chosen_card = player.card_hand[idx]
            player.card_hand.remove(chosen_card)
            player.card_deck.insert(0, chosen_card)
            chosen_card.move_to("deck", game)
            print(f"  占位符3：{chosen_card.name} 被置入卡组顶")

    return True

def _zhanweifu4_effect(player, target, game, extras=None, card=None):
    """占位符4：将所有手牌洗入卡组，抽取等量的牌。"""
    import random
    count = len(player.card_hand)
    # 将所有手牌洗入卡组
    while player.card_hand:
        c = player.card_hand.pop()
        player.card_deck.append(c)
        c.move_to("deck", game)
    random.shuffle(player.card_deck)
    from card_pools.effect_utils import clear_shown_in_deck
    clear_shown_in_deck(player)
    print(f"  占位符4：{count}张手牌洗入卡组")

    # 抽取等量的牌
    player.draw_card(count, game=game)
    return True

def _qinchen_effect(player, target, game, extras=None, card=None):
    """侵晨：对1个异象造成3点伤害。抽1张牌。"""
    from tards.cards import Minion
    from tards.core.targeting import TargetingRequest

    def scope(p, board):
        return [m for m in board.minion_place.values() if m.is_alive()]

    req = TargetingRequest()
    req.source = card or player
    req.scope_fn = scope
    req.prompt = "侵晨：选择1个异象"
    req.deciding_player = player

    target = game.targeting_system.request_target(req)
    if target is None:
        return False

    if isinstance(target, Minion) and target.is_alive():
        target.take_damage(3, source_type="strategy")
        print(f"  侵晨：{target.name} 受到3点伤害")
    player.draw_card(1, game=game)
    return True

def _yuzhong_effect(player, target, game, extras=None, card=None):
    """隅中：你获得+4HP。抽1张牌。"""
    player.health_max_change(4)
    player.health_change(4)
    print(f"  隅中：{player.name} 获得4点HP")
    player.draw_card(1, game=game)
    return True

def _tingwu_effect(player, target, game, extras=None, card=None):
    """亭午：抽2张牌。"""
    player.draw_card(2, game=game)
    return True

def _bomu_effect(player, target, game, extras=None, card=None):
    """薄暮：抽1张牌。下个抽牌阶段，对方无法抽牌。"""
    opponent = game.p2 if player == game.p1 else game.p1
    player.draw_card(1, game=game)
    opponent._skip_next_draw = True
    print(f"  薄暮：{opponent.name} 下个抽牌阶段无法抽牌")
    return True

def _rending_effect(player, target, game, extras=None, card=None):
    """人定：冰冻1个异象及其相邻的1个异象。抽1张牌。"""
    import random

    # 找到所有存活异象中至少有一个相邻异象的
    all_minions = [m for m in game.board.minion_place.values() if m.is_alive()]
    candidates = []
    for m in all_minions:
        r, c = m.position[0], m.position[1]
        adjacent_positions = []
        if r - 1 >= 0:
            adjacent_positions.append((r - 1, c))
        if r + 1 < 5:
            adjacent_positions.append((r + 1, c))
        if c - 1 >= 0:
            adjacent_positions.append((r, c - 1))
        if c + 1 < 5:
            adjacent_positions.append((r, c + 1))
        for pos in adjacent_positions:
            adj = game.board.get_minion_at(pos)
            if adj and adj.is_alive():
                candidates.append((m, adj))
                break

    if candidates:
        primary, adjacent = random.choice(candidates)
        primary.apply_fear()
        print(f"  人定：{primary.name} 被冰冻")
        adjacent.apply_fear()
        print(f"  人定：{adjacent.name}（相邻）被冰冻")
    else:
        print("  人定：场上没有相邻的异象对")

    player.draw_card(1, game=game)
    return True

def _meidan_effect(player, target, game, extras=None, card=None):
    """昧旦：将场上攻击力最高的1个异象返回其所有者手牌。抽1张牌。"""
    import random
    from card_pools.effect_utils import return_minion_to_hand

    all_minions = [m for m in game.board.minion_place.values() if m.is_alive()]
    if all_minions:
        max_attack = max(m.attack for m in all_minions)
        highest = [m for m in all_minions if m.attack == max_attack]
        chosen = random.choice(highest)
        return_minion_to_hand(chosen, game)
    else:
        print("  昧旦：场上没有异象")

    player.draw_card(1, game=game)
    return True
# =============================================================================
# 指尖方寸：部署：将1个异象返回其所有者手牌，其所有者抽1张牌。
# =============================================================================
@special
def _zhijianfangcun_special(minion, player, game, extras=None):
    """指尖方寸：部署：将1个异象返回其所有者手牌，其所有者抽1张牌。"""
    from tards.core.targeting import TargetingRequest
    from card_pools.effect_utils import return_minion_to_hand
    from tards.cards import Minion

    def scope(p, board):
        return [m for m in board.minion_place.values() if m.is_alive()]

    req = TargetingRequest()
    req.source = minion
    req.scope_fn = scope
    req.prompt = "指尖方寸：选择1个异象返回其所有者手牌"
    req.deciding_player = player

    target = game.targeting_system.request_target(req)
    if target is None:
        return False

    if not isinstance(target, Minion) or not target.is_alive():
        print("  指尖方寸：目标无效")
        return False

    return_minion_to_hand(target, game)

    owner = target.owner
    if owner:
        owner.draw_card(1, game=game)
        print(f"  指尖方寸：{owner.name} 抽1张牌")

    return True


def _jiaopian_choice(player, board):
    """胶片：抉择。"""
    return ["造成1点伤害", "移除卡组顶1张"]

_peiti_targets = target("minion", friendly=True, enemy=False, tag="纯净")
_yongheng_targets = target("minion", keyword="恐惧")
_wangyi_targets = target("hand")

def _guobao_cost_modifier(card, cost):
    """过曝！：对方手中每有1张牌，费用-1S。"""
    owner = getattr(card, "owner", None)
    if not owner:
        return
    game = getattr(getattr(owner, "board_ref", None), "game_ref", None)
    if not game:
        return
    opponent = game.p2 if owner == game.p1 else game.p1
    discount = len(opponent.card_hand)
    cost.s = max(0, cost.s - discount)

def _xuezhi_huaibiao_game_start(player, game, card):
    """对局开始时：将血渍怀表置入卡组顶。"""
    if card in player.card_deck:
        player.card_deck.remove(card)
        player.card_deck.insert(0, card)
        print(f"  血渍怀表：{player.name} 将其置入卡组顶")

def target_highland_minion(player, board):
    """返回所有位于高地列（col=0）的异象。"""
    return [m for m in board.minion_place.values()
            if m.is_alive() and isinstance(m.position, (list, tuple)) and len(m.position) >= 2 and m.position[1] == 0]

def _zhanweifu1_draw_trigger(player, game, card):
    """抽取：若可能，消耗1S，对对手造成2点伤害。"""
    if player.s_point >= 1:
        player.s_point -= 1
        opponent = game.p2 if player == game.p1 else game.p2
        opponent.health_change(-2)
        print(f"  {card.name} 抽取：{player.name} 消耗1S，{opponent.name} 受到2点伤害")
    else:
        print(f"  {card.name} 抽取：{player.name} S不足，无法造成伤害")

def _zhanweifu2_draw_trigger(player, game, card):
    """抽取：对所有具有恐惧的异象造成2点伤害。"""
    for m in game.board.minion_place.values():
        if m.is_alive() and m.keywords.get("恐惧", False):
            m.take_damage(2, source_type="strategy")
            print(f"  {card.name} 抽取：{m.name} 受到2点伤害")

def _zhanweifu4_draw_trigger(player, game, card):
    """抽取：抽1张具有抽取效果的牌。

    正确实现：将候选卡放到卡组顶，然后通过 draw_card 真正抽进手牌，
    由 draw_card 内部统一触发抽取效果。
    """
    import random
    candidates = [c for c in player.card_deck if getattr(c, "hidden_keywords", {}).get("抽取")]
    if candidates:
        chosen = random.choice(candidates)
        # 将选中的卡放到卡组顶，然后通过 draw_card 真正抽进手牌
        player.card_deck.remove(chosen)
        player.card_deck.insert(0, chosen)
        chosen.move_to("deck", game)
        print(f"  {card.name} 抽取：将 {chosen.name} 置入卡组顶")
        player.draw_card(1, game=game)
    else:
        print(f"  {card.name} 抽取：卡组中没有具有抽取效果的牌")

def _yilong_cost_modifier(card, cost):
    """翼龙费用修饰器：根据卡牌实例累计的伤害次数减少费用。"""
    if card.name == "翼龙":
        reduction = getattr(card, "_yilong_damage_count", 0)
        if reduction > 0:
            cost.t = max(0, cost.t - reduction)


def _yilong_game_start(player, game, card):
    """翼龙对局开始时效果：注册全局监听器，玩家受伤时给手牌中所有翼龙+1计数；翼龙离开手牌时清零计数。"""
    from tards.constants import EVENT_PLAYER_DAMAGE

    attr_name = f"_yilong_listener_registered_{id(player)}"
    if getattr(game, attr_name, False):
        return
    setattr(game, attr_name, True)

    def on_player_damage(event, g):
        evt_player = event.data.get("player")
        if evt_player is not player:
            return
        for c in player.card_hand:
            if c.name == "翼龙":
                c._yilong_damage_count = getattr(c, "_yilong_damage_count", 0) + 1
                print(f"  翼龙：{player.name} 受到伤害，手牌中翼龙费用累计减少 {c._yilong_damage_count}T")

    def on_card_moved(event, g):
        moved_card = event.data.get("card")
        if not moved_card or moved_card.name != "翼龙":
            return
        from_loc = event.data.get("from_loc")
        if from_loc == "hand":
            moved_card._yilong_damage_count = 0
            print(f"  翼龙：离开手牌，费用减免重置")

    game.history.listen(EVENT_PLAYER_DAMAGE, on_player_damage, owner=None)
    game.history.listen("card_moved", on_card_moved, owner=None)


@special
def _tiexin_special(minion, player, game, extras=None):
    """铁心：部署：将1张"环丁二烯"和1张"配体"加入手牌。"""
    from card_pools.effect_utils import give_card_by_name
    give_card_by_name(player, "环丁二烯", reason="铁心部署")
    give_card_by_name(player, "配体", reason="铁心部署")
    return True


@special
def _leijinade_special(minion, player, game, extras=None):
    """雷金纳德：HP不小于4时，具有"你受到伤害时，改为由本异象承受。" 部署：每有1个敌方异象，获得1次+1HP。"""
    from tards.constants import EVENT_BEFORE_DAMAGE
    from tards.core.player import Player

    # 部署效果：每有1个敌方异象，+1HP
    enemy_count = sum(
        1 for m in game.board.minion_place.values()
        if m.is_alive() and m.owner != player
    )
    if enemy_count > 0:
        minion.gain_health_bonus(enemy_count, permanent=True)
        minion.current_health += enemy_count
        print(f"  雷金纳德：敌方有 {enemy_count} 个异象，获得 +{enemy_count}HP（当前 {minion.current_health}/{minion.current_max_health}）")

    # 动态效果：HP >= 4时，玩家受伤改为由本异象承受
    def on_before_damage(event, g):
        if not minion.is_alive():
            return
        if getattr(minion, "_leijinade_redirecting", False):
            return
        if minion.current_health < 4:
            return

        target = event.data.get("target")
        damage = event.data.get("damage", 0)
        if damage <= 0:
            return
        if not isinstance(target, Player):
            return
        if target is not player:
            return

        event.cancelled = True
        event.data["damage"] = 0
        print(f"  雷金纳德：{player.name} 本应受到 {damage} 点伤害，由雷金纳德承担")
        minion._leijinade_redirecting = True
        try:
            source = event.data.get("source_minion")
            minion.take_damage(damage, source_minion=source)
        finally:
            minion._leijinade_redirecting = False

    game.history.listen(EVENT_BEFORE_DAMAGE, on_before_damage, owner=minion)
    return True


@special
def _wuqiongxiaoliang_special(minion, player, game, extras=None):
    """无穷小量：部署：消灭1个受伤异象。"""
    from tards.core.targeting import TargetingRequest
    from card_pools.effect_utils import destroy_minion

    # 获取全场所有存活的受伤异象
    wounded = [
        m for m in game.board.minion_place.values()
        if m.is_alive() and m.current_health < m.current_max_health
    ]

    if not wounded:
        print("  无穷小量：场上没有受伤异象")
        return True

    def scope(p, board):
        return wounded

    req = TargetingRequest()
    req.source = minion
    req.scope_fn = scope
    req.prompt = "无穷小量：选择一个受伤异象消灭"
    req.deciding_player = player

    target = game.targeting_system.request_target(req)
    if target is None:
        print("  无穷小量：未选择目标")
        return True

    destroy_minion(target, game)
    print(f"  无穷小量：消灭受伤异象 {target.name}")
    return True


@special
def _yunjun_special(minion, player, game, extras=None):
    """云君：攻击时，改为对攻击力最高的敌方异象造成等量伤害。部署：攻击1次。"""
    from card_pools.effect_utils import on_before_attack, perform_attack_action

    def _retarget(event):
        if event.get("attacker") != minion:
            return
        enemies = [
            m for m in game.board.minion_place.values()
            if m.is_alive() and m.owner != player
        ]
        if not enemies:
            return
        highest = max(enemies, key=lambda m: m.attack)
        event.data["target"] = highest
        event.data["defender"] = highest
        print(f"  云君：攻击目标改为攻击力最高的 {highest.name}（攻{highest.attack}）")

    on_before_attack(minion, game, _retarget)

    # 部署时攻击1次
    perform_attack_action(minion, game)
    return True


@special
def _silingfashi_special(minion, player, game, extras=None):
    """死灵法师：敌方异象被消灭时，将1个"亡灵"加入其原位。"""
    from tards.constants import EVENT_AFTER_DESTROY
    from card_pools.effect_utils import summon_minion_by_name

    def on_after_destroy(event, g):
        if not minion.is_alive():
            return
        destroyed = event.data.get("minion")
        if not destroyed or destroyed is minion:
            return
        # 只响应敌方异象被消灭
        if destroyed.owner == player:
            return

        pos = destroyed.position
        if pos is None:
            return

        if pos in g.board.minion_place:
            print(f"  死灵法师：{destroyed.name} 的原位 {pos} 已被占用，无法召唤亡灵")
            return

        result = summon_minion_by_name(g, "亡灵", destroyed.owner, pos)
        if result:
            print(f"  死灵法师：{destroyed.name} 被消灭，在其原位 {pos} 召唤亡灵（属于 {destroyed.owner.name}）")

    game.history.listen(EVENT_AFTER_DESTROY, on_after_destroy, owner=minion)
    return True


@special
def _xianyingshi_special(minion, player, game, extras=None):
    """显影室：结算阶段开始：将1个"溴化银"加入本异象前方。"""
    from tards.constants import EVENT_PHASE_START
    from card_pools.effect_utils import summon_minion_by_name

    def on_phase_start(event, g):
        print(player,f"[DEBUG 显影室] on_phase_start 触发, phase={event.data.get('phase')}, expected={g.PHASE_RESOLVE}")
        if event.data.get("phase") != g.PHASE_RESOLVE:
            print(player,f"[DEBUG 显影室] 阶段不匹配，跳过")
            return

        print(player,f"[DEBUG 显影室] minion.is_alive()={minion.is_alive()}")
        if not minion.is_alive():
            print(player,f"[DEBUG 显影室] 显影室已死亡，跳过")
            return

        pos = minion.position
        print(player,f"[DEBUG 显影室] minion.position={pos}")

        friendly_rows = player.get_friendly_rows()
        current_row = pos[0]
        col = pos[1]
        
        # 后排 -> 前排
        if current_row == friendly_rows[1]:
            front_pos = (friendly_rows[0], col)
            print(player,f"[DEBUG 显影室] 在后排，前方位置={front_pos}")
        else:
            print(player,f"[DEBUG 显影室] 已在前排，无法在前方召唤")
            return

        if front_pos in g.board.minion_place:
            print(player,f"[DEBUG 显影室] 前方 {front_pos} 已被占用，无法召唤溴化银")
            return

        print(player,f"[DEBUG 显影室] 尝试召唤溴化银到 {front_pos}")
        result = summon_minion_by_name(g, "溴化银", player, front_pos)
        if result:
            print(player,f"[DEBUG 显影室] 在前方 {front_pos} 召唤溴化银成功")
        else:
            print(player,f"[DEBUG 显影室] 召唤溴化银失败")

    game.history.listen(EVENT_PHASE_START, on_phase_start, owner=minion)
    print(player,f"[DEBUG 显影室] 监听器已注册，owner={minion.name} at {minion.position}")
    return True


@special
def _dujiaodadao_special(minion, player, game, extras=None):
    """独脚大盗：部署：抽取对方卡组顶的1张牌。"""
    opponent = game.p2 if player == game.p1 else game.p1
    drawn = player.draw_card(1, game=game, deck_owner=opponent)
    if drawn:
        drawn[0].owner = player
    else:
        if not opponent.card_deck:
            print(f"  独脚大盗：{opponent.name} 的牌库已空")
    return True


@special
def _liting_special(minion, player, game, extras=None):
    """礼堂：双方打出手牌时，对所有目标造成1点伤害。"""
    from tards.constants import EVENT_CARD_PLAYED

    def on_card_played(event, g):
        if not minion.is_alive():
            return
        # 对所有存活异象造成1点伤害
        for m in g.board.minion_place.values():
            if m.is_alive():
                m.take_damage(1, source_minion=minion, source_type="effect")
        # 对双方玩家各造成1点伤害
        for p in g.players:
            p.health_change(-1, source=minion)
        print(f"  礼堂：双方打出手牌，全场受到1点伤害")

    game.history.listen(EVENT_CARD_PLAYED, on_card_played, owner=minion)
    return True


@special
def _liuming_special(minion, player, game, extras=None):
    """流明：部署：至多消耗6S，每消耗2S，随机将1张精灵异象加入战场。"""
    import random
    from tards.data.card_db import DEFAULT_REGISTRY, CardType

    available_s = player.s_point
    max_consume = min(available_s, 6)
    consumed = (max_consume // 2) * 2

    if consumed <= 0:
        print("  流明：没有足够的S点数召唤精灵")
        return True

    player.s_point_change(-consumed)
    print(f"  流明：消耗 {consumed}S")

    spirits = [
        c for c in DEFAULT_REGISTRY.all_cards()
        if hasattr(c, "tags") and "精灵" in c.tags
        and hasattr(c, "card_type") and c.card_type == CardType.MINION
    ]

    if not spirits:
        print("  流明：没有可用的精灵异象")
        return True

    summon_count = consumed // 2
    empties = empty_positions(player, game.board)

    for i in range(summon_count):
        if not empties:
            print(f"  流明：战场已满，无法继续召唤")
            break
        spirit_def = random.choice(spirits)
        spirit_card = spirit_def.to_game_card(player)
        valid_positions = [pos for pos in empties if game.board.is_valid_deploy(pos, player, spirit_card)]
        if not valid_positions:
            print(f"  流明：没有合法位置召唤 {spirit_def.name}")
            continue
        pos = random.choice(valid_positions)
        empties.remove(pos)
        result = summon_minion_by_name(game, spirit_def.name, player, pos)
        if result:
            print(f"  流明：召唤 {spirit_def.name} 至 {pos}")

    return True


# ── 炸弹人：被弃掉时对方随机弃1张牌 ──

def _register_zhadanren_listener(card, player, game):
    """为单张炸弹人卡牌注册弃置监听器，防止重复注册。
    只响应 reason != 'mill' 的弃置（磨牌不是弃牌）。"""
    if getattr(card, "_zhadanren_registered", False):
        return
    card._zhadanren_registered = True

    from tards.constants import EVENT_DISCARDED

    def on_discarded(event_data):
        discarded = event_data.get("card")
        if discarded is not card:
            return
        # 磨牌不是弃牌
        if event_data.get("reason") == "mill":
            return
        opponent = game.p2 if player == game.p1 else game.p1
        if opponent.card_hand:
            import random
            to_discard = random.choice(opponent.card_hand)
            opponent.discard_card(to_discard, game, reason="effect")
            print(f"  炸弹人：{player.name} 的炸弹人被弃掉，{opponent.name} 随机弃掉 {to_discard.name}")
        card.off_all()

    card.on(EVENT_DISCARDED, on_discarded)


def _zhadanren_draw_trigger(player, game, card):
    """炸弹人 hidden_keywords['抽取']：被抽到手上时注册弃置监听器。"""
    _register_zhadanren_listener(card, player, game)


@special
def _budongdian_special(minion, player, game, extras=None):
    """不动点：部署：所有友方异象攻击1次本异象。亡语：所有对其造成过伤害的异象获得+1/1。"""
    from tards.constants import EVENT_AFTER_DAMAGE
    from card_pools.effect_utils import add_deathrattle

    # 1. 追踪所有对不动点造成过伤害的异象
    minion._budongdian_attackers = set()

    def on_after_damage(event, g):
        target = event.data.get("target")
        if target is not minion:
            return
        source = event.data.get("source_minion")
        if source and hasattr(source, "is_alive"):
            minion._budongdian_attackers.add(source)

    game.history.listen(EVENT_AFTER_DAMAGE, on_after_damage, owner=minion)

    # 2. 部署效果：所有友方异象依次攻击不动点
    allies = [
        m for m in game.board.minion_place.values()
        if m.is_alive() and m.owner == player and m != minion
    ]

    for ally in allies:
        if not minion.is_alive():
            print(f"  不动点：已被击杀，停止攻击")
            break
        if not ally.is_alive():
            continue
        print(f"  不动点：{ally.name} 攻击不动点")
        ally.attack_target(minion)

    # 3. 注册亡语
    def deathrattle(m, p, board):
        for attacker in list(minion._budongdian_attackers):
            if attacker.is_alive():
                attacker.gain_attack(1, permanent=True)
                attacker.gain_health_bonus(1, permanent=True)
                attacker.current_health += 1
                print(f"  不动点亡语：{attacker.name} 获得+1/1（当前 {attacker.current_health}/{attacker.current_max_health}）")

    add_deathrattle(minion, deathrattle)

    return True


def _shuixieshi_cost_modifier(card, cost):
    """水漫缮写室卡牌级费用修正器：根据 _shuixieshi_discount 减少T费用。"""
    reduction = getattr(card, "_shuixieshi_discount", 0)
    if reduction > 0:
        cost.t = max(0, cost.t - reduction)
        print(f"  水漫缮写室：费用减免 {reduction}T，实际费用 {cost.t}T")


def _shuixieshi_register_listeners(card, player, game):
    """为水漫缮写室注册监听器：手牌移出时减费，离开手牌时重置。"""
    if getattr(card, "_shuixieshi_listeners_registered", False):
        return
    card._shuixieshi_listeners_registered = True
    card._shuixieshi_discount = 0

    def apply_discount():
        if card._location != "hand":
            return
        card._shuixieshi_discount += 2
        print(f"  水漫缮写室：手牌被移出，费用减少2T（累计减免 {card._shuixieshi_discount}T）")

    def on_discarded(event, g):
        discarded = event.data.get("card")
        if discarded and discarded.owner == player and discarded._location == "hand":
            apply_discount()

    def on_card_moved(event, g):
        moved = event.data.get("card")
        from_loc = event.data.get("from_loc")
        to_loc = event.data.get("to_loc")
        if moved and moved.owner == player and from_loc == "hand" and to_loc == "deck":
            apply_discount()
        if moved is card and from_loc == "hand":
            card._shuixieshi_discount = 0
            print(f"  水漫缮写室：离开手牌，费用减免重置")

    from tards.constants import EVENT_DISCARDED
    game.history.listen(EVENT_DISCARDED, on_discarded, owner=card)
    game.history.listen("card_moved", on_card_moved, owner=card)


def _shuixieshi_game_start(player, game, card):
    """水漫缮写室 on_game_start：为牌库中的实例注册监听器。"""
    _shuixieshi_register_listeners(card, player, game)


def _shuixieshi_draw_effect(player, game, card):
    """水漫缮写室抽取效果：选择1张手牌洗入卡组，获得等同于此牌折算花费的HP。

    对局开始阶段（current_turn == 0）不触发，避免阻塞开局抽牌流程。
    """
    from card_pools.effect_utils import convert_cost_to_t

    # 开局初始化阶段跳过，防止阻塞游戏线程
    if getattr(game, "current_turn", 0) == 0:
        return

    if not player.card_hand:
        print("  水漫缮写室：手牌为空，无法执行抽取效果")
        return

    options = [f"{i+1}. {c.name}" for i, c in enumerate(player.card_hand)]
    chosen_str = game.request_choice(player, options, title="水漫缮写室：选择1张手牌洗入卡组")
    if chosen_str is None:
        print("  水漫缮写室：未选择手牌")
        return

    idx = int(chosen_str.split('.')[0]) - 1
    chosen = player.card_hand[idx]

    # 从手牌移除并洗入卡组
    player.card_hand.remove(chosen)
    chosen.move_to("deck", game)
    player.card_deck.append(chosen)
    import random
    random.shuffle(player.card_deck)
    from card_pools.effect_utils import clear_shown_in_deck
    clear_shown_in_deck(player)
    print(f"  水漫缮写室：{chosen.name} 被洗入卡组")

    # 获得等同于此牌折算花费的HP
    cost_t = convert_cost_to_t(chosen.cost)
    player.health_max_change(cost_t)
    player.health_change(cost_t)
    print(f"  水漫缮写室：获得 {cost_t} 点HP")


def _shuixieshi_draw_trigger(player, game, card):
    """水漫缮写室 hidden_keywords['抽取']：抽到手上时注册监听器 + 执行抽取效果。"""
    _shuixieshi_register_listeners(card, player, game)
    _shuixieshi_draw_effect(player, game, card)


def _guankui_effect(player, target, game, extras=None, card=None):
    """管窥：开发1张纯净异象。若场上有友方纯净异象，再开发1张时刻。"""
    from tards.data.card_db import DEFAULT_REGISTRY, CardType

    # 1. 构建纯净异象池
    pure_minions = [
        c for c in DEFAULT_REGISTRY.all_cards()
        if hasattr(c, "tags") and "纯净" in c.tags
        and hasattr(c, "card_type") and c.card_type == CardType.MINION
    ]

    if pure_minions:
        game.develop(player, pure_minions, count=min(3, len(pure_minions)))
    else:
        print("  管窥：没有可用的纯净异象")

    # 2. 检查场上是否有友方纯净异象
    has_pure = any(
        m.is_alive() and m.owner == player and "纯净" in getattr(m, "tags", [])
        for m in game.board.minion_place.values()
    )

    if has_pure:
        # 开发时刻：优先从隐藏标签筛选，fallback 到卡牌名
        moment_defs = [
            c for c in DEFAULT_REGISTRY.all_cards()
            if hasattr(c, "hidden_keywords") and "时刻" in c.hidden_keywords
        ]
        if not moment_defs:
            moment_def = DEFAULT_REGISTRY.get("时刻")
            if moment_def:
                moment_defs = [moment_def]

        if moment_defs:
            game.develop(player, moment_defs, count=min(3, len(moment_defs)))
        else:
            print("  管窥：场上存在友方纯净异象，但时刻池为空（用户尚未注册时刻卡牌）")

    return True


@special
def _yixi_special(minion, player, game, extras=None):
    """乙烯：部署：还原一个异象的HP（恢复到初始面板生命值）。"""
    from tards.core.targeting import TargetingRequest

    def scope(p, board):
        return [m for m in board.minion_place.values() if m.is_alive()]

    req = TargetingRequest()
    req.source = minion
    req.scope_fn = scope
    req.prompt = "乙烯：选择一个异象还原其HP"
    req.deciding_player = player

    target = game.targeting_system.request_target(req)
    if target is None:
        print("  乙烯：未选择目标")
        return False

    if not hasattr(target, "is_alive") or not target.is_alive():
        print("  乙烯：目标无效")
        return False

    # 还原到初始面板生命值（不低于当前HP）
    if target.current_health < target.base_max_health:
        target.current_health = target.base_max_health
        print(f"  乙烯：{target.name} 的HP还原到 {target.base_max_health}")
    else:
        print(f"  乙烯：{target.name} 的HP已为 {target.current_health}，无需还原")

    return True


@special
def _erliuhuatan_special(minion, player, game, extras=None):
    """二硫化碳：部署：对1个异象造成1点伤害，将其冰冻。"""
    from tards.core.targeting import TargetingRequest
    from card_pools.effect_utils import gain_keyword
    from tards.cards import Minion

    def scope(p, board):
        return [m for m in board.minion_place.values() if m.is_alive()]

    req = TargetingRequest()
    req.source = minion
    req.scope_fn = scope
    req.prompt = "二硫化碳：选择1个异象"
    req.deciding_player = player

    target = game.targeting_system.request_target(req)
    if target is None:
        return False

    if not isinstance(target, Minion) or not target.is_alive():
        print("  二硫化碳：目标无效")
        return False

    # 造成1点伤害
    target.take_damage(1, source_minion=minion, source_type="effect")
    print(f"  二硫化碳：对 {target.name} 造成1点伤害")

    # 若目标存活，将其冰冻
    if target.is_alive():
        gain_keyword(target, "冰冻", 1)
        print(f"  二硫化碳：{target.name} 被冰冻")

    return True


@special
def _sanfuhualu_special(minion, player, game, extras=None):
    """三氟化氯：场上有异象具有恐惧时，无法被异象指向。结算阶段开始：随机使1个敌方异象具有恐惧。"""
    from tards.constants import EVENT_PHASE_START

    # 1. 动态"虚化"：通过 _aura_keyword_fns 实现
    def xuhua_aura(m):
        # 检查场上是否有任何存活异象具有恐惧（含友方和敌方）
        for other in game.board.minion_place.values():
            if other is not m and other.is_alive() and other.keywords.get("恐惧", False):
                return {"虚化": True}
        return {}

    minion._aura_keyword_fns.append(xuhua_aura)

    # 2. 通过 gamehistory 实时追踪场上恐惧异象数量变化
    # 初始化计数器
    game._fear_count = sum(
        1 for m in game.board.minion_place.values()
        if m.is_alive() and m.keywords.get("恐惧", False)
    )

    def track_fear_change(event, g):
        new_count = sum(
            1 for m in g.board.minion_place.values()
            if m.is_alive() and m.keywords.get("恐惧", False)
        )
        old_count = getattr(g, "_fear_count", 0)
        if new_count == old_count:
            return
        g._fear_count = new_count
        for m in g.board.minion_place.values():
            if m.name == "三氟化氯" and m.is_alive():
                m.recalculate()
                if new_count == 0:
                    print(f"  {m.name}：场上无恐惧异象，取消虚化")
                else:
                    print(f"  {m.name}：场上恐惧异象数量变化为 {new_count}，更新虚化状态")

    # 监听任意事件，确保任何状态变化后都检查恐惧计数
    game.history.listen("*", track_fear_change, owner=minion)

    # 3. 结算阶段开始：随机使1个敌方异象具有恐惧
    def on_phase_start(event, g):
        if event.data.get("phase") != g.PHASE_RESOLVE:
            return
        if event.data.get("first") is not player:
            return
        if not minion.is_alive():
            return

        minion.recalculate()

        # 随机选择1个敌方存活异象赋予恐惧
        import random
        opponent = game.p1 if player == game.p2 else game.p2
        enemies = [m for m in game.board.minion_place.values()
                   if m.is_alive() and m.owner == opponent]
        if not enemies:
            print("  三氟化氯：敌方没有异象，无法赋予恐惧")
            return

        target = random.choice(enemies)
        target.apply_fear()
        print(f"  三氟化氯：{target.name} 获得恐惧")

    game.history.listen(EVENT_PHASE_START, on_phase_start, owner=minion)

    return True


@special
def _xuanchen_special(minion, player, game, extras=None):
    """宣辰：部署：展示卡组顶的3张牌，将其中1张置入手牌。若其折算花费不大于5，你获得等量血契。"""
    from card_pools.effect_utils import convert_cost_to_t

    deck = player.card_deck
    show_count = min(3, len(deck))
    if show_count == 0:
        print("  宣辰：牌库已空")
        return True

    # 从牌库顶依次取出（deck.pop() 取末尾即牌库顶）
    shown = [deck.pop() for _ in range(show_count)]

    # 构建选项，显示折算花费
    options = [f"{i+1}. {c.name}({convert_cost_to_t(c.cost)}T折算)" for i, c in enumerate(shown)]
    chosen_str = game.request_choice(player, options, title="宣辰：选择1张牌置入手牌")
    if chosen_str is None:
        # 玩家取消，将展示牌按原顺序放回牌库顶
        for c in reversed(shown):
            deck.append(c)
        print("  宣辰：未选择牌，展示牌放回牌库顶")
        return False

    idx = int(chosen_str.split('.')[0]) - 1
    chosen = shown[idx]

    # 置入手牌（或手牌满则磨牌）
    player.add_card_to_hand(chosen, game=game, emit_events=False)

    # 剩余牌保持原顺序放回牌库顶
    remaining = [c for c in shown if c is not chosen]
    for c in reversed(remaining):
        deck.append(c)
    if remaining:
        print(f"  宣辰：剩余 {len(remaining)} 张牌放回牌库顶")

    # 计算折算花费，若不大于5则获得等量血契
    cost_t = convert_cost_to_t(chosen.cost)
    if cost_t <= 5:
        player.s_point_change(cost_t)
        print(f"  宣辰：{chosen.name} 折算花费 {cost_t} ≤ 5，获得 {cost_t} 血契")
    else:
        print(f"  宣辰：{chosen.name} 折算花费 {cost_t} > 5，不获得血契")

    return True


@special
def _jupian_special(minion, player, game, extras=None):
    """锯片：部署：对1个异象和你造成3点伤害。"""
    from tards.core.targeting import TargetingRequest
    from tards.cards import Minion

    def scope(p, board):
        return [m for m in board.minion_place.values() if m.is_alive()]

    req = TargetingRequest()
    req.source = minion
    req.scope_fn = scope
    req.prompt = "锯片：选择1个异象"
    req.deciding_player = player

    target = game.targeting_system.request_target(req)
    if target is None:
        return False

    if not isinstance(target, Minion) or not target.is_alive():
        print("  锯片：目标无效")
        return False

    # 对目标异象造成3点伤害
    target.take_damage(3, source_minion=minion, source_type="effect")
    print(f"  锯片：对 {target.name} 造成3点伤害")

    # 对玩家造成3点伤害
    player.health_change(-3, source=minion)
    print(f"  锯片：{player.name} 受到3点伤害")

    return True


@special
def _shimengmo_special(minion, player, game, extras=None):
    """食梦貘：攻击力不大于4时具有迅捷。部署：选择并弃1张手牌，获得等同于其花费的攻击力。"""

    # 1. 动态迅捷：通过 _aura_keyword_fns 实现，每次 recalculate() 自动更新
    def swiftness_aura(m):
        if m.current_attack <= 4:
            return {"迅捷": True}
        return {}

    minion._aura_keyword_fns.append(swiftness_aura)

    # 2. 部署效果：选择并弃1张手牌，获得等同于其T费用的攻击力
    if not player.card_hand:
        print("  食梦貘：手牌为空，无法弃牌")
        return True

    options = [f"{i+1}. {c.name}({c.cost.t}T)" for i, c in enumerate(player.card_hand)]
    chosen = game.request_choice(player, options, title="食梦貘：选择弃1张手牌")
    if chosen is None:
        print("  食梦貘：未选择手牌")
        return False

    idx = int(chosen.split('.')[0]) - 1
    discarded = player.card_hand[idx]
    cost_t = discarded.cost.t

    player.discard_card(discarded, game, reason="effect")
    print(f"  食梦貘：弃掉 {discarded.name}，获得 {cost_t} 点攻击力")

    minion.gain_attack(cost_t, permanent=True)

    return True


# Alias for backward compatibility
_tianxiawushuang_effect = _tianxia_wushuang_effect


# ── 阿波罗之卫：拦截 random.choice ──
import random
import inspect
from tards.cards import Minion
from tards.game import Game

_original_random_choice = random.choice
_apollo_games = {}   # id(game) -> minion
_apollo_refcount = 0


def _apollo_choice(seq):
    """拦截 random.choice：当用于选择 Minion 目标时改为指向。"""
    # 防御性清理：移除已死亡的阿波罗之卫注册
    dead_games = [gid for gid, m in _apollo_games.items() if not m.is_alive()]
    for gid in dead_games:
        _apollo_games.pop(gid, None)
        _uninstall_apollo_choice()
    if not _apollo_games:
        return _original_random_choice(seq)

    # 只拦截非空序列
    if not isinstance(seq, (list, tuple)) or not seq:
        return _original_random_choice(seq)

    # 只拦截 Minion 列表
    if not all(isinstance(x, Minion) for x in seq):
        return _original_random_choice(seq)

    # 从调用栈查找 Game 实例
    game = None
    frame = inspect.currentframe().f_back
    while frame:
        for val in frame.f_locals.values():
            if isinstance(val, Game):
                game = val
                break
        if game:
            break
        frame = frame.f_back

    if game is None or id(game) not in _apollo_games:
        return _original_random_choice(seq)

    apollo = _apollo_games[id(game)]
    if not apollo.is_alive():
        return _original_random_choice(seq)

    # 弹出 TargetingRequest，让阿波罗之卫的拥有者指向
    from tards.core.targeting import TargetingRequest
    req = TargetingRequest()
    req.source = apollo
    req.deciding_player = apollo.owner
    req.scope_fn = lambda p, b: list(seq)
    req.prompt = "阿波罗之卫：随机效果改为指向，选择目标"

    target = game.targeting_system.request_target(req)
    if target is not None and target in seq:
        print(f"  阿波罗之卫：随机目标改为指向 {target.name}")
        return target

    # 玩家取消或无效，回退到随机（使用独立 Random 实例，避免污染全局 RNG 状态）
    _apollo_fallback_random = random.Random(id(game) + len(seq))
    return _apollo_fallback_random.choice(seq)


def _install_apollo_choice():
    global _apollo_refcount
    _apollo_refcount += 1
    if _apollo_refcount == 1:
        random.choice = _apollo_choice


def _uninstall_apollo_choice():
    global _apollo_refcount
    _apollo_refcount -= 1
    if _apollo_refcount <= 0:
        random.choice = _original_random_choice
        _apollo_refcount = 0


@special
def _aboluozhiwei_special(minion, player, game, extras=None):
    """阿波罗之卫：你的随机效果改为指向。"""
    _apollo_games[id(game)] = minion
    _install_apollo_choice()

    def _has_other_apollo(g, exclude):
        for m in g.board.minion_place.values():
            if m is not exclude and m.name == "阿波罗之卫" and m.is_alive():
                return True
        return False

    def on_death(event, g):
        if _has_other_apollo(g, minion):
            return
        _apollo_games.pop(id(g), None)
        _uninstall_apollo_choice()

    def on_removed(event, g):
        data = event.data
        dead = getattr(data, "minion", None) or data.get("minion")
        if dead is not minion:
            return
        if _has_other_apollo(g, minion):
            return
        _apollo_games.pop(id(g), None)
        _uninstall_apollo_choice()

    game.history.listen("minion_death", on_death, owner=minion)
    game.history.listen("minion_removed", on_removed, owner=minion)
    return True


# =============================================================================
# 雪降：抽取时若可能消耗3S冰冻所有异象；打出时对一个被冰冻异象造成4点伤害
# =============================================================================
def _xuejiang_draw_trigger(player, game, card):
    """抽取：如可能，消耗3S，然后冰冻所有异象。"""
    from card_pools.effect_utils import freeze_minion

    if player.s_point >= 3:
        player.s_point -= 3
        print(f"  {card.name} 抽取：{player.name} 消耗3S")
    else:
        print(f"  {card.name} 抽取：{player.name} S不足，无法消耗")

    all_minions = list(game.board.minion_place.values())
    frozen_count = 0
    for m in all_minions:
        if m.is_alive():
            freeze_minion(m, layers=1)
            frozen_count += 1
    if frozen_count > 0:
        print(f"  {card.name} 抽取：冰冻了 {frozen_count} 个异象")


def _xuejiang_effect(player, target, game, extras=None, card=None):
    """雪降：对一个被冰冻的异象造成4点伤害。"""
    from card_pools.effect_utils import deal_damage_to_minion

    if target is None or not getattr(target, "is_alive", lambda: False)():
        print(f"  雪降：没有有效的目标")
        return False

    if not target.keywords.get("冰冻", 0):
        print(f"  雪降：目标 {target.name} 未被冰冻")
        return False

    deal_damage_to_minion(target, 4, game=game)
    print(f"  雪降：被冰冻的 {target.name} 受到4点伤害")
    return True


# =============================================================================
# 血痂：2T 1/1 协同；抽取自伤3，部署回血3，亡语抽1
# =============================================================================
def _xuejia_draw_trigger(player, game, card):
    """抽取：对己方主角造成3点伤害。"""
    player.health_change(-3)
    print(f"  {card.name} 抽取：{player.name} 受到3点伤害")


@special
def _xuejia_special(minion, player, game, extras=None):
    """血痂：部署：你获得3点HP。亡语：抽1张牌。"""
    player.health_change(3)
    print(f"  {minion.name} 部署：{player.name} 获得3点HP")

    def _dr(m, p, b):
        from card_pools.effect_utils import draw_cards
        g = b.game_ref if hasattr(b, "game_ref") else None
        draw_cards(p, 1, game=g)
        print(f"  {m.name} 亡语：{p.name} 抽1张牌")

    add_deathrattle(minion, _dr)
    return True


def _xuejia_deathrattle(minion, player, board):
    """血痂亡语（外部引用占位，实际亡语在 _xuejia_special 中注册）。"""
    pass
