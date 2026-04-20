from tards import (
    Cost,
    CardType,
    Pack,
    Rarity,
    register_card,
    Deck,
    Player,
    Game,
    target_friendly_positions,
    target_enemy_minions,
    target_none,
    target_self,
)


def setup_sample_registry():
    """注册一些示例卡牌用于构筑演示。"""

    # === 通用卡包 ===
    register_card(
        name="小兵",
        cost_str="1T",
        card_type=CardType.MINION,
        pack=Pack.GENERAL,
        rarity=Rarity.IRON,
        attack=1,
        health=1,
        targets_fn=target_friendly_positions,
    )
    register_card(
        name="哨兵",
        cost_str="2T",
        card_type=CardType.MINION,
        pack=Pack.GENERAL,
        rarity=Rarity.BRONZE,
        attack=2,
        health=3,
        targets_fn=target_friendly_positions,
    )
    register_card(
        name="急救",
        cost_str="1T",
        card_type=CardType.STRATEGY,
        pack=Pack.GENERAL,
        rarity=Rarity.BRONZE,
        effect_fn=lambda p, t, g: t.health_change(3) or True if isinstance(t, Player) else False,
        targets_fn=target_self,
    )
    register_card(
        name="增援",
        cost_str="1T",
        card_type=CardType.STRATEGY,
        pack=Pack.GENERAL,
        rarity=Rarity.IRON,
        effect_fn=lambda p, t, g: (p.draw_card(1, game=g), True)[1],
        targets_fn=target_none,
    )
    register_card(
        name="火球",
        cost_str="2T",
        card_type=CardType.STRATEGY,
        pack=Pack.GENERAL,
        rarity=Rarity.BRONZE,
        effect_fn=lambda p, t, g: (t.take_damage(2), True)[1] if hasattr(t, 'take_damage') else False,
        targets_fn=target_enemy_minions,
    )
    register_card(
        name="游侠",
        cost_str="2T",
        card_type=CardType.MINION,
        pack=Pack.GENERAL,
        rarity=Rarity.BRONZE,
        attack=2,
        health=1,
        keywords={"迅捷": True},
        targets_fn=target_friendly_positions,
    )

    # === 离散卡包 ===
    register_card(
        name="火把",
        cost_str="3T",
        card_type=CardType.MINION,
        pack=Pack.DISCRETE,
        rarity=Rarity.BRONZE,
        immersion_level=1,
        attack=2,
        health=5,
        targets_fn=target_friendly_positions,
    )
    register_card(
        name="萤石",
        cost_str="3T",
        card_type=CardType.MINION,
        pack=Pack.DISCRETE,
        rarity=Rarity.SILVER,
        immersion_level=1,
        attack=0,
        health=4,
        targets_fn=target_friendly_positions,
    )
    register_card(
        name="烈焰人",
        cost_str="1D",
        card_type=CardType.MINION,
        pack=Pack.DISCRETE,
        rarity=Rarity.SILVER,
        immersion_level=2,
        attack=4,
        health=2,
        keywords={"迅捷": True},
        targets_fn=target_friendly_positions,
    )
    register_card(
        name="高炉",
        cost_str="4I",
        card_type=CardType.MINION,
        pack=Pack.DISCRETE,
        rarity=Rarity.GOLD,
        immersion_level=3,
        attack=5,
        health=5,
        targets_fn=target_friendly_positions,
    )
    register_card(
        name="铁锭",
        cost_str="2CT",
        card_type=CardType.MINERAL,
        pack=Pack.DISCRETE,
        rarity=Rarity.IRON,
        immersion_level=1,
        mineral_type="I",
        stack_limit=4,
    )
    register_card(
        name="精准采集",
        cost_str="1T",
        card_type=CardType.STRATEGY,
        pack=Pack.DISCRETE,
        rarity=Rarity.BRONZE,
        immersion_level=1,
        effect_fn=lambda p, t, g: True,
        targets_fn=target_none,
    )
    register_card(
        name="末影螨",
        cost_str="1I",
        card_type=CardType.MINION,
        pack=Pack.DISCRETE,
        rarity=Rarity.BRONZE,
        immersion_level=1,
        attack=1,
        health=1,
        keywords={"协同": True},
        targets_fn=target_friendly_positions,
    )
    register_card(
        name="狗",
        cost_str="2I",
        card_type=CardType.MINION,
        pack=Pack.DISCRETE,
        rarity=Rarity.BRONZE,
        immersion_level=1,
        attack=1,
        health=1,
        keywords={"协同": True, "迅捷": True},
        targets_fn=target_friendly_positions,
    )

    # === 冥刻卡包 ===
    register_card(
        name="松鼠",
        cost_str="1T",
        card_type=CardType.MINION,
        pack=Pack.UNDERWORLD,
        rarity=Rarity.IRON,
        immersion_level=1,
        attack=0,
        health=2,
        targets_fn=target_friendly_positions,
    )
    register_card(
        name="臭虫",
        cost_str="2T1B",
        card_type=CardType.MINION,
        pack=Pack.UNDERWORLD,
        rarity=Rarity.BRONZE,
        immersion_level=1,
        attack=1,
        health=6,
        keywords={"协同": True, "尖刺": 1},
        targets_fn=target_friendly_positions,
    )
    register_card(
        name="猫",
        cost_str="1T1B",
        card_type=CardType.MINION,
        pack=Pack.UNDERWORLD,
        rarity=Rarity.GOLD,
        immersion_level=1,
        attack=0,
        health=1,
        targets_fn=target_friendly_positions,
    )
    register_card(
        name="林鼠",
        cost_str="2T1B",
        card_type=CardType.MINION,
        pack=Pack.UNDERWORLD,
        rarity=Rarity.SILVER,
        immersion_level=1,
        attack=2,
        health=3,
        keywords={"丰饶": 2},
        targets_fn=target_friendly_positions,
    )
    register_card(
        name="弱狼",
        cost_str="2T1B",
        card_type=CardType.MINION,
        pack=Pack.UNDERWORLD,
        rarity=Rarity.BRONZE,
        immersion_level=1,
        attack=2,
        health=4,
        keywords={"协同": True},
        targets_fn=target_friendly_positions,
    )
    register_card(
        name="狼",
        cost_str="2T2B",
        card_type=CardType.MINION,
        pack=Pack.UNDERWORLD,
        rarity=Rarity.SILVER,
        immersion_level=2,
        attack=4,
        health=4,
        targets_fn=target_friendly_positions,
    )
    register_card(
        name="虎",
        cost_str="4T3B",
        card_type=CardType.MINION,
        pack=Pack.UNDERWORLD,
        rarity=Rarity.GOLD,
        immersion_level=3,
        attack=6,
        health=6,
        keywords={"坚韧": 2, "绝缘": True},
        targets_fn=target_friendly_positions,
    )

    # === 血祭卡包 ===
    register_card(
        name="保卫者",
        cost_str="2T",
        card_type=CardType.MINION,
        pack=Pack.BLOOD,
        rarity=Rarity.IRON,
        immersion_level=1,
        attack=0,
        health=3,
        keywords={"协同": True},
        targets_fn=target_friendly_positions,
    )
    register_card(
        name="Bishop",
        cost_str="3T3S",
        card_type=CardType.MINION,
        pack=Pack.BLOOD,
        rarity=Rarity.SILVER,
        immersion_level=2,
        attack=3,
        health=6,
        targets_fn=target_friendly_positions,
    )
    register_card(
        name="流明",
        cost_str="2T",
        card_type=CardType.MINION,
        pack=Pack.BLOOD,
        rarity=Rarity.BRONZE,
        immersion_level=1,
        attack=2,
        health=2,
        targets_fn=target_friendly_positions,
    )


def build_valid_deck():
    """构建一个合法的示例卡组（1+1+1分配，共40张）。"""
    from tards import DEFAULT_REGISTRY

    deck = Deck(name="示例合法卡组", registry=DEFAULT_REGISTRY)

    # 分配沉浸点：通用1点，离散1点，冥刻1点（总和=3）
    deck.set_immersion(Pack.GENERAL, 1)
    deck.set_immersion(Pack.DISCRETE, 1)
    deck.set_immersion(Pack.UNDERWORLD, 1)

    # 通用卡包：14张
    deck.add_card("小兵", 4)
    deck.add_card("哨兵", 3)
    deck.add_card("急救", 3)
    deck.add_card("增援", 4)

    # 离散卡包：16张
    deck.add_card("火把", 3)
    deck.add_card("萤石", 2)
    deck.add_card("精准采集", 3)
    deck.add_card("铁锭", 4)
    deck.add_card("末影螨", 3)
    deck.add_card("狗", 1)

    # 冥刻卡包：10张
    deck.add_card("松鼠", 4)
    deck.add_card("臭虫", 3)
    deck.add_card("猫", 1)
    deck.add_card("林鼠", 2)

    return deck


def test_validation(deck: Deck, description: str):
    print(f"\n{'='*40}")
    print(f"测试: {description}")
    print(f"{'='*40}")
    errors = deck.validate()
    if errors:
        print("校验失败:")
        for err in errors:
            print(f"  - {err}")
    else:
        print("校验通过！")
    print(deck.deck_summary())


def main():
    setup_sample_registry()

    # 测试1：合法卡组
    valid_deck = build_valid_deck()
    test_validation(valid_deck, "合法卡组（通用1/离散1/冥刻1）")

    # 测试2：牌数不对
    bad_count_deck = Deck(name="牌数错误", registry=valid_deck.registry)
    bad_count_deck.set_immersion(Pack.GENERAL, 3)
    for _ in range(35):
        bad_count_deck.add_card("小兵")
    test_validation(bad_count_deck, "牌数不足（35张）")

    # 测试3：沉浸点超限
    bad_immersion_deck = Deck(name="沉浸超限", registry=valid_deck.registry)
    bad_immersion_deck.set_immersion(Pack.GENERAL, 2)
    bad_immersion_deck.set_immersion(Pack.DISCRETE, 2)
    for _ in range(20):
        bad_immersion_deck.add_card("小兵")
    for _ in range(20):
        bad_immersion_deck.add_card("火把")
    test_validation(bad_immersion_deck, "沉浸点超限（2+2=4）")

    # 测试4：卡包数量不足
    bad_pack_count_deck = Deck(name="卡包数量不足", registry=valid_deck.registry)
    bad_pack_count_deck.set_immersion(Pack.GENERAL, 2)
    bad_pack_count_deck.set_immersion(Pack.DISCRETE, 1)
    for _ in range(15):
        bad_pack_count_deck.add_card("小兵")
    for _ in range(25):
        bad_pack_count_deck.add_card("火把")
    test_validation(bad_pack_count_deck, "通用卡包数量不足（15张 < 20张）")

    # 测试5：稀有度超限
    bad_rarity_deck = Deck(name="稀有度超限", registry=valid_deck.registry)
    bad_rarity_deck.set_immersion(Pack.GENERAL, 3)
    for _ in range(40):
        bad_rarity_deck.add_card("哨兵")
    test_validation(bad_rarity_deck, "稀有度超限（哨兵为铜卡，带了40张）")

    # 测试6：沉浸等级不足
    bad_level_deck = Deck(name="沉浸等级不足", registry=valid_deck.registry)
    bad_level_deck.set_immersion(Pack.DISCRETE, 1)
    bad_level_deck.set_immersion(Pack.GENERAL, 2)
    for _ in range(10):
        bad_level_deck.add_card("火把")
    for _ in range(30):
        bad_level_deck.add_card("小兵")
    test_validation(bad_level_deck, "沉浸等级不足（离散仅1点，却带了3级卡高炉）")
    # 修正：上面没有加高炉，让我修正这个测试
    bad_level_deck.remove_card("小兵", 10)
    bad_level_deck.add_card("高炉", 2)
    test_validation(bad_level_deck, "沉浸等级不足（离散1点带了3级高炉x2）")

    # 测试7：生成对战用卡组并运行一局
    print(f"\n{'='*40}")
    print("测试: 从合法卡组生成对战并进行一局")
    print(f"{'='*40}")
    if valid_deck.is_valid():
        p1_deck = valid_deck.to_game_deck(None)
        p2_deck = valid_deck.to_game_deck(None)
        p1_defs = valid_deck.to_original_deck_defs()
        p2_defs = valid_deck.to_original_deck_defs()
        p1 = Player(side=0, name="玩家A", diver="测试员", card_deck=p1_deck, original_deck_defs=p1_defs)
        p2 = Player(side=1, name="玩家B", diver="测试员", card_deck=p2_deck, original_deck_defs=p2_defs)

        # 简单的随机行动器（临时）
        import random
        def random_actor(game, active, opponent):
            playable = []
            for idx, card in enumerate(active.card_hand):
                serial = idx + 1
                targets = active.get_valid_targets(card)
                for t in targets:
                    if hasattr(card, '__class__') and card.__class__.__name__ == 'MinionCard':
                        if not game.board.is_valid_deploy(t, active, card) or game.board.get_minion_at(t) is not None:
                            continue
                    if active.card_can_play(serial, t)[0]:
                        playable.append((serial, t, card))
            if playable:
                playable.sort(key=lambda x: x[2].cost.t + x[2].cost.b + x[2].cost.s + x[2].cost.ct + sum(x[2].cost.minerals.values()), reverse=True)
                serial, target, card = playable[0]
                bluff = False
                if card.__class__.__name__ == 'Conspiracy':
                    bluff = random.random() < 0.3
                return {"type": "play", "serial": serial, "target": target, "bluff": bluff}
            return {"type": "brake"}

        game = Game(p1, p2, action_provider=random_actor)
        game.start_game()
    else:
        print("卡组不合法，无法开始游戏")


if __name__ == "__main__":
    main()
