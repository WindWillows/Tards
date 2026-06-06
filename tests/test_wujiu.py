"""兀鹫测试"""

from __future__ import annotations

from tests.assertions import (
    assert_minion_exists,
    assert_minion_hp,
    assert_player_hp,
)
from tests.harness import GameHarness


def test_wujiu_triggers_on_minion_target_hp_ge_2():
    """兀鹫：友方异象攻击敌方异象，目标HP≥2，触发失去1HP。"""
    h = GameHarness()
    p1, p2 = h.players

    # p1 部署兀鹫和友方攻击者
    h.deploy("兀鹫", p1, (4, 2))
    h.deploy("蛇", p1, (4, 1))  # 蛇 1/4，有攻击力

    # p2 部署一个高血量目标
    h.deploy("地鼠", p2, (0, 1))  # 地鼠 0/6
    mouse = h.at((0, 1))
    assert_minion_hp(h.game, (0, 1), 6)

    # 让蛇攻击地鼠
    snake = h.at((4, 1))
    snake.attack_target(mouse)

    # 蛇造成1点伤害，地鼠剩余5/6
    # 兀鹫触发：地鼠HP≥2，再失去1HP，剩余4/6
    assert_minion_hp(h.game, (0, 1), 4)


def test_wujiu_no_trigger_on_minion_target_hp_lt_2():
    """兀鹫：友方异象攻击敌方异象，目标HP<2，不触发。"""
    h = GameHarness()
    p1, p2 = h.players

    h.deploy("兀鹫", p1, (4, 2))
    h.deploy("蛇", p1, (4, 1))

    # p2 部署一个目标并将其设为1血
    h.deploy("地鼠", p2, (0, 1))  # 地鼠 0/6
    mouse = h.at((0, 1))
    mouse.current_health = 1  # 直接设为1血
    assert_minion_hp(h.game, (0, 1), 1)

    # 让蛇攻击地鼠
    snake = h.at((4, 1))
    snake.attack_target(mouse)

    # 蛇造成1点伤害，地鼠死亡
    # 兀鹫不触发：目标HP<2
    assert h.game.board.get_minion_at((0, 1)) is None  # 已被消灭


def test_wujiu_triggers_on_player_target_hp_ge_2():
    """兀鹫：友方异象攻击敌方玩家，玩家HP≥2，触发失去1HP。"""
    h = GameHarness()
    p1, p2 = h.players

    h.deploy("兀鹫", p1, (4, 2))
    h.deploy("蛇", p1, (4, 1))

    # p2 当前HP=30
    assert_player_hp(p2, 30)

    # 让蛇攻击玩家
    snake = h.at((4, 1))
    snake.attack_target(p2)

    # 蛇造成1点伤害，p2 剩余29
    # 兀鹫触发：p2 HP≥2，再失去1HP，剩余28
    assert_player_hp(p2, 28)


def test_wujiu_no_trigger_on_enemy_attack():
    """兀鹫：敌方异象攻击时，不应触发兀鹫效果。"""
    h = GameHarness()
    p1, p2 = h.players

    h.deploy("兀鹫", p1, (4, 2))

    # p2 部署攻击者
    h.deploy("蛇", p2, (0, 1))  # 敌方蛇 1/4

    # 让敌方蛇直接攻击友方玩家 p1
    assert_player_hp(p1, 30)
    snake = h.at((0, 1))
    snake.attack_target(p1)

    # 敌方攻击不应触发友方兀鹫
    # 蛇对玩家造成2点伤害（伤害+1），无额外效果
    assert_player_hp(p1, 28)
