import random
from typing import Any, Dict, List, Optional

from tards import (
    Cost,
    Game,
    Minion,
    MinionCard,
    Player,
    Strategy,
    Conspiracy,
    MineralCard,
    target_enemy_minions,
    target_friendly_positions,
    target_none,
    target_self,
    EVENT_DEPLOY,
    EVENT_BELL,
)


def simple_sacrifice_chooser(required_blood: int):
    """简单的献祭选择器：优先献祭丰饶高的友方单位。"""
    def chooser(player: Player):
        candidates = [m for m in player.board_ref.get_minions_of_player(player) if m.is_alive()]
        if not candidates:
            return None
        # 按丰饶降序，无丰饶则视为1
        candidates.sort(key=lambda m: m.keywords.get("丰饶", 1), reverse=True)
        selected = []
        total = 0
        for m in candidates:
            selected.append(m)
            total += m.keywords.get("丰饶", 1)
            if total >= required_blood:
                return selected
        return None
    return chooser


def make_sample_deck(owner: Player) -> List[Any]:
    deck = []
    for _ in range(5):
        deck.append(MinionCard("小兵", owner, Cost.from_string("1T"), target_friendly_positions, 1, 1))
    for _ in range(3):
        deck.append(MinionCard("哨兵", owner, Cost.from_string("2T"), target_friendly_positions, 2, 3))
    for _ in range(2):
        deck.append(MinionCard("游侠", owner, Cost.from_string("2T"), target_friendly_positions, 2, 1, keywords={"迅捷": True}))

    def heal_effect(p, t, g):
        if isinstance(t, Player):
            t.health_change(3)
            return True
        return False
    for _ in range(2):
        deck.append(Strategy("急救", Cost.from_string("1T"), heal_effect, target_self))

    def fireball_effect(p, t, g):
        if isinstance(t, Minion):
            t.take_damage(2)
            return True
        return False
    for _ in range(2):
        deck.append(Strategy("火球", Cost.from_string("2T"), fireball_effect, target_enemy_minions))

    def draw_effect(p, t, g):
        p.draw_card(1, game=g)
        return True
    for _ in range(2):
        deck.append(Strategy("增援", Cost.from_string("1T"), draw_effect, target_none))

    def ambush_condition(game, event, owner):
        return event.get("event_type") == EVENT_DEPLOY and event.get("player") != owner
    def ambush_effect(game, event, owner):
        minion = event.get("minion")
        if minion and minion.is_alive():
            print(f"    伏击生效！{minion.name} 受到 2 点伤害")
            minion.take_damage(2)
    for _ in range(2):
        deck.append(Conspiracy("伏击", Cost.from_string("1T"), ambush_condition, ambush_effect, target_none))

    def backstab_condition(game, event, owner):
        return event.get("event_type") == EVENT_BELL and event.get("player") != owner
    def backstab_effect(game, event, owner):
        victim = event.get("player")
        if victim:
            print(f"    背刺生效！{victim.name} 受到 3 点伤害")
            victim.health_change(-3)
    for _ in range(2):
        deck.append(Conspiracy("背刺", Cost.from_string("2T"), backstab_condition, backstab_effect, target_none))

    random.shuffle(deck)
    return deck


def random_actor(game: Game, active: Player, opponent: Player) -> Optional[Dict[str, Any]]:
    """临时随机行动生成器（仅用于 demo）。每次调用返回一个行动。"""
    playable = []
    for idx, card in enumerate(active.card_hand):
        serial = idx + 1
        targets = active.get_valid_targets(card)
        for t in targets:
            if isinstance(card, MinionCard):
                if not game.board.is_valid_deploy(t, active, card) or game.board.get_minion_at(t) is not None:
                    continue
            if active.card_can_play(serial, t):
                playable.append((serial, t, card))

    if playable:
        playable.sort(
            key=lambda x: x[2].cost.t + x[2].cost.b + x[2].cost.s + x[2].cost.ct + sum(x[2].cost.minerals.values()),
            reverse=True,
        )
        serial, target, card = playable[0]
        bluff = False
        if isinstance(card, Conspiracy):
            bluff = random.random() < 0.3
        return {"type": "play", "serial": serial, "target": target, "bluff": bluff}

    return {"type": "brake"}


def main():
    p1_deck = make_sample_deck(None)
    p2_deck = make_sample_deck(None)
    p1 = Player(side=0, name="玩家A", diver="测试员", card_deck=p1_deck)
    p2 = Player(side=1, name="玩家B", diver="测试员", card_deck=p2_deck)

    # 注入献祭选择器（使用 lambda 延迟求值，因为 board_ref 在 Game 初始化后才设置）
    p1.sacrifice_chooser = lambda req: simple_sacrifice_chooser(req)(p1)
    p2.sacrifice_chooser = lambda req: simple_sacrifice_chooser(req)(p2)

    game = Game(p1, p2, action_provider=random_actor)
    game.start_game()


if __name__ == "__main__":
    main()
