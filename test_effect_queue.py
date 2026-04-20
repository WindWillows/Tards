"""
测试效果队列：验证"效果一旦开始结算不被打断"的规则。
场景：
1. 玩家A 部署"自爆兵"
2. 玩家B 使用策略"火球"攻击"自爆兵"
3. 观察："火球"效果先完全结算，然后"自爆兵"的亡语才触发
"""

from tards import (
    Game, Player, MinionCard, Strategy,
    Cost, target_friendly_positions, target_any_minion,
)


def build_p1_deck(owner):
    deck = []
    for _ in range(4):
        deck.append(MinionCard(
            name="自爆兵",
            owner=owner,
            cost=Cost(t=1),
            targets=target_friendly_positions,
            attack=1,
            health=1,
            keywords={
                "亡语": lambda m, p, b: print(f"    >>> 亡语效果：{m.name} 爆炸了！")
            },
        ))
    return deck


def build_p2_deck(owner):
    deck = []
    for _ in range(10):
        deck.append(Strategy(
            name="火球",
            cost=Cost(t=2),
            effect_fn=lambda p, t, g: (t.take_damage(2), True)[1] if hasattr(t, 'take_damage') else False,
            targets=target_any_minion,
        ))
    return deck


def test_deathrattle_queue():
    p1 = Player(side=0, name="玩家A", diver="测试", card_deck=build_p1_deck(None))
    p2 = Player(side=1, name="玩家B", diver="测试", card_deck=build_p2_deck(None))

    p1.sacrifice_chooser = lambda req: None
    p2.sacrifice_chooser = lambda req: None

    state = {"step": 0}

    def actor(game, active, opponent):
        # 回合1 A先手：部署自爆兵然后拉闸
        if game.current_turn == 1 and active.name == "玩家A" and state["step"] == 0:
            state["step"] = 1
            return {"type": "play", "serial": 1, "target": (3, 0)}
        if game.current_turn == 1 and active.name == "玩家A" and state["step"] == 1:
            state["step"] = 2
            return {"type": "brake"}

        # 回合2 B先手：用火球打自爆兵然后拉闸
        if game.current_turn == 2 and active.name == "玩家B" and state["step"] == 2:
            state["step"] = 3
            targets = [m for m in game.board.minion_place.values() if m.owner == p1]
            if targets:
                return {"type": "play", "serial": 1, "target": targets[0]}
            return {"type": "brake"}
        if game.current_turn == 2 and active.name == "玩家B" and state["step"] == 3:
            state["step"] = 4
            return {"type": "brake"}

        return {"type": "brake"}

    game = Game(p1, p2, action_provider=actor)
    game.start_game()


if __name__ == "__main__":
    print("=" * 50)
    print("测试：亡语应在策略效果结束后才触发")
    print("=" * 50)
    test_deathrattle_queue()
