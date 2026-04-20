# 冥刻卡包复杂效果辅助函数
# 该文件不被 translate_packs.py 覆盖，供 underworld.py 引用

from card_pools.effect_decorator import special, strategy
from card_pools.effect_utils import (
    add_deathrattle,
    buff_minion,
    create_card_by_name,
    deal_damage_to_minion,
    deal_damage_to_player,
    destroy_minion,
    draw_cards,
    draw_cards_of_type,
    gain_keyword,
    gain_resource,
    heal_minion,
    initiate_combat,
    on,
    on_before_attack,
    redirect_damage,
    return_minion_to_hand,
)

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
]


def _arthropod_top_effect(game, top):
    for m in game.board.get_minions_of_player(top.owner):
        if "昆虫" in getattr(m, "tags", []):
            m.base_keywords["亡语"] = True
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
            m.base_keywords["丰饶"] = m.base_keywords.get("丰饶", 1) + 1
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
            from tards.cards import MinionCard
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
        from tards.cards import MinionCard
        for name in list(m._recorded_echoes):
            m._recorded_echoes.remove(name)
            from tards.cost import Cost
            from tards.cards import MinionCard
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

def _zhuyan_special(minion, player, game, extras=None):
    """烛烟：亡语：抽1张牌。"""
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
    """大团烛烟：亡语：抽2张牌。"""
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
        if not target.is_alive():
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
