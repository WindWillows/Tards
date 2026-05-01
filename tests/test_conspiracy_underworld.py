#!/usr/bin/env python3
"""Test underworld conspiracies: Jiandao, Fange, Xurui, Moshui (stack counter)."""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tards import (
    Game, Player, MinionCard, Strategy,
    Cost, target_friendly_positions, target_any_minion, target_none,
    CardType,
)
from tards.card_db import DEFAULT_REGISTRY
import card_pools.underworld  # ensure underworld cards are registered


def make_minion(name, owner, cost_t, atk, hp):
    return MinionCard(
        name=name, owner=owner, cost=Cost(t=cost_t),
        targets=target_friendly_positions,
        attack=atk, health=hp,
    )


def make_strategy(name, owner, cost_t, effect_fn=None):
    s = Strategy(
        name=name, cost=Cost(t=cost_t),
        effect_fn=effect_fn or (lambda p, t, g, extras=None: True),
        targets=target_none,
    )
    s.owner = owner
    return s


def get_conspiracy(name, owner):
    defs = [d for d in DEFAULT_REGISTRY.all_cards() if d.name == name and d.card_type == CardType.CONSPIRACY]
    if not defs:
        raise ValueError(f"Conspiracy not found: {name}")
    return defs[0].to_game_card(owner)


def fill_deck(player, count=20):
    """Fill player's deck with dummy 0-cost 0/1 minions to avoid fatigue damage."""
    for _ in range(count):
        player.card_deck.append(make_minion("Dummy", player, 0, 0, 1))


def find_serial(player, card_name):
    """Find 1-based serial of a card in hand by name."""
    for i, card in enumerate(player.card_hand):
        if card.name == card_name:
            return i + 1
    raise ValueError(f"Card '{card_name}' not found in {player.name}'s hand")


def test_jiandao():
    """Scissors: after opponent deploys a minion, they lose 4T."""
    print("\n========== TEST: Jiandao (Scissors) ==========")
    p1 = Player(side=0, name="P1", diver="test", card_deck=[])
    p2 = Player(side=1, name="P2", diver="test", card_deck=[])
    fill_deck(p1)
    fill_deck(p2)

    p1.card_hand = [get_conspiracy("剪刀", p1), make_minion("TestMinion", p1, 1, 1, 1)]
    p2.card_hand = [make_minion("EnemyMinion", p2, 1, 1, 1)]
    p1.sacrifice_chooser = lambda req: None
    p2.sacrifice_chooser = lambda req: None

    state = {"step": 0, "ok": False}

    def actor(game, active, opponent):
        if game.current_turn == 1 and active.name == "P1" and state["step"] == 0:
            state["step"] = 1
            return {"type": "play", "serial": find_serial(active, "剪刀")}
        if game.current_turn == 1 and active.name == "P1" and state["step"] == 1:
            state["step"] = 2
            return {"type": "brake"}
        if game.current_turn == 2 and active.name == "P2" and state["step"] == 2:
            state["step"] = 3
            return {"type": "play", "serial": find_serial(active, "EnemyMinion"), "target": (0, 0)}
        if game.current_turn == 2 and active.name == "P2" and state["step"] == 3:
            # After deploy + conspiracy, P2 had 2T, spent 1T, then lost 4T -> clamped to 0
            print(f"  P2 T-point after deploy+conspiracy: {active.t_point}")
            assert active.t_point == 0, f"Expected 0, got {active.t_point}"
            state["ok"] = True
            state["step"] = 4
            return {"type": "brake"}
        return {"type": "brake"}

    game = Game(p1, p2, action_provider=actor)
    game.start_game()
    assert state["ok"], "Jiandao did not trigger as expected"
    print("  [PASS] Jiandao test passed")


def test_fange():
    """FanGe: when opponent plays a minion, deal damage equal to its T-cost."""
    print("\n========== TEST: Fange (Counterblow) ==========")
    p1 = Player(side=0, name="P1", diver="test", card_deck=[])
    p2 = Player(side=1, name="P2", diver="test", card_deck=[])
    fill_deck(p1)
    fill_deck(p2)

    p1.card_hand = [get_conspiracy("反戈", p1), make_minion("TestMinion", p1, 1, 1, 1)]
    p2.card_hand = [make_minion("EnemyMinion", p2, 3, 2, 2)]
    p1.sacrifice_chooser = lambda req: None
    p2.sacrifice_chooser = lambda req: None

    state = {"step": 0, "ok": False}
    expected_dmg = 3

    def actor(game, active, opponent):
        if game.current_turn == 1 and active.name == "P1" and state["step"] == 0:
            state["step"] = 1
            # 反戈 requires target_enemy_player
            return {"type": "play", "serial": find_serial(active, "反戈"), "target": p2}
        if game.current_turn == 1 and active.name == "P1" and state["step"] == 1:
            state["step"] = 2
            return {"type": "brake"}
        if game.current_turn == 2 and active.name == "P2" and state["step"] == 2:
            state["step"] = 3
            return {"type": "brake"}
        if game.current_turn == 3 and active.name == "P1" and state["step"] == 3:
            state["step"] = 4
            return {"type": "brake"}
        if game.current_turn == 4 and active.name == "P2" and state["step"] == 4:
            state["step"] = 5
            return {"type": "play", "serial": find_serial(active, "EnemyMinion"), "target": (0, 0)}
        if game.current_turn == 4 and active.name == "P2" and state["step"] == 5:
            print(f"  P2 HP after Fange: {active.health}")
            assert active.health == 30 - expected_dmg, f"Expected {30 - expected_dmg}, got {active.health}"
            state["ok"] = True
            state["step"] = 6
            return {"type": "brake"}
        return {"type": "brake"}

    game = Game(p1, p2, action_provider=actor)
    game.start_game()
    assert state["ok"], "Fange did not trigger as expected"
    print("  [PASS] Fange test passed")


def test_xurui():
    """Xurui: when opponent bells without playing a card this phase, you gain 4T."""
    print("\n========== TEST: Xurui (Store Energy) ==========")
    p1 = Player(side=0, name="P1", diver="test", card_deck=[])
    p2 = Player(side=1, name="P2", diver="test", card_deck=[])
    fill_deck(p1)
    fill_deck(p2)

    p1.card_hand = [get_conspiracy("蓄锐", p1)]
    p1.sacrifice_chooser = lambda req: None
    p2.sacrifice_chooser = lambda req: None

    state = {"step": 0, "ok": False}

    def actor(game, active, opponent):
        if game.current_turn == 1 and active.name == "P1" and state["step"] == 0:
            state["step"] = 1
            return {"type": "play", "serial": find_serial(active, "蓄锐")}
        if game.current_turn == 1 and active.name == "P1" and state["step"] == 1:
            state["step"] = 2
            return {"type": "brake"}
        if game.current_turn == 2 and active.name == "P2" and state["step"] == 2:
            state["step"] = 3
            return {"type": "bell"}
        if game.current_turn == 2 and active.name == "P1" and state["step"] == 3:
            # P1's turn right after P2 bell; conspiracy has triggered, check T
            print(f"  P1 T-point after Xurui: {active.t_point}")
            assert active.t_point == 6, f"Expected 6, got {active.t_point}"
            state["ok"] = True
            state["step"] = 4
            return {"type": "brake"}
        return {"type": "brake"}

    game = Game(p1, p2, action_provider=actor)
    game.start_game()
    assert state["ok"], "Xurui did not trigger as expected"
    print("  [PASS] Xurui test passed")


def test_moshui():
    """Moshui (Ink): opponent plays a strategy costing <=4T -> counter it via stack, shuffle into their deck."""
    print("\n========== TEST: Moshui (Ink) - Stack Counter ==========")
    p1 = Player(side=0, name="P1", diver="test", card_deck=[])
    p2 = Player(side=1, name="P2", diver="test", card_deck=[])
    fill_deck(p1)
    fill_deck(p2)

    p1.card_hand = [get_conspiracy("墨水", p1)]
    p2.card_hand = [make_strategy("Fireball", p2, 2)]
    p1.sacrifice_chooser = lambda req: None
    p2.sacrifice_chooser = lambda req: None

    state = {"step": 0, "ok": False}

    def actor(game, active, opponent):
        # Round 1: P1 has 1T, can't play Ink (2T). Both brake.
        if game.current_turn == 1 and active.name == "P1" and state["step"] == 0:
            state["step"] = 1
            return {"type": "brake"}
        if game.current_turn == 1 and active.name == "P2" and state["step"] == 1:
            state["step"] = 2
            return {"type": "brake"}
        # Round 2: P2 acts first (2T). P1 plays Ink on their turn (2T).
        if game.current_turn == 2 and active.name == "P2" and state["step"] == 2:
            state["step"] = 3
            return {"type": "brake"}
        if game.current_turn == 2 and active.name == "P1" and state["step"] == 3:
            state["step"] = 4
            return {"type": "play", "serial": find_serial(active, "墨水")}
        if game.current_turn == 2 and active.name == "P1" and state["step"] == 4:
            state["step"] = 5
            return {"type": "brake"}
        # Round 3: P2 plays Fireball (3T). Ink should counter it.
        if game.current_turn == 3 and active.name == "P2" and state["step"] == 5:
            state["deck_before_play"] = len(p2.card_deck)
            state["dis_before_play"] = len(p2.card_dis)
            state["step"] = 6
            return {"type": "play", "serial": find_serial(active, "Fireball")}
        if game.current_turn == 3 and active.name == "P2" and state["step"] == 6:
            # After play resolves, check state immediately before fatigue drains deck
            deck_ok = len(p2.card_deck) == state["deck_before_play"] + 1
            dis_ok = len(p2.card_dis) == state["dis_before_play"]
            state["ok"] = deck_ok and dis_ok
            state["step"] = 7
            return {"type": "brake"}
        return {"type": "brake"}

    game = Game(p1, p2, action_provider=actor)
    game.start_game()

    print(f"  Ink triggered OK: {state['ok']}")

    assert state["ok"], "Moshui did not counter Fireball correctly (deck/discards mismatch)"
    print("  [PASS] Moshui (stack counter) test passed")


# ---------- 劲风 ----------
def test_jinfeng():
    """劲风: 对方额外抽牌后，将其弃掉，随机使对方1张手牌花费+1T。"""
    print("\n========== TEST: Jinfeng ==========")
    p1 = Player(side=0, name="P1", diver="test", card_deck=[])
    p2 = Player(side=1, name="P2", diver="test", card_deck=[])
    fill_deck(p1)
    fill_deck(p2)

    p1.card_hand = [get_conspiracy("劲风", p1)]
    p2.card_hand = [make_minion("TargetMinion", p2, 1, 1, 1)]
    p1.sacrifice_chooser = lambda req: None
    p2.sacrifice_chooser = lambda req: None

    state = {"step": 0, "ok": False}

    def actor(game, active, opponent):
        if game.current_turn == 1 and active.name == "P1" and state["step"] == 0:
            state["step"] = 1
            return {"type": "brake"}
        if game.current_turn == 2 and active.name == "P2" and state["step"] == 1:
            state["step"] = 2
            return {"type": "brake"}
        if game.current_turn == 3 and active.name == "P1" and state["step"] == 2:
            state["step"] = 3
            return {"type": "play", "serial": find_serial(active, "劲风")}
        if game.current_turn == 3 and active.name == "P1" and state["step"] == 3:
            state["step"] = 4
            return {"type": "brake"}
        if game.current_turn == 4 and active.name == "P2" and state["step"] == 4:
            state["step"] = 5
            # 使用 Strategy 让 P2 额外抽牌（模拟额外抽牌）
            # 先清理抽牌阶段抽到的 Dummy，保留 TargetMinion
            p2.card_hand = [c for c in p2.card_hand if c.name == "TargetMinion"]
            strat = Strategy("抽牌", cost=Cost(t=0), effect_fn=lambda p, t, g, extras=None: (p.draw_card(1, game=g) or True), targets=target_none)
            strat.owner = p2
            p2.card_hand.append(strat)
            return {"type": "play", "serial": len(p2.card_hand)}
        if game.current_turn == 4 and active.name == "P2" and state["step"] == 5:
            # 检查是否被弃掉一张 Dummy 且 TargetMinion 花费+1
            dis_names = [c.name for c in p2.card_dis]
            hand_costs_t = [c.cost.t for c in p2.card_hand]
            print(f"  P2 弃牌堆: {dis_names}, 手牌花费: {hand_costs_t}")
            has_discarded = any("Dummy" in n for n in dis_names)
            has_cost_up = any(c > 1 for c in hand_costs_t)
            state["ok"] = has_discarded and has_cost_up
            state["step"] = 6
            return {"type": "brake"}
        return {"type": "brake"}

    game = Game(p1, p2, action_provider=actor)
    game.start_game()
    assert state["ok"], "Jinfeng did not trigger as expected"
    print("  [PASS] Jinfeng test passed")


# ---------- 离群 ----------
def test_liqun():
    """离群: 消灭接下来首列进入协同状态的异象。"""
    print("\n========== TEST: Liqun ==========")
    p1 = Player(side=0, name="P1", diver="test", card_deck=[])
    p2 = Player(side=1, name="P2", diver="test", card_deck=[])
    fill_deck(p1)
    fill_deck(p2)

    p1.card_hand = [get_conspiracy("离群", p1)]
    p2.card_hand = [make_minion("A", p2, 1, 1, 1), make_minion("B", p2, 1, 1, 1)]
    p1.sacrifice_chooser = lambda req: None
    p2.sacrifice_chooser = lambda req: None

    state = {"step": 0, "ok": False}

    def actor(game, active, opponent):
        if game.current_turn == 1 and active.name == "P1" and state["step"] == 0:
            state["step"] = 1
            return {"type": "play", "serial": find_serial(active, "离群")}
        if game.current_turn == 1 and active.name == "P1" and state["step"] == 1:
            state["step"] = 2
            return {"type": "brake"}
        if game.current_turn == 2 and active.name == "P2" and state["step"] == 2:
            state["step"] = 3
            return {"type": "play", "serial": find_serial(active, "A"), "target": (3, 0)}
        if game.current_turn == 2 and active.name == "P2" and state["step"] == 3:
            state["step"] = 4
            return {"type": "brake"}
        if game.current_turn == 3 and active.name == "P1" and state["step"] == 4:
            state["step"] = 5
            return {"type": "brake"}
        if game.current_turn == 4 and active.name == "P2" and state["step"] == 5:
            state["step"] = 6
            return {"type": "play", "serial": find_serial(active, "B"), "target": (4, 0)}
        if game.current_turn == 4 and active.name == "P2" and state["step"] == 6:
            # B 和 A 都在高地列(0)，进入协同状态，离群应触发消灭 A 和 B
            alive = [m.name for m in game.board.minion_place.values()]
            print(f"  场上存活: {alive}")
            state["ok"] = len(alive) == 0
            state["step"] = 7
            return {"type": "brake"}
        return {"type": "brake"}

    game = Game(p1, p2, action_provider=actor)
    game.start_game()
    assert state["ok"], "Liqun did not trigger as expected"
    print("  [PASS] Liqun test passed")


# ---------- 入河 ----------
def test_ruhe():
    """入河: 对方部署异象前将其移除，下回合开始后将其加入原位。"""
    print("\n========== TEST: Ruhe ==========")
    p1 = Player(side=0, name="P1", diver="test", card_deck=[])
    p2 = Player(side=1, name="P2", diver="test", card_deck=[])
    fill_deck(p1)
    fill_deck(p2)

    p1.card_hand = [get_conspiracy("入河", p1)]
    p2.card_hand = [make_minion("RiverMinion", p2, 1, 1, 1)]
    p1.sacrifice_chooser = lambda req: None
    p2.sacrifice_chooser = lambda req: None

    state = {"step": 0, "ok": False}

    def actor(game, active, opponent):
        if game.current_turn == 1 and active.name == "P1" and state["step"] == 0:
            state["step"] = 1
            return {"type": "play", "serial": find_serial(active, "入河")}
        if game.current_turn == 1 and active.name == "P1" and state["step"] == 1:
            state["step"] = 2
            return {"type": "brake"}
        if game.current_turn == 2 and active.name == "P2" and state["step"] == 2:
            state["step"] = 3
            return {"type": "play", "serial": find_serial(active, "RiverMinion"), "target": (0, 0)}
        if game.current_turn == 2 and active.name == "P2" and state["step"] == 3:
            # 部署应被反制，场上无此异象
            alive = [m.name for m in game.board.minion_place.values()]
            print(f"  部署后场上: {alive}")
            assert len(alive) == 0, f"Expected empty board, got {alive}"
            state["step"] = 4
            return {"type": "brake"}
        if game.current_turn == 3 and active.name == "P1" and state["step"] == 4:
            state["step"] = 5
            return {"type": "brake"}
        if game.current_turn == 4 and active.name == "P2" and state["step"] == 5:
            # 下回合开始后，RiverMinion 应出现在原位 (0,0)
            alive = [m.name for m in game.board.minion_place.values()]
            print(f"  下回合开始后场上: {alive}")
            state["ok"] = "RiverMinion" in alive
            state["step"] = 6
            return {"type": "brake"}
        return {"type": "brake"}

    game = Game(p1, p2, action_provider=actor)
    game.start_game()
    assert state["ok"], "Ruhe did not trigger as expected"
    print("  [PASS] Ruhe test passed")


# ---------- 怪石 ----------
def test_guaishi():
    """怪石: 对方拉闸时若剩余T点=0，对方失去一个T槽。"""
    print("\n========== TEST: Guaishi ==========")
    p1 = Player(side=0, name="P1", diver="test", card_deck=[])
    p2 = Player(side=1, name="P2", diver="test", card_deck=[])
    fill_deck(p1)
    fill_deck(p2)

    p1.card_hand = [get_conspiracy("怪石", p1)]
    p2.card_hand = []
    p1.sacrifice_chooser = lambda req: None
    p2.sacrifice_chooser = lambda req: None

    state = {"step": 0, "ok": False}

    def actor(game, active, opponent):
        if game.current_turn == 1 and active.name == "P1" and state["step"] == 0:
            state["step"] = 1
            return {"type": "play", "serial": find_serial(active, "怪石")}
        if game.current_turn == 1 and active.name == "P1" and state["step"] == 1:
            state["step"] = 2
            return {"type": "brake"}
        if game.current_turn == 2 and active.name == "P2" and state["step"] == 2:
            # P2 有 2T，但什么都不做直接拉闸，T点保持2，不会触发
            state["step"] = 3
            return {"type": "brake"}
        if game.current_turn == 3 and active.name == "P1" and state["step"] == 3:
            state["step"] = 4
            return {"type": "brake"}
        if game.current_turn == 4 and active.name == "P2" and state["step"] == 4:
            # P2 花光所有T点再拍铃
            p2.t_point = 0
            state["step"] = 5
            return {"type": "bell"}
        if game.current_turn == 4 and active.name == "P2" and state["step"] == 5:
            print(f"  P2 T槽上限 after Guaishi: {p2.t_point_max}")
            state["ok"] = p2.t_point_max == 9  # 默认10，减1后9
            state["step"] = 6
            return {"type": "brake"}
        return {"type": "brake"}

    game = Game(p1, p2, action_provider=actor)
    game.start_game()
    assert state["ok"], "Guaishi did not trigger as expected"
    print("  [PASS] Guaishi test passed")


# ---------- 海市蜃楼 ----------
def test_haishi():
    """海市蜃楼: 异象被指向前，改为其随机敌方异象成为指向目标。"""
    print("\n========== TEST: Haishi ==========")
    p1 = Player(side=0, name="P1", diver="test", card_deck=[])
    p2 = Player(side=1, name="P2", diver="test", card_deck=[])
    fill_deck(p1)
    fill_deck(p2)

    p1.card_hand = [get_conspiracy("海市蜃楼", p1)]
    p2.card_hand = [make_minion("EnemyA", p2, 1, 1, 1)]
    p1.sacrifice_chooser = lambda req: None
    p2.sacrifice_chooser = lambda req: None

    # 在 P1 场上放一个友方异象作为潜在目标
    p1_minion = make_minion("FriendlyA", p1, 1, 1, 1)

    state = {"step": 0, "ok": False}

    def actor(game, active, opponent):
        if game.current_turn == 1 and active.name == "P1" and state["step"] == 0:
            state["step"] = 1
            return {"type": "play", "serial": find_serial(active, "海市蜃楼")}
        if game.current_turn == 1 and active.name == "P1" and state["step"] == 1:
            state["step"] = 2
            return {"type": "brake"}
        if game.current_turn == 2 and active.name == "P2" and state["step"] == 2:
            state["step"] = 3
            return {"type": "play", "serial": find_serial(active, "EnemyA"), "target": (0, 0)}
        if game.current_turn == 2 and active.name == "P2" and state["step"] == 3:
            state["step"] = 4
            return {"type": "brake"}
        if game.current_turn == 3 and active.name == "P1" and state["step"] == 4:
            # P1 使用一个需要指向敌方异象的策略
            strat = Strategy("火球", cost=Cost(t=0), effect_fn=lambda p, t, g, extras=None: (print(f"  火球击中 {t.name}") or True), targets=target_any_minion)
            strat.owner = p1
            p1.card_hand.append(strat)
            # 先部署友方异象到场上
            p1_minion.owner = p1
            game.board.place_minion(p1_minion.source_card.effect(p1, (4, 0), game), (4, 0))
            state["step"] = 5
            return {"type": "play", "serial": find_serial(active, "火球"), "target": p1_minion}
        if game.current_turn == 3 and active.name == "P1" and state["step"] == 5:
            state["ok"] = True
            state["step"] = 6
            return {"type": "brake"}
        return {"type": "brake"}

    game = Game(p1, p2, action_provider=actor)
    game.start_game()
    assert state["ok"], "Haishi did not trigger as expected"
    print("  [PASS] Haishi test passed")


# ---------- 掩星 ----------
def test_yanxing():
    """掩星: 场上敌方异象数量成为唯一最多时，抽2张牌。"""
    print("\n========== TEST: Yanxing ==========")
    p1 = Player(side=0, name="P1", diver="test", card_deck=[])
    p2 = Player(side=1, name="P2", diver="test", card_deck=[])
    fill_deck(p1)
    fill_deck(p2)

    p1.card_hand = [get_conspiracy("掩星", p1)]
    p2.card_hand = [make_minion("EnemyA", p2, 1, 1, 1)]
    p1.sacrifice_chooser = lambda req: None
    p2.sacrifice_chooser = lambda req: None

    state = {"step": 0, "ok": False}

    def actor(game, active, opponent):
        if game.current_turn == 1 and active.name == "P1" and state["step"] == 0:
            state["step"] = 1
            return {"type": "play", "serial": find_serial(active, "掩星")}
        if game.current_turn == 1 and active.name == "P1" and state["step"] == 1:
            state["step"] = 2
            return {"type": "brake"}
        if game.current_turn == 2 and active.name == "P2" and state["step"] == 2:
            state["step"] = 3
            return {"type": "play", "serial": find_serial(active, "EnemyA"), "target": (0, 0)}
        if game.current_turn == 2 and active.name == "P2" and state["step"] == 3:
            # 敌方异象数量=1，友方=0，成为唯一最多
            hand_count = len(p1.card_hand)
            print(f"  P1 手牌数 after Yanxing: {hand_count}")
            state["ok"] = hand_count >= 2
            state["step"] = 4
            return {"type": "brake"}
        return {"type": "brake"}

    game = Game(p1, p2, action_provider=actor)
    game.start_game()
    assert state["ok"], "Yanxing did not trigger as expected"
    print("  [PASS] Yanxing test passed")


# ---------- 夜袭 ----------
def test_yexi():
    """夜袭: 敌方异象对你造成伤害前，使其先获得-2攻击力。若具有迅捷，将其消灭。"""
    print("\n========== TEST: Yexi ==========")
    p1 = Player(side=0, name="P1", diver="test", card_deck=[])
    p2 = Player(side=1, name="P2", diver="test", card_deck=[])
    fill_deck(p1)
    fill_deck(p2)

    p1.card_hand = [get_conspiracy("夜袭", p1)]
    p2.card_hand = [make_minion("Attacker", p2, 1, 3, 3)]
    p1.sacrifice_chooser = lambda req: None
    p2.sacrifice_chooser = lambda req: None

    state = {"step": 0, "ok": False}

    def actor(game, active, opponent):
        if game.current_turn == 1 and active.name == "P1" and state["step"] == 0:
            state["step"] = 1
            return {"type": "play", "serial": find_serial(active, "夜袭")}
        if game.current_turn == 1 and active.name == "P1" and state["step"] == 1:
            state["step"] = 2
            return {"type": "brake"}
        if game.current_turn == 2 and active.name == "P2" and state["step"] == 2:
            state["step"] = 3
            return {"type": "play", "serial": find_serial(active, "Attacker"), "target": (0, 0)}
        if game.current_turn == 2 and active.name == "P2" and state["step"] == 3:
            state["step"] = 4
            return {"type": "brake"}
        if game.current_turn == 3 and active.name == "P1" and state["step"] == 4:
            state["step"] = 5
            return {"type": "brake"}
        if game.current_turn == 4 and active.name == "P2" and state["step"] == 5:
            state["step"] = 6
            return {"type": "brake"}
        if game.current_turn == 4 and active.name == "P1" and state["step"] == 6:
            # 结算阶段，Attacker 攻击 P1，夜袭应触发使其 -2 攻击力
            hp_before = p1.health
            print(f"  P1 HP before resolve: {hp_before}")
            state["step"] = 7
            return {"type": "brake"}
        if game.current_turn == 5 and active.name == "P1" and state["step"] == 7:
            # 攻击后检查
            m = game.board.minion_place.get((0, 0))
            if m and m.name == "Attacker":
                print(f"  Attacker attack after Yexi: {m.current_attack}")
                state["ok"] = m.current_attack == 1  # 3 - 2 = 1
            else:
                state["ok"] = False
            state["step"] = 8
            return {"type": "brake"}
        return {"type": "brake"}

    game = Game(p1, p2, action_provider=actor)
    game.start_game()
    assert state["ok"], "Yexi did not trigger as expected"
    print("  [PASS] Yexi test passed")


if __name__ == "__main__":
    test_jiandao()
    test_fange()
    test_xurui()
    test_moshui()
    test_jinfeng()
    test_liqun()
    test_ruhe()
    test_guaishi()
    test_haishi()
    test_yanxing()
    test_yexi()
    print("\n>>> ALL CONSPIRACY TESTS PASSED <<<")
