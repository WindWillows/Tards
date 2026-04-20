import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

"""
测试三张"对战"卡牌：僵尸猪人、怪物猎人、鸮(铁)
直接测试效果函数，绕过 play_card 的费用检查。
"""

from tards import Game, Player
from tards.cards import Minion, MinionCard
from tards.board import Board
from tards.cost import Cost
from tards.targets import target_friendly_positions

from card_pools.discrete_effects import (
    _jiangshizhuren_special,
    _guaiwulieren_strategy,
)
from card_pools.underworld_effects import _xiao_special


def _make_minion(name, owner, atk, hp, pos, game):
    """直接创建一个 Minion 并放置到场上。"""
    minion = Minion(
        name=name,
        owner=owner,
        position=pos,
        attack=atk,
        health=hp,
        source_card=None,
        board=game.board,
        keywords={},
    )
    game.board.place_minion(minion, pos)
    return minion


def test_jiangshizhuren():
    """测试僵尸猪人：部署后与敌方异象对战，若消灭则-1攻。"""
    print("\n========== 测试 僵尸猪人 ==========")
    p1 = Player(0, "玩家A", "测试", [])
    p2 = Player(1, "玩家B", "测试", [])
    g = Game(p1, p2)
    for p in g.players:
        p.board_ref = g.board

    # 敌方 2/2 小兵
    enemy = _make_minion("敌方小兵", p2, 2, 2, (1, 2), g)
    print(f"  敌方小兵 HP={enemy.current_health}")

    # 僵尸猪人 4/4
    zhuren = _make_minion("僵尸猪人", p1, 4, 4, (3, 2), g)
    print(f"  僵尸猪人攻击={zhuren.current_attack}")

    # 模拟部署效果：指向敌方小兵
    _jiangshizhuren_special(zhuren, p1, g, extras=[enemy])

    print(f"  战后敌方小兵存活={enemy.is_alive()}")
    print(f"  战后僵尸猪人攻击={zhuren.current_attack}")
    if not enemy.is_alive() and zhuren.current_attack == 3:
        print("  [OK] 僵尸猪人测试通过")
    else:
        print("  [FAIL] 测试未通过")


def test_guaiwulieren():
    """测试怪物猎人：使友方生物+1/+3，然后与敌方对战。"""
    print("\n========== 测试 怪物猎人 ==========")
    p1 = Player(0, "玩家A", "测试", [])
    p2 = Player(1, "玩家B", "测试", [])
    g = Game(p1, p2)
    for p in g.players:
        p.board_ref = g.board

    friendly = _make_minion("友方小兵", p1, 1, 1, (3, 2), g)
    enemy = _make_minion("敌方小兵", p2, 2, 2, (1, 2), g)
    print(f"  友方小兵 初始={friendly.current_attack}/{friendly.current_health}")
    print(f"  敌方小兵 初始={enemy.current_attack}/{enemy.current_health}")

    # 模拟打出：target=友方，extra_targets=[敌方]
    ok = _guaiwulieren_strategy(p1, friendly, g, extras=[enemy])
    print(f"  效果执行结果: {ok}")
    print(f"  友方小兵 战后={friendly.current_attack}/{friendly.current_health}")
    print(f"  敌方小兵 存活={enemy.is_alive()}")
    # buff 后 attack=2, max_health=4; 对战可能受伤，所以 current_health 在 2~4 之间都算对
    if friendly.current_attack == 2 and 2 <= friendly.current_health <= 4:
        print("  [OK] buff 正确")
    else:
        print("  [FAIL] buff 异常")


def test_xiao():
    """测试鸮(铁)：攻击时改为与目标对战，消灭后恢复HP=目标攻击力。"""
    print("\n========== 测试 鸮(铁) ==========")
    p1 = Player(0, "玩家A", "测试", [])
    p2 = Player(1, "玩家B", "测试", [])
    g = Game(p1, p2)
    for p in g.players:
        p.board_ref = g.board

    # 敌方 2/1 小兵（容易被消灭）
    enemy = _make_minion("敌方小兵", p2, 2, 1, (1, 2), g)
    print(f"  敌方小兵 初始={enemy.current_attack}/{enemy.current_health}")

    # 鸮 4/5
    xiao = _make_minion("鸮(铁)", p1, 4, 5, (3, 2), g)
    print(f"  鸮(铁) 初始HP={xiao.current_health}")

    # 注册 special 效果（攻击时拦截）
    _xiao_special(xiao, p1, g)

    # 模拟攻击：调用 attack_target
    xiao.attack_target(enemy)

    print(f"  战后敌方小兵存活={enemy.is_alive()}")
    print(f"  战后鸮(铁) HP={xiao.current_health}")
    # 原始5HP，受2伤剩3，恢复2HP => 5HP
    if not enemy.is_alive() and xiao.current_health == 5:
        print("  [OK] 鸮(铁)测试通过")
    else:
        print("  [FAIL] 测试未通过")


if __name__ == "__main__":
    test_jiangshizhuren()
    test_guaiwulieren()
    test_xiao()
    print("\n测试结束")
