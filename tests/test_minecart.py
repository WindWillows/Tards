import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

#!/usr/bin/env python3
"""矿车效果验证脚本。

构建一个包含矿车的卡组，通过随机行动让矿车被部署并消灭，
验证亡语"获得1个T槽"是否正确触发。
"""

import random
from typing import Any, Dict, Optional

from tards import Cost, Game, MinionCard, Player, Strategy, target_friendly_positions, target_none
import card_pools  # 触发卡牌注册
from tards.card_db import DEFAULT_REGISTRY


def make_minecart_deck(owner: Player) -> list:
    """构建一个以矿车为核心的测试卡组。"""
    deck = []

    # 添加 10 张矿车
    minecart_def = DEFAULT_REGISTRY.get("矿车")
    if minecart_def:
        for _ in range(10):
            deck.append(minecart_def.to_game_card(owner))
    else:
        print("错误：找不到矿车卡牌定义")
        return []

    # 添加几张火球用于消灭矿车
    def fireball_effect(p, t, g):
        if hasattr(t, "take_damage"):
            t.take_damage(2)
            return True
        return False
    for _ in range(5):
        deck.append(Strategy("火球", Cost.from_string("2T"), fireball_effect, target_friendly_positions))

    random.shuffle(deck)
    return deck


def test_actor(game: Game, active: Player, opponent: Player) -> Optional[Dict[str, Any]]:
    """测试行动生成器：优先部署矿车，然后用火球打自己的矿车触发亡语。"""
    # 优先找可部署的矿车
    for idx, card in enumerate(active.card_hand):
        serial = idx + 1
        if card.name == "矿车":
            # 找一个友方空位
            for r in active.get_friendly_rows():
                for c in range(5):
                    pos = (r, c)
                    if active.board_ref.get_minion_at(pos) is None:
                        if active.card_can_play(serial, pos):
                            return {"type": "play", "serial": serial, "target": pos}

    # 其次找火球打自己的矿车（测试亡语）
    for idx, card in enumerate(active.card_hand):
        serial = idx + 1
        if card.name == "火球":
            # 找友方矿车作为目标
            for m in active.board_ref.get_minions_of_player(active):
                if m.is_alive() and m.name == "矿车":
                    if active.card_can_play(serial, m):
                        return {"type": "play", "serial": serial, "target": m}

    # 否则拉闸
    return {"type": "brake"}


def main():
    print("=" * 50)
    print("矿车效果验证：亡语'获得1个T槽'")
    print("=" * 50)

    p1_deck = make_minecart_deck(None)
    p2_deck = make_minecart_deck(None)
    if not p1_deck:
        return

    p1 = Player(side=0, name="玩家A", diver="测试员", card_deck=p1_deck)
    p2 = Player(side=1, name="玩家B", diver="测试员", card_deck=p2_deck)

    game = Game(p1, p2, action_provider=test_actor)
    game.start_game()


if __name__ == "__main__":
    main()
