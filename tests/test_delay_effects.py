import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

"""
延迟效果工具实战验证脚本。
验证点：
1. once=True 时监听器只触发一次
2. 异象死亡后监听器是否正确跳过/注销
3. 跨回合时 game.current_turn 判断是否正确
"""

from tards import Game, Player, DEFAULT_REGISTRY
from tards.card_db import CardDefinition, Pack
from tards.cost import Cost
from tards.cards import MinionCard
from tards.targets import target_friendly_positions


def make_test_deck(player, names):
    """从注册表创建测试卡组。"""
    cards = []
    for name in names:
        c = DEFAULT_REGISTRY.get(name)
        if c:
            cards.append(c.to_game_card(player))
    return cards


def test_delay_to_turn_end():
    """测试 delay_to_turn_end：部署一张卡，当前回合结束时触发效果。"""
    print("\n========== 测试 delay_to_turn_end ==========")
    p1 = Player(0, "玩家A", "测试", [])
    p2 = Player(1, "玩家B", "测试", [])

    # 给玩家A的手牌塞一张可以直接部署的测试卡（随便一张 0T 异象）
    test_card = MinionCard(
        name="延迟测试-回合结束",
        owner=p1,
        cost=Cost(t=0),
        targets=target_friendly_positions,
        attack=1,
        health=1,
    )
    p1.card_hand.append(test_card)

    turn_count = [0]
    actions = [
        {"type": "play", "serial": 1, "target": (3, 2)},  # 回合1：部署测试异象
        {"type": "brake"},
        {"type": "brake"},
    ]

    def provider(game, active, opponent):
        turn_count[0] = game.current_turn
        if active is p1 and game.current_phase == game.PHASE_ACTION:
            if not p1.card_hand:
                return {"type": "brake"}
            idx = game.current_turn - 1
            if idx < len(actions):
                return actions[idx]
        if active is p2:
            return {"type": "brake"}
        return {"type": "brake"}

    g = Game(p1, p2, action_provider=provider)

    # 在部署前给 test_card 绑定 special_fn，使用 delay_to_turn_end
    def _test_special(minion, player, game, extras=None):
        from card_pools.effect_utils import delay_to_turn_end
        def _cb(event):
            print(f"  [delay_to_turn_end 回调触发] 回合={game.current_turn}, minion存活={minion.is_alive()}")
            # 效果：给玩家恢复1HP
            from card_pools.effect_utils import heal_player
            heal_player(player, 1)
            print(f"  {player.name} 获得+1HP")
        delay_to_turn_end(minion, game, _cb, once=True)
        print(f"  [注册] delay_to_turn_end 已注册，当前回合={game.current_turn}")

    test_card.special = _test_special
    g.start_game()
    print("测试结束")


def test_delay_to_next_turn():
    """测试 delay_to_next_turn：部署一张卡，下回合开始时触发效果。"""
    print("\n========== 测试 delay_to_next_turn ==========")
    p1 = Player(0, "玩家A", "测试", [])
    p2 = Player(1, "玩家B", "测试", [])

    test_card = MinionCard(
        name="延迟测试-下回合",
        owner=p1,
        cost=Cost(t=0),
        targets=target_friendly_positions,
        attack=1,
        health=1,
    )
    p1.card_hand.append(test_card)

    actions = [
        {"type": "play", "serial": 1, "target": (3, 2)},
        {"type": "brake"},
        {"type": "brake"},
        {"type": "brake"},
    ]

    def provider(game, active, opponent):
        if active is p1 and game.current_phase == game.PHASE_ACTION:
            if not p1.card_hand:
                return {"type": "brake"}
            idx = game.current_turn - 1
            if idx < len(actions):
                return actions[idx]
        if active is p2:
            return {"type": "brake"}
        return {"type": "brake"}

    g = Game(p1, p2, action_provider=provider)

    def _test_special(minion, player, game, extras=None):
        from card_pools.effect_utils import delay_to_next_turn
        def _cb(event):
            print(f"  [delay_to_next_turn 回调触发] 回合={game.current_turn}, minion存活={minion.is_alive()}")
            player.t_point_change(1)
            print(f"  {player.name} 获得1T点")
        delay_to_next_turn(minion, game, _cb, once=True)
        print(f"  [注册] delay_to_next_turn 已注册，当前回合={game.current_turn}")

    test_card.special = _test_special
    g.start_game()
    print("测试结束")


def test_delay_dead_minion():
    """测试异象死亡后延迟监听器是否不再触发。"""
    print("\n========== 测试 死亡后监听器跳过 ==========")
    p1 = Player(0, "玩家A", "测试", [])
    p2 = Player(1, "玩家B", "测试", [])

    test_card = MinionCard(
        name="延迟测试-死亡",
        owner=p1,
        cost=Cost(t=0),
        targets=target_friendly_positions,
        attack=1,
        health=1,
    )
    p1.card_hand.append(test_card)

    actions = [
        {"type": "play", "serial": 1, "target": (3, 2)},
        {"type": "brake"},
        {"type": "brake"},
        {"type": "brake"},
    ]

    def provider(game, active, opponent):
        if active is p1 and game.current_phase == game.PHASE_ACTION:
            if not p1.card_hand:
                return {"type": "brake"}
            idx = game.current_turn - 1
            if idx < len(actions):
                return actions[idx]
        if active is p2:
            return {"type": "brake"}
        return {"type": "brake"}

    g = Game(p1, p2, action_provider=provider)

    def _test_special(minion, player, game, extras=None):
        from card_pools.effect_utils import delay_to_next_turn
        def _cb(event):
            print(f"  [死亡测试回调] 回合={game.current_turn}, minion存活={minion.is_alive()}")
        delay_to_next_turn(minion, game, _cb, once=True)
        print(f"  [注册] 死亡测试 delay_to_next_turn 已注册")
        # 部署后立即自杀（模拟死亡）
        from card_pools.effect_utils import destroy_minion
        destroy_minion(minion, game)
        print(f"  [测试] 异象已被立即消灭")

    test_card.special = _test_special
    g.start_game()
    print("测试结束")


if __name__ == "__main__":
    test_delay_to_turn_end()
    test_delay_to_next_turn()
    test_delay_dead_minion()
