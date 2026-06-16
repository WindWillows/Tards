"""凋零骷髅与潜行者测试"""

from __future__ import annotations

from tests.assertions import (
    assert_board_empty,
    assert_hand_contains,
    assert_hand_missing,
    assert_minion_exists,
    assert_minion_hp,
    assert_minion_attack,
    assert_player_hp,
)
from tests.event_spy import EventSpy
from tests.harness import GameHarness

from tards.constants import EVENT_DEATH, EVENT_TURN_END


# =============================================================================
# 潜行者测试
# =============================================================================

def test_qianxingzhe_kills_nearest_enemy():
    """潜行者：部署时消灭距离最近的敌方异象。"""
    h = GameHarness()
    p1, p2 = h.players

    # p2 部署两个异象（火把不能放在水路，改为河岸）
    h.deploy("书架", p2, (0, 1))
    h.deploy("火把", p2, (0, 3))
    assert_minion_exists(h.game, (0, 1), "书架")
    assert_minion_exists(h.game, (0, 3), "火把")

    # p1 在 (4,1) 部署潜行者，最近的是 (0,1) 的书架（距离4）
    h.deploy("潜行者", p1, (4, 1))

    # 书架应被消灭，火把存活
    assert_board_empty(h.game, (0, 1))
    assert_minion_exists(h.game, (0, 3), "火把")


def test_qianxingzhe_prefers_enemy_when_tied():
    """潜行者：距离相同时优先消灭敌方异象。"""
    h = GameHarness()
    p1, p2 = h.players

    # p1 友方在 (4,0)，p2 敌方在 (0,2)
    # (3,2) 到 (4,0) = 1+2=3，到 (0,2) = 3+0=3
    h.deploy("书架", p1, (4, 0))
    h.deploy("火把", p2, (0, 2))

    h.deploy("潜行者", p1, (3, 2))

    # 距离相同，优先敌方火把
    assert_minion_exists(h.game, (4, 0), "书架")
    assert_board_empty(h.game, (0, 2))


def test_qianxingzhe_no_other_minions():
    """潜行者：场上无其他异象时，部署无事发生。"""
    h = GameHarness()
    p1, p2 = h.players

    h.deploy("潜行者", p1, (4, 2))
    assert_minion_exists(h.game, (4, 2), "潜行者")


# =============================================================================
# 凋零骷髅测试
# =============================================================================

def test_diaolingkulou_deathrattle_gives_token():
    """凋零骷髅：亡语触发时将"凋零骷髅头"加入手牌。"""
    h = GameHarness()
    p1, p2 = h.players

    h.deploy("凋零骷髅", p1, (4, 2))
    assert_minion_exists(h.game, (4, 2), "凋零骷髅")
    assert_hand_missing(p1, "凋零骷髅头")

    # 消灭凋零骷髅
    skull = h.at((4, 2))
    skull.current_health = 0
    skull.minion_death()

    # 处理死亡队列
    h.game.effect_queue.resolve_stack()
    h.game.effect_queue._process_queue()

    assert_hand_contains(p1, "凋零骷髅头")


def test_diaolingkulou_damage_debuffs_target_at_turn_end():
    """凋零骷髅：造成伤害后，目标异象在回合结束时获得-1/1。"""
    h = GameHarness()
    p1, p2 = h.players

    h.deploy("凋零骷髅", p1, (4, 2))
    h.deploy("萤石", p2, (0, 2))
    # 萤石基础 0/4，给加血避免被一击必杀
    fluorite = h.at((0, 2))
    from card_pools.effect_utils import buff_minion, heal_minion
    buff_minion(fluorite, 0, 5, permanent=True)
    heal_minion(fluorite, 5)
    assert_minion_attack(h.game, (0, 2), 0)
    assert_minion_hp(h.game, (0, 2), 9)

    # 让凋零骷髅攻击萤石
    skull = h.at((4, 2))
    skull.attack_target(fluorite)
    # 萤石受到3点伤害，剩余6/9
    assert_minion_hp(h.game, (0, 2), 6)

    # 发射回合结束事件，触发凋零骷髅的 debuff
    h.end_turn(p1, p2)

    # 萤石应获得永久-1/1
    assert_minion_attack(h.game, (0, 2), -1)
    # 当前生命值 6，最大生命值变为 8（9-1），所以 current_health 保持 6
    assert_minion_hp(h.game, (0, 2), 6)


def test_diaolingkulou_damage_to_player_mills_card():
    """凋零骷髅：对敌方玩家造成伤害后，移除其卡组顶的1张牌。"""
    h = GameHarness()
    p1, p2 = h.players

    # 给p2牌库放几张牌
    from card_pools.effect_utils import create_card_by_name
    for _ in range(3):
        card = create_card_by_name("书架", p2)
        p2.card_deck.append(card)
    deck_before = len(p2.card_deck)

    h.deploy("凋零骷髅", p1, (4, 2))

    # 让凋零骷髅直接攻击玩家
    skull = h.at((4, 2))
    skull.attack_target(p2)
    assert_player_hp(p2, 27)

    # 发射回合结束事件
    h.end_turn(p1, p2)

    # p2 牌库应被移除1张
    assert len(p2.card_deck) == deck_before - 1, \
        f"牌库应从{deck_before}变为{deck_before-1}，实际{len(p2.card_deck)}"
