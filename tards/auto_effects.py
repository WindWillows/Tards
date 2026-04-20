# 自动效果辅助函数（兼容层）
# 本文件保留以保证现有代码（translate_packs.py 生成的 import）不中断
# 移动/交换/返回手牌等兼容函数已内聚至此
#
# 注意：所有函数内部采用惰性导入，避免与 card_pools/__init__.py → discrete.py
# → tards.auto_effects 形成循环导入。


def move_minion(minion, new_pos, game):
    """【兼容】将单位移动到新的空格子。等价于 move()。"""
    from card_pools.effect_utils import move
    return move(minion, new_pos, game)


def swap_minions(m1, m2, game):
    """【兼容】交换两个单位的位置。等价于 swap()。"""
    from card_pools.effect_utils import swap
    return swap(m1, m2, game)


def move_enemy_to_friendly(player, target, game):
    """【兼容】将一个敌方单位劫持到友方区域，并改变其阵营为当前玩家。"""
    from card_pools.effect_utils import move, empty_positions
    if not target or not getattr(target, "is_alive", lambda: False)():
        return False
    old_owner = target.owner
    if old_owner is player:
        return False
    target.owner = player
    for pos in empty_positions(player, game.board):
        if move(target, pos, game, allow_cross_side=True):
            print(f"  {target.name} 被劫持到 {pos}，阵营变为 {player.name}")
            return True
    target.owner = old_owner
    return False


def move_enemy_to_enemy(player, target, game):
    """【兼容】将一个敌方单位自动移动到敌方区域的另一个合法空位（不改变阵营）。"""
    from card_pools.effect_utils import move, empty_positions
    if not target or not getattr(target, "is_alive", lambda: False)():
        return False
    for pos in empty_positions(target.owner, game.board):
        if move(target, pos, game):
            print(f"  {target.name} 被移动到 {pos}")
            return True
    return False


def move_friendly_to_friendly(player, target, game):
    """【兼容】将一个友方单位自动移动到友方区域的另一个合法空位。"""
    from card_pools.effect_utils import move, empty_positions
    if not target or not getattr(target, "is_alive", lambda: False)():
        return False
    for pos in empty_positions(player, game.board):
        if move(target, pos, game):
            print(f"  {target.name} 被移动到 {pos}")
            return True
    return False


def swap_units(target, extras, game):
    """【兼容】交换 target 与 extras[0] 两个单位的位置。（策略效果签名适配器）"""
    from card_pools.effect_utils import swap
    if not extras or len(extras) < 1:
        return False
    other = extras[0]
    if not other or not getattr(other, "is_alive", lambda: False)():
        return False
    return swap(target, other, game)


def return_to_hand(target, game, owner):
    """将一个单位返回其拥有者的手牌。（兼容层，底层使用 return_minion_to_hand）"""
    from card_pools.effect_utils import return_minion_to_hand
    if not target or not getattr(target, "is_alive", lambda: False)():
        return False
    return return_minion_to_hand(target, game)


__all__ = [
    "move_minion",
    "swap_minions",
    "move_enemy_to_friendly",
    "move_enemy_to_enemy",
    "move_friendly_to_friendly",
    "return_to_hand",
    "swap_units",
]
