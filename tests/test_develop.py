import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

"""测试开发（Discover/Develop）机制。"""
import sys
sys.path.insert(0, __file__.rsplit("\\", 1)[0])

from tards.game import Game
from tards.player import Player
from tards.board import Board
from tards.card_db import CardDefinition, CardRegistry, CardType, Pack, Rarity
from tards.cards import MinionCard, Strategy
from tards.cost import Cost
from tards.targets import target_none


class FakeGame:
    """最小化的 Game 替身，用于独立测试 develop_card。"""
    def __init__(self):
        self.game_over = False
        self.discover_provider = None
        self.p1 = None
        self.p2 = None
        self.players = []
        self.board = Board()

    def register_listener(self, *a, **k):
        pass

    def unregister_listeners_by_owner(self, *a, **k):
        pass

    def emit_event(self, *a, **k):
        return None

    def refresh_all_auras(self):
        pass

    def effect_queue_is_resolving(self):
        return False


def _make_minion_def(name, pack=Pack.GENERAL):
    return CardDefinition(
        name=name,
        cost_str="1T",
        card_type=CardType.MINION,
        pack=pack,
        rarity=Rarity.IRON,
        attack=1,
        health=1,
        targets_fn=target_none,
    )


def test_develop_basic():
    """开发基本流程：从 original_deck_defs 中选 3 张候选，生成 1 张到手牌。"""
    defs = [_make_minion_def(f"卡{i}") for i in range(5)]
    p1 = Player(side=0, name="P1", diver="测试", card_deck=[], original_deck_defs=defs)
    p2 = Player(side=1, name="P2", diver="测试", card_deck=[])
    game = Game(p1, p2)

    result = game.develop_card(p1, p1.original_deck_defs)
    assert result is True, "开发应返回 True"
    assert len(p1.card_hand) == 1, "手牌应增加 1 张"
    assert p1.card_hand[0].name in [d.name for d in defs], "生成的牌应在原池内"
    print("[PASS] test_develop_basic")


def test_develop_no_duplicate_candidates():
    """候选不应重复（即使原池只有 3 张）。"""
    defs = [_make_minion_def(f"卡{i}") for i in range(3)]
    p1 = Player(side=0, name="P1", diver="测试", card_deck=[], original_deck_defs=defs)
    p2 = Player(side=1, name="P2", diver="测试", card_deck=[])

    seen = set()
    for _ in range(50):
        game = Game(p1, p2)
        # 清空手牌
        p1.card_hand.clear()
        game.develop_card(p1, p1.original_deck_defs)
        seen.add(p1.card_hand[0].name)

    # 3 张牌都应该有机会被选中
    assert len(seen) == 3, f"应能选中全部 3 张牌，但只选中 {len(seen)} 张"
    print("[PASS] test_develop_no_duplicate_candidates")


def test_develop_hand_full():
    """手牌满时开发应移入弃牌堆。"""
    defs = [_make_minion_def("满手牌测试")]
    p1 = Player(side=0, name="P1", diver="测试", card_deck=[], original_deck_defs=defs)
    # 塞满手牌
    for _ in range(p1.card_hand_max):
        p1.card_hand.append(_make_minion_def("占位").to_game_card(p1))
    p2 = Player(side=1, name="P2", diver="测试", card_deck=[])
    game = Game(p1, p2)

    result = game.develop_card(p1, p1.original_deck_defs)
    assert result is True
    assert len(p1.card_hand) == p1.card_hand_max, "手牌数量不应变"
    assert len(p1.card_dis) == 1, "应弃置 1 张"
    assert p1.card_dis[0].name == "满手牌测试"
    print("[PASS] test_develop_hand_full")


def test_develop_immersion_discrete_3():
    """离散3级沉浸度：开发时 +1HP。"""
    defs = [_make_minion_def("沉浸测试", pack=Pack.DISCRETE)]
    p1 = Player(side=0, name="P1", diver="测试", card_deck=[], original_deck_defs=defs)
    p1.immersion_points[Pack.DISCRETE] = 3
    p1.health = 20
    p2 = Player(side=1, name="P2", diver="测试", card_deck=[])
    game = Game(p1, p2)

    game.develop_card(p1, p1.original_deck_defs)
    assert p1.health == 21, f"离散3级开发应+1HP，当前 {p1.health}"
    print("[PASS] test_develop_immersion_discrete_3")


def test_develop_empty_pool():
    """空池开发应返回 False。"""
    p1 = Player(side=0, name="P1", diver="测试", card_deck=[])
    p2 = Player(side=1, name="P2", diver="测试", card_deck=[])
    game = Game(p1, p2)
    assert game.develop_card(p1, []) is False
    print("[PASS] test_develop_empty_pool")


def test_develop_provider_receives_candidates():
    """discover_provider 应接收已生成的候选列表。"""
    defs = [_make_minion_def(f"卡{i}") for i in range(10)]
    p1 = Player(side=0, name="P1", diver="测试", card_deck=[], original_deck_defs=defs)
    p2 = Player(side=1, name="P2", diver="测试", card_deck=[])
    game = Game(p1, p2)

    received = {}
    def provider(g, player, candidates, count):
        received["candidates"] = candidates
        received["count"] = count
        return candidates[0]

    game.discover_provider = provider
    game.develop_card(p1, p1.original_deck_defs)

    assert len(received["candidates"]) == 3, "provider 应收到 3 张候选"
    assert len(set(id(c) for c in received["candidates"])) == 3, "候选应不重复"
    print("[PASS] test_develop_provider_receives_candidates")


if __name__ == "__main__":
    test_develop_basic()
    test_develop_no_duplicate_candidates()
    test_develop_hand_full()
    test_develop_immersion_discrete_3()
    test_develop_empty_pool()
    test_develop_provider_receives_candidates()
    print("\n所有开发机制测试通过！")
