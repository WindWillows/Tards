# 冥刻卡包复杂效果辅助函数
# 该文件不被 translate_packs.py 覆盖，供 underworld.py 引用

from card_pools.effect_decorator import special, strategy
from card_pools.effect_utils import (
    add_deathrattle,
    buff_minion,
    convert_cost_to_t,
    create_card_by_name,
    deal_damage_to_minion,
    deal_damage_to_player,
    destroy_minion,
    draw_cards,
    draw_cards_of_type,
    empty_positions,
    gain_keyword,
    gain_resource,
    heal_minion,
    initiate_combat,
    on,
    on_before_attack,
    redirect_damage,
    return_minion_to_hand,
)
from tards import DEFAULT_REGISTRY, Pack, Rarity, CardType
from tards.cards import Minion, MinionCard
from tards.constants import EVENT_TURN_START

SPECIAL_MAP = {
    "松鼠球": "_songshuqiu_special",
    "雕": "_diao_special",
    "鹏": "_peng_special",
    "天牛": "_tianniu_special",
    "寄居蟹": "_jijuxie_special",
    "烛烟": "_zhuyan_special",
    "大团烛烟": "_datuanzhuyan_special",
    "猫": "_mao_special",
    "白鼬": "_baiyou_special",
    "弱狼": "_ruolang_special",
    "西瓜": "_xigua_special",
    "信鸽": "_xinge_special",
    "鸮": "_xiao_special",
    "臭虫": "_chouchong_special",
    "林鼠": "_linshu_special",
    "狐": "_hu_special",
}

__all__ = [
    "_arthropod_top_effect",
    "_arthropod_bottom_effect",
    "_aquatic_top_effect",
    "_aquatic_bottom_effect",
    "_predator_top_effect",
    "_predator_bottom_effect",
    "_sacrifice_top_effect",
    "_sacrifice_bottom_effect",
    "_avian_top_effect",
    "_avian_bottom_effect",
    "_diao_special",
    "_peng_special",
    "_songshuqiu_special",
    "_jijuxie_special",
    "_tianniu_special",
    "_zhuyan_special",
    "_datuanzhuyan_special",
    "_mao_special",
    "_baiyou_special",
    "_ruolang_special",
    "_xigua_special",
    "_xinge_special",
    "_xiao_special",
    "_chouchong_special",
    "_linshu_special",
    "_hu_special",
    "_jin_yachi_strategy",
    "_shanzi_strategy",
    "target_any_minion_or_enemy_player",
    "_jiandao_effect",
    "_fange_effect",
    "_xurui_effect",
    "_moshui_effect",
    "_jinfeng_effect",
    "_liqun_effect",
    "_ruhe_effect",
    "_guaishi_effect",
    "_haishi_effect",
    "_yanxing_effect",
    "_yexi_effect",
    "_songshuping_effect",
    "_shudong_effect",
    "_xueping_effect",
    "_qianzi_effect",
    "_linshu_daobing_effect",
    "_guwang_effect",
    "_guwangzhi_hui_effect",
    "_guwangzhi_shang_effect",
    "_lazhu_effect",
    "_zhiwuxuejia_effect",
    "_pimaoshang_effect",
    "_lieren_effect",
    "_yugou_effect",
    "_bopidao_effect",
    "_yanping_effect",
    "_lanyue_effect",
    "_zhadan_yao_effect",
    "_xiangji_effect",
    "_shalou_effect",
    "_xueyue_effect",
    "_jiaoshui_effect",
    "_shizhong_effect",
    "_yinghuo_effect",
    "_bingkuai_effect",
    "_mudiaoshi_effect",
    "_muqi_effect",
    "_make_effect",
    "_hanji_effect",
    "_shanhong_effect",
    "_shuiyi_effect",
    "_shachen_effect",
    "_kuangfeng_effect",
    "_gaozhi_effect",
    "_zhouyu_effect",
    "_fansheng_effect",
    "_tudao_effect",
    "_zhenban_effect",
    "_haichen_effect",
    "_jidai_effect",
    "_yehuo_effect",
    "_lunhui_effect",
    "_gengti_effect",
    "_poxiao_effect",
    "_liulinfengsheng_effect",
    "_hesheng_effect",
    "_shanqian_effect",
    "_culi_effect",
    "_fushu_special",
    "_biyi_special",
    "_jinyangpi_effect",
    "_shudong_targets",
    "_pimaoshang_choice",
    "_lieren_targets",
    "_yanping_targets",
    "_shalou_cost_modifier",
    "_shizhong_targets",
    "_muqi_targets",
    "_make_targets",
    "_shanhong_targets",
    "_gaozhi_cost_modifier",
    "_zhenban_targets",
    "_haichen_targets",
    "_yehuo_targets",
    "_yehuo_minion_choice",
    "_lunhui_targets",
    "_lunhui_target_choice",
    "_gengti_targets",
    "_liulinfengsheng_targets",
]






def _arthropod_top_effect(game, top):
    for m in game.board.get_minions_of_player(top.owner):
        if "昆虫" in getattr(m, "tags", []):
            if not m.base_keywords.get("亡语"):
                m.base_keywords["亡语"] = lambda minion, owner, board: None
            m.recalculate()
    opp = game.p1 if top.owner == game.p2 else game.p2
    opp.health_change(-1)


def _arthropod_bottom_effect(game, bottom, top):
    def buff(m):
        if "昆虫" in getattr(m, "tags", []):
            m.perm_attack_bonus += 1
            m.perm_max_health_bonus += 1
            m.perm_health_bonus += 1
            m.recalculate()
    bottom.owner._deploy_buffs.append(buff)


def _aquatic_top_effect(game, top):
    def mod(card, cost):
        aquatic = "两栖" in card.keywords or "水生" in card.keywords or "两栖" in getattr(card, "tags", []) or "水生" in getattr(card, "tags", [])
        if aquatic:
            cost.t = max(0, cost.t - 1)
    top.owner._cost_modifiers.append(mod)


def _aquatic_bottom_effect(game, bottom, top):
    for m in game.board.get_minions_of_player(bottom.owner):
        if "两栖" in m.keywords or "水生" in m.keywords or "两栖" in getattr(m, "tags", []) or "水生" in getattr(m, "tags", []):
            m.base_keywords["先攻"] = 1
            m.recalculate()


def _predator_top_effect(game, top):
    def buff(m):
        if "陆生" in getattr(m, "tags", []) and "肉食动物" in getattr(m, "tags", []):
            m.perm_attack_bonus += 2
            m.perm_max_health_bonus += 1
            m.perm_health_bonus += 1
            m.recalculate()
    top.owner._deploy_buffs.append(buff)


def _predator_bottom_effect(game, bottom, top):
    def mod(card, cost):
        if "陆生" in getattr(card, "tags", []) and "肉食动物" in getattr(card, "tags", []):
            cost.b = max(0, cost.b - 1)
    bottom.owner._cost_modifiers.append(mod)


def _sacrifice_top_effect(game, top):
    def buff(m):
        if m.source_card and m.source_card.cost.b == 0 and not getattr(top.owner, "_fertile_top_used", False):
            top.owner._fertile_top_used = True
            m.base_keywords["献祭"] = m.base_keywords.get("献祭", 0) + 1
            m.recalculate()
    top.owner._deploy_buffs.append(buff)
    old = top.owner.on_turn_start
    def reset(g, e, p):
        p._fertile_top_used = False
        if old:
            old(g, e, p)
    top.owner.on_turn_start = reset


def _sacrifice_bottom_effect(game, bottom, top):
    for m in game.board.get_minions_of_player(bottom.owner):
        if m.source_card and m.source_card.cost.b == 0:
            m.base_keywords["丰饶"] = m.base_keywords.get("丰饶", 0) + 1
            m.recalculate()


def _avian_top_effect(game, top):
    for m in game.board.get_minions_of_player(top.owner):
        if "飞禽" in getattr(m, "tags", []):
            m.base_keywords["迅捷"] = True
            m.recalculate()


def _avian_bottom_effect(game, bottom, top):
    for m in game.board.get_minions_of_player(bottom.owner):
        if "飞禽" in getattr(m, "tags", []):
            m.perm_attack_bonus += 2
            m.recalculate()


# ===== 复杂卡牌手动效果 =====

# 雕(铁) - 先攻3；首次攻击后永久失去先攻3，-3攻击力，获得空袭
def _diao_special(minion, player, game, extras=None):
    minion._diao_triggered = False
    def on_attack(attacker, target):
        if attacker is not minion:
            return
        if getattr(minion, "_diao_triggered", False):
            return
        minion._diao_triggered = True
        fs = minion.keywords.get("先攻", 0)
        if isinstance(fs, int) and fs > 0:
            minion.base_keywords["先攻"] = max(0, fs - 3)
        minion.perm_attack_bonus -= 3
        minion.base_keywords["空袭"] = True
        minion.recalculate()
        print(f"  {minion.name} 首次攻击后失去先攻3，攻击力-3，获得空袭")
    if not hasattr(minion, "_pre_attack_fns"):
        minion._pre_attack_fns = []
    minion._pre_attack_fns.append(on_attack)


# 鹏(铁) - 所有花费≤5的非飞禽异象部署时具有休眠2（不分敌我）；部署：使敌方花费≤4的异象返回手牌
def _peng_special(minion, player, game, extras=None):
    # 部署时：使敌方场上花费≤4的异象返回手牌
    enemies = [m for m in game.board.get_all_minions() if m.owner is not player and m.is_alive()]
    for e in enemies:
        sc = getattr(e, 'source_card', None)
        if sc and sc.cost.t <= 4:
            game.board.remove_minion(e.position)
            bc = e.source_card
            new_card = MinionCard(
                name=bc.name,
                owner=e.owner,
                cost=bc.cost,
                targets=bc.targets,
                attack=bc.attack,
                health=bc.health,
                special=getattr(bc, 'special', None),
                keywords=dict(bc.keywords) if hasattr(bc, 'keywords') else {},
            )
            if hasattr(bc, "tags"):
                new_card.tags = list(bc.tags)
            if len(e.owner.card_hand) < e.owner.card_hand_max:
                e.owner.card_hand.append(new_card)
            else:
                e.owner.card_dis.append(new_card)
            print(f"  {e.name} 被鹏遣返回手牌")

    # 部署钩子：花费≤5的非飞禽异象获得休眠2
    def deploy_hook(g, deployed):
        sc = getattr(deployed, 'source_card', None)
        if sc and sc.cost.t <= 5 and "飞禽" not in getattr(deployed, "tags", []):
            deployed.base_keywords["休眠"] = 2
            deployed.recalculate()
            print(f"  {deployed.name} 因鹏获得休眠2")
    minion.register_deploy_hook(game, deploy_hook)


# 松鼠球(铁) - 受到伤害后向相邻陆地移动一格，在原地留下松鼠
def _songshuqiu_special(minion, player, game, extras=None):
    from card_pools.effect_utils import get_adjacent_positions, move, summon_token
    import random

    def on_damage():
        if not minion.is_alive():
            return
        adj = get_adjacent_positions(minion.position, game.board)
        candidates = [p for p in adj if p not in game.board.minion_place]
        if not candidates:
            return
        old_pos = minion.position
        new_pos = random.choice(candidates)
        if move(minion, new_pos, game):
            summon_token(game, "松鼠", player, old_pos, attack=1, health=1)
    minion._on_take_combat_damage.append(on_damage)


# 寄居蟹(铁) - 回合结束向相邻移动一格；记录被其伤害异象的回响，回合开始时加入手牌再弃掉
def _jijuxie_special(minion, player, game, extras=None):
    minion._recorded_echoes = []

    # 回合结束向相邻移动一格
    from card_pools.effect_utils import get_adjacent_positions, move
    import random

    def on_turn_end(g, e, m=minion):
        adj = get_adjacent_positions(m.position, g.board)
        candidates = [p for p in adj if p not in g.board.minion_place]
        if candidates:
            new_pos = random.choice(candidates)
            if move(m, new_pos, g):
                print(f"  {m.name} 回合结束移动至 {new_pos}")
    minion.on_turn_end = on_turn_end

    # 记录被其伤害异象的回响
    old_attack = minion.attack_target
    def attack_target(target, g=game, m=minion):
        result = old_attack(target)
        if isinstance(target, type(m)) and target.source_card:
            name = target.source_card.name
            if name not in m._recorded_echoes:
                m._recorded_echoes.append(name)
                print(f"  {m.name} 记录了 {name} 的回响")
        return result
    minion.attack_target = attack_target

    # 回合开始时加入手牌再弃掉
    def on_turn_start(g, e, m=minion):
        for name in list(m._recorded_echoes):
            m._recorded_echoes.remove(name)
            from tards.cost import Cost
            echo = MinionCard(name=name, owner=m.owner, cost=Cost(), targets=lambda p, b: [], attack=0, health=1)
            if len(m.owner.card_hand) < m.owner.card_hand_max:
                m.owner.card_hand.append(echo)
            else:
                m.owner.card_dis.append(echo)
            print(f"  {m.name} 将 {name} 的回响加入手牌并弃掉")
            if echo in m.owner.card_hand:
                m.owner.card_hand.remove(echo)
                m.owner.card_dis.append(echo)
    minion.on_turn_start = on_turn_start


# 天牛(铁) - 回合结束：使同列敌方前排异象移动至后排，后排异象返回对方手牌
def _tianniu_special(minion, player, game, extras=None):
    from card_pools.effect_utils import move, return_minion_to_hand

    def on_turn_end(g, e, m=minion):
        col = m.position[1]
        enemies = [x for x in g.board.get_enemy_minions_in_column(col, m.owner) if x.is_alive()]
        if not enemies:
            return
        enemies.sort(key=lambda x: abs(x.position[0] - 2))
        front = enemies[0]
        backs = [x for x in enemies if x is not front]
        # 移动前排到后排（敌方区域的远端）
        enemy_rows = front.owner.get_friendly_rows()
        for r in sorted(enemy_rows, key=lambda x: abs(x - front.position[0]), reverse=True):
            dest = (r, col)
            if dest not in g.board.minion_place:
                move(front, dest, g)
                break
        # 后排返回手牌
        for back in backs:
            if back.is_alive():
                return_minion_to_hand(back, g)
    minion.on_turn_end = on_turn_end


# =============================================================================
# 冥刻包 — 代表性效果（特殊资源机制）
# =============================================================================

def _register_candle_modifier_and_count(player):
    """注册蜡烛费用修正器（若尚未注册）并增加烛烟部署计数。"""
    if not getattr(player, "_candle_modifier_registered", False):
        def _mod(card, cost):
            if card.name == "蜡烛":
                reduction = getattr(player, "_zhuyan_deployed_count", 0) * 2
                if reduction > 0:
                    cost.t = max(0, cost.t - reduction)
        player._cost_modifiers.append(_mod)
        player._candle_modifier_registered = True
    player._zhuyan_deployed_count = getattr(player, "_zhuyan_deployed_count", 0) + 1


def _zhuyan_special(minion, player, game, extras=None):
    """烛烟：亡语：抽1张牌。部署时增加烛烟计数并注册蜡烛费用修正。"""
    _register_candle_modifier_and_count(player)

    def _dr(m, p, b):
        draw_cards(p, 1, game=b.game_ref if hasattr(b, "game_ref") else None)
    add_deathrattle(minion, _dr)


# =============================================================================
# 新实现 — 简单亡语/回合效果
# =============================================================================

# 西瓜 — 亡语：双方各抽2张牌。
@special
def _xigua_special(minion, player, game, extras=None):
    """西瓜：亡语：双方各抽2张牌。"""
    def _dr(m, p, b):
        g = b.game_ref if hasattr(b, "game_ref") else None
        draw_cards(p, 2, game=g)
        opponent = game.p1 if p == game.p2 else game.p2
        draw_cards(opponent, 2, game=g)
        print(f"  西瓜亡语：双方各抽2张牌")
    add_deathrattle(minion, _dr)


# 信鸽(铁)(I) — 回合结束：返回手牌，抽一张牌。
@special
def _xinge_special(minion, player, game, extras=None):
    """信鸽(铁)(I)：回合结束：返回手牌，抽一张牌。"""
    def on_turn_end(g, event_data, source=minion):
        if not source.is_alive():
            return
        return_minion_to_hand(source, g)
        draw_cards(player, 1, game=g)
        print(f"  信鸽回合结束：返回手牌并抽1张牌")
    minion.on_turn_end = on_turn_end


def _datuanzhuyan_special(minion, player, game, extras=None):
    """大团烛烟：亡语：抽2张牌。部署时增加烛烟计数并注册蜡烛费用修正。"""
    _register_candle_modifier_and_count(player)

    def _dr(m, p, b):
        draw_cards(p, 2, game=b.game_ref if hasattr(b, "game_ref") else None)
    add_deathrattle(minion, _dr)


def _mao_special(minion, player, game, extras=None):
    """猫(铁)：不会因献祭而被消灭。标记该异象免疫献祭消灭，献祭时只提供B点而不被移除。"""
    minion._immune_to_sacrifice = True


def _baiyou_special(minion, player, game, extras=None):
    """白鼬(铁)：受到战斗伤害后，将其消灭。"""
    def _on_combat_damage():
        if minion.is_alive():
            destroy_minion(minion, game)
            print(f"  白鼬受到战斗伤害后自毁")
    minion._on_take_combat_damage.append(_on_combat_damage)


def _ruolang_special(minion, player, game, extras=None):
    """弱狼(铁)：亡语：造成3点伤害，随机分配至敌方主角与伤害来源。简化实现：3点伤害全部给敌方主角（伤害来源追踪较复杂）。"""
    def _dr(m, p, b):
        opponent = game.p1 if p == game.p2 else game.p2
        # 造成3点伤害给敌方主角
        deal_damage_to_player(opponent, 3, source=m, game=game)
        print(f"  弱狼亡语：对 {opponent.name} 造成3点伤害")
    add_deathrattle(minion, _dr)


@special
def _xiao_special(minion, player, game, extras=None):
    """鸮(铁)：攻击时，改为与目标对战。消灭一个异象后，获得等同于其攻击力的HP。"""
    def _on_before_attack(event):
        attacker = event.data.get("attacker")
        if attacker is not minion:
            return
        # 避免递归：initiate_combat 内部也会触发 before_attack
        if getattr(minion, "_in_initiate_combat", False):
            return
        target = event.data.get("target")
        if not target or not hasattr(target, "is_alive") or not target.is_alive():
            return

        # 记录目标攻击力（用于战后恢复）
        target_atk = getattr(target, "current_attack", 0)

        # 取消原攻击，改为对战
        event.cancelled = True
        print(f"  {minion.name} 攻击时改为与 {target.name} 对战")
        initiate_combat(minion, target, game)

        # 若目标被消灭，恢复HP = 目标攻击力
        if not target.is_alive() and target_atk > 0:
            heal_minion(minion, target_atk)
            print(f"  {minion.name} 消灭目标后恢复 {target_atk} HP")

    on_before_attack(minion, game, _on_before_attack)


# =============================================================================
# 冥刻包 — 新增卡牌效果（臭虫、林鼠、狐、金牙齿、扇子）
# =============================================================================

@special
def _chouchong_special(minion, player, game, extras=None):
    """臭虫：与其同列的敌方异象具有-1攻击力（光环效果）。"""

    def aura_fn(target):
        if not minion.is_alive():
            return 0
        if target.owner is minion.owner:
            return 0
        bug_pos = minion.position
        target_pos = target.position
        if bug_pos is None or target_pos is None:
            return 0
        if bug_pos[1] == target_pos[1]:
            return -1
        return 0

    # 给所有当前敌方异象添加 aura
    for m in game.board.minion_place.values():
        if m.owner is not minion.owner and m.is_alive():
            minion.provide_aura_attack(m, aura_fn)

    # 新部署的敌方异象也获得 aura
    def on_deployed(event):
        deployed = event.data.get("minion")
        if not deployed or not deployed.is_alive():
            return
        if deployed.owner is minion.owner:
            return
        minion.provide_aura_attack(deployed, aura_fn)

    on("deployed", on_deployed, game, minion=minion)


@special
def _linshu_special(minion, player, game, extras=None):
    """林鼠：部署：抉择：抽一张策略，或将1只0T的松鼠加入手牌。"""
    choice = game.request_choice(
        player,
        ["抽一张策略", "将1只0T的松鼠加入手牌"],
        title="林鼠：选择一项",
    )
    if choice == "抽一张策略":
        from tards.cards import Strategy

        drawn = draw_cards_of_type(player, 1, Strategy, game)
        if drawn:
            print(f"  林鼠：{player.name} 抽到策略 {drawn[0].name}")
        else:
            print(f"  林鼠：{player.name} 牌库中没有策略")
    elif choice == "将1只0T的松鼠加入手牌":
        card = create_card_by_name("松鼠", player)
        if card:
            card.cost.t = 0
            if len(player.card_hand) < player.card_hand_max:
                player.card_hand.append(card)
                print(f"  林鼠：{player.name} 将0T松鼠加入手牌")
            else:
                player.card_dis.append(card)
                print(f"  林鼠：{player.name} 手牌满，0T松鼠被弃置")


@special
def _hu_special(minion, player, game, extras=None):
    """狐：攻击后，获得+1攻击力。免疫偶数伤害。"""
    # 免疫偶数伤害
    redirect_damage(minion, lambda d, s: d % 2 == 0, 0, "even_immunity")
    print(f"  狐：{minion.name} 免疫偶数伤害")

    # 攻击后永久+1攻击力
    def on_after_attack(event):
        attacker = event.data.get("attacker")
        if attacker is not minion:
            return
        if not minion.is_alive():
            return
        buff_minion(minion, atk_delta=1, permanent=True)
        print(f"  狐：{minion.name} 攻击后获得+1攻击力")

    on("after_attack", on_after_attack, game, minion=minion)


# ----- 策略卡效果 -----

def target_any_minion_or_enemy_player(player, board):
    """返回所有场上异象 + 敌方玩家（用于金牙齿等需要指向玩家或异象的策略）。"""
    targets = list(board.minion_place.values())
    if board.game_ref:
        for p in board.game_ref.players:
            if p != player:
                targets.append(p)
    return targets


@strategy
def _jin_yachi_strategy(player, target, game, extras=None):
    """金牙齿：对一个目标造成1点伤害。若将其消灭，获得1T，抽一张牌。"""
    from tards.cards import Minion

    if isinstance(target, Minion):
        deal_damage_to_minion(target, 1, source=None, game=game)
        # 注意：minion_death() 将实际移除操作放入 effect_queue，is_alive() 此时仍为 True
        # 应直接检查血量或 _pending_death 标记来判断是否已消灭
        if target.current_health <= 0 or getattr(target, "_pending_death", False):
            gain_resource(player, "t", 1)
            draw_cards(player, 1, game)
            print(f"  金牙齿消灭 {target.name}，{player.name} 获得1T并抽一张牌")
    else:
        # 对玩家造成伤害（无法消灭玩家，不触发后续）
        deal_damage_to_player(target, 1, source=None, game=game)
        print(f"  金牙齿对 {target.name} 造成1点伤害")
    return True


@strategy
def _shanzi_strategy(player, target, game, extras=None):
    """扇子：使一个异象具有空袭直到回合结束。抽1张牌。"""
    from tards.cards import Minion

    if not isinstance(target, Minion) or not target.is_alive():
        print("  扇子：目标无效")
        return False
    gain_keyword(target, "空袭", value=True, permanent=False)
    draw_cards(player, 1, game)
    print(f"  扇子：{target.name} 获得空袭直到回合结束，{player.name} 抽1张牌")
    return True
# =============================================================================
# =============================================================================
# 自动迁移的效果函数
# =============================================================================
def _jiandao_effect(game, event_data, player):
    """对方失去4T。"""
    deploy_player = event_data.get("player")
    if deploy_player:
        print(f"  阴谋 [剪刀] 触发：{deploy_player.name} 失去 4T")
        deploy_player.t_point_change(-4)

def _fange_effect(game, event_data, player):
    """对打出异象的玩家造成等同于其T花费的伤害。"""
    card = event_data.get("card")
    if isinstance(card, MinionCard):
        damage = card.cost.t if card.cost else 0
        target = card.owner
        if target and damage > 0:
            print(f"  阴谋 [反戈] 触发：{card.name} 的反噬对 {target.name} 造成 {damage} 点伤害")
            target.health_change(-damage)

def _xurui_effect(game, event_data, player):
    """阴谋拥有者获得4T。"""
    print(f"  阴谋 [蓄锐] 触发：{player.name} 获得 4T")
    player.t_point_change(4)

def _moshui_effect(game, event_data, player):
    """反制的主要工作已在 condition_fn 的堆栈推入中完成，
    此处仅打印确认信息。阴谋卡本身由 register_conspiracy 自动弃置。
    """
    print(f"  阴谋 [墨水] 结算完毕")

def _jinfeng_effect(game, event_data, player):
    """弃掉对方抽到的牌，并随机使其一张手牌花费+1T。"""
    draw_player = event_data.get("player")
    card = event_data.get("card")
    if card and card in draw_player.card_hand:
        draw_player.card_hand.remove(card)
        draw_player.card_dis.append(card)
        print(f"  阴谋 [劲风] 弃掉了 {draw_player.name} 抽到的 [{card.name}]")
    if draw_player.card_hand:
        import random
        target_card = random.choice(draw_player.card_hand)
        target_card.cost.t += 1
        print(f"  阴谋 [劲风] 使 {draw_player.name} 的 [{target_card.name}] 花费 +1T")

def _liqun_effect(game, event_data, player):
    """消灭该列所有进入协同状态的敌方异象。"""
    minion = event_data.get("minion")
    c = minion.position[1]
    from card_pools.effect_utils import destroy_minion
    to_destroy = []
    for r in range(game.board.SIZE):
        m = game.board.minion_place.get((r, c))
        if m and m.owner == minion.owner:
            to_destroy.append(m)
    for m in to_destroy:
        destroy_minion(m, game)
    print(f"  阴谋 [离群] 消灭了 {len(to_destroy)} 个进入协同状态的异象")

def _ruhe_effect(game, event_data, player):
    """注册回合开始监听器，延迟部署被反制的异象。"""
    listener_id = id(event_data)

    def _redeploy_listener(event):
        pending = getattr(game, "_ruhe_pending", [])
        to_remove = []
        for item in pending:
            if game.current_turn >= item["trigger_turn"]:
                card = item["card"]
                deploy_player = item["player"]
                pos = item["pos"]
                minion = Minion(
                    name=card.name,
                    owner=deploy_player,
                    position=pos,
                    attack=card.attack,
                    health=card.health,
                    source_card=card,
                    board=game.board,
                    keywords=dict(card.keywords) if card.keywords else {},
                    on_turn_start=card.on_turn_start,
                    on_turn_end=card.on_turn_end,
                    on_phase_start=card.on_phase_start,
                    on_phase_end=card.on_phase_end,
                    tags=list(card.tags) if card.tags else [],
                    hidden_keywords=dict(card.hidden_keywords) if card.hidden_keywords else {},
                )
                if hasattr(card, "statue_top"):
                    minion.statue_top = card.statue_top
                if hasattr(card, "statue_bottom"):
                    minion.statue_bottom = card.statue_bottom
                if hasattr(card, "statue_pair"):
                    minion.statue_pair = card.statue_pair
                minion.summon_turn = game.current_turn
                game.board.place_minion(minion, pos)
                print(f"  阴谋 [入河] 将 [{card.name}] 加入战场 {pos}")
                to_remove.append(item)
        for item in to_remove:
            pending.remove(item)
        game._ruhe_pending = pending
        if not pending:
            game.unregister_listeners_by_owner(listener_id)

    game.register_listener(EVENT_TURN_START, _redeploy_listener, priority=50, owner_id=listener_id)
    print(f"  阴谋 [入河] 效果触发：等待下回合将异象加入原位")

def _guaishi_effect(game, event_data, player):
    """对方永久失去一个T槽。"""
    bell_player = event_data.get("player")
    if bell_player:
        bell_player.t_point_max_change(-1)
        print(f"  阴谋 [怪石] 触发：{bell_player.name} 失去一个T槽（当前上限 {bell_player.t_point_max}）")

def _haishi_effect(game, event_data, player):
    """重定向已在 condition_fn 中同步完成。"""
    print(f"  阴谋 [海市蜃楼] 结算完毕")

def _yanxing_effect(game, event_data, player):
    """阴谋拥有者抽2张牌。"""
    print(f"  阴谋 [掩星] 触发：{player.name} 抽2张牌")
    player.draw_card(2, game=game)

def _yexi_effect(game, event_data, player):
    """使其先获得-2攻击力。若具有迅捷，将其消灭。"""
    attacker = event_data.get("attacker")
    from card_pools.effect_utils import destroy_minion
    if attacker.keywords.get("迅捷", False):
        destroy_minion(attacker, game)
        print(f"  阴谋 [夜袭] 消灭了具有迅捷的 [{attacker.name}]")
    else:
        attacker.base_attack -= 2
        attacker.recalculate()
        print(f"  阴谋 [夜袭] 使 [{attacker.name}] 获得-2攻击力（当前 {attacker.current_attack}）")

def _songshuping_effect(player, target, game, extras=None):
    """松鼠瓶：将2张"松鼠"加入手牌，此前你每使用过一次"松鼠瓶"，额外加入一只"松鼠"。

    松鼠直接从卡池定义创建新 token（不消耗 squirrel_deck）。
    若手牌已满，超出部分弃置。
    """
    squirrel_def = DEFAULT_REGISTRY.get("松鼠")
    if not squirrel_def:
        print(f"  [警告] 找不到松鼠定义，松鼠瓶效果失败")
        return False

    used_count = getattr(player, "_squirrel_bottle_used", 0)
    count = 2 + used_count

    added = 0
    discarded = 0
    for _ in range(count):
        card = squirrel_def.to_game_card(player)
        if len(player.card_hand) < player.card_hand_max:
            player.card_hand.append(card)
            added += 1
        else:
            player.card_dis.append(card)
            discarded += 1

    player._squirrel_bottle_used = used_count + 1

    print(
        f"  {player.name} 使用松鼠瓶，将 {added} 张松鼠加入手牌"
        f"{'（' + str(discarded) + ' 张因手牌满被弃置）' if discarded else ''}"
    )
    return True

def _shudong_effect(player, target, game, extras=None):
    from card_pools.effect_utils import all_friendly_minions, deploy_card_copy


    # 1. 部署松鼠
    squirrel_def = DEFAULT_REGISTRY.get("松鼠")
    if not squirrel_def:
        return False
    card = squirrel_def.to_game_card(player)
    ok = deploy_card_copy(player, game, card, target)
    if not ok:
        return False

    # 2. 给友方 B=0 冥刻异象添加"无法被选中"
    affected = []
    for m in all_friendly_minions(game, player):
        source = getattr(m, "source_card", None)
        if source and getattr(source, "pack", None) == Pack.UNDERWORLD and source.cost.b == 0:
            m.temp_keywords["无法被选中"] = True
            affected.append(m.name)
    if affected:
        print(f"  树洞：本回合 {', '.join(affected)} 无法被选中")

    return True

def _xueping_effect(player, target, game, extras=None):
    if target not in player.card_hand:
        return False
    from tards.cards import MinionCard
    if not isinstance(target, MinionCard):
        return False
    # 弃掉目标异象
    player.card_hand.remove(target)
    player.card_dis.append(target)
    print(f"  {player.name} 弃掉了 [{target.name}]")
    # 获得3B
    player.b_point_change(3)
    # 若非松鼠，抽一张牌
    if target.name != "松鼠":
        player.draw_card(1, game=game)
    return True

def _qianzi_effect(player, target, game, extras=None):
    """钳子：对你造成2点伤害，然后对一个异象造成4点伤害。抽一张牌。"""
    from tards.cards import Minion

    # 对自己造成2点伤害
    deal_damage_to_player(player, 2, game=game)
    print(f"  钳子：{player.name} 受到2点伤害")

    # 对目标异象造成4点伤害
    if isinstance(target, Minion) and target.is_alive():
        deal_damage_to_minion(target, 4, game=game)
        print(f"  钳子：{target.name} 受到4点伤害")

    # 抽一张牌
    player.draw_card(1, game=game)
    print(f"  钳子：{player.name} 抽1张牌")
    return True

def _linshu_daobing_effect(player, target, game, extras=None):
    import random
    from card_pools.effect_utils import all_enemy_minions
    from tards.cards import Minion

    # 1. 对你造成4点伤害
    deal_damage_to_player(player, 4, source=None, game=game)

    # 2. 8点伤害随机分配至所有敌方目标
    opponent = game.p2 if player == game.p1 else game.p1
    for _ in range(8):
        enemy_minions = [m for m in all_enemy_minions(game, player) if m.is_alive()]
        candidates = enemy_minions + [opponent]
        if not candidates:
            break
        chosen = random.choice(candidates)
        if isinstance(chosen, Minion):
            deal_damage_to_minion(chosen, 1, source=None, game=game)
        else:
            deal_damage_to_player(chosen, 1, source=None, game=game)

    return True

def _guwang_effect(player, target, game, extras=None):
    from tards.cards import MinionCard
    if not isinstance(target, MinionCard) or target not in player.card_hand:
        return False

    # 弃掉目标异象
    player.card_hand.remove(target)
    player.card_dis.append(target)

    # 计算献祭等级与丰饶等级
    sac_level = target.keywords.get("献祭", 0)
    if sac_level is True:
        sac_level = 1
    elif not isinstance(sac_level, int):
        sac_level = 0

    fer_level = target.keywords.get("丰饶", 0)
    if fer_level is True:
        fer_level = 1
    elif not isinstance(fer_level, int):
        fer_level = 0

    product = sac_level * fer_level
    card_name = "骨王之赏" if product >= 2 else "骨王之惠"

    card_def = DEFAULT_REGISTRY.get(card_name)
    if card_def:
        card = card_def.to_game_card(player)
        if len(player.card_hand) < player.card_hand_max:
            player.card_hand.append(card)
        else:
            player.card_dis.append(card)
        print(f"  骨王：弃掉 [{target.name}]（献祭{sac_level}×丰饶{fer_level}={product}），获得 [{card_name}]")
    else:
        print(f"  骨王：找不到 {card_name} 的定义")

    return True

def _guwangzhi_hui_effect(player, target, game, extras=None):
    """骨王之惠：抽一张牌，使其-2T1B。"""
    if not player.card_deck:
        print("  骨王之惠：牌库为空")
        return True
    card = player.card_deck.pop()
    card.cost.t = max(0, card.cost.t - 2)
    card.cost.b += 1
    if len(player.card_hand) < player.card_hand_max:
        player.card_hand.append(card)
        print(f"  骨王之惠：抽出 [{card.name}]，费用变为 {card.cost}")
    else:
        player.card_dis.append(card)
        print(f"  骨王之惠：手牌已满，[{card.name}] 被弃置")
    return True

def _guwangzhi_shang_effect(player, target, game, extras=None):
    """骨王之赏：抽2张牌，免除其献祭点数。"""
    drawn = []
    for _ in range(2):
        if not player.card_deck:
            break
        card = player.card_deck.pop()
        drawn.append(card)

    for card in drawn:
        # 免除献祭点数：将鲜血费用设为0
        card.cost.b = 0
        if len(player.card_hand) < player.card_hand_max:
            player.card_hand.append(card)
            print(f"  骨王之赏：抽出 [{card.name}]，献祭点数已免除")
        else:
            player.card_dis.append(card)
            print(f"  骨王之赏：手牌已满，[{card.name}] 被弃置")
    return True

def _lazhu_effect(player, target, game, extras=None):
    # 获得+6HP（上限+当前）
    player.health_max_change(6)
    player.health_change(6)
    # 抽2张牌
    player.draw_card(2, game=game)
    return True

def _zhiwuxuejia_effect(player, target, game, extras=None):
    from tards.cards import MinionCard
    if not isinstance(target, MinionCard) or target not in player.card_hand:
        return False

    # 弃掉目标异象
    player.card_hand.remove(target)
    player.card_dis.append(target)
    print(f"  植物学家：弃掉 [{target.name}]")

    # 在手牌中查找另一张同名异象
    same_name = [c for c in player.card_hand
                 if isinstance(c, MinionCard) and c.name == target.name]
    if not same_name:
        print(f"  植物学家：手牌中没有另一张 [{target.name}]")
        return True

    buff_card = same_name[0]
    buff_card.attack *= 2
    buff_card.health *= 2
    buff_card.cost.t += 1
    print(f"  植物学家：[{buff_card.name}] 攻防翻倍（{buff_card.attack}/{buff_card.health}），花费+1T")
    return True

def _pimaoshang_effect(player, target, game, extras=None):
    import random
    from tards.cards import MinionCard

    # 阶段1：随机将一张手牌（非自身）洗入卡组
    remaining = [c for c in player.card_hand if c.name != "皮毛商"]
    if remaining:
        chosen = random.choice(remaining)
        player.card_hand.remove(chosen)
        player.card_deck.append(chosen)
        random.shuffle(player.card_deck)
        print(f"  皮毛商：将 [{chosen.name}] 洗入卡组")

    # 阶段2：抉择
    choice = (extras or [None])[0]
    if choice == "抽2张异象":
        minion_cards = [c for c in player.card_deck if isinstance(c, MinionCard)]
        drawn = 0
        for card in minion_cards[:2]:
            player.card_deck.remove(card)
            if len(player.card_hand) < player.card_hand_max:
                player.card_hand.append(card)
            else:
                player.card_dis.append(card)
                print(f"  皮毛商：手牌已满，{card.name} 被弃置")
            drawn += 1
        print(f"  皮毛商：从卡组中抽出 {drawn} 张异象")
    elif choice == "获得4T":
        player.t_point_change(4)
        print(f"  皮毛商：{player.name} 获得 4T")

    return True

def _lieren_effect(player, target, game, extras=None):
    import copy
    import random
    if target not in player.card_hand:
        return False

    # 弃掉目标
    player.card_hand.remove(target)
    player.card_dis.append(target)
    print(f"  猎人：弃掉 [{target.name}]")

    # 复制2张洗入牌库
    for _ in range(2):
        cloned = copy.copy(target)
        player.card_deck.append(cloned)
    random.shuffle(player.card_deck)
    print(f"  猎人：将2张 [{target.name}] 的复制洗入牌库")
    return True

def _yugou_effect(player, target, game, extras=None):
    from tards.cards import Minion
    from card_pools.effect_utils import convert_cost_to_t

    if not isinstance(target, Minion):
        return False

    # 检查费用折算不大于3T
    source_card = getattr(target, "source_card", None)
    if source_card and hasattr(source_card, "cost"):
        cost_t = convert_cost_to_t(source_card.cost)
    else:
        cost_t = 999
    if cost_t > 3:
        print(f"  鱼钩：{target.name} 折算费用 {cost_t}T > 3，无法移动")
        return False

    # 找到友方同一列最靠近前排的空位
    col = target.position[1]
    rows = sorted(player.get_friendly_rows(), key=lambda r: abs(r - 2))
    new_pos = None
    for r in rows:
        pos = (r, col)
        if pos not in game.board.minion_place:
            new_pos = pos
            break

    if new_pos is None:
        print(f"  鱼钩：友方第{col}列没有空位，移动失败")
        return False

    # 转移所有权并跨阵营移动
    target.owner = player
    ok = game.board.move_minion(target, new_pos, allow_cross_side=True)
    if ok:
        print(f"  鱼钩：将 [{target.name}] 转移至 {new_pos}")
    else:
        # 所有权回滚
        opponent = game.p2 if player == game.p1 else game.p1
        target.owner = opponent
        print(f"  鱼钩：移动 [{target.name}] 失败")
    return ok

def _bopidao_effect(player, target, game, extras=None):
    from tards.cards import Minion
    from card_pools.effect_utils import (
        destroy_minion, give_temp_keyword_until_turn_end,
    )
    if not isinstance(target, Minion) or not target.is_alive():
        return False

    if target.keywords.get("迅捷", False):
        destroy_minion(target, game)
        print(f"  剥皮刀：{target.name} 具有迅捷，被消灭")
    else:
        give_temp_keyword_until_turn_end(target, "眩晕", 1)
        print(f"  剥皮刀：{target.name} 被眩晕")
    return True

def _yanping_effect(player, target, game, extras=None):
    from tards.cards import MinionCard
    if not isinstance(target, int) or not (0 <= target < 5):
        return False

    col = target
    # 永久覆盖该列为高地
    if not hasattr(game, "_terrain_overrides"):
        game._terrain_overrides = {}
    for r in range(5):
        game._terrain_overrides[(r, col)] = "高地"
    print(f"  岩瓶：第 {col} 列（{game.board.COL_NAMES[col]}）永久视为高地")

    # 抽一张高地异象
    for i, card in enumerate(player.card_deck):
        if isinstance(card, MinionCard) and card.keywords.get("高地", False):
            player.card_deck.pop(i)
            if len(player.card_hand) < player.card_hand_max:
                player.card_hand.append(card)
            else:
                player.card_dis.append(card)
                print(f"  岩瓶：手牌已满，{card.name} 被弃置")
            print(f"  岩瓶：抽出高地异象 [{card.name}]")
            return True

    print("  岩瓶：卡组中没有高地异象")
    return True

def _lanyue_effect(player, target, game, extras=None):
    from card_pools.effect_utils import on
    from tards.constants import EVENT_PHASE_START, EVENT_PHASE_END

    # 防止多次打出叠加监听器
    if getattr(player, "_lan_yue_active", False):
        print("  蓝月：效果已在生效中")
        return True
    player._lan_yue_active = True
    player._lan_yue_pending = True

    def on_action_start(event_data):
        if event_data.get("phase") != getattr(game, "PHASE_ACTION", "action"):
            return
        if not getattr(player, "_lan_yue_pending", False):
            return
        player._lan_yue_pending = False

        affected = 0
        for m in game.board.minion_place.values():
            if m.owner == player and m.is_alive():
                m._sacrifice_remaining += 1
                m.gain_keyword("献祭", 1, permanent=False)
                m._lan_yue_affected = True
                affected += 1
        if affected:
            print(f"  蓝月：{affected} 个友方异象献祭等级+1")

    def on_resolve_end(event_data):
        if event_data.get("phase") != getattr(game, "PHASE_RESOLVE", "resolve"):
            return
        if not getattr(player, "_lan_yue_active", False):
            return
        player._lan_yue_active = False
        cleaned = 0
        for m in list(game.board.minion_place.values()):
            if getattr(m, "_lan_yue_affected", False):
                m._lan_yue_affected = False

                base = m.base_keywords.get("献祭", 0)
                if base is True:
                    base = 1
                elif not isinstance(base, int):
                    base = 0

                if m._sacrifice_remaining > base:
                    m._sacrifice_remaining -= 1
                    if base >= 1 and m._sacrifice_remaining < 1:
                        m._sacrifice_remaining = 1
                cleaned += 1
        if cleaned:
            print(f"  蓝月效果结束（{cleaned} 个异象）")

    on(EVENT_PHASE_START, on_action_start, game)
    on(EVENT_PHASE_END, on_resolve_end, game)
    return True

def _zhadan_yao_effect(player, target, game, extras=None):
    """炸弹夫人的遥控器：使友方异象获得传染亡语。"""
    from tards.cards import Minion
    from card_pools.effect_utils import add_deathrattle, deal_damage_to_minion
    import random

    if not isinstance(target, Minion) or not target.is_alive():
        print("  炸弹夫人：目标不合法")
        return False

    def _make_deathrattle():
        def _deathrattle(minion, owner, board):
            g = getattr(board, "game_ref", None)
            friends = [m for m in board.minion_place.values() if m.owner == owner and m.is_alive() and m != minion]
            if not friends:
                return
            victim = random.choice(friends)
            deal_damage_to_minion(victim, 2, game=g)
            print(f"  炸弹夫人亡语：{victim.name} 受到2点伤害")
            if victim.is_alive():
                add_deathrattle(victim, _deathrattle)
                print(f"  炸弹夫人亡语：{victim.name} 获得传染亡语")
        return _deathrattle

    add_deathrattle(target, _make_deathrattle())
    print(f"  炸弹夫人：{target.name} 获得传染亡语")
    return True

def _xiangji_effect(player, target, game, extras=None):
    if not isinstance(target, Minion) or not target.is_alive():
        return False

    # 移除场上异象（不触发亡语）
    game.board.remove_minion(target.position)

    # 复制 source_card，所有权转移
    sc = target.source_card
    new_card = MinionCard(
        name=sc.name,
        owner=player,
        cost=sc.cost.copy() if hasattr(sc.cost, "copy") else sc.cost,
        targets=sc.targets,
        attack=sc.attack,
        health=sc.health,
        special=getattr(sc, "special", None),
        keywords=dict(sc.keywords) if hasattr(sc, "keywords") else {},
    )
    # 复制额外属性
    for attr in ("pack", "asset_id", "asset_back_id", "evolve_to",
                 "statue_top", "statue_bottom", "statue_pair",
                 "targets_count", "targets_repeat"):
        if hasattr(sc, attr):
            setattr(new_card, attr, getattr(sc, attr))
    if hasattr(sc, "tags"):
        new_card.tags = list(sc.tags)
    if hasattr(sc, "hidden_keywords"):
        new_card.hidden_keywords = dict(sc.hidden_keywords)
    if hasattr(sc, "extra_targeting_stages"):
        new_card.extra_targeting_stages = list(sc.extra_targeting_stages)
    # 复制回调
    for cb in ("on_turn_start", "on_turn_end", "on_phase_start", "on_phase_end"):
        if hasattr(sc, cb):
            setattr(new_card, cb, getattr(sc, cb))

    if len(player.card_hand) < player.card_hand_max:
        player.card_hand.append(new_card)
        print(f"  相机：将 [{target.name}] 移入 {player.name} 手牌")
    else:
        player.card_dis.append(new_card)
        print(f"  相机：手牌已满，{target.name} 被弃置")
    return True

def _shalou_effect(player, target, game, extras=None):
    import random
    opponent = game.p2 if player == game.p1 else game.p2

    # 随机将对方一张手牌放置至其卡组顶
    if opponent.card_hand:
        chosen = random.choice(opponent.card_hand)
        opponent.card_hand.remove(chosen)
        opponent.card_deck.insert(0, chosen)
        print(f"  沙漏：将 {opponent.name} 的 [{chosen.name}] 放置至其卡组顶")
    else:
        print(f"  沙漏：{opponent.name} 手牌为空")

    # 自己抽1张牌
    player.draw_card(1, game=game)
    return True

def _xueyue_effect(player, target, game, extras=None):
    affected = 0
    for m in game.board.minion_place.values():
        if m.owner == player and m.is_alive():
            m.temp_attack_bonus += 1
            m.temp_keywords["坚韧"] = m.temp_keywords.get("坚韧", 0) + 1
            m.recalculate()
            affected += 1
    if affected:
        print(f"  血月：{affected} 个友方异象+1攻击力，获得坚韧1")
    return True

def _jiaoshui_effect(player, target, game, extras=None):
    from tards.cards import Minion
    from card_pools.effect_utils import on
    from tards.constants import EVENT_BEFORE_DAMAGE, EVENT_AFTER_DAMAGE

    if not isinstance(target, Minion) or not target.is_alive():
        return False

    def protect(event_data):
        if event_data.get("target") is not target:
            return
        damage = event_data.get("damage", 0)
        if damage <= 0:
            return

        # 预判是否致命（考虑坚韧）
        tough = target.keywords.get("坚韧", 0)
        if target.keywords.get("脆弱", False) and tough == 0:
            tough = -1
        actual = max(0, damage - tough) if isinstance(tough, int) else damage
        if target.current_health > actual:
            return

        # +0/1：获得1HP（上限+当前）
        target.gain_health_bonus(1, permanent=True)
        target.current_health += 1
        target._jiaoshui_protected = True
        print(f"  胶水：{target.name} 受到致命伤害，+0/1")

    def check_survival(event_data):
        if event_data.get("target") is not target:
            return
        if not getattr(target, "_jiaoshui_protected", False):
            return
        target._jiaoshui_protected = False
        if target.is_alive():
            target.gain_attack(1, permanent=True)
            target.gain_health_bonus(1, permanent=True)
            target.current_health += 1
            print(f"  胶水：{target.name} 因此存活，+1/1")

    on(EVENT_BEFORE_DAMAGE, protect, game, minion=target)
    on(EVENT_AFTER_DAMAGE, check_survival, game, minion=target)
    print(f"  胶水：{target.name} 获得致命伤害保护")
    return True

def _shizhong_effect(player, target, game, extras=None):
    from tards.cards import MinionCard, Minion
    from card_pools.effect_utils import on, empty_positions
    from tards.constants import EVENT_PHASE_START
    import random

    if not isinstance(target, MinionCard) or target not in player.card_hand:
        return False

    # 弃掉目标
    player.card_hand.remove(target)
    player.card_dis.append(target)

    target_turn = game.current_turn + 3
    if not hasattr(player, "_shizhong_delayed"):
        player._shizhong_delayed = []
    player._shizhong_delayed.append({"turn": target_turn, "card": target})
    print(f"  时钟：弃掉 [{target.name}]，将在第 {target_turn} 回合抽牌阶段加入战场")

    def on_draw_phase(event_data):
        if event_data.get("phase") != getattr(game, "PHASE_DRAW", "draw"):
            return
        delayed = getattr(player, "_shizhong_delayed", [])
        to_deploy = [d for d in delayed if d["turn"] == game.current_turn]
        if not to_deploy:
            return

        for entry in to_deploy:
            card = entry["card"]
            empties = empty_positions(player, game.board)
            valid = [pos for pos in empties if game.board.is_valid_deploy(pos, player, card)]
            if not valid:
                print(f"  时钟：无合法空位部署 {card.name}")
                continue

            pos = random.choice(valid)
            minion = Minion(
                name=card.name,
                owner=player,
                position=pos,
                attack=card.attack,
                health=card.health,
                source_card=card,
                board=game.board,
                keywords=dict(card.keywords) if hasattr(card, "keywords") else {},
                on_turn_start=getattr(card, "on_turn_start", None),
                on_turn_end=getattr(card, "on_turn_end", None),
                on_phase_start=getattr(card, "on_phase_start", None),
                on_phase_end=getattr(card, "on_phase_end", None),
                tags=list(card.tags) if hasattr(card, "tags") else [],
                hidden_keywords=dict(card.hidden_keywords) if hasattr(card, "hidden_keywords") else {},
            )
            if hasattr(card, "statue_top"):
                minion.statue_top = card.statue_top
            if hasattr(card, "statue_bottom"):
                minion.statue_bottom = card.statue_bottom
            if hasattr(card, "statue_pair"):
                minion.statue_pair = card.statue_pair
            game.board.place_minion(minion, pos)
            print(f"  时钟：{card.name} 加入战场 {pos}")

        player._shizhong_delayed = [d for d in delayed if d["turn"] != game.current_turn]

    if not getattr(player, "_shizhong_listener_registered", False):
        on(EVENT_PHASE_START, on_draw_phase, game)
        player._shizhong_listener_registered = True

    return True

def _yinghuo_effect(player, target, game, extras=None):
    from tards.cards import MinionCard
    if not isinstance(target, MinionCard) or target not in player.card_hand:
        return False

    # +2/3（永久修改卡牌面板）
    target.attack += 2
    target.health += 3

    # 添加亡语：对方抽一张牌
    def deathrattle(minion, owner, board):
        opponent = game.p1 if owner == game.p2 else game.p2
        opponent.draw_card(1, game=game)
        print(f"  {minion.name} 亡语：{opponent.name} 抽1张牌")

    target.keywords["亡语"] = deathrattle
    print(f"  营火：{target.name} 获得+2/3和亡语（对方抽牌）")
    return True

def _bingkuai_effect(player, target, game, extras=None):
    from tards.cards import Minion
    from card_pools.effect_utils import on
    from tards.constants import EVENT_PHASE_END

    if not isinstance(target, Minion) or not target.is_alive() or target.owner != player:
        return False

    # +0/4 永久
    target.base_max_health_bonus += 4
    target.current_health += 4
    target.recalculate()

    # 冰冻2回合
    target.base_keywords["冰冻"] = 2

    # 坚韧I（冰冻期间生效）
    target.base_keywords["坚韧"] = 1
    target.recalculate()

    def on_resolve_end(event_data):
        if event_data.get("phase") != getattr(game, "PHASE_RESOLVE", "resolve"):
            return
        frozen = target.keywords.get("冰冻", 0)
        if not isinstance(frozen, int) or frozen <= 0:
            # 冰冻已解除，移除坚韧
            target.base_keywords.pop("坚韧", None)
            target.perm_keywords.pop("坚韧", None)
            target.temp_keywords.pop("坚韧", None)
            target.recalculate()
            print(f"  冰块：{target.name} 冰冻解除，坚韧消失")

    on(EVENT_PHASE_END, on_resolve_end, game, minion=target)
    print(f"  冰块：{target.name} +0/4，冰冻2回合，坚韧I")
    return True

def _mudiaoshi_effect(player, target, game, extras=None):
    # 开发一张座首
    top_defs = [c for c in DEFAULT_REGISTRY.all_cards() if getattr(c, "statue_top", False)]
    if top_defs:
        game.develop_card(player, top_defs, count=min(3, len(top_defs)))
        print("  木雕师：开发一张座首")
    else:
        print("  木雕师：无可用座首")

    # 开发一张底座
    bottom_defs = [c for c in DEFAULT_REGISTRY.all_cards() if getattr(c, "statue_bottom", False)]
    if bottom_defs:
        game.develop_card(player, bottom_defs, count=min(3, len(bottom_defs)))
        print("  木雕师：开发一张底座")
    else:
        print("  木雕师：无可用底座")

    return True

def _muqi_effect(player, target, game, extras=None):
    if not target.is_alive() or target.owner != player:
        return False
    if not (getattr(target, "statue_top", False) or getattr(target, "statue_bottom", False)):
        return False

    target.gain_health_bonus(6, permanent=True)
    target.current_health += 6
    target.base_keywords["绝缘"] = True
    target.recalculate()
    print(f"  木漆：{target.name} +6HP，获得绝缘")
    return True

def _make_effect(player, target, game, extras=None):
    def filter_fn(t, damage, source):
        return t is target

    def replace_fn(damage):
        return 0

    game.add_damage_replacement(filter_fn, replace_fn, once=True, reason="玛珂")

    if isinstance(target, Minion):
        player.draw_card(1, game=game)
        print(f"  玛珂：{target.name} 免疫下次伤害，{player.name} 抽1张牌")
    else:
        print(f"  玛珂：{getattr(target, 'name', str(target))} 免疫下次伤害")
    return True

def _hanji_effect(player, target, game, extras=None):
    """旱季：对所有陆地异象造成3点伤害，然后使所有陆地异象+1/+2。失去1个T槽。"""
    board = game.board
    from card_pools.effect_utils import deal_damage_to_minion

    def _get_land_minions():
        seen = set()
        result = []
        for m in list(board.minion_place.values()) + list(board.cell_underlay.values()):
            if m.is_alive() and m.position[1] != 4 and id(m) not in seen:
                result.append(m)
                seen.add(id(m))
        return result

    land_minions = _get_land_minions()
    for m in land_minions:
        deal_damage_to_minion(m, 3, game=game)
        print(f"  旱季：对 {m.name} 造成3点伤害")

    for m in _get_land_minions():
        m.gain_attack(1, permanent=True)
        m.gain_health_bonus(2, permanent=True)
        print(f"  旱季：{m.name} +1/+2")

    player.t_point_max_change(-1)
    print(f"  旱季：{player.name} 失去1个T槽")
    return True

def _shanhong_effect(player, target, game, extras=None):
    """山洪：使一列陆地算作水路直到下回合结束。失去1个T槽。"""
    if not isinstance(target, int) or not (0 <= target <= 3):
        print("  山洪：目标列不合法")
        return False

    col = target
    from card_pools.effect_utils import register_terrain_enforcement
    register_terrain_enforcement(game, col, "水路", game.current_turn + 1)
    print(f"  山洪：第 {col} 列（{game.board.COL_NAMES[col]}）被视为水路，直到下回合结束")

    player.t_point_max_change(-1)
    print(f"  山洪：{player.name} 失去1个T槽")
    return True

def _shuiyi_effect(player, target, game, extras=None):
    """水疫：若水路（列4）有敌方异象，对所有敌方异象造成1点伤害；若有异象被消灭，重复。"""
    opponent = game.p2 if player == game.p1 else game.p1
    board = game.board
    from card_pools.effect_utils import deal_damage_to_minion

    iteration = 0
    while True:
        iteration += 1
        # 检查水路是否有敌方异象
        water_enemies = board.get_enemy_minions_in_column(4, player)
        if not water_enemies:
            print(f"  水疫（第{iteration}轮）：水路无敌方异象，效果结束")
            break

        # 收集所有当前敌方异象（包含新召唤的）
        all_enemies = []
        seen = set()
        for m in list(board.minion_place.values()) + list(board.cell_underlay.values()):
            if m.is_alive() and m.owner == opponent and id(m) not in seen:
                all_enemies.append(m)
                seen.add(id(m))

        if not all_enemies:
            print(f"  水疫（第{iteration}轮）：无敌方异象可伤害")
            break

        any_killed = False
        for m in all_enemies:
            before_alive = m.is_alive()
            deal_damage_to_minion(m, 1, game=game)
            if before_alive and not m.is_alive():
                any_killed = True

        print(f"  水疫（第{iteration}轮）：对 {len(all_enemies)} 个敌方异象造成1点伤害")

        if not any_killed:
            print(f"  水疫（第{iteration}轮）：无异象被消灭，效果结束")
            break

    return True

def _shachen_effect(player, target, game, extras=None):
    """沙尘：眩晕一个敌方异象。若本回合对方先手，结束双方出牌阶段。"""
    from card_pools.effect_utils import give_temp_keyword_until_turn_end
    from tards.cards import Minion

    if not isinstance(target, Minion) or not target.is_alive():
        print("  沙尘：目标不合法")
        return False

    give_temp_keyword_until_turn_end(target, "眩晕", 1)
    print(f"  沙尘：{target.name} 被眩晕")

    # 判断本回合对方是否先手
    first = game.p1 if game.current_turn % 2 == 1 else game.p2
    if first != player:
        # 对方先手，结束双方出牌阶段
        game.p1.braked = True
        game.p2.braked = True
        print(f"  沙尘：本回合对方先手，双方出牌阶段结束")

    return True

def _kuangfeng_effect(player, target, game, extras=None):
    """狂风：对方无法部署异象，直到下一个出牌阶段结束。"""
    opponent = game.p2 if player == game.p1 else game.p1

    def _restriction_fn(p, card):
        if p == opponent:
            return False
        return True

    game._global_deploy_restrictions.append(_restriction_fn)
    print(f"  狂风：{opponent.name} 无法部署异象，直到下回合结束")

    # 下回合结束时移除限制
    def _cleanup():
        if _restriction_fn in game._global_deploy_restrictions:
            game._global_deploy_restrictions.remove(_restriction_fn)
            print(f"  狂风：{opponent.name} 的部署限制已解除")

    game._delayed_effects.append({
        "trigger": "turn_end",
        "turn": game.current_turn + 1,
        "fn": _cleanup,
    })
    return True

def _gaozhi_effect(player, target, game, extras=None):
    opponent = game.p2 if player == game.p1 else game.p1
    player.t_point_max_change(1)
    opponent.t_point_max_change(-1)
    print(f"  稿纸：{player.name} 获得1T槽，{opponent.name} 失去1T槽")
    return True

def _zhouyu_effect(player, target, game, extras=None):
    """骤雨：将1个异象返回其所有者手牌。对手下回合无法抽牌。"""
    from card_pools.effect_utils import return_minion_to_hand

    if not isinstance(target, Minion) or not target.is_alive():
        print("  骤雨：目标不合法")
        return False

    return_minion_to_hand(target, game)
    print(f"  骤雨：{target.name} 返回其所有者手牌")

    opponent = game.p2 if player == game.p1 else game.p1
    opponent._skip_next_draw = True
    print(f"  骤雨：{opponent.name} 下回合无法抽牌")
    return True

def _fansheng_effect(player, target, game, extras=None):
    """繁盛：弃掉所有手牌，获得'抽牌阶段多抽1张'。"""
    from card_pools.effect_utils import on
    from tards.constants import EVENT_PHASE_START

    # 弃掉所有手牌
    discarded = list(player.card_hand)
    player.card_hand.clear()
    player.card_dis.extend(discarded)
    if discarded:
        names = ", ".join([c.name for c in discarded])
        print(f"  繁盛：{player.name} 弃掉 {len(discarded)} 张手牌（{names}）")
    else:
        print(f"  繁盛：{player.name} 手牌为空")

    # 注册一次性抽牌阶段监听器
    def _extra_draw(event_data):
        if event_data.get("phase") != game.PHASE_DRAW:
            return
        draw_player = event_data.get("player")
        if draw_player and draw_player != player:
            return
        # 检查是否已触发过
        if getattr(player, "_fansheng_triggered", False):
            return
        player._fansheng_triggered = True
        player.draw_card(1, game=game)
        print(f"  繁盛：{player.name} 额外抽1张牌")

    player._fansheng_triggered = False
    on(EVENT_PHASE_START, _extra_draw, game)
    print(f"  繁盛：{player.name} 获得'抽牌阶段多抽1张'")
    return True

def _tudao_effect(player, target, game, extras=None):
    """屠刀：将2张'松鼠'加入手牌。本回合，你每献祭一个异象，抽一张牌。"""
    from tards.constants import EVENT_SACRIFICE

    # 加入2张松鼠
    squirrel_count = 0
    for _ in range(2):
        if player.squirrel_deck:
            card = player.squirrel_deck.pop()
            if len(player.card_hand) < player.card_hand_max:
                player.card_hand.append(card)
                squirrel_count += 1
            else:
                player.card_dis.append(card)
                print(f"  屠刀：手牌已满，松鼠被弃置")
        else:
            # squirrel_deck 空了，从 registry 创建
            squirrel_def = DEFAULT_REGISTRY.get("松鼠")
            if squirrel_def:
                card = squirrel_def.to_game_card(player)
                if len(player.card_hand) < player.card_hand_max:
                    player.card_hand.append(card)
                    squirrel_count += 1
                else:
                    player.card_dis.append(card)
                    print(f"  屠刀：手牌已满，松鼠被弃置")
    print(f"  屠刀：{player.name} 将 {squirrel_count} 张松鼠加入手牌")

    # 注册献祭监听器
    def on_sacrifice(event_data):
        if event_data.get("player") == player:
            player.draw_card(1, game=game)
            print(f"  屠刀：{player.name} 献祭抽1张牌")

    owner_id = game.event_bus.register(EVENT_SACRIFICE, on_sacrifice)

    # 本回合结束时注销
    def cleanup():
        game.event_bus.unregister_by_owner(owner_id)
        print(f"  屠刀：献祭抽牌效果结束")

    game._delayed_effects.append({
        "trigger": "turn_end",
        "turn": game.current_turn,
        "fn": cleanup,
    })

    return True

def _zhenban_effect(player, target, game, extras=None):
    """砧板：弃一张牌，抽一张花费更高的牌。若弃牌献祭等级×丰饶等级≥2，获得2B。"""
    if target not in player.card_hand:
        print("  砧板：目标不在手牌中")
        return False

    # 弃掉选中的牌
    player.card_hand.remove(target)
    player.card_dis.append(target)
    print(f"  砧板：{player.name} 弃掉 [{target.name}]")

    # 计算弃牌总费用
    def _cost_total(cost):
        return cost.t + cost.c + cost.b + cost.s + cost.ct + sum(cost.minerals.values())

    discarded_cost = _cost_total(target.cost)

    # 从牌库顶找第一张费用更高的牌
    drawn = None
    for i, card in enumerate(player.card_deck):
        if _cost_total(card.cost) > discarded_cost:
            drawn = player.card_deck.pop(i)
            break

    if drawn:
        if len(player.card_hand) < player.card_hand_max:
            player.card_hand.append(drawn)
            print(f"  砧板：抽出更高费牌 [{drawn.name}]")
        else:
            player.card_dis.append(drawn)
            print(f"  砧板：手牌已满，[{drawn.name}] 被弃置")
    else:
        print("  砧板：牌库中没有更高费的牌")

    # 计算献祭等级 × 丰饶等级
    sacrifice_kw = getattr(target, "keywords", {}).get("献祭", False)
    if sacrifice_kw is True:
        sacrifice_level = 1
    elif isinstance(sacrifice_kw, int):
        sacrifice_level = sacrifice_kw
    else:
        sacrifice_level = 0

    feng_rang_kw = getattr(target, "keywords", {}).get("丰饶", False)
    if feng_rang_kw is True:
        feng_rang_level = 1
    elif isinstance(feng_rang_kw, int):
        feng_rang_level = feng_rang_kw
    else:
        feng_rang_level = 0

    if sacrifice_level * feng_rang_level >= 2:
        player.b_point += 2
        print(f"  砧板：{player.name} 获得 2B（献祭{sacrifice_level}×丰饶{feng_rang_level}={sacrifice_level * feng_rang_level}）")

    return True

def _haichen_effect(player, target, game, extras=None):
    """还尘：消灭一个受伤异象。若是友方异象，抽三张牌。"""
    from tards.cards import Minion
    from card_pools.effect_utils import destroy_minion

    if not isinstance(target, Minion) or not target.is_alive():
        print("  还尘：目标不合法")
        return False

    if target.current_health >= target.max_health:
        print("  还尘：目标未受伤")
        return False

    destroy_minion(target, game)
    print(f"  还尘：消灭受伤异象 {target.name}")

    if target.owner == player:
        player.draw_card(3, game=game)
        print(f"  还尘：{player.name} 抽3张牌（友方异象）")

    return True

def _jidai_effect(player, target, game, extras=None):
    """继代：使一个异象获得亡语，将其-1/1的复制加入你的手牌。"""
    from tards.cards import Minion
    from card_pools.effect_utils import add_deathrattle

    if not isinstance(target, Minion) or not target.is_alive():
        print("  继代：目标不合法")
        return False

    def _deathrattle(minion, owner, board):
        sc = minion.source_card
        new_card = MinionCard(
            name=sc.name,
            owner=owner,
            cost=sc.cost.copy(),
            targets=sc.targets,
            attack=max(0, sc.attack - 1),
            health=max(1, sc.health - 1),
            special=getattr(sc, "special", None),
            keywords=dict(sc.keywords) if hasattr(sc, "keywords") else {},
        )
        if hasattr(sc, "tags"):
            new_card.tags = list(sc.tags)
        if hasattr(sc, "hidden_keywords"):
            new_card.hidden_keywords = dict(sc.hidden_keywords)
        for attr in ("statue_top", "statue_bottom", "statue_pair"):
            if hasattr(sc, attr):
                setattr(new_card, attr, getattr(sc, attr))
        if len(owner.card_hand) < owner.card_hand_max:
            owner.card_hand.append(new_card)
            print(f"  继代亡语：{new_card.name}({new_card.attack}/{new_card.health}) 加入 {owner.name} 手牌")
        else:
            owner.card_dis.append(new_card)
            print(f"  继代亡语：手牌已满，{new_card.name} 被弃置")

    add_deathrattle(target, _deathrattle)
    print(f"  继代：{target.name} 获得亡语")
    return True

def _yehuo_effect(player, target, game, extras=None):
    """野火：弃1张牌，将1个异象返回其所有者牌库顶，眩晕周围异象。"""
    from card_pools.effect_utils import get_adjacent_positions, give_temp_keyword_until_turn_end
    from card_pools.effect_utils import place_at_deck_top
    from tards.cards import Minion

    # 阶段1：弃牌
    if target not in player.card_hand:
        print("  野火：弃牌目标不在手牌中")
        return False
    player.card_hand.remove(target)
    player.card_dis.append(target)
    print(f"  野火：{player.name} 弃掉 [{target.name}]")

    # 阶段2：选异象
    minion_target = (extras or [None])[0]
    if not isinstance(minion_target, Minion) or not minion_target.is_alive():
        print("  野火：异象目标不合法")
        return False

    owner = minion_target.owner
    pos = minion_target.position
    sc = minion_target.source_card

    # 从场上移除
    game.board.remove_minion(pos)
    print(f"  野火：{minion_target.name} 从场上移除")

    # 将 source_card 放入所有者牌库顶
    place_at_deck_top(owner, [sc])
    print(f"  野火：{sc.name} 返回 {owner.name} 牌库顶")

    # 眩晕周围异象
    adj_positions = get_adjacent_positions(pos, game.board)
    for adj_pos in adj_positions:
        m = game.board.get_minion_at(adj_pos)
        if m and m.is_alive():
            give_temp_keyword_until_turn_end(m, "眩晕", 1)
            print(f"  野火：{m.name} 被眩晕")

    return True

def _lunhui_effect(player, target, game, extras=None):
    """轮回：弃1张牌，抽1张。若弃掉回响，对目标造成4点伤害。"""
    from card_pools.effect_utils import deal_damage_to_minion, deal_damage_to_player
    from tards.cards import Minion

    if target not in player.card_hand:
        print("  轮回：目标不在手牌中")
        return False

    # 弃牌
    player.card_hand.remove(target)
    player.card_dis.append(target)
    print(f"  轮回：{player.name} 弃掉 [{target.name}]")

    # 抽1张
    player.draw_card(1, game=game)
    print(f"  轮回：{player.name} 抽1张牌")

    # 若弃掉回响，造成4点伤害
    if target.keywords.get("回响", False):
        dmg_target = (extras or [None])[0]
        if isinstance(dmg_target, Minion) and dmg_target.is_alive():
            deal_damage_to_minion(dmg_target, 4, game=game)
            print(f"  轮回：{dmg_target.name} 受到4点伤害")
        elif dmg_target is player or dmg_target is (game.p2 if player == game.p1 else game.p1):
            deal_damage_to_player(dmg_target, 4, game=game)
            print(f"  轮回：{dmg_target.name} 受到4点伤害")
        else:
            print("  轮回：伤害目标不合法")

    return True

def _gengti_effect(player, target, game, extras=None):
    """更替：使手牌中的1个回响异象回响等级+1。"""
    from tards.cards import MinionCard

    if not isinstance(target, MinionCard) or target not in player.card_hand:
        print("  更替：目标不合法")
        return False

    if not (target.keywords.get("回响", False) or getattr(target, "echo_level", 0) > 0):
        print("  更替：目标不是回响异象")
        return False

    # 增加回响等级
    target.echo_level = getattr(target, "echo_level", 0) + 1
    # 同步更新关键词
    if "回响" in target.keywords:
        current = target.keywords["回响"]
        if isinstance(current, int):
            target.keywords["回响"] = current + 1
        elif current is True:
            target.keywords["回响"] = 2
    else:
        target.keywords["回响"] = target.echo_level

    print(f"  更替：{target.name} 回响等级+1（当前 {target.echo_level}）")
    return True

def _poxiao_effect(player, target, game, extras=None):
    """破晓：抽2张牌。若剩余T点≤1，获得两倍于本对局失去T槽数的T点。"""
    player.draw_card(2, game=game)
    print(f"  破晓：{player.name} 抽2张牌")

    if player.t_point <= 1:
        total_lost = sum(
            entry.get("amount", 0)
            for entry in getattr(game, "_state_log", [])
            if entry.get("event") == "t_max_lost" and entry.get("player") == player
        )
        gain = total_lost * 2
        if gain > 0:
            player.t_point_change(gain)
            print(f"  破晓：{player.name} 剩余T点≤1，获得 {gain}T（失去过{total_lost}个T槽）")
        else:
            print(f"  破晓：{player.name} 剩余T点≤1，但未失去过T槽")

    return True

def _liulinfengsheng_effect(player, target, game, extras=None):
    """柳林风声：弃1异象，将5T复制加入对方手牌。对方部署其它异象时，复制卡加入友方区域。"""
    from tards.cards import MinionCard, Minion
    from tards.cost import Cost
    from card_pools.effect_utils import empty_positions
    import random

    if not isinstance(target, MinionCard) or target not in player.card_hand:
        print("  柳林风声：目标不在手牌中")
        return False

    # 弃掉
    player.card_hand.remove(target)
    player.card_dis.append(target)
    print(f"  柳林风声：{player.name} 弃掉 [{target.name}]")

    opponent = game.p2 if player == game.p1 else game.p1

    # 创建5T复制卡
    shadow_card = MinionCard(
        name=target.name,
        owner=opponent,
        cost=Cost(t=5),
        targets=target.targets,
        attack=target.attack,
        health=target.health,
        special=target.special,
        keywords=dict(target.keywords) if target.keywords else {},
    )
    shadow_card.pack = getattr(target, "pack", None)
    shadow_card._liulin_shadow = True

    if len(opponent.card_hand) < opponent.card_hand_max:
        opponent.card_hand.append(shadow_card)
        print(f"  柳林风声：{shadow_card.name}(5T) 加入 {opponent.name} 手牌")
    else:
        opponent.card_dis.append(shadow_card)
        print(f"  柳林风声：{opponent.name} 手牌已满，复制卡被弃置")
        return True

    # deploy_hook：对方部署异象时触发
    def deploy_hook(minion):
        sc = getattr(minion, "source_card", None)
        # 检查是否是复制卡本身被部署
        if sc is shadow_card or getattr(sc, "_liulin_shadow", False):
            if deploy_hook in game.deploy_hooks:
                game.deploy_hooks.remove(deploy_hook)
            print(f"  柳林风声：{opponent.name} 手动部署了复制卡，效果不触发")
            return

        # 对方部署了其它异象，将复制卡加入友方区域
        if shadow_card in opponent.card_hand:
            opponent.card_hand.remove(shadow_card)
            valid_positions = empty_positions(player, game.board)
            if valid_positions:
                deploy_pos = random.choice(valid_positions)
                shadow_minion = Minion(
                    name=shadow_card.name,
                    owner=player,
                    position=deploy_pos,
                    attack=shadow_card.attack,
                    health=shadow_card.health,
                    source_card=shadow_card,
                    board=game.board,
                    keywords=dict(shadow_card.keywords) if shadow_card.keywords else {},
                )
                game.board.place_minion(shadow_minion, deploy_pos)
                shadow_minion.summon_turn = game.current_turn
                print(f"  柳林风声：{shadow_card.name} 加入 {player.name} 友方区域 {deploy_pos}")
            else:
                print(f"  柳林风声：{player.name} 友方区域无空位，复制卡被弃置")
        else:
            print(f"  柳林风声：复制卡已不在 {opponent.name} 手牌中")

        # 只触发一次，移除钩子
        if deploy_hook in game.deploy_hooks:
            game.deploy_hooks.remove(deploy_hook)

    game.deploy_hooks.append(deploy_hook)
    print(f"  柳林风声：已注册部署钩子")
    return True

def _hesheng_effect(player, target, game, extras=None):
    """贺胜：展示牌库顶4张，抽取最高费的一张，使其花费为0T。"""
    from card_pools.effect_utils import peek_deck_top, place_at_deck_bottom
    from tards.cost import Cost

    candidates = peek_deck_top(player, 4)
    if not candidates:
        print("  贺胜：牌库为空")
        return True

    # 展示
    names = ", ".join([f"[{c.name}]" for c in candidates])
    print(f"  贺胜：{player.name} 牌库顶展示 {len(candidates)} 张：{names}")

    # 找最高费
    def _cost_total(card):
        c = card.cost
        return c.t + c.c + c.b + c.s + c.ct + sum(c.minerals.values())

    best = max(candidates, key=_cost_total)
    print(f"  贺胜：最高费为 [{best.name}]")

    # 费用T设为0
    best.cost.t = 0
    print(f"  贺胜：[{best.name}] T花费设为 0")

    # 从牌库移除并加入手牌
    player.card_deck.remove(best)
    if len(player.card_hand) < player.card_hand_max:
        player.card_hand.append(best)
        print(f"  贺胜：[{best.name}] 加入手牌")
    else:
        player.card_dis.append(best)
        print(f"  贺胜：手牌已满，[{best.name}] 被弃置")

    # 其余置底
    remaining = [c for c in candidates if c is not best]
    if remaining:
        place_at_deck_bottom(player, remaining)

    return True

def _shanqian_effect(player, target, game, extras=None):
    """善潜：使一个异象立刻成长，然后+1/+1。"""
    from tards.cards import Minion

    if not isinstance(target, Minion) or not target.is_alive():
        print("  善潜：目标不合法")
        return False

    pos = target.position
    success = target.evolve(game)
    if success:
        new_minion = game.board.get_minion_at(pos)
        if new_minion and new_minion.is_alive():
            new_minion.gain_attack(1, permanent=True)
            new_minion.gain_health_bonus(1, permanent=True)
            print(f"  善潜：{new_minion.name} +1/+1")
    else:
        print(f"  善潜：{target.name} 无法成长")

    return True

def _culi_effect(player, target, game, extras=None):
    """粗粝：使1个异象获得：成长时，+2/2。"""
    from tards.cards import Minion

    if not isinstance(target, Minion) or not target.is_alive():
        print("  粗粝：目标不合法")
        return False

    target._on_evolve_buff = (2, 2)
    print(f"  粗粝：{target.name} 获得成长时+2/+2")
    return True
# =============================================================================
# 迁移的 lambda 效果 (underworld)
# =============================================================================

def _fushu_special(p, t, g, extras=None):
    return g.develop_card(p, p.original_deck_defs)

def _biyi_special(p, t, g, extras=None):
    return g.develop_card(p, [c for c in DEFAULT_REGISTRY.all_cards() if c.pack == Pack.UNDERWORLD and c.card_type == CardType.CONSPIRACY])

def _jinyangpi_effect(p, t, g, extras=None):
    return g.develop_card(p, [c for c in DEFAULT_REGISTRY.all_cards() if c.pack == Pack.UNDERWORLD and c.rarity == Rarity.GOLD and c.card_type == CardType.MINION])

def _shudong_targets(player, board):
    from card_pools.effect_utils import empty_positions
    return empty_positions(player, board)




def _pimaoshang_choice(player, board):
    return ["抽2张异象", "获得4T"]




def _lieren_targets(player, board):
    return player.card_hand[:]




def _yanping_targets(player, board):
    return list(range(board.SIZE))




def _shalou_cost_modifier(card, cost):
    owner = getattr(card, "owner", None)
    if owner and len(owner.card_hand) <= 3:
        cost.t = max(0, cost.t - 2)




def _shizhong_targets(player, board):
    from tards.cards import MinionCard
    from card_pools.effect_utils import convert_cost_to_t
    return [c for c in player.card_hand
            if isinstance(c, MinionCard) and convert_cost_to_t(c.cost) <= 7]




def _muqi_targets(player, board):
    return [m for m in board.minion_place.values()
            if m.owner == player and m.is_alive()
            and (getattr(m, "statue_top", False) or getattr(m, "statue_bottom", False))]




def _make_targets(player, board):
    from tards.cards import Minion
    minions = [m for m in board.minion_place.values() if isinstance(m, Minion)]
    opponent = None
    if board.game_ref:
        opponent = board.game_ref.p2 if player == board.game_ref.p1 else board.game_ref.p1
    return minions + ([opponent] if opponent else [])




def _shanhong_targets(player, board):
    """山洪：选择一列陆地（0-3）。"""
    return [0, 1, 2, 3]










def _gaozhi_cost_modifier(card, cost):
    player = getattr(card, "owner", None)
    if not player:
        return
    game = getattr(getattr(player, "board_ref", None), "game_ref", None)
    if not game:
        return
    deployed = getattr(game, "_deployed_this_turn", {})
    count = len(deployed.get(player, []))
    if count > 0:
        cost.t = max(0, cost.t - count)
        print(f"  稿纸费用：本回合部署 {count} 个异象，费用-{count}T")






def _zhenban_targets(player, board):
    """砧板：选择手牌中的一张牌。"""
    return player.card_hand




def _haichen_targets(player, board):
    """还尘：选择任意一个受伤异象。"""
    result = []
    seen = set()
    for m in list(board.minion_place.values()) + list(board.cell_underlay.values()):
        if m.is_alive() and m.current_health < m.max_health and id(m) not in seen:
            result.append(m)
            seen.add(id(m))
    return result




def _yehuo_targets(player, board):
    """野火：选择手牌中的一张牌弃掉。"""
    return player.card_hand


def _yehuo_minion_choice(player, board):
    """野火：选择场上一个异象返回其所有者牌库顶。"""
    result = []
    seen = set()
    for m in list(board.minion_place.values()) + list(board.cell_underlay.values()):
        if m.is_alive() and id(m) not in seen:
            result.append(m)
            seen.add(id(m))
    return result




def _lunhui_targets(player, board):
    """轮回：选择手牌中的一张牌弃掉。"""
    return player.card_hand


def _lunhui_target_choice(player, board):
    """轮回：若弃掉回响，选择一个目标（敌方异象或敌方玩家）造成4点伤害。"""
    opponent = player.board_ref.game_ref.p2 if player == player.board_ref.game_ref.p1 else player.board_ref.game_ref.p1
    targets = []
    for m in list(board.minion_place.values()) + list(board.cell_underlay.values()):
        if m.is_alive() and m.owner == opponent:
            targets.append(m)
    targets.append(opponent)
    return targets




def _gengti_targets(player, board):
    """更替：选择手牌中的一个回响异象。"""
    from tards.cards import MinionCard
    result = []
    for card in player.card_hand:
        if isinstance(card, MinionCard) and (card.keywords.get("回响", False) or getattr(card, "echo_level", 0) > 0):
            result.append(card)
    return result




def _liulinfengsheng_targets(player, board):
    """柳林风声：选择手牌中的一个异象弃掉。"""
    from tards.cards import MinionCard
    return [c for c in player.card_hand if isinstance(c, MinionCard)]




