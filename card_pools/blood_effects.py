# 血契卡包人工效果实现
# 由 blood.py 引用

from card_pools.effect_decorator import special
from card_pools.effect_utils import (
    add_deathrattle,
    add_event_listener,
    buff_minion,
    destroy_minion,
    draw_cards,
    give_card_by_name,
    heal_player,
    on_after_attack,
    random_enemy_minion,
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
]


# =============================================================================
# 保卫者：你受到伤害时，本单位获得+1/1
# =============================================================================
@special
def _baoweizhe_special(minion, player, game, extras=None):
    """保卫者：你受到伤害时，本单位获得+1/1。"""
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
# 溴化银：攻击后，消灭本单位。亡语：将1张"胶片"加入对方手牌
# =============================================================================
@special
def _xiuhuayin_special(minion, player, game, extras=None):
    """溴化银：攻击后，消灭本单位。亡语：将1张"胶片"加入对方手牌。"""
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
# 亡灵：无法被单位选中（已有恐惧关键词，此函数仅为占位/无额外效果）
# =============================================================================
@special
def _wangling_special(minion, player, game, extras=None):
    """亡灵：无法被单位选中（已有恐惧关键词）。"""
    # 恐惧关键词已在 keywords 中定义，board.get_front_minion 会自动过滤
    pass


# =============================================================================
# 硫氰化钾：部署：使1个单位获得恐惧。若其已具有恐惧，将其HP设为1点。
# =============================================================================
@special
def _liuqinghuajia_special(minion, player, game, extras=None):
    """硫氰化钾：部署：使1个目标获得恐惧。若其已具有恐惧，将其HP设为1点。"""
    target = extras[0] if extras else None
    if not target or not getattr(target, "is_alive", lambda: False)():
        return
    if getattr(target, "keywords", {}).get("恐惧", False):
        # 已具有恐惧，将其HP设为1点
        target.current_health = 1
        target.health = 1
        print(f"  硫氰化钾：{target.name} 已具有恐惧，HP 被设为 1")
    else:
        target.apply_fear()
        print(f"  硫氰化钾：{target.name} 获得恐惧")


# =============================================================================
# 竹心：亡语：随机消灭1个处于协同的敌方单位。
# =============================================================================
@special
def _zhuxin_special(minion, player, game, extras=None):
    """竹心：亡语：随机消灭1个处于协同的敌方单位。"""
    def _dr(m, p, b):
        enemies = [x for x in game.board.get_all_minions() if x.owner != p and x.is_alive() and x.keywords.get("协同", False)]
        if not enemies:
            print(f"  竹心亡语：没有处于协同的敌方单位")
            return
        import random
        target = random.choice(enemies)
        destroy_minion(target, game)
        print(f"  竹心亡语：随机消灭处于协同的 {target.name}")

    add_deathrattle(minion, _dr)


# =============================================================================
# 环丁二烯：亡语：使敌方部署的下一个单位获得恐惧。
# =============================================================================
@special
def _huanderxixi_special(minion, player, game, extras=None):
    """环丁二烯：亡语：使敌方部署的下一个单位获得恐惧。"""
    def _dr(m, p, b):
        from tards.constants import EVENT_DEPLOYED
        def _listener(event):
            deployed = event.data.get("minion")
            if deployed and deployed.owner != p and deployed.is_alive():
                deployed.apply_fear()
                print(f"  环丁二烯亡语触发：{deployed.name} 获得恐惧")
                game.unregister_listener(EVENT_DEPLOYED, _listener)

        game.register_listener(EVENT_DEPLOYED, _listener)
        print(f"  环丁二烯亡语：已注册敌方下一单位恐惧效果")

    add_deathrattle(minion, _dr)


# =============================================================================
# Bishop：回合结束：场上每有1个具有恐惧的单位，你获得1点HP。
# =============================================================================
@special
def _bishop_special(minion, player, game, extras=None):
    """Bishop：回合结束：场上每有1个具有恐惧的单位，你获得1点HP。"""
    def on_turn_end(g, event_data, source=minion):
        if not source.is_alive():
            return
        count = sum(1 for m in g.board.get_all_minions() if m.is_alive() and m.keywords.get("恐惧", False))
        if count > 0:
            heal_player(player, count)
            print(f"  Bishop 触发：场上 {count} 个恐惧单位，{player.name} 恢复 {count} HP")

    minion.on_turn_end = on_turn_end
