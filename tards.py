import random
from typing import List, Any, Optional, Tuple, Union, Callable, Dict

# ========== 事件常量 ==========
EVENT_DEPLOY = "deploy"
EVENT_DEATH = "death"
EVENT_PLAYER_DAMAGE = "player_damage"
EVENT_PHASE_START = "phase_start"
EVENT_PHASE_END = "phase_end"
EVENT_BELL = "bell"


class Player:
    def __init__(self, side, name, diver, card_deck):
        self.side = side
        self.diver = diver
        self.name = name
        self.card_deck = card_deck[:]
        self.card_hand = []
        self.card_dis = []
        self.active_conspiracies: List['Conspiracy'] = []
        self.health = 30
        self.health_max = 30
        self.t_point = 0
        self.t_point_max = 0
        self.card_hand_max = 8
        self.draw_fail = 0
        self.bell = False
        self.braked = False
        self.t_changed_this_round = False
        self.board_ref: Optional['Board'] = None

    def get_friendly_rows(self):
        return (3, 4) if self.side == 0 else (0, 1)

    def get_enemy_rows(self):
        return (0, 1) if self.side == 0 else (3, 4)

    def health_change(self, delta):
        """改变生命值。delta < 0 时表示【受到伤害】，触发 player_damage 事件。"""
        self.health += delta
        if self.health > self.health_max:
            self.health = self.health_max
        if delta >= 0:
            print(f"{self.name} 恢复 {delta} 点生命，剩余 {self.health} HP")
        else:
            print(f"{self.name} 受到 {-delta} 点伤害，剩余 {self.health} HP")
            if self.board_ref and self.board_ref.game_ref:
                self.board_ref.game_ref.emit_event(EVENT_PLAYER_DAMAGE, player=self, damage=-delta)
        if self.health <= 0:
            print(f"{self.name} 战败！")

    def lose_hp(self, amount):
        """【流失生命值】：不触发'受到伤害时'效果。"""
        if amount <= 0:
            return
        self.health -= amount
        print(f"{self.name} 失去 {amount} 点生命值，剩余 {self.health} HP")
        if self.health <= 0:
            print(f"{self.name} 战败！")
            return True
        return False

    def health_max_change(self, delta):
        self.health_max += delta
        if self.health > self.health_max:
            self.health = self.health_max
        if self.health <= 0:
            print(f"{self.name} 战败！")
            return True
        if delta >= 0:
            print(f"{self.name} 生命上限增加 {delta}，当前生命 {self.health}")
        else:
            print(f"{self.name} 生命上限减少 {-delta}，当前生命 {self.health}")
        return False

    def draw_card(self, amount):
        drawn_names = []
        while amount > 0:
            if len(self.card_deck) == 0:
                self.draw_fail += 1
                print(f"  {self.name} 牌库已空，虚空侵蚀！失去 {self.draw_fail} 点生命")
                self.lose_hp(self.draw_fail)
                amount -= 1
                continue
            if len(self.card_hand) == self.card_hand_max:
                card = self.card_deck.pop()
                self.card_dis.append(card)
                amount -= 1
                print(f"  {self.name} 手牌已满，{card.name} 被弃置")
                continue
            card = self.card_deck.pop()
            self.card_hand.append(card)
            drawn_names.append(card.name)
            amount -= 1
        if drawn_names:
            print(f"  {self.name} 抽取了: {', '.join(drawn_names)}")

    def t_point_change(self, delta):
        self.t_point += delta
        if self.t_point < 0:
            self.t_point = 0
        if delta != 0:
            self.t_changed_this_round = True

    def get_valid_targets(self, card):
        if callable(card.targets):
            return card.targets(self, self.board_ref if self.board_ref else None)
        return card.targets

    def card_can_play(self, serial, target):
        if serial < 1 or serial > len(self.card_hand):
            return False
        card = self.card_hand[serial - 1]
        if card.cost > self.t_point:
            return False
        if card.can_play == False:
            return False
        valid_targets = self.get_valid_targets(card)
        return target in valid_targets

    def play_card(self, serial, target, game, bluff=False):
        if not self.card_can_play(serial, target):
            return False
        card = self.card_hand[serial - 1]
        self.t_point_change(-card.cost)
        if isinstance(card, Minioncard):
            effect = card.effect(player=self, target=target, game=game)
            if effect:
                self.card_hand.pop(serial - 1)
            else:
                self.t_point_change(card.cost)
                return False
        elif isinstance(card, Strategy):
            effect = card.effect(player=self, target=target, game=game)
            if effect:
                self.card_hand.pop(serial - 1)
                self.card_dis.append(card)
            else:
                self.t_point_change(card.cost)
                return False
        elif isinstance(card, Conspiracy):
            if bluff:
                print(f"  {self.name} 假装激活了 [{card.name}]（虚张声势）")
                # 手牌保留，仅扣除费用
                return True
            else:
                print(f"  {self.name} 暗中激活了阴谋 [{card.name}]")
                self.card_hand.pop(serial - 1)
                self.active_conspiracies.append(card)
                return True
        return True

    def reset_turn_flags(self):
        self.t_changed_this_round = False
        self.bell = False
        self.braked = False


# ========== 卡牌 ==========
class Card:
    def __init__(self, name, cost, targets):
        self.name = name
        self.cost = cost
        self.can_play = True
        self.targets = targets


class Minioncard(Card):
    def __init__(self, name, owner, cost, targets, attack, health, special=None, keywords=None):
        super().__init__(name, cost, targets)
        self.attack = attack
        self.health = health
        self.special = special
        self.owner = owner
        self.keywords = keywords or {}

    def effect(self, player, target, game):
        if game.board.target_check(target) == False:
            return False
        if not game.board.is_valid_deploy(target, player, self):
            print("  无法在此位置部署单位。")
            return False
        if game.board.get_minion_at(target) is not None:
            print("  该格子已被占用")
            return False
        minion = Minion(
            name=self.name,
            owner=player,
            position=target,
            attack=self.attack,
            health=self.health,
            source_card=self,
            board=game.board,
            keywords=self.keywords.copy()
        )
        if game.board.place_minion(minion, target):
            print(f"  {player.name} 在 {target} 部署了 {minion.name}")
            minion.summon_turn = game.current_turn
            if self.special:
                self.special(minion, player, game)
            game.emit_event(EVENT_DEPLOY, minion=minion, player=player, card=self)
            return True
        return False


class Strategy(Card):
    def __init__(self, name, cost, effect_fn, targets):
        super().__init__(name, cost, targets)
        self.effect_fn = effect_fn

    def effect(self, player, target, game):
        if self.effect_fn is None:
            return True
        return self.effect_fn(player, target, game)


class Conspiracy(Card):
    def __init__(self, name, cost, condition_fn, effect_fn, targets):
        super().__init__(name, cost, targets)
        self.condition_fn = condition_fn
        self.effect_fn = effect_fn


# ========== 战斗单位 ==========
class Minion:
    def __init__(self, name, owner, position, attack, health, source_card, board, keywords=None):
        self.name = name
        self.owner = owner
        self.position = position
        self.attack = attack
        self.health = health
        self.max_health = health
        self.source_card = source_card
        self.can_attack = True
        self.board = board
        self.keywords = keywords or {}
        self.summon_turn = -1

    def is_alive(self):
        return self.position in self.board.minion_place and self.board.minion_place[self.position] is self

    def minion_death(self):
        if self.health <= 0 and self.is_alive():
            print(f"  {self.name} 被消灭了！")
            self.board.remove_minion(self.position)
            if self.board.game_ref:
                self.board.game_ref.emit_event(EVENT_DEATH, minion=self, player=self.owner)
            deathrattle = self.keywords.get("亡语")
            if deathrattle:
                deathrattle(self, self.owner, self.board)

    def take_damage(self, damage):
        if damage <= 0:
            return
        tough = self.keywords.get("坚韧", 0)
        actual = max(0, damage - tough)
        self.health -= actual
        print(f"  {self.name} 受到 {actual} 点伤害，剩余 {self.health}/{self.max_health}")
        if self.health <= 0:
            self.minion_death()

    def minion_heal(self, heal):
        self.health += heal
        if self.max_health < self.health:
            self.health = self.max_health

    def can_attack_this_turn(self, turn_number):
        if self.attack <= 0:
            return False
        if "迅捷" in self.keywords:
            return True
        return self.summon_turn < turn_number

    def attack_target(self, target):
        if isinstance(target, Minion):
            print(f"  {self.name} 攻击 {target.name}，造成 {self.attack} 点伤害")
            target.take_damage(self.attack)
            if target.is_alive():
                spike = target.keywords.get("尖刺", 0)
                if spike > 0:
                    print(f"  {target.name} 的尖刺反弹 {spike} 点伤害")
                    self.take_damage(spike)
        elif isinstance(target, Player):
            print(f"  {self.name} 直接攻击 {target.name}，造成 {self.attack} 点伤害")
            target.health_change(-self.attack)

    def __str__(self):
        return f"{self.name}({self.attack}/{self.health})"


# ========== 棋盘 ==========
class Board:
    SIZE = 5
    COL_NAMES = ["高地", "山脊", "中路", "河岸", "水路"]

    def __init__(self):
        self.minion_place: dict[Tuple[int, int], 'Minion'] = {}
        self.game_ref: Optional['Game'] = None

    def target_check(self, target):
        if not isinstance(target, tuple) or len(target) != 2:
            return False
        r, c = target
        return 0 <= r < self.SIZE and 0 <= c < self.SIZE

    def is_valid_deploy(self, pos, player, card):
        r, c = pos
        if r not in player.get_friendly_rows():
            return False
        is_water_col = (c == 4)
        aquatic = card.keywords.get("水生", False) or card.keywords.get("两栖", False)
        if is_water_col and not aquatic:
            return False
        if not is_water_col and card.keywords.get("水生", False):
            return False
        if "独行" in card.keywords:
            friendlies = self.get_minions_in_column(c, friendly_to=player)
            if friendlies:
                return False
        friendlies = self.get_minions_in_column(c, friendly_to=player)
        if friendlies:
            has_synergy = any("协同" in m.keywords for m in friendlies)
            if not has_synergy and "协同" not in card.keywords:
                return False
        return True

    def get_minion_at(self, target: Tuple[int, int]):
        return self.minion_place.get(target)

    def remove_minion(self, target):
        return self.minion_place.pop(target, None)

    def place_minion(self, minion, target):
        if target in self.minion_place:
            return False
        self.minion_place[target] = minion
        minion.position = target
        return True

    def get_minions_of_player(self, player):
        return [m for m in self.minion_place.values() if m.owner == player]

    def get_minions_in_column(self, col, friendly_to=None):
        result = []
        for r in range(self.SIZE):
            m = self.minion_place.get((r, col))
            if m and (friendly_to is None or m.owner == friendly_to):
                result.append(m)
        return result

    def get_enemy_minions_in_column(self, col, player: Player):
        return [m for m in self.minion_place.values() if m.position[1] == col and m.owner != player]

    def get_front_minion(self, col, player: Player):
        enemies = self.get_enemy_minions_in_column(col, player)
        if not enemies:
            return None
        enemies.sort(key=lambda m: abs(m.position[0] - 2))
        return enemies[0]

    def __str__(self):
        lines = []
        header = "    " + "  ".join(f"{name:6}" for name in self.COL_NAMES)
        lines.append(header)
        for r in range(self.SIZE):
            cells = []
            for c in range(self.SIZE):
                m = self.minion_place.get((r, c))
                if m:
                    owner = "A" if m.owner.side == 0 else "B"
                    cells.append(f"{owner}{m.name}")
                else:
                    cells.append("")
            line = f"[{r}] " + " | ".join(f"{cell:6}" for cell in cells)
            lines.append(line)
        return "\n".join(lines)


# ========== 游戏主控 ==========
class Game:
    PHASE_START = "start"
    PHASE_DRAW = "draw"
    PHASE_ACTION = "action"
    PHASE_RESOLVE = "resolve"
    PHASE_END = "end"

    def __init__(self, player1, player2):
        self.p1 = player1
        self.p2 = player2
        self.players = [player1, player2]
        self.board = Board()
        self.current_turn = 0
        self.current_phase = self.PHASE_START
        self.current_player = None
        self.first_player = None
        self.game_over = False
        self.winner = None
        # 绑定引用
        self.board.game_ref = self
        for p in self.players:
            p.board_ref = self.board

    def emit_event(self, event_type, **kwargs):
        if self.game_over:
            return
        event_data = dict(event_type=event_type, **kwargs)
        for p in self.players:
            # 复制列表防止触发过程中修改
            conspiracies = p.active_conspiracies[:]
            triggered = []
            for c in conspiracies:
                if c.condition_fn and c.condition_fn(self, event_data, p):
                    triggered.append(c)
            for c in triggered:
                if c in p.active_conspiracies:
                    print(f"  阴谋 [{c.name}] 被触发！")
                    if c.effect_fn:
                        c.effect_fn(self, event_data, p)
                    p.active_conspiracies.remove(c)
                    p.card_dis.append(c)
                    if self.check_game_over():
                        return

    def start_game(self):
        print("=" * 40)
        print("Tards 对战开始！")
        print("=" * 40)
        self.first_player = self.p1
        for p in self.players:
            p.health = 30
            p.health_max = 30
            p.t_point_max = 0
            p.t_point = 0
            p.draw_card(4)
        self.current_turn = 1
        while not self.game_over:
            self.run_turn()
            self.current_turn += 1
            if self.current_turn > 30:
                print("\n回合数达到上限，强制结束游戏。")
                break
        self.print_result()

    def run_turn(self):
        first = self.p1 if self.current_turn % 2 == 1 else self.p2
        second = self.p2 if first == self.p1 else self.p1
        print(f"\n========== 回合 {self.current_turn} | 先手: {first.name} ==========")
        self.draw_phase(first, second)
        if self.check_game_over():
            return
        self.action_phase(first, second)
        if self.check_game_over():
            return
        self.resolve_phase(first, second)
        self.check_game_over()

    def draw_phase(self, first, second):
        self.current_phase = self.PHASE_DRAW
        self.emit_event(EVENT_PHASE_START, phase=self.PHASE_DRAW, first=first, second=second)
        print("[抽牌阶段]")
        if self.current_turn == 1:
            second.draw_card(1)
        else:
            second.draw_card(1)
            first.draw_card(1)
        for p in [first, second]:
            if p.t_point_max < 10:
                p.t_point_max += 1
            p.t_point = p.t_point_max
            print(f"  {p.name} T槽={p.t_point_max}，获得 {p.t_point} T点")

    def action_phase(self, first, second):
        self.current_phase = self.PHASE_ACTION
        self.emit_event(EVENT_PHASE_START, phase=self.PHASE_ACTION, first=first, second=second)
        print("[出牌阶段]")
        for p in self.players:
            p.reset_turn_flags()
        active = first
        opponent = second
        turn_count = 0
        while not self.game_over:
            turn_count += 1
            if turn_count > 20:
                print("  出牌阶段回合数过多，强制结束")
                break
            print(f"\n  >>> {active.name} 的回合 (T点:{active.t_point}, HP:{active.health})")
            self.show_hand(active)
            active.bell = False
            active.braked = False
            self.ai_turn(active, opponent)
            if active.braked:
                print(f"  {active.name} 拉闸，出牌阶段结束")
                break
            if active.bell:
                self.emit_event(EVENT_BELL, player=active)
                if not active.t_changed_this_round:
                    print(f"  {active.name} 未改变T点即拍铃，失去 1 T点")
                    active.t_point_change(-1)
                active, opponent = opponent, active
                continue
            # 默认拉闸
            print(f"  {active.name} 结束行动")
            break

    def show_hand(self, player):
        if not player.card_hand:
            print(f"    手牌: (空)")
            return
        parts = []
        for i, c in enumerate(player.card_hand, 1):
            if isinstance(c, Minioncard):
                parts.append(f"[{i}]{c.name}({c.cost}T {c.attack}/{c.health})")
            else:
                parts.append(f"[{i}]{c.name}({c.cost}T)")
        print(f"    手牌: {' | '.join(parts)}")
        if player.active_conspiracies:
            print(f"    活跃阴谋: {', '.join(c.name for c in player.active_conspiracies)}")

    def ai_turn(self, player, opponent):
        played_any = False
        tried = set()
        while player.t_point > 0:
            playable = []
            for idx, card in enumerate(player.card_hand):
                serial = idx + 1
                targets = player.get_valid_targets(card)
                for t in targets:
                    if (serial, t) in tried:
                        continue
                    if isinstance(card, Minioncard):
                        if not self.board.is_valid_deploy(t, player, card) or self.board.get_minion_at(t) is not None:
                            continue
                    if player.card_can_play(serial, t):
                        playable.append((serial, t, card))
            if not playable:
                break
            playable.sort(key=lambda x: x[2].cost, reverse=True)
            serial, target, card = playable[0]
            print(f"  {player.name} 尝试打出 {card.name} (目标: {self._fmt_target(target)})")

            # 阴谋卡特殊处理：决定是虚张声势还是真正激活
            if isinstance(card, Conspiracy):
                bluff = random.random() < 0.3  # 30% 概率虚张声势
                ok = player.play_card(serial, target, self, bluff=bluff)
                tried.add((serial, target))
                if ok:
                    played_any = True
            else:
                ok = player.play_card(serial, target, self)
                tried.add((serial, target))
                if ok:
                    played_any = True
                else:
                    print(f"  出牌失败")

        if player.braked or player.bell:
            return
        if player.t_point == 0 or not played_any:
            player.braked = True
        else:
            player.bell = True

    def _fmt_target(self, target):
        if isinstance(target, tuple):
            r, c = target
            col_name = Board.COL_NAMES[c] if 0 <= c < 5 else str(c)
            return f"({r},{col_name})"
        if isinstance(target, Minion):
            return target.name
        if isinstance(target, Player):
            return target.name
        return str(target)

    def resolve_phase(self, first, second):
        self.current_phase = self.PHASE_RESOLVE
        self.emit_event(EVENT_PHASE_START, phase=self.PHASE_RESOLVE, first=first, second=second)
        print("[结算阶段]")
        print(self.board)
        for col in range(4, -1, -1):
            col_name = self.board.COL_NAMES[col]
            attackers = [m for m in self.board.minion_place.values()
                         if m.position[1] == col and m.can_attack_this_turn(self.current_turn)]
            if not attackers:
                continue
            attackers.sort(key=lambda m: (abs(m.position[0] - 2), m.owner.side))
            print(f"  {col_name}列发生战斗")
            for m in attackers:
                if not m.is_alive():
                    continue
                target = self.board.get_front_minion(col, m.owner)
                if target and target.is_alive():
                    m.attack_target(target)
                else:
                    enemy = self.p2 if m.owner == self.p1 else self.p1
                    m.attack_target(enemy)
                if self.check_game_over():
                    return
        self.emit_event(EVENT_PHASE_END, phase=self.PHASE_RESOLVE, first=first, second=second)

    def check_game_over(self):
        if self.game_over:
            return True
        p1_dead = self.p1.health <= 0
        p2_dead = self.p2.health <= 0
        if p1_dead and p2_dead:
            print("\n双方同时倒下，平局！")
            self.game_over = True
            return True
        elif p1_dead:
            print(f"\n{self.p2.name} 获得胜利！")
            self.game_over = True
            self.winner = self.p2
            return True
        elif p2_dead:
            print(f"\n{self.p1.name} 获得胜利！")
            self.game_over = True
            self.winner = self.p1
            return True
        return False

    def print_result(self):
        if self.winner:
            print(f"\n>>> 最终胜者: {self.winner.name} <<<")
        elif self.game_over:
            print("\n>>> 游戏结束：平局 <<<")
        else:
            print("\n>>> 游戏中断 <<<")


# ========== 目标生成器 ==========
def target_friendly_positions(player, board):
    rows = player.get_friendly_rows()
    return [(r, c) for r in rows for c in range(5)]

def target_enemy_minions(player, board):
    return [m for m in board.minion_place.values() if m.owner != player]

def target_any_minion(player, board):
    return list(board.minion_place.values())

def target_self(player, board):
    return [player]

def target_none(player, board):
    return [None]


# ========== 示例卡组 ==========
def make_sample_deck(owner):
    deck = []
    # 小兵 1T 1/1
    for _ in range(5):
        deck.append(Minioncard("小兵", owner, 1, target_friendly_positions, 1, 1))
    # 哨兵 2T 2/3
    for _ in range(3):
        deck.append(Minioncard("哨兵", owner, 2, target_friendly_positions, 2, 3))
    # 游侠 2T 2/1 迅捷
    for _ in range(2):
        deck.append(Minioncard("游侠", owner, 2, target_friendly_positions, 2, 1, keywords={"迅捷": True}))
    # 急救 1T 恢复3HP
    def heal_effect(p, t, g):
        if isinstance(t, Player):
            t.health_change(3)
            return True
        return False
    for _ in range(2):
        deck.append(Strategy("急救", 1, heal_effect, target_self))
    # 火球 2T 对敌方单位造成2点伤害
    def fireball_effect(p, t, g):
        if isinstance(t, Minion):
            t.take_damage(2)
            return True
        return False
    for _ in range(2):
        deck.append(Strategy("火球", 2, fireball_effect, target_enemy_minions))
    # 增援 1T 抽一张牌
    def draw_effect(p, t, g):
        p.draw_card(1)
        return True
    for _ in range(2):
        deck.append(Strategy("增援", 1, draw_effect, target_none))
    # 阴谋卡：伏击 —— 当敌方部署单位时，对其造成 2 点伤害
    def ambush_condition(game, event, owner):
        return event.get("event_type") == EVENT_DEPLOY and event.get("player") != owner
    def ambush_effect(game, event, owner):
        minion = event.get("minion")
        if minion and minion.is_alive():
            print(f"    伏击生效！{minion.name} 受到 2 点伤害")
            minion.take_damage(2)
    for _ in range(2):
        deck.append(Conspiracy("伏击", 1, ambush_condition, ambush_effect, target_none))
    # 阴谋卡：背刺 —— 当敌方拍铃时，对敌方英雄造成 3 点伤害
    def backstab_condition(game, event, owner):
        return event.get("event_type") == EVENT_BELL and event.get("player") != owner
    def backstab_effect(game, event, owner):
        victim = event.get("player")
        if victim:
            print(f"    背刺生效！{victim.name} 受到 3 点伤害")
            victim.health_change(-3)
    for _ in range(2):
        deck.append(Conspiracy("背刺", 2, backstab_condition, backstab_effect, target_none))
    random.shuffle(deck)
    return deck


# ========== 入口 ==========
if __name__ == "__main__":
    p1_deck = make_sample_deck(None)
    p2_deck = make_sample_deck(None)
    p1 = Player(side=0, name="玩家A", diver="测试员", card_deck=p1_deck)
    p2 = Player(side=1, name="玩家B", diver="测试员", card_deck=p2_deck)
    game = Game(p1, p2)
    game.start_game()
