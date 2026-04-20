import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

"""
离散卡包 EventBus 重写验证

测试场景：
1. 铁傀儡：受到等于HP的伤害时被免除
2. 狐狸：受到大于HP的伤害时被免除
3. 僵尸：造成伤害时吸血
4. 骷髅：攻击前改目标为HP最低敌方
5. 滴水石锥：受伤时反伤对手
"""

from tards import Game, Player, MinionCard, Cost, target_friendly_positions
from tards.board import Board


def make_test_deck(owner, name, atk, hp, keywords=None):
    """创建测试用异象卡。"""
    return [
        MinionCard(
            name=name,
            owner=owner,
            cost=Cost(t=1),
            targets=target_friendly_positions,
            attack=atk,
            health=hp,
            keywords=keywords or {},
        )
        for _ in range(4)
    ]


def test_iron_golem():
    """铁傀儡：受到等于HP的单次伤害时，将其免除。"""
    print("\n=== 测试：铁傀儡 ===")
    p1 = Player(side=0, name="P1", diver="测试", card_deck=[])
    p2 = Player(side=1, name="P2", diver="测试", card_deck=[])
    game = Game(p1, p2)
    p1.sacrifice_chooser = lambda req: None
    p2.sacrifice_chooser = lambda req: None

    # 手动创建铁傀儡并部署
    from tards.card_db import DEFAULT_REGISTRY
    card_def = DEFAULT_REGISTRY.get("铁傀儡")
    assert card_def, "铁傀儡定义不存在"
    card = card_def.to_game_card(p1)
    card.effect(p1, (3, 0), game)
    golem = game.board.get_minion_at((3, 0))
    assert golem, "铁傀儡部署失败"
    assert golem.current_health == 6, f"铁傀儡HP应为6，实际{golem.current_health}"

    # 造成6点伤害（等于HP）
    golem.take_damage(6)
    assert golem.is_alive(), "铁傀儡应存活（等额伤害被免除）"
    assert golem.current_health == 6, f"铁傀儡HP应保持6，实际{golem.current_health}"

    # 造成5点伤害（不等于HP），应受伤
    golem.take_damage(5)
    assert golem.current_health == 1, f"铁傀儡HP应为1，实际{golem.current_health}"
    print("  通过：等额伤害被免除，非等额伤害正常结算")


def test_fox():
    """狐狸：受到大于其HP的单次伤害时，将其免除。"""
    print("\n=== 测试：狐狸 ===")
    p1 = Player(side=0, name="P1", diver="测试", card_deck=[])
    p2 = Player(side=1, name="P2", diver="测试", card_deck=[])
    game = Game(p1, p2)
    p1.sacrifice_chooser = lambda req: None
    p2.sacrifice_chooser = lambda req: None

    from tards.card_db import DEFAULT_REGISTRY
    card_def = DEFAULT_REGISTRY.get("狐狸")
    assert card_def, "狐狸定义不存在"
    card = card_def.to_game_card(p1)
    card.effect(p1, (3, 0), game)
    fox = game.board.get_minion_at((3, 0))
    assert fox, "狐狸部署失败"
    assert fox.current_health == 2

    # 造成3点伤害（大于HP）
    fox.take_damage(3)
    assert fox.is_alive(), "狐狸应存活（超额伤害被免除）"
    assert fox.current_health == 2, f"狐狸HP应保持2，实际{fox.current_health}"

    # 造成1点伤害（不大于HP）
    fox.take_damage(1)
    assert fox.current_health == 1, f"狐狸HP应为1，实际{fox.current_health}"
    print("  通过：超额伤害被免除，非超额伤害正常结算")


def test_zombie_leech():
    """僵尸：造成伤害时，你获得等量HP。"""
    print("\n=== 测试：僵尸 ===")
    p1 = Player(side=0, name="P1", diver="测试", card_deck=[])
    p2 = Player(side=1, name="P2", diver="测试", card_deck=[])
    game = Game(p1, p2)
    p1.sacrifice_chooser = lambda req: None
    p2.sacrifice_chooser = lambda req: None

    from tards.card_db import DEFAULT_REGISTRY
    card_def = DEFAULT_REGISTRY.get("僵尸")
    assert card_def, "僵尸定义不存在"
    card = card_def.to_game_card(p1)
    card.effect(p1, (3, 0), game)
    zombie = game.board.get_minion_at((3, 0))
    assert zombie, "僵尸部署失败"

    # 在敌方部署一个目标
    p2_card = MinionCard(name="靶子", owner=p2, cost=Cost(t=1), targets=target_friendly_positions, attack=1, health=5)
    p2_card.effect(p2, (0, 0), game)
    target = game.board.get_minion_at((0, 0))
    assert target

    p1.health = 20
    before_hp = p1.health
    # 僵尸攻击目标
    zombie.attack_target(target)
    actual_damage = 5 - target.current_health
    expected_hp = before_hp + actual_damage
    assert p1.health == expected_hp, f"僵尸吸血后玩家HP应为{expected_hp}，实际{p1.health}"
    print(f"  通过：僵尸造成{actual_damage}点伤害，玩家恢复{actual_damage}HP")


def test_skeleton_retarget():
    """骷髅：攻击前，改为对HP最低的敌方异象造成等量伤害。"""
    print("\n=== 测试：骷髅 ===")
    p1 = Player(side=0, name="P1", diver="测试", card_deck=[])
    p2 = Player(side=1, name="P2", diver="测试", card_deck=[])
    game = Game(p1, p2)
    p1.sacrifice_chooser = lambda req: None
    p2.sacrifice_chooser = lambda req: None

    from tards.card_db import DEFAULT_REGISTRY
    card_def = DEFAULT_REGISTRY.get("骷髅")
    assert card_def, "骷髅定义不存在"
    card = card_def.to_game_card(p1)
    card.effect(p1, (3, 0), game)
    skeleton = game.board.get_minion_at((3, 0))
    assert skeleton, "骷髅部署失败"

    # 部署两个敌方异象：一个满血，一个残血
    p2_card1 = MinionCard(name="满血", owner=p2, cost=Cost(t=1), targets=target_friendly_positions, attack=1, health=5)
    p2_card1.effect(p2, (0, 0), game)
    full = game.board.get_minion_at((0, 0))

    p2_card2 = MinionCard(name="残血", owner=p2, cost=Cost(t=1), targets=target_friendly_positions, attack=1, health=1)
    p2_card2.effect(p2, (0, 1), game)
    low = game.board.get_minion_at((0, 1))

    # 骷髅攻击（应该改目标到残血）
    # 需要设置一个假目标来触发 before_attack
    skeleton.attack_target(full)
    # 由于 before_attack 改目标，实际应该打残血
    assert low.current_health <= 0, f"残血应被消灭，实际HP={low.current_health}"
    assert full.current_health == 5, f"满血不应受伤，实际HP={full.current_health}"
    print("  通过：骷髅攻击前自动改目标到HP最低的敌方异象")


def test_dripstone():
    """滴水石锥：受到伤害时，对对手造成1点伤害。"""
    print("\n=== 测试：滴水石锥 ===")
    p1 = Player(side=0, name="P1", diver="测试", card_deck=[])
    p2 = Player(side=1, name="P2", diver="测试", card_deck=[])
    game = Game(p1, p2)
    p1.sacrifice_chooser = lambda req: None
    p2.sacrifice_chooser = lambda req: None

    from tards.card_db import DEFAULT_REGISTRY
    card_def = DEFAULT_REGISTRY.get("滴水石锥")
    assert card_def, "滴水石锥定义不存在"
    card = card_def.to_game_card(p1)
    card.effect(p1, (3, 0), game)
    drip = game.board.get_minion_at((3, 0))
    assert drip, "滴水石锥部署失败"

    p2.health = 30
    before_p2_hp = p2.health
    drip.take_damage(1)
    assert p2.health == before_p2_hp - 1, f"对手应受到1点反伤，实际HP={p2.health}"
    print("  通过：滴水石锥受伤时对对手造成1点伤害")


if __name__ == "__main__":
    import card_pools  # 触发卡牌注册
    test_iron_golem()
    test_fox()
    test_zombie_leech()
    test_skeleton_retarget()
    test_dripstone()
    print("\n>>> 全部离散卡包 EventBus 测试通过 <<<")
