#!/usr/bin/env python3
"""效果实现标准工具库（EffectUtils）。

所有人工编写的 special_fn / effect_fn **必须优先使用**本库的 API。
禁止直接调用底层方法（如 board.remove_minion()）来模拟"返回手牌"等行为——
请使用本库提供的标准函数，以确保边界情况（手牌满、死亡触发、状态清理等）
被统一处理。

扩展指南：
  - 新增效果类别时，在本文件底部新增分区并添加函数。
  - 保持统一的参数风格：(target, amount, game=None, ...)。
  - 所有函数在非法参数时打印警告日志并返回安全的哨兵值（None/False/[]），
    禁止向外抛异常中断 EffectQueue。
"""

from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional, Tuple, Union

if TYPE_CHECKING:
    from tards.cards import Card, Minion, MinionCard
    from tards.cost import Cost
    from tards.game import Game
    from tards.player import Player
    from tards.board import Board


# =============================================================================
# 附魔书开发卡池（离散卡包）
# =============================================================================

ENCHANTED_BOOK_POOL = [
    "多重射击",
    "冰霜行者",
    "火矢",
    "横扫之刃",
    "饵钓",
    "锋利",
    "忠诚",
    "击退",
    "时运",
    "深海探索者",
    "耐久",
    "保护",
    "精准采集",
    "效率",
    "经验修补",
]


def get_enchanted_book_definitions() -> List[Any]:
    """获取附魔书开发池中的所有卡牌定义（已过滤掉注册表中不存在的）。"""
    from tards.card_db import DEFAULT_REGISTRY
    result = []
    for name in ENCHANTED_BOOK_POOL:
        card_def = DEFAULT_REGISTRY.get(name)
        if card_def:
            result.append(card_def)
    return result


# =============================================================================
# 1. 伤害与治疗
# =============================================================================

def deal_damage_to_minion(
    target: "Minion",
    damage: int,
    source: Optional["Minion"] = None,
    game: Optional["Game"] = None,
) -> int:
    """对异象造成标准【伤害】。

    依次触发：伤害替换 → 藤蔓替伤 → 坚韧/破甲/脆弱 → 冰冻 → 实际扣血。
    返回实际造成的伤害值（经过所有减免后的正值）。
    """
    if damage <= 0:
        return 0
    if not target.is_alive():
        print(f"  [警告] deal_damage_to_minion 目标 {target.name} 已死亡")
        return 0
    before_hp = target.health
    target.take_damage(damage, source)
    actual = max(0, before_hp - max(0, target.health))
    return actual


def deal_damage_to_player(
    target: "Player",
    damage: int,
    source: Optional["Minion"] = None,
    game: Optional["Game"] = None,
) -> int:
    """对玩家造成标准【伤害】。

    触发伤害替换、血契2级（受到≥3伤害时+3S）、player_damage 事件。
    返回实际造成的伤害值。
    """
    if damage <= 0:
        return 0
    before_hp = target.health
    target.health_change(-damage)
    actual = max(0, before_hp - target.health)
    return actual


def lose_hp_to_player(target: "Player", amount: int) -> None:
    """使玩家【流失生命值】。

    不受坚韧/伤害替换影响，不触发'受到伤害时'效果（如血契2级）。
    用于疲劳惩罚、血契1级沉浸度、以及卡牌中的'失去X点HP'效果。
    """
    if amount <= 0:
        return
    if not hasattr(target, "lose_hp"):
        # 兼容旧 Player 实现（fallback 到 health_change）
        target.health_change(-amount)
        return
    target.lose_hp(amount)


def heal_minion(minion: "Minion", amount: int) -> None:
    """治疗异象，恢复其当前生命值（不超过最大生命值）。"""
    if amount <= 0:
        return
    if not minion.is_alive():
        print(f"  [警告] heal_minion 目标 {minion.name} 已死亡")
        return
    minion.minion_heal(amount)
    print(f"  {minion.name} 恢复 {amount} 点生命，剩余 {minion.health}/{minion.max_health}")


def heal_player(player: "Player", amount: int) -> None:
    """恢复玩家生命值（不超过上限）。"""
    if amount <= 0:
        return
    player.health_change(amount)


# =============================================================================
# 2. 场上异象操作
# =============================================================================

def summon_token(
    game: "Game",
    name: str,
    owner: "Player",
    position: Tuple[int, int],
    attack: int = 1,
    health: int = 1,
    keywords: Optional[dict] = None,
    summon_turn: Optional[int] = None,
) -> Optional["Minion"]:
    """在指定位置召唤一个 token 异象。

    位置被占用时返回 None。召唤出的 token 会自动加入棋盘。
    若未指定 summon_turn，默认使用当前回合数。
    """
    from tards.cards import MinionCard, Minion
    from tards.cost import Cost

    if position in game.board.minion_place:
        print(f"  无法召唤 {name}：位置 {position} 已被占用")
        return None

    card = MinionCard(
        name=name,
        owner=owner,
        cost=Cost(),
        targets=lambda p, b: [],
        attack=attack,
        health=health,
        keywords=keywords or {},
    )
    token = Minion(
        name=name,
        owner=owner,
        position=position,
        attack=attack,
        health=health,
        source_card=card,
        board=game.board,
        keywords=keywords or {},
    )
    game.board.place_minion(token, position)
    token.summon_turn = summon_turn if summon_turn is not None else game.current_turn
    print(f"  {owner.name} 在 {position} 召唤了 {name}")
    return token


def convert_cost_to_t(cost: "Cost") -> int:
    """将费用折算为等效T点数，向下取整。

    折算规则：
    - 1T = 1T
    - 2B = 3T  →  b * 3 // 2
    - 3S = 2T  →  s * 2 // 3
    - 1I = 1T
    - 1G = 2T
    - 1D = 4T
    """
    total = cost.t
    total += cost.b * 3 // 2
    total += cost.s * 2 // 3
    minerals = getattr(cost, "minerals", {})
    total += minerals.get("I", 0) * 1
    total += minerals.get("G", 0) * 2
    total += minerals.get("D", 0) * 4
    return total


def destroy_minion(minion: "Minion", game: "Game") -> None:
    """【消灭】异象：将其生命值设为 0 并触发死亡流程（亡语等）。

    与 remove_minion 不同：destroy 会正常触发所有死亡相关效果。
    """
    if not minion.is_alive():
        return
    minion.current_health = 0
    minion.minion_death()
    print(f"  {minion.name} 被消灭")


def return_minion_to_hand(minion: "Minion", game: "Game") -> bool:
    """将场上异象以原卡形式返回其拥有者手牌。

    手牌满则弃置到弃牌堆。自动清理战场占位。
    返回 True 表示成功返回手牌，False 表示因手牌满而被弃置。
    """
    board = game.board
    owner = minion.owner
    board.remove_minion(minion.position)

    from tards.cards import MinionCard
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
    if len(owner.card_hand) < owner.card_hand_max:
        owner.card_hand.append(new_card)
        print(f"  {minion.name} 返回 {owner.name} 手牌")
        return True
    else:
        owner.card_dis.append(new_card)
        print(f"  {minion.name} 返回手牌失败（手牌满），已弃置")
        return False


def transform_minion_to(minion: "Minion", target_name: str, game: "Game") -> Optional["Minion"]:
    """将场上异象变形为指定名称的新异象。

    保持位置不变，不触发亡语。新异象的 summon_turn 继承旧异象。
    """
    from tards.card_db import DEFAULT_REGISTRY
    target_def = DEFAULT_REGISTRY.get(target_name)
    if not target_def:
        print(f"  变形失败：找不到卡牌定义 [{target_name}]")
        return None
    new_minion = game.transform_minion(minion, target_def, preserve_summon_turn=True)
    if new_minion:
        print(f"  {minion.name} 变形为 {new_minion.name}")
    return new_minion


# =============================================================================
# 移动框架（坐标运算为核心）
# =============================================================================

def move(minion: "Minion", to: Tuple[int, int], game: "Game", allow_cross_side: bool = False) -> bool:
    """将异象移动到指定坐标。底层会发射 before_move / moved 事件。"""
    if not minion or not getattr(minion, "is_alive", lambda: False)():
        print(f"  [警告] move 目标已死亡")
        return False
    ok = game.move_minion(minion, to, allow_cross_side=allow_cross_side)
    if ok:
        print(f"  {minion.name} 移动至 {to}")
    return ok


def shift(minion: "Minion", delta: Tuple[int, int], game: "Game", allow_cross_side: bool = False) -> bool:
    """按偏移量移动异象。新位置 = 旧位置 + delta。

    自动处理边界检查。若新位置越界或被占用，移动失败。
    """
    if not minion or not getattr(minion, "is_alive", lambda: False)():
        return False
    old = minion.position
    if old is None:
        return False
    dr, dc = delta
    new_pos = (old[0] + dr, old[1] + dc)
    if not game.board.target_check(new_pos):
        return False
    return move(minion, new_pos, game, allow_cross_side=allow_cross_side)


def swap(a: "Minion", b: "Minion", game: "Game") -> bool:
    """交换两个异象的位置。不改变阵营。"""
    if not a or not b:
        return False
    ok = game.swap_minions(a, b)
    if ok:
        print(f"  {a.name} 与 {b.name} 交换位置")
    return ok


# =============================================================================
# 坐标运算辅助
# =============================================================================

def empty_positions(player: "Player", board: "Board") -> List[Tuple[int, int]]:
    """返回玩家友方区域内的所有空位坐标列表。"""
    rows = player.get_friendly_rows()
    result = []
    for r in rows:
        for c in range(board.SIZE):
            pos = (r, c)
            if pos not in board.minion_place:
                result.append(pos)
    return result


# =============================================================================
# 向后兼容层（旧函数名保留）
# =============================================================================

def silence_minion(minion: "Minion") -> None:
    """沉默异象：清除所有后天获得的关键词、增益/减益和光环效果，恢复基础面板。

    保留卡牌定义时的基础攻击力、生命值和最大生命值。
    种族/类型标签（tags）不受影响。
    """
    from tards.constants import GENERAL_KEYWORDS

    if not minion.is_alive():
        print(f"  [警告] silence_minion 目标 {minion.name} 已死亡")
        return

    # 清除所有增益/减益
    minion.perm_attack_bonus = 0
    minion.perm_health_bonus = 0
    minion.perm_max_health_bonus = 0
    minion.perm_keywords.clear()
    minion.temp_attack_bonus = 0
    minion.temp_health_bonus = 0
    minion.temp_max_health_bonus = 0
    minion.temp_keywords.clear()

    # 清除所有光环
    minion._aura_attack_fns.clear()
    minion._aura_health_fns.clear()
    minion._aura_max_health_fns.clear()
    minion._aura_keyword_fns.clear()

    # 清除 base_keywords 中的通用关键词（卡牌自带的特殊机制被沉默移除）
    for kw in list(minion.base_keywords.keys()):
        if kw in GENERAL_KEYWORDS:
            minion.base_keywords.pop(kw, None)

    # 清除恐惧状态
    minion._fear_active = False

    # 恢复当前生命值不超过基础值（沉默不恢复生命）
    if minion.current_health > minion.base_health:
        minion.current_health = minion.base_health

    minion.recalculate()
    print(f"  {minion.name} 被沉默")


def buff_minion(
    minion: "Minion",
    atk_delta: int = 0,
    hp_delta: int = 0,
    permanent: bool = True,
) -> None:
    """为异象提供攻击/生命 buff（或 debuff，传入负值即可）。

    hp_delta 作用于最大生命值（current_max_health），当前生命值不自动增加，
    但降低时会截断。
    """
    if not minion.is_alive():
        print(f"  [警告] buff_minion 目标 {minion.name} 已死亡")
        return
    if atk_delta != 0:
        minion.gain_attack(atk_delta, permanent=permanent)
    if hp_delta != 0:
        minion.gain_health_bonus(hp_delta, permanent=permanent)
    p_str = "永久" if permanent else "临时"
    print(
        f"  {minion.name} {p_str}获得 {atk_delta:+d}攻/{hp_delta:+d}血，"
        f"当前 {minion.attack}/{minion.health}"
    )


def gain_keyword(
    minion: "Minion",
    keyword: str,
    value=True,
    permanent: bool = True,
) -> None:
    """为异象赋予关键词。"""
    if not minion.is_alive():
        print(f"  [警告] gain_keyword 目标 {minion.name} 已死亡")
        return
    minion.gain_keyword(keyword, value, permanent=permanent)
    print(f"  {minion.name} 获得关键词 [{keyword}]")


def remove_keyword(minion: "Minion", keyword: str) -> None:
    """为异象移除关键词。"""
    if not minion.is_alive():
        print(f"  [警告] remove_keyword 目标 {minion.name} 已死亡")
        return
    minion.lose_keyword(keyword)
    print(f"  {minion.name} 失去关键词 [{keyword}]")


def set_alias(minion: "Minion", name: str) -> None:
    """使异象"也算作是"指定名称的异象（命名牌效果）。"""
    if not minion.is_alive():
        print(f"  [警告] set_alias 目标 {minion.name} 已死亡")
        return
    minion.alias_name = name
    print(f"  {minion.name} 也算作是 {name}")


# =============================================================================
# 3. 手牌与牌库操作
# =============================================================================

def draw_cards(player: "Player", amount: int, game: Optional["Game"] = None) -> int:
    """抽牌。返回实际抽到手牌中的张数（手牌满而弃置的不计入）。"""
    if amount <= 0:
        return 0
    before = len(player.card_hand)
    player.draw_card(amount, game=game)
    after = len(player.card_hand)
    return max(0, after - before)


def discard_card(player: "Player", card: "Card") -> bool:
    """从手牌弃置一张卡到弃牌堆。

    返回 True 表示成功弃置，False 表示该卡不在手牌中。
    """
    if card not in player.card_hand:
        print(f"  [警告] {card.name} 不在 {player.name} 的手牌中，弃置失败")
        return False
    player.card_hand.remove(card)
    player.card_dis.append(card)
    print(f"  {player.name} 弃置了 {card.name}")
    return True


def mill_cards(player: "Player", amount: int, game: Optional["Game"] = None) -> int:
    """从牌库顶弃置 amount 张牌到弃牌堆（磨牌）。返回实际弃置数量。"""
    if amount <= 0:
        return 0
    milled = 0
    for _ in range(amount):
        if len(player.card_deck) == 0:
            break
        card = player.card_deck.pop()
        player.card_dis.append(card)
        milled += 1
        print(f"  {player.name} 磨牌：{card.name} 被弃置")
    return milled


def remove_top_of_deck(player: "Player", amount: int) -> List["Card"]:
    """从牌库顶移除 amount 张牌（直接消失，不进弃牌堆，不触发任何效果）。

    返回被移除的卡牌列表。
    """
    if amount <= 0:
        return []
    removed: List["Card"] = []
    for _ in range(amount):
        if len(player.card_deck) == 0:
            break
        card = player.card_deck.pop()
        removed.append(card)
        print(f"  {player.name} 牌库顶的 {card.name} 被移除")
    return removed


def shuffle_into_deck(player: "Player", card: "Card") -> None:
    """将一张卡洗入玩家的牌库。"""
    player.card_deck.append(card)
    import random
    random.shuffle(player.card_deck)
    print(f"  {card.name} 被洗入 {player.name} 的牌库")


def copy_card_to_hand(
    source_card: "MinionCard",
    owner: "Player",
    game: Optional["Game"] = None,
    cost_modifier: Optional[callable] = None,
) -> bool:
    """将一张卡的复制加入指定玩家的手牌。

    cost_modifier 可选，是一个接收 Cost 对象并修改它的函数。
    手牌满则弃置到弃牌堆。
    返回 True 表示成功加入手牌，False 表示因手牌满被弃置。
    """
    from tards.cards import MinionCard
    new_card = MinionCard(
        name=source_card.name,
        owner=owner,
        cost=source_card.cost.copy(),
        targets=source_card.targets,
        attack=source_card.attack,
        health=source_card.health,
        special=getattr(source_card, "special", None),
        keywords=source_card.keywords.copy() if source_card.keywords else None,
    )
    if cost_modifier:
        cost_modifier(new_card.cost)
    if len(owner.card_hand) < owner.card_hand_max:
        owner.card_hand.append(new_card)
        print(f"  {owner.name} 获得 {new_card.name} 的复制")
        return True
    else:
        owner.card_dis.append(new_card)
        print(f"  {owner.name} 手牌满，{new_card.name} 的复制被弃置")
        return False


def create_echo_card(source_card: "MinionCard", echo_level: int) -> "MinionCard":
    """根据源卡创建回响版本（花费2T，1/1，回响等级-1）。

    回响卡部署后不会触发特殊效果（special=None），关键词继承原卡。
    """
    from tards.cards import MinionCard
    from tards.cost import Cost

    echo = MinionCard(
        name=source_card.name,
        owner=source_card.owner,
        cost=Cost(t=2),
        targets=source_card.targets,
        attack=1,
        health=1,
        special=None,
        keywords=source_card.keywords.copy() if source_card.keywords else None,
    )
    echo.echo_level = echo_level - 1
    return echo


# =============================================================================
# 4. 返回指定类型的异象（通用查询）
# =============================================================================

def get_minions(
    game: "Game",
    *,
    player: Optional["Player"] = None,
    friendly_only: bool = False,
    enemy_only: bool = False,
    tag: Optional[str] = None,
    random_one: bool = False,
    alive_only: bool = True,
) -> Union[List["Minion"], Optional["Minion"]]:
    """返回指定类型的异象。

    通用查询函数，通过参数组合筛选场上异象。

    Args:
        game: 当前 Game 实例。
        player: 参照玩家，配合 friendly_only/enemy_only 使用。
        friendly_only: 为 True 时只返回属于 player 的异象。
        enemy_only: 为 True 时只返回敌方异象。
        tag: 若指定，只返回带此标签的异象。
        random_one: 为 True 时随机返回一个异象（或 None），否则返回列表。
        alive_only: 为 True 时只返回存活异象（默认）。

    Returns:
        random_one=True 时返回单个异象或 None；否则返回列表。
    """
    result: List["Minion"] = []
    for m in game.board.minion_place.values():
        if alive_only and not m.is_alive():
            continue
        if friendly_only and player and m.owner is not player:
            continue
        if enemy_only and player and m.owner is player:
            continue
        if tag is not None and tag not in getattr(m, "tags", []):
            continue
        result.append(m)

    if random_one:
        import random
        return random.choice(result) if result else None
    return result


# ---- 以下为兼容层薄包装，直接调用 get_minions ----

def all_enemy_minions(game: "Game", player: "Player") -> List["Minion"]:
    """【兼容】返回场上所有存活敌方异象列表。"""
    return get_minions(game, player=player, enemy_only=True)  # type: ignore


def all_friendly_minions(game: "Game", player: "Player") -> List["Minion"]:
    """【兼容】返回场上所有存活友方异象列表。"""
    return get_minions(game, player=player, friendly_only=True)  # type: ignore


def random_enemy_minion(game: "Game", player: "Player") -> Optional["Minion"]:
    """【兼容】返回一个随机存活敌方异象。没有则返回 None。"""
    return get_minions(game, player=player, enemy_only=True, random_one=True)  # type: ignore


def random_friendly_minion(game: "Game", player: "Player") -> Optional["Minion"]:
    """【兼容】返回一个随机存活友方异象。没有则返回 None。"""
    return get_minions(game, player=player, friendly_only=True, random_one=True)  # type: ignore


def random_minion(
    game: "Game", player: "Player", friendly: bool = False
) -> Optional["Minion"]:
    """【兼容】返回一个随机存活异象（默认敌方）。没有则返回 None。"""
    if friendly:
        return get_minions(game, player=player, friendly_only=True, random_one=True)  # type: ignore
    return get_minions(game, player=player, enemy_only=True, random_one=True)  # type: ignore


def get_enemy_minions_by_tag(game: "Game", player: "Player", tag: str) -> List["Minion"]:
    """【兼容】获取敌方场上所有带某标签的存活异象。"""
    return get_minions(game, player=player, tag=tag, enemy_only=True)  # type: ignore


def get_all_minions_by_tag(game: "Game", tag: str) -> List["Minion"]:
    """【兼容】获取场上所有带某标签的存活异象（双方）。"""
    return get_minions(game, tag=tag)  # type: ignore


# =============================================================================
# 标签查询工具
# =============================================================================

def has_tag(obj: Any, tag: str) -> bool:
    """检查卡牌/异象/卡牌定义是否有某标签。
    对 Minion 会回退检查其 source_card 的标签。
    """
    tags = getattr(obj, "tags", None)
    if tags is None and hasattr(obj, "source_card"):
        tags = getattr(obj.source_card, "tags", None)
    return tag in tags if tags else False


def get_card_defs_by_tag(tag: str) -> List[Any]:
    """从注册表获取所有带某标签的卡牌定义。"""
    from tards.card_db import DEFAULT_REGISTRY
    return [c for c in DEFAULT_REGISTRY._cards.values() if has_tag(c, tag)]


def get_adjacent_positions(position: Tuple[int, int], board: "Board") -> List[Tuple[int, int]]:
    """返回上下左右四个相邻位置（仅在棋盘范围内）。

    不检查位置是否被占用——占用检查由调用方决定。
    """
    r, c = position
    result: List[Tuple[int, int]] = []
    for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
        nr, nc = r + dr, c + dc
        if 0 <= nr < board.SIZE and 0 <= nc < board.SIZE:
            result.append((nr, nc))
    return result


def adjacent_columns(column: int, board_size: int = 5) -> List[int]:
    """返回指定列的左右相邻列索引（在棋盘范围内）。

    例如：column=2 → [1, 3]；column=0 → [1]；column=4 → [3]。
    """
    result: List[int] = []
    if column - 1 >= 0:
        result.append(column - 1)
    if column + 1 < board_size:
        result.append(column + 1)
    return result


def get_frontmost_enemy(
    column: int, owner: "Player", board: "Board", attacker: Optional["Minion"] = None
):
    """获取指定列中最靠前（距离中线最近）的存活敌方异象。

    自动过滤潜水/潜行异象（结算阶段）。
    """
    return board.get_front_minion(column, owner, attacker)


# =============================================================================
# 5. 资源管理
# =============================================================================

def gain_resource(player: "Player", resource: str, amount: int) -> None:
    """增加玩家资源。resource 可为 't'/'c'/'b'/'s'（大小写不敏感）。

    注意：鲜血(B)在回合结束时会自动清空，此处仅做临时增加。
    """
    if amount == 0:
        return
    r = resource.lower()
    if r == "t":
        player.t_point_change(amount)
    elif r == "c":
        player.c_point_change(amount)
    elif r == "b":
        player.b_point = max(0, player.b_point + amount)
    elif r == "s":
        player.s_point = max(0, player.s_point + amount)
    else:
        print(f"  [警告] gain_resource 未知资源类型: {resource}")
        return
    _res_name = {"t": "T点", "c": "C点", "b": "B点", "s": "S点"}.get(r, r.upper())
    print(
        f"  {player.name} {'获得' if amount >= 0 else '失去'} {abs(amount)}{_res_name}，"
        f"当前 T点={player.t_point}(上限{player.t_point_max}) C点={player.c_point}(上限{player.c_point_max}) B点={player.b_point} S点={player.s_point}"
    )


def lose_resource(player: "Player", resource: str, amount: int) -> None:
    """减少玩家资源。amount 为正数。"""
    if amount <= 0:
        return
    gain_resource(player, resource, -amount)


# =============================================================================
# 6. 亡语与其他辅助
# =============================================================================

def is_enemy(m1, m2) -> bool:
    """判断两个对象（异象或玩家）是否为敌对关系。"""
    return getattr(m1, "owner", m1) != getattr(m2, "owner", m2)


def add_deathrattle(minion: "Minion", deathrattle_fn: callable) -> None:
    """为一个异象动态添加亡语效果。

    deathrattle_fn 的签名为 (minion, player, board) -> None。
    如果异象已有亡语，新亡语会覆盖旧的（暂不支持多亡语叠加）。
    """
    if not minion.is_alive():
        print(f"  [警告] add_deathrattle 目标 {minion.name} 已死亡")
        return
    minion.base_keywords["亡语"] = deathrattle_fn
    minion.recalculate()
    print(f"  {minion.name} 获得亡语")


# =============================================================================
# 6.5 抽取效果（Draw-trigger）
# =============================================================================

def set_draw_trigger(card: "Card", callback: Callable[["Game", Dict[str, Any], "Card"], None]) -> None:
    """为一张卡牌设置"抽取"触发效果。

    当该卡从牌库被抽入手牌时，callback 会被自动调用。
    callback 签名: (game, event_data, card) -> None，
    其中 event_data 包含 {player, card}。

    实现方式：设置 card.on_drawn 属性，由 _trigger_auto_effects 在 EVENT_DRAW 时统一调度。
    """
    card.on_drawn = callback
    print(f"  {card.name} 获得抽取效果")


def remove_draw_trigger(card: "Card") -> None:
    """移除卡牌的"抽取"效果。"""
    if hasattr(card, "on_drawn"):
        delattr(card, "on_drawn")
    print(f"  {card.name} 失去抽取效果")


# =============================================================================
# 7. 卡牌创建与注册表查询
# =============================================================================

def get_card_definition(name: str) -> Optional[Any]:
    """从全局注册表查询卡牌定义。"""
    from tards.card_db import DEFAULT_REGISTRY
    return DEFAULT_REGISTRY.get(name)


def create_card_by_name(name: str, owner: "Player") -> Optional[Any]:
    """根据卡牌名称从注册表创建一张对战用 Card 对象。

    找不到定义或创建失败时返回 None。
    """
    card_def = get_card_definition(name)
    if not card_def:
        print(f"  [警告] 注册表中找不到卡牌定义 [{name}]")
        return None
    try:
        return card_def.to_game_card(owner)
    except Exception as e:
        print(f"  [警告] 创建卡牌 [{name}] 失败: {e}")
        return None


def add_card_to_hand_by_name(name: str, owner: "Player", game: Optional["Game"] = None) -> bool:
    """将指定名称的卡牌创建并加入玩家手牌。

    手牌满则弃置到弃牌堆。返回 True 表示成功加入手牌。
    """
    card = create_card_by_name(name, owner)
    if not card:
        return False
    if len(owner.card_hand) < owner.card_hand_max:
        owner.card_hand.append(card)
        print(f"  {owner.name} 获得 {name}")
        return True
    else:
        owner.card_dis.append(card)
        print(f"  {owner.name} 手牌满，{name} 被弃置")
        return False


# =============================================================================
# 8. 异象移除（不触发亡语）
# =============================================================================

def remove_minion_no_death(minion: "Minion", game: "Game") -> bool:
    """将异象从战场直接移除，不触发亡语和死亡事件。

    用于"移除"类效果（与 destroy_minion 不同）。
    """
    if not minion.is_alive():
        return False
    game.board.remove_minion(minion.position)
    print(f"  {minion.name} 被移除")
    return True


# =============================================================================
# 9. 数值型关键词修改
# =============================================================================

def modify_keyword_number(minion: "Minion", keyword: str, delta: int) -> None:
    """修改异象身上某个数值型关键词的数值（如坚韧±1）。

    若修改后数值不大于 0，则直接删除该关键词。
    """
    if not minion.is_alive():
        print(f"  [警告] modify_keyword_number 目标 {minion.name} 已死亡")
        return
    current = minion.keywords.get(keyword, 0)
    if not isinstance(current, int):
        print(f"  [警告] {minion.name} 的 {keyword} 不是数值类型，无法修改")
        return
    new_val = current + delta
    if new_val > 0:
        minion.base_keywords[keyword] = new_val
    else:
        minion.base_keywords.pop(keyword, None)
    minion.recalculate()
    if delta > 0:
        print(f"  {minion.name} 的 {keyword} 增加 {delta}，当前 {new_val}")
    else:
        print(f"  {minion.name} 的 {keyword} 减少 {abs(delta)}，当前 {new_val if new_val > 0 else '已移除'}")


# =============================================================================
# 10. 场上全体异象
# =============================================================================

def get_all_minions(game: "Game") -> List["Minion"]:
    """返回场上所有存活异象列表（不分敌我）。"""
    return [m for m in game.board.minion_place.values() if m.is_alive()]


# =============================================================================
# 11. 事件监听器注册辅助
# =============================================================================

def add_event_listener(minion: "Minion", game: "Game", event_type: str,
                       callback: Callable, priority: int = 0) -> int:
    """为一个异象注册事件监听器，并返回 owner_id。

    异象死亡时，所有以此 owner_id 注册的监听器会自动注销。
    """
    # 使用 minion 的 id 作为默认 owner_id（如果没有 _event_owner_id）
    if not hasattr(minion, "_event_owner_id"):
        minion._event_owner_id = id(minion)
    return game.register_listener(event_type, callback, priority, owner_id=minion._event_owner_id)


def remove_event_listener(game: "Game", event_type: str, callback: Callable) -> None:
    """注销单个事件监听器。"""
    game.unregister_listener(event_type, callback)


def clear_event_listeners(minion: "Minion", game: "Game") -> None:
    """清除某个异象注册的所有事件监听器。"""
    if hasattr(minion, "_event_owner_id"):
        game.unregister_listeners_by_owner(minion._event_owner_id)


# =============================================================================
# 11.5 通用事件注册（on_tick 简化版）
# =============================================================================

_EVENT_NAME_MAP: Dict[str, str] = {}


def _init_event_name_map():
    """延迟初始化事件名映射表，避免循环导入。"""
    global _EVENT_NAME_MAP
    if _EVENT_NAME_MAP:
        return
    from tards import constants as C
    _EVENT_NAME_MAP = {
        # 伤害
        "before_damage": C.EVENT_BEFORE_DAMAGE, "伤害前": C.EVENT_BEFORE_DAMAGE,
        "damaged": C.EVENT_DAMAGED, "受伤后": C.EVENT_DAMAGED,
        "after_damage": C.EVENT_AFTER_DAMAGE,
        # 攻击
        "before_attack": C.EVENT_BEFORE_ATTACK, "攻击前": C.EVENT_BEFORE_ATTACK,
        "attacked": C.EVENT_ATTACKED, "攻击后": C.EVENT_ATTACKED,
        "after_attack": C.EVENT_AFTER_ATTACK,
        # 部署
        "before_deploy": C.EVENT_BEFORE_DEPLOY, "部署前": C.EVENT_BEFORE_DEPLOY,
        "deployed": C.EVENT_DEPLOYED, "部署后": C.EVENT_AFTER_DEPLOY,
        "after_deploy": C.EVENT_AFTER_DEPLOY,
        # 消灭
        "before_destroy": C.EVENT_BEFORE_DESTROY, "消灭前": C.EVENT_BEFORE_DESTROY,
        "destroyed": C.EVENT_DESTROYED,
        # 移除
        "before_remove": C.EVENT_BEFORE_REMOVE,
        "removed": C.EVENT_REMOVED,
        # 回合/阶段
        "turn_start": C.EVENT_TURN_START, "回合开始": C.EVENT_TURN_START,
        "turn_end": C.EVENT_TURN_END, "回合结束": C.EVENT_TURN_END,
        "phase_start": C.EVENT_PHASE_START, "阶段开始": C.EVENT_PHASE_START,
        "phase_end": C.EVENT_PHASE_END, "阶段结束": C.EVENT_PHASE_END,
        # 资源
        "before_t_change": C.EVENT_BEFORE_T_CHANGE,
        "before_c_change": C.EVENT_BEFORE_C_CHANGE,
        "t_changed": C.EVENT_T_CHANGED, "c_changed": C.EVENT_C_CHANGED,
        # 手牌/牌库
        "before_draw": C.EVENT_BEFORE_DRAW, "抽牌前": C.EVENT_BEFORE_DRAW,
        "drawn": C.EVENT_DRAWN, "抽牌": C.EVENT_DRAWN,
        "before_discard": C.EVENT_BEFORE_DISCARD, "弃置前": C.EVENT_BEFORE_DISCARD,
        "discarded": C.EVENT_DISCARDED, "弃置": C.EVENT_DISCARDED,
        "before_mill": C.EVENT_BEFORE_MILL, "磨牌前": C.EVENT_BEFORE_MILL,
        "milled": C.EVENT_MILLED, "磨牌": C.EVENT_MILLED,
        # 其他
        "sacrifice": C.EVENT_SACRIFICE, "献祭": C.EVENT_SACRIFICE,
        "card_played": C.EVENT_CARD_PLAYED, "卡牌打出": C.EVENT_CARD_PLAYED,
        "played": C.EVENT_PLAYED,
        "bell": C.EVENT_BELL, "鸣钟": C.EVENT_BELL,
        "death": C.EVENT_DEATH, "死亡": C.EVENT_DEATH,
        "player_damage": C.EVENT_PLAYER_DAMAGE,
        # 开发
        "developed": C.EVENT_DEVELOPED,
        # 移动
        "before_move": C.EVENT_BEFORE_MOVE, "移动前": C.EVENT_BEFORE_MOVE,
        "moved": C.EVENT_MOVED, "移动后": C.EVENT_MOVED,
    }


def on(period: str, callback, game, minion=None, priority: int = 0) -> int:
    """注册一个事件监听器。period 支持中英文事件名。

    常用 period：
      "before_damage"/"伤害前", "damaged"/"受伤后", "after_damage",
      "before_attack"/"攻击前", "attacked"/"攻击后", "after_attack",
      "before_deploy"/"部署前", "deployed"/"部署后", "after_deploy",
      "before_destroy"/"消灭前", "destroyed",
      "turn_start"/"回合开始", "turn_end"/"回合结束",
      "phase_start"/"阶段开始", "phase_end"/"阶段结束",
      "sacrifice"/"献祭", "draw"/"抽牌", "discarded"/"弃置", "milled"/"磨牌",
      "card_played"/"卡牌打出", "bell"/"鸣钟", "death"/"死亡"

    minion 为 None 时，使用 callback 本身的 id 作为 owner_id。
    """
    _init_event_name_map()
    event_type = _EVENT_NAME_MAP.get(period, period)
    if minion is None:
        owner_id = id(callback)
    else:
        if not hasattr(minion, "_event_owner_id"):
            minion._event_owner_id = id(minion)
        owner_id = minion._event_owner_id
    return game.register_listener(event_type, callback, priority, owner_id=owner_id)


# =============================================================================
# 12. 事件驱动型伤害/攻击监听器包装（兼容层，内部调用 on()）
# =============================================================================

def on_before_damage(minion: "Minion", game: "Game", callback: Callable,
                     priority: int = 0) -> int:
    """【兼容】注册 before_damage 监听器。"""
    return on("before_damage", callback, game, minion, priority)


def on_damaged(minion: "Minion", game: "Game", callback: Callable,
               priority: int = 0) -> int:
    """【兼容】注册 damaged 监听器。"""
    return on("damaged", callback, game, minion, priority)


def on_after_damage(minion: "Minion", game: "Game", callback: Callable,
                    priority: int = 0) -> int:
    """【兼容】注册 after_damage 监听器。"""
    return on("after_damage", callback, game, minion, priority)


def on_before_attack(minion: "Minion", game: "Game", callback: Callable,
                     priority: int = 0) -> int:
    """【兼容】注册 before_attack 监听器。"""
    return on("before_attack", callback, game, minion, priority)


def on_after_attack(minion: "Minion", game: "Game", callback: Callable,
                    priority: int = 0) -> int:
    """【兼容】注册 after_attack 监听器。"""
    return on("after_attack", callback, game, minion, priority)


def on_before_destroy(minion: "Minion", game: "Game", callback: Callable,
                      priority: int = 0) -> int:
    """【兼容】注册 before_destroy 监听器。"""
    return on("before_destroy", callback, game, minion, priority)


# =============================================================================
# 7. 开发机制辅助函数
# =============================================================================

def give_card_by_name(player: "Player", name: str, reason: str = "") -> bool:
    """将指定名称的卡牌定义加入玩家手牌（或弃牌堆）。"""
    from tards.card_db import DEFAULT_REGISTRY
    card_def = DEFAULT_REGISTRY.get(name)
    if not card_def:
        return False
    card = card_def.to_game_card(player)
    if len(player.card_hand) < player.card_hand_max:
        player.card_hand.append(card)
    else:
        player.card_dis.append(card)
    msg = f"  {player.name} {reason}：获得 {name}" if reason else f"  {player.name} 获得 {name}"
    print(msg)
    return True


def deploy_card_copy(player: "Player", game: "Game", card: "Card", target_pos: Optional[Any] = None) -> bool:
    """复制一张异象卡并部署到战场。若未指定目标位置，自动寻找空位。"""
    from tards.cards import MinionCard
    if not isinstance(card, MinionCard):
        return False
    if target_pos is None:
        empties = empty_positions(player, game.board)
        target_pos = empties[0] if empties else None
    if target_pos is None:
        print(f"  {player.name} 战场已满，无法部署 {card.name} 的复制")
        return False
    if not game.board.is_valid_deploy(target_pos, player, card):
        return False
    # 调用原卡的 effect 来完成部署流程
    return card.effect(player, target_pos, game)


def auto_attack(minion: "Minion", game: "Game") -> bool:
    """让异象执行一次自动攻击：选择本列最前排敌方目标，没有则攻击敌方玩家。"""
    col = minion.position[1]
    target = game.board.get_front_minion(col, minion.owner, attacker=minion)
    if target and target.is_alive():
        minion.attack_target(target)
        return True
    opponent = game.p2 if minion.owner == game.p1 else game.p1
    minion.attack_target(opponent)
    return True


# =============================================================================
# 13. 延迟效果（基于 EventBus）
# =============================================================================

def delay_to_next_turn(
    minion: "Minion",
    game: "Game",
    callback: Callable[[Any], None],
    once: bool = True,
) -> int:
    """注册一个在下一回合开始时执行的回调。

    自动过滤：只在 game.current_turn > 注册时的回合数 时触发，
    避免在同一回合内重复执行。
    返回 owner_id（可用于手动注销）。
    """
    from tards.constants import EVENT_TURN_START

    turn_registered = game.current_turn

    def _wrapper(event):
        if game.current_turn <= turn_registered:
            return
        if not minion.is_alive():
            if once:
                game.unregister_listener(EVENT_TURN_START, _wrapper)
            return
        try:
            callback(event)
        except Exception as e:
            print(f"  [警告] delay_to_next_turn 回调异常: {e}")
        if once:
            game.unregister_listener(EVENT_TURN_START, _wrapper)

    return add_event_listener(minion, game, EVENT_TURN_START, _wrapper)


def delay_to_phase_start(
    minion: "Minion",
    game: "Game",
    phase: str,
    callback: Callable[[Any], None],
    once: bool = True,
) -> int:
    """注册一个在指定 phase_start 时执行的回调。

    phase 应与 game.PHASE_DRAW / PHASE_ACTION / PHASE_RESOLVE 等常量一致。
    """
    from tards.constants import EVENT_PHASE_START

    def _wrapper(event):
        if event.data.get("phase") != phase:
            return
        if not minion.is_alive():
            if once:
                game.unregister_listener(EVENT_PHASE_START, _wrapper)
            return
        try:
            callback(event)
        except Exception as e:
            print(f"  [警告] delay_to_phase_start 回调异常: {e}")
        if once:
            game.unregister_listener(EVENT_PHASE_START, _wrapper)

    return add_event_listener(minion, game, EVENT_PHASE_START, _wrapper)


def delay_to_turn_end(
    minion: "Minion",
    game: "Game",
    callback: Callable[[Any], None],
    once: bool = True,
) -> int:
    """注册一个在当前回合结束时执行的回调。"""
    from tards.constants import EVENT_TURN_END

    turn_registered = game.current_turn

    def _wrapper(event):
        if game.current_turn != turn_registered:
            return
        if not minion.is_alive():
            if once:
                game.unregister_listener(EVENT_TURN_END, _wrapper)
            return
        try:
            callback(event)
        except Exception as e:
            print(f"  [警告] delay_to_turn_end 回调异常: {e}")
        if once:
            game.unregister_listener(EVENT_TURN_END, _wrapper)

    return add_event_listener(minion, game, EVENT_TURN_END, _wrapper)


# =============================================================================
# 14. 状态追踪框架（全局计数器）
# =============================================================================

def _get_state_tracker(game: "Game") -> Dict[str, Any]:
    """获取或惰性初始化游戏的状态追踪器。"""
    if not hasattr(game, "_state_tracker"):
        game._state_tracker = {}
    return game._state_tracker


def track_stat(game: "Game", key: str, value: Any) -> None:
    """记录一个全局状态值（跨回合持久）。"""
    tracker = _get_state_tracker(game)
    tracker[key] = value


def get_stat(game: "Game", key: str, default: Any = None) -> Any:
    """读取状态追踪器中的值。"""
    tracker = _get_state_tracker(game)
    return tracker.get(key, default)


def increment_stat(game: "Game", key: str, delta: int = 1) -> int:
    """累加状态值，返回新值。"""
    tracker = _get_state_tracker(game)
    tracker[key] = tracker.get(key, 0) + delta
    return tracker[key]


def track_per_turn(game: "Game", key: str, value: Any, turn_offset: int = 0) -> None:
    """记录当前回合（或偏移回合）的状态。
    key 会自动附加回合后缀，回合结束时由 game.py 自动清理。
    """
    turn = game.current_turn + turn_offset
    full_key = f"{key}_turn_{turn}"
    tracker = _get_state_tracker(game)
    tracker[full_key] = value


def get_per_turn(game: "Game", key: str, turn_offset: int = 0, default: Any = None) -> Any:
    """读取某回合的状态值。"""
    turn = game.current_turn + turn_offset
    full_key = f"{key}_turn_{turn}"
    tracker = _get_state_tracker(game)
    return tracker.get(full_key, default)


def track_event_per_turn(
    minion: "Minion",
    game: "Game",
    key: str,
    event_type: str,
    filter_fn: Optional[Callable[[Any], bool]] = None,
) -> int:
    """自动追踪某事件每回合的发生次数，并在回合结束时清零。

    注册一个 event_type 的全局监听器，满足 filter_fn 时计数 +1。
    返回 owner_id（可用于手动注销）。

    使用示例：
        track_event_per_turn(minion, game, "turn_deploys", EVENT_DEPLOYED,
                       lambda e: e.data.get("minion", {}).owner == minion.owner)
    """
    tracker = _get_state_tracker(game)
    turn = getattr(game, "current_turn", 0)
    full_key = f"{key}_turn_{turn}"
    tracker[full_key] = 0

    def _on_event(event):
        if filter_fn and not filter_fn(event):
            return
        current_turn = getattr(game, "current_turn", 0)
        current_key = f"{key}_turn_{current_turn}"
        tracker[current_key] = tracker.get(current_key, 0) + 1

    def _on_turn_end(event):
        turn_to_clear = event.data.get("turn", getattr(game, "current_turn", 0))
        key_to_clear = f"{key}_turn_{turn_to_clear}"
        if key_to_clear in tracker:
            del tracker[key_to_clear]

    oid1 = add_event_listener(minion, game, event_type, _on_event)
    from tards.constants import EVENT_TURN_END
    add_event_listener(minion, game, EVENT_TURN_END, _on_turn_end)
    return oid1


# =============================================================================
# 15. 即时对战（决斗）
# =============================================================================

def initiate_combat(a: "Minion", b: "Minion", game: "Game") -> None:
    """使两个指定异象互相攻击一次（对战）。

    双方各攻击一次，走完整的 attack_target 事件链。
    若任一方已死亡，则直接返回。
    """
    if not a.is_alive() or not b.is_alive():
        return

    # 防止递归标志（供攻击前监听器识别）
    a._in_initiate_combat = True
    b._in_initiate_combat = True

    try:
        # A 攻击 B
        a.attack_target(b)
        if game.check_game_over():
            return

        # B 攻击 A
        b.attack_target(a)
        if game.check_game_over():
            return
    finally:
        a._in_initiate_combat = False
        b._in_initiate_combat = False


# =============================================================================
# 15. 战斗伤害增强与替换
# =============================================================================

# =============================================================================
# 16. 全局事件钩子
# =============================================================================

def on_deploy_global(minion: "Minion", game: "Game", callback: Callable,
                     priority: int = 0) -> int:
    """【兼容】监听全局部署事件。"""
    return on("deployed", callback, game, minion, priority)


def on_sacrifice_global(minion: "Minion", game: "Game", callback: Callable,
                        priority: int = 0) -> int:
    """【兼容】监听全局献祭事件。"""
    return on("sacrifice", callback, game, minion, priority)


def on_draw_global(minion: "Minion", game: "Game", callback: Callable,
                   priority: int = 0) -> int:
    """【兼容】监听全局抽牌事件。"""
    return on("drawn", callback, game, minion, priority)


def on_card_played_global(minion: "Minion", game: "Game", callback: Callable,
                          priority: int = 0) -> int:
    """【兼容】监听全局卡牌打出事件。"""
    return on("played", callback, game, minion, priority)


def on_turn_start_global(minion: "Minion", game: "Game", callback: Callable,
                         priority: int = 0) -> int:
    """【兼容】监听全局回合开始事件。
    规则：回合开始等价于结算阶段开始（PHASE_RESOLVE）。"""
    def _wrapper(event):
        if event.data.get("phase") != game.PHASE_RESOLVE:
            return
        callback(event)
    return on("phase_start", _wrapper, game, minion, priority)


def on_turn_end_global(minion: "Minion", game: "Game", callback: Callable,
                       priority: int = 0) -> int:
    """【兼容】监听全局回合结束事件。
    规则：回合结束等价于结算阶段结束（PHASE_RESOLVE）。"""
    def _wrapper(event):
        if event.data.get("phase") != game.PHASE_RESOLVE:
            return
        callback(event)
    return on("phase_end", _wrapper, game, minion, priority)


def on_before_damage_global(minion: "Minion", game: "Game", callback: Callable,
                            priority: int = 0) -> int:
    """【兼容】监听全局 before_damage 事件。"""
    return on("before_damage", callback, game, minion, priority)


def on_damaged_global(minion: "Minion", game: "Game", callback: Callable,
                      priority: int = 0) -> int:
    """【兼容】监听全局 damaged 事件。"""
    return on("damaged", callback, game, minion, priority)


# =============================================================================
# 17. 批量 / AOE 效果
# =============================================================================

def damage_all_enemies(
    game: "Game",
    player: "Player",
    amount: int,
    source: Optional["Minion"] = None,
) -> int:
    """对所有存活敌方异象造成伤害。返回实际造成的总伤害。"""
    if amount <= 0:
        return 0
    total = 0
    for m in all_enemy_minions(game, player):
        total += deal_damage_to_minion(m, amount, source=source, game=game)
    return total


def damage_all_friendly(
    game: "Game",
    player: "Player",
    amount: int,
    source: Optional["Minion"] = None,
) -> int:
    """对所有存活友方异象造成伤害。返回实际造成的总伤害。"""
    if amount <= 0:
        return 0
    total = 0
    for m in all_friendly_minions(game, player):
        total += deal_damage_to_minion(m, amount, source=source, game=game)
    return total


def heal_all_friendly(
    game: "Game",
    player: "Player",
    amount: int,
) -> int:
    """治疗所有存活友方异象。返回实际治疗的总生命值。"""
    if amount <= 0:
        return 0
    total = 0
    for m in all_friendly_minions(game, player):
        before = m.health
        heal_minion(m, amount)
        total += max(0, m.health - before)
    return total


def buff_all_friendly(
    game: "Game",
    player: "Player",
    atk_delta: int = 0,
    hp_delta: int = 0,
    permanent: bool = True,
) -> int:
    """为所有存活友方异象提供 buff。返回被 buff 的异象数。"""
    count = 0
    for m in all_friendly_minions(game, player):
        buff_minion(m, atk_delta, hp_delta, permanent=permanent)
        count += 1
    return count


def destroy_all_enemies(
    game: "Game",
    player: "Player",
) -> int:
    """消灭所有存活敌方异象。返回消灭的异象数。"""
    count = 0
    for m in list(all_enemy_minions(game, player)):
        destroy_minion(m, game)
        count += 1
    return count


def freeze_minion(minion: "Minion", layers: int = 1) -> None:
    """为异象添加【冰冻】关键词（指定层数）。

    若异象已死亡则跳过并打印警告。
    """
    if not minion.is_alive():
        print(f"  [警告] freeze_minion 目标 {minion.name} 已死亡")
        return
    gain_keyword(minion, "冰冻", layers, permanent=True)


def freeze_enemies_in_columns(
    game: "Game",
    player: "Player",
    columns: List[int],
    layers: int = 1,
) -> int:
    """冰冻指定列中的所有存活敌方异象。返回被冰冻的异象数。"""
    count = 0
    for m in all_enemy_minions(game, player):
        if m.position[1] in columns:
            freeze_minion(m, layers)
            count += 1
    return count


def silence_all_enemies(
    game: "Game",
    player: "Player",
) -> int:
    """沉默所有存活敌方异象。返回沉默的异象数。"""
    count = 0
    for m in all_enemy_minions(game, player):
        silence_minion(m)
        count += 1
    return count


# =============================================================================
# 18. 更多目标选择器
# =============================================================================

def weakest_enemy_minion(
    game: "Game",
    player: "Player",
) -> Optional["Minion"]:
    """返回当前生命值最低的存活敌方异象。平局时取先遍历到的。没有则 None。"""
    enemies = all_enemy_minions(game, player)
    if not enemies:
        return None
    return min(enemies, key=lambda m: m.health)


def strongest_enemy_minion(
    game: "Game",
    player: "Player",
) -> Optional["Minion"]:
    """返回当前攻击力最高的存活敌方异象。平局时取先遍历到的。没有则 None。"""
    enemies = all_enemy_minions(game, player)
    if not enemies:
        return None
    return max(enemies, key=lambda m: m.attack)


def find_unique_highest_attack(
    minions: List["Minion"],
    key_fn: Optional[Callable[["Minion"], int]] = None,
) -> Optional["Minion"]:
    """找出攻击力（或自定义 key）唯一最高的异象。

    若最高值有多个并列，返回 None（不唯一）。
    若列表为空，返回 None。
    """
    if not minions:
        return None
    if key_fn is None:
        key_fn = lambda m: m.attack
    max_val = max(key_fn(m) for m in minions)
    highest = [m for m in minions if key_fn(m) == max_val]
    if len(highest) != 1:
        return None
    return highest[0]


def enemy_minions_in_column(
    game: "Game",
    player: "Player",
    column: int,
) -> List["Minion"]:
    """返回指定列中的所有存活敌方异象。"""
    return [
        m for m in all_enemy_minions(game, player)
        if m.position[1] == column
    ]


def adjacent_friendly_minions(
    minion: "Minion",
    game: "Game",
) -> List["Minion"]:
    """返回与指定异象相邻（上下左右）的存活友方异象。"""
    result: List["Minion"] = []
    if not minion.is_alive():
        return result
    positions = get_adjacent_positions(minion.position, game.board)
    for pos in positions:
        m = game.board.get_minion_at(pos)
        if m and m.is_alive() and m.owner == minion.owner:
            result.append(m)
    return result


def adjacent_enemy_minions(
    minion: "Minion",
    game: "Game",
) -> List["Minion"]:
    """返回与指定异象相邻（上下左右）的存活敌方异象。"""
    result: List["Minion"] = []
    if not minion.is_alive():
        return result
    positions = get_adjacent_positions(minion.position, game.board)
    for pos in positions:
        m = game.board.get_minion_at(pos)
        if m and m.is_alive() and m.owner != minion.owner:
            result.append(m)
    return result


def nearest_enemy_minion(
    minion: "Minion",
    game: "Game",
) -> Optional["Minion"]:
    """返回距离指定异象最近的存活敌方异象（曼哈顿距离）。平局时取先遍历到的。"""
    if not minion.is_alive():
        return None
    enemies = all_enemy_minions(game, minion.owner)
    if not enemies:
        return None
    r, c = minion.position
    return min(enemies, key=lambda m: abs(m.position[0] - r) + abs(m.position[1] - c))


# =============================================================================
# 19. 条件与组合
# =============================================================================

def conditional_effect(
    condition_fn: Callable[[], bool],
    then_fn: Callable[[], None],
    else_fn: Optional[Callable[[], None]] = None,
) -> None:
    """条件执行效果函数。

    condition_fn: 无参函数，返回 bool。
    then_fn / else_fn: 无参函数，条件满足/不满足时执行。
    """
    try:
        if condition_fn():
            then_fn()
        elif else_fn:
            else_fn()
    except Exception as e:
        print(f"  [警告] conditional_effect 执行异常: {e}")


# =============================================================================
# 19.5 "如可能"条件执行（If-possible semantics）
# =============================================================================

def if_possible_then(
    condition_fn: Callable[[], bool],
    then_fn: Callable[[], None],
) -> bool:
    """如可能：当 condition_fn 返回 True 时执行 then_fn，否则效果失效。

    返回 True 表示条件满足并已执行，False 表示条件不满足、效果未执行。
    用于"如可能，..."类效果（如"如可能，消耗1S，对对手造成2点伤害"）。

    与 conditional_effect 的区别：
      - if_possible_then 强调"前提条件不满足则效果完全失效"；
      - conditional_effect 是通用的 if/else 分支。
    """
    try:
        if condition_fn():
            then_fn()
            return True
        return False
    except Exception as e:
        print(f"  [警告] if_possible_then 执行异常: {e}")
        return False


def if_resource_then(
    player: "Player",
    resource: str,
    amount: int,
    then_fn: Callable[[], None],
) -> bool:
    """如可能，消耗 resource：当玩家拥有足够资源时扣除并执行 then_fn，否则效果失效。

    resource: 't'/'c'/'b'/'s'（大小写不敏感）
    amount: 需要消耗的正数

    示例：
        if_resource_then(player, 's', 1, lambda: deal_damage_to_player(opponent, 2))
        # 如可能，消耗1S，对对手造成2点伤害
    """
    if amount <= 0:
        try:
            then_fn()
        except Exception as e:
            print(f"  [警告] if_resource_then 后续效果异常: {e}")
        return True
    r = resource.lower()
    current = {
        "t": player.t_point,
        "c": player.c_point,
        "b": player.b_point,
        "s": player.s_point,
    }.get(r, 0)
    if current < amount:
        print(f"  {player.name} 的{r.upper()}点不足（当前{current}，需要{amount}），效果失效")
        return False
    try:
        # 扣除资源
        if r == "t":
            player.t_point_change(-amount)
        elif r == "c":
            player.c_point_change(-amount)
        elif r == "b":
            player.b_point = max(0, player.b_point - amount)
        elif r == "s":
            player.s_point = max(0, player.s_point - amount)
        else:
            print(f"  [警告] if_resource_then 未知资源类型: {resource}")
            return False
        print(f"  {player.name} 消耗了 {amount}{r.upper()}点")
        then_fn()
        return True
    except Exception as e:
        print(f"  [警告] if_resource_then 执行异常: {e}")
        return False


def if_has_cards_then(
    player: "Player",
    amount: int,
    then_fn: Callable[[], None],
) -> bool:
    """如可能，弃置/使用手牌：当玩家手牌数不少于 amount 时执行 then_fn，否则效果失效。"""
    if len(player.card_hand) < amount:
        print(f"  {player.name} 手牌不足（当前{len(player.card_hand)}张，需要{amount}张），效果失效")
        return False
    try:
        then_fn()
        return True
    except Exception as e:
        print(f"  [警告] if_has_cards_then 执行异常: {e}")
        return False


def if_has_friendly_minions_then(
    game: "Game",
    player: "Player",
    amount: int,
    then_fn: Callable[[], None],
) -> bool:
    """如可能，献祭/选择友方异象：当场上有不少于 amount 个存活友方异象时执行 then_fn，否则效果失效。"""
    count = len(all_friendly_minions(game, player))
    if count < amount:
        print(f"  {player.name} 友方异象不足（当前{count}个，需要{amount}个），效果失效")
        return False
    try:
        then_fn()
        return True
    except Exception as e:
        print(f"  [警告] if_has_friendly_minions_then 执行异常: {e}")
        return False


def if_has_enemy_minions_then(
    game: "Game",
    player: "Player",
    amount: int,
    then_fn: Callable[[], None],
) -> bool:
    """如可能，选择敌方异象：当场上有不少于 amount 个存活敌方异象时执行 then_fn，否则效果失效。"""
    count = len(all_enemy_minions(game, player))
    if count < amount:
        print(f"  {player.name} 敌方异象不足（当前{count}个，需要{amount}个），效果失效")
        return False
    try:
        then_fn()
        return True
    except Exception as e:
        print(f"  [警告] if_has_enemy_minions_then 执行异常: {e}")
        return False


def chain_effects(
    minion: "Minion",
    game: "Game",
    *effect_fns: Callable,
    extras=None,
) -> None:
    """按顺序链式执行多个效果函数。

    每个 effect_fn 的签名为 (minion, player, game) -> None，
    或 (minion, player, game, extras=None) -> None。
    遇到异常时打印警告并继续执行下一个。
    """
    player = minion.owner
    for fn in effect_fns:
        try:
            if not minion.is_alive():
                print(f"  [警告] chain_effects 中断：{minion.name} 已死亡")
                return
            import inspect
            sig = inspect.signature(fn)
            if len(sig.parameters) >= 4:
                fn(minion, player, game, extras)
            else:
                fn(minion, player, game)
        except Exception as e:
            print(f"  [警告] chain_effects 中某效果异常: {e}")


def repeat_effect(
    n: int,
    effect_fn: Callable[[], None],
) -> None:
    """重复执行某个无参效果函数 n 次。"""
    if n <= 0:
        return
    for i in range(n):
        try:
            effect_fn()
        except Exception as e:
            print(f"  [警告] repeat_effect 第 {i+1} 次执行异常: {e}")


# =============================================================================
# 20. 临时效果管理
# =============================================================================

def give_temp_keyword_until_turn_end(
    minion: "Minion",
    keyword: str,
    value: Any = True,
) -> None:
    """为异象赋予一个临时关键词，当前回合结束时自动清除。

    通过 minion 已有的 temp_keywords 机制实现（clear_temp_effects 会在回合结束清理）。
    """
    gain_keyword(minion, keyword, value, permanent=False)


def give_temp_buff_until_turn_end(
    minion: "Minion",
    atk_delta: int = 0,
    hp_delta: int = 0,
) -> None:
    """为异象提供临时 buff，当前回合结束时自动清除。"""
    buff_minion(minion, atk_delta, hp_delta, permanent=False)


def inject_temporary_deathrattle(
    minion: "Minion",
    game: "Game",
    deathrattle_fn: Callable,
) -> None:
    """为异象注入一个临时亡语（覆盖原有亡语）。

    新亡语触发后自动恢复原有的亡语（如果存在）。
    注意：此实现基于覆盖-恢复模式，不适用于需要叠加多个亡语的场景。
    """
    if not minion.is_alive():
        print(f"  [警告] inject_temporary_deathrattle 目标 {minion.name} 已死亡")
        return
    original_dr = minion.keywords.get("亡语")

    def _wrapped_deathrattle(m, p, b):
        try:
            deathrattle_fn(m, p, b)
        except Exception as e:
            print(f"  [警告] 临时亡语执行异常: {e}")
        # 恢复原亡语
        if original_dr:
            m.base_keywords["亡语"] = original_dr
        else:
            m.base_keywords.pop("亡语", None)
        m.recalculate()

    minion.base_keywords["亡语"] = _wrapped_deathrattle
    minion.recalculate()
    print(f"  {minion.name} 获得临时亡语")


# =============================================================================
# 21. 牌库操作增强
# =============================================================================

def reveal_top_of_deck(
    player: "Player",
    amount: int,
) -> List["Card"]:
    """揭示牌库顶的 amount 张牌（只读，不修改牌库）。

    返回卡牌列表（从顶到底）。牌库不足时返回实际能揭示的张数。
    """
    if amount <= 0:
        return []
    revealed = []
    # 牌库顶是列表末尾
    for i in range(1, amount + 1):
        if len(player.card_deck) < i:
            break
        revealed.append(player.card_deck[-i])
    return revealed


def put_on_top_of_deck(
    player: "Player",
    card: "Card",
) -> None:
    """将一张牌放到牌库顶（列表末尾）。"""
    player.card_deck.append(card)
    print(f"  {card.name} 被放到 {player.name} 牌库顶")


def put_on_bottom_of_deck(
    player: "Player",
    card: "Card",
) -> None:
    """将一张牌放到牌库底（列表开头）。"""
    player.card_deck.insert(0, card)
    print(f"  {card.name} 被放到 {player.name} 牌库底")


def search_deck(
    player: "Player",
    predicate: Callable[["Card"], bool],
) -> List["Card"]:
    """搜索牌库中满足条件的所有牌。返回列表（从顶到底）。

    不修改牌库顺序。仅用于读取/检查。
    """
    return [c for c in reversed(player.card_deck) if predicate(c)]


# =============================================================================
# 22. 高级事件包装（补充第 11-12 区已有包装）
# =============================================================================

def on_after_deploy(minion: "Minion", game: "Game", callback: Callable,
                      priority: int = 0) -> int:
    """【兼容】注册 after_deploy 监听器。"""
    return on("after_deploy", callback, game, minion, priority)


def on_card_played(minion: "Minion", game: "Game", callback: Callable,
                   priority: int = 0) -> int:
    """【兼容】注册 played 监听器。"""
    return on("played", callback, game, minion, priority)


def on_sacrifice(minion: "Minion", game: "Game", callback: Callable,
                 priority: int = 0) -> int:
    """【兼容】注册 sacrifice 监听器。"""
    return on("sacrifice", callback, game, minion, priority)


def on_turn_start(minion: "Minion", game: "Game", callback: Callable,
                  priority: int = 0) -> int:
    """【兼容】注册 turn_start 监听器。
    规则：回合开始等价于结算阶段开始（PHASE_RESOLVE）。"""
    def _wrapper(event):
        if event.data.get("phase") != game.PHASE_RESOLVE:
            return
        callback(event)
    return on("phase_start", _wrapper, game, minion, priority)


def on_turn_end(minion: "Minion", game: "Game", callback: Callable,
                priority: int = 0) -> int:
    """【兼容】注册 turn_end 监听器。
    规则：回合结束等价于结算阶段结束（PHASE_RESOLVE）。"""
    def _wrapper(event):
        if event.data.get("phase") != game.PHASE_RESOLVE:
            return
        callback(event)
    return on("phase_end", _wrapper, game, minion, priority)


def on_discarded(minion: "Minion", game: "Game", callback: Callable,
                 priority: int = 0) -> int:
    """【兼容】注册 discarded 监听器。"""
    return on("discarded", callback, game, minion, priority)


def on_milled(minion: "Minion", game: "Game", callback: Callable,
              priority: int = 0) -> int:
    """【兼容】注册 milled 监听器。"""
    return on("milled", callback, game, minion, priority)


# =============================================================================
# 23. 其他实用工具
# =============================================================================

def count_keyword_on_board(
    game: "Game",
    keyword: str,
    player: Optional["Player"] = None,
) -> int:
    """统计场上具有指定关键词的存活异象数量。

    player 为 None 时统计双方，否则只统计该玩家的异象。
    """
    minions = get_all_minions(game)
    if player:
        minions = [m for m in minions if m.owner == player]
    return sum(1 for m in minions if m.keywords.get(keyword))


def has_keyword(minion: "Minion", keyword: str) -> bool:
    """检查异象是否拥有指定关键词（含临时和基础）。"""
    return bool(minion.keywords.get(keyword))


def get_opponent(game: "Game", player: "Player") -> "Player":
    """返回指定玩家的对手。"""
    return game.p2 if player == game.p1 else game.p1


def get_minions_by_cost(
    game: "Game",
    player: "Player",
    cost_type: str = "t",
    max_cost: Optional[int] = None,
    friendly: bool = True,
) -> List["Minion"]:
    """按费用筛选场上异象（基于 source_card 的费用）。

    cost_type: 't' 或 'c'。
    max_cost: 最大费用上限（含），None 表示不限。
    friendly: True 只选友方，False 只选敌方。
    """
    pool = all_friendly_minions(game, player) if friendly else all_enemy_minions(game, player)
    result = []
    for m in pool:
        sc = getattr(m, "source_card", None)
        if not sc:
            continue
        cost = getattr(sc, "cost", None)
        if not cost:
            continue
        val = getattr(cost, f"{cost_type}_point", 0)
        if max_cost is None or val <= max_cost:
            result.append(m)
    return result


# =============================================================================
# 15. 伤害来源标记
# =============================================================================

# deal_damage_to_minion 已支持 source 参数，无需单独的 deal_damage_with_source


# =============================================================================
# 16. 动态效果注入
# =============================================================================

def add_turn_start_effect(minion: "Minion", fn: Callable[["Minion", "Player", "Game"], None]) -> None:
    """给异象注入一个回合开始效果。"""
    if not hasattr(minion, "_injected_turn_start"):
        minion._injected_turn_start = []
    minion._injected_turn_start.append(fn)


def add_turn_end_effect(minion: "Minion", fn: Callable[["Minion", "Player", "Game"], None]) -> None:
    """给异象注入一个回合结束效果。"""
    if not hasattr(minion, "_injected_turn_end"):
        minion._injected_turn_end = []
    minion._injected_turn_end.append(fn)


# =============================================================================
# 18. 全局部署限制
# =============================================================================

def add_deploy_restriction(game: "Game", fn: Callable[["Player", Any], bool]) -> None:
    """添加一个全局部署限制条件。fn 返回 False 则阻止部署。"""
    if not hasattr(game, "_global_deploy_restrictions"):
        game._global_deploy_restrictions = []
    game._global_deploy_restrictions.append(fn)


# =============================================================================
# 19. 卡组顶操作
# =============================================================================

def peek_deck_top(player: "Player", n: int) -> List[Any]:
    """查看卡组顶 n 张牌（不移除）。"""
    return list(player.card_deck[:n])


def place_at_deck_bottom(player: "Player", cards: List[Any]) -> None:
    """将若干张牌放置到卡组底部。"""
    for c in cards:
        player.card_deck.append(c)


def place_at_deck_top(player: "Player", cards: List[Any]) -> None:
    """将若干张牌放置到卡组顶部。"""
    for c in reversed(cards):
        player.card_deck.insert(0, c)


def shuffle_deck(player: "Player") -> None:
    """洗切玩家的牌堆。"""
    import random
    random.shuffle(player.card_deck)
    print(f"  {player.name} 的牌堆已被洗切")


def discover_from_deck_top(
    player: "Player",
    n: int,
    game: "Game",
    title: str = "展示卡组顶",
) -> Optional[Any]:
    """展示玩家卡组顶的 n 张牌，让玩家选择 1 张加入手牌，其余置底。

    利用 game.request_choice 实现跨 GUI/CLI/网络 的通用选择。
    返回被选中的 Card，若无则返回 None。
    """
    candidates = peek_deck_top(player, n)
    if not candidates:
        print(f"  {player.name} 的牌库为空，无法展示")
        return None

    options = [f"{i+1}. {c.name}" for i, c in enumerate(candidates)]
    chosen = game.request_choice(player, options, title=title)
    if not chosen:
        # 其余置底
        place_at_deck_bottom(player, candidates)
        return None

    idx = int(chosen.split('.')[0]) - 1
    if idx < 0 or idx >= len(candidates):
        idx = 0
    chosen_card = candidates[idx]

    # 从牌库移除并加入手牌
    player.card_deck.remove(chosen_card)
    if len(player.card_hand) < player.card_hand_max:
        player.card_hand.append(chosen_card)
        print(f"  {player.name} 展示了卡组顶 {len(candidates)} 张，选择了 {chosen_card.name} 加入手牌")
    else:
        player.card_dis.append(chosen_card)
        print(f"  {player.name} 手牌已满，{chosen_card.name} 被弃置")

    # 其余置底
    remaining = [c for c in candidates if c is not chosen_card]
    if remaining:
        place_at_deck_bottom(player, remaining)

    return chosen_card


# =============================================================================
# 20. 过滤抽牌（按卡牌类型）
# =============================================================================

def draw_cards_of_type(
    player: "Player",
    amount: int,
    card_type: type,
    game: Optional["Game"] = None,
) -> List[Any]:
    """从牌库中抽取指定类型的牌。

    从牌库顶部开始按顺序搜索，遇到指定类型的牌即抽入手牌。
    若牌库中该类型不足 amount 张，抽多少算多少。
    返回实际抽到的牌列表。
    """
    drawn: List[Any] = []
    i = 0
    while amount > 0 and i < len(player.card_deck):
        card = player.card_deck[i]
        if isinstance(card, card_type):
            if game and game.game_over:
                break
            # 移除这张牌
            player.card_deck.pop(i)
            if len(player.card_hand) >= player.card_hand_max:
                player.card_dis.append(card)
                print(f"  {player.name} 手牌已满，{card.name} 被弃置")
                amount -= 1
                continue
            player.card_hand.append(card)
            drawn.append(card)
            amount -= 1
            if game:
                from tards.constants import EVENT_DRAW
                game.emit_event(EVENT_DRAW, player=player, card=card)
            # 不移 i，因为 pop 后下一个元素前移
        else:
            i += 1

    if drawn:
        print(f"  {player.name} 抽取了: {', '.join(c.name for c in drawn)}")
    else:
        print(f"  {player.name} 牌库中没有指定类型的牌")
    return drawn


# =============================================================================
# 24. 伤害重定向与免疫（冥刻包）
# =============================================================================

def redirect_damage(
    minion: "Minion",
    when: Callable[[int, Optional["Minion"]], bool],
    to: Union[int, Callable[[int], int]] = 0,
    reason: str = "",
) -> None:
    """通用伤害重定向/替换。

    when: (damage, source) -> bool，返回 True 时触发替换
    to: 替换后的伤害值（int 或 callable），默认 0 表示取消伤害
    """
    game = getattr(minion.board, "game_ref", None)
    if not game:
        return

    replace_fn = to if callable(to) else lambda d: to

    def filter_fn(target, damage, source):
        if target is not minion or not minion.is_alive() or damage <= 0:
            return False
        return when(damage, source)

    game.register_damage_replacement(filter_fn, replace_fn, once=False, reason=reason)


# =============================================================================
# 25. 全局地形覆盖
# =============================================================================

def get_terrain_at(
    game: "Game",
    position: Tuple[int, int],
    default: Optional[str] = None,
) -> Optional[str]:
    """获取指定格子的当前地形类型，优先返回覆盖值。"""
    overrides = getattr(game, "_terrain_overrides", {})
    return overrides.get(position, default)


def _is_minion_legal_on_terrain(minion: "Minion", terrain: str) -> bool:
    """检查异象是否能在指定地形上合法存活。"""
    aquatic = minion.keywords.get("水生", False) or minion.keywords.get("两栖", False)
    if terrain == "水路":
        return aquatic
    return not minion.keywords.get("水生", False)


def register_terrain_enforcement(
    game: "Game",
    column: int,
    forced_terrain: str,
    end_turn: int,
) -> None:
    """注册一列的地形强制覆盖，并在每个阶段检查该列异象合法性，移除非法者。

    参数：
        game: 游戏实例
        column: 被覆盖的列号（0-4）
        forced_terrain: 强制地形（如"水路"、"高地"）
        end_turn: 覆盖持续到哪个回合结束（含）
    """
    from tards.constants import EVENT_PHASE_START

    board = game.board
    if not hasattr(game, "_terrain_overrides"):
        game._terrain_overrides = {}

    # 设置地形覆盖
    for r in range(5):
        game._terrain_overrides[(r, column)] = forced_terrain

    def _check_illegal():
        """检查该列所有异象是否合法，移除非法者（不触发亡语）。"""
        for r in range(5):
            pos = (r, column)
            m = board.minion_place.get(pos)
            if m and m.is_alive() and not _is_minion_legal_on_terrain(m, forced_terrain):
                board.remove_minion(pos)
                print(f"  地形强制({forced_terrain})：{m.name} 因不合法被移除")
            u = board.cell_underlay.get(pos)
            if u and u.is_alive() and not _is_minion_legal_on_terrain(u, forced_terrain):
                board.cell_underlay.pop(pos)
                u.position = None
                print(f"  地形强制({forced_terrain})：{u.name} 因不合法被移除")

    # 立即检查一次
    _check_illegal()

    # 注册阶段监听器，持续检查
    def _phase_checker(event_data):
        _check_illegal()

    game.event_bus.on(EVENT_PHASE_START, _phase_checker)

    # 清理函数：在 end_turn 回合结束时移除覆盖、注销监听器、最终检查
    def _cleanup():
        # 注销监听器
        game.event_bus.off(EVENT_PHASE_START, _phase_checker)
        # 移除地形覆盖
        for r in range(5):
            game._terrain_overrides.pop((r, column), None)
        # 恢复为默认陆地后，再次检查并移除不合法异象（如纯水生）
        restored_terrain = "陆地"
        for r in range(5):
            pos = (r, column)
            m = board.minion_place.get(pos)
            if m and m.is_alive() and not _is_minion_legal_on_terrain(m, restored_terrain):
                board.remove_minion(pos)
                print(f"  地形恢复({restored_terrain})：{m.name} 因不合法被移除")
            u = board.cell_underlay.get(pos)
            if u and u.is_alive() and not _is_minion_legal_on_terrain(u, restored_terrain):
                board.cell_underlay.pop(pos)
                u.position = None
                print(f"  地形恢复({restored_terrain})：{u.name} 因不合法被移除")

    game._delayed_effects.append({
        "trigger": "turn_end",
        "turn": end_turn,
        "fn": _cleanup,
    })


# =============================================================================
# 26. 无法被异象选中
# =============================================================================

def is_untargetable_by_minions(minion: "Minion") -> bool:
    """检查异象是否设置了"无法被异象选中"。"""
    return getattr(minion, "_untargetable_by_minions", False)


# =============================================================================
# 27. 全局攻击禁止
# =============================================================================

def clear_attack_restrictions(game: "Game") -> None:
    """清除所有全局攻击限制。应在回合结束时调用。"""
    if hasattr(game, "_attack_restrictions"):
        game._attack_restrictions.clear()


def can_minion_attack(minion: "Minion", game: "Game") -> bool:
    """检查异象是否被全局攻击限制禁止攻击。"""
    restrictions = getattr(game, "_attack_restrictions", [])
    for fn in restrictions:
        if fn(minion):
            return False
    return True


# =============================================================================
# 28. 猪灵掉落物卡池（用户手动添加衍生卡牌定义）
# =============================================================================

DROP_POOL: List[Any] = []
"""猪灵掉落物卡池：存放 CardDefinition 对象，首次使用金锭时随机抽取一张加入手牌。"""

