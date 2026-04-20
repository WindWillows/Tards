from typing import Any, Callable, Dict, List, Optional, TYPE_CHECKING
from .constants import EVENT_DRAW
from .cost import Cost
from .cards import Card, Conspiracy, MineralCard, MinionCard, Strategy

if TYPE_CHECKING:
    from .board import Board
    from .card_db import Pack
    from .cards import Minion
    from .game import Game


def _give_card_to_hand(player: "Player", card_def_name: str, reason: str):
    from .card_db import DEFAULT_REGISTRY
    card_def = DEFAULT_REGISTRY.get(card_def_name)
    if not card_def:
        return
    card = card_def.to_game_card(player)
    if len(player.card_hand) < player.card_hand_max:
        player.card_hand.append(card)
    else:
        player.card_dis.append(card)
    print(f"  {player.name} {reason}：获得 {card_def_name}")


class Player:
    def __init__(self, side: int, name: str, diver: str, card_deck: List[Card], original_deck_defs: Optional[List[Any]] = None):
        self.side = side
        self.diver = diver
        self.name = name
        self.card_deck = card_deck[:]
        self.card_hand: List[Card] = []
        self.card_dis: List[Card] = []
        self.original_deck_defs: List[Any] = list(original_deck_defs) if original_deck_defs else []  # CardDefinition 列表，用于开发
        self.active_conspiracies: List[Conspiracy] = []
        self.health = 30
        self.health_max = 30

        # 资源系统
        self.t_point = 0
        self.t_point_max = 0
        self.c_point = 0
        self.c_point_max = 0
        self.b_point = 0
        self.s_point = 0

        self.card_hand_max = 8
        self.draw_fail = 0
        self.bell = False
        self.braked = False
        self.t_changed_this_round = False
        self.board_ref: Optional["Board"] = None

        # 献祭选择器：由外部注入，接收 (required_blood) -> Optional[List[Minion]]
        self.sacrifice_chooser: Optional[Callable[[int], Optional[List["Minion"]]]] = None

        # 沉浸度增益
        self.immersion_points: Dict["Pack", int] = {}
        self.squirrel_deck: List[Card] = []
        self.squirrel_exchanged_this_turn: bool = False
        self._underworld_candle_20_given: bool = False
        self._underworld_candle_10_given: bool = False

        # 自动化事件回调（时间节点触发）
        self.on_turn_start: Optional[Callable] = None
        self.on_turn_end: Optional[Callable] = None
        self.on_phase_start: Optional[Callable] = None
        self.on_phase_end: Optional[Callable] = None

        # 部署增益与费用修正（雕像等机制使用）
        self._deploy_buffs: List[Callable[["Minion"], None]] = []
        self._cost_modifiers: List[Callable[["MinionCard", Cost], None]] = []

        # 通用状态标志（任何卡牌都可以通过 effect_fn / special_fn 设置）
        self._skip_next_draw = False
        self._on_develop_callbacks: List[Callable[["Player", "Game"], None]] = []

    @property
    def minions_on_board(self) -> List["Minion"]:
        """返回该玩家当前在场上的所有异象（动态计算，无需手动同步）。"""
        if self.board_ref:
            return [m for m in self.board_ref.minion_place.values() if m.owner is self]
        return []

    def get_friendly_rows(self) -> tuple:
        return (3, 4) if self.side == 0 else (0, 1)

    def get_enemy_rows(self) -> tuple:
        return (0, 1) if self.side == 0 else (3, 4)

    def health_change(self, delta: int) -> bool:
        """改变生命值。delta < 0 时表示【受到伤害】，触发伤害替换、血契2级、player_damage 事件。
        delta > 0 时表示恢复生命。"""
        game = getattr(self.board_ref, "game_ref", None)

        # === BEFORE_HEALTH_CHANGE ===
        if game:
            from .constants import EVENT_BEFORE_HEALTH_CHANGE
            event = game.emit_event(
                EVENT_BEFORE_HEALTH_CHANGE,
                source=None,
                target=self,
                player=self,
                delta=delta,
            )
            if getattr(event, "cancelled", False):
                return False
            delta = event.get("delta", delta)

        actual_delta = delta
        # 伤害替换（"取消该伤害"等机制）：仅对伤害生效
        if delta < 0:
            if game:
                actual_damage = game.apply_damage_replacements(self, -delta, None)
                actual_delta = -actual_damage

        self.health += actual_delta
        if self.health > self.health_max:
            self.health = self.health_max
        if actual_delta > 0:
            print(f"{self.name} 恢复 {actual_delta} 点生命，剩余 {self.health} HP")
        elif actual_delta < 0:
            print(f"{self.name} 受到 {-actual_delta} 点伤害，剩余 {self.health} HP")
            # 血契2级：受到单次≥3伤害时，+3S
            if -actual_delta >= 3:
                from .card_db import Pack
                if self.immersion_points.get(Pack.BLOOD, 0) >= 2:
                    self.s_point += 3
                    print(f"  {self.name} 血契沉浸度触发：受到不小于3点伤害，获得3S")
            if game:
                from .constants import EVENT_PLAYER_DAMAGE
                game.emit_event(EVENT_PLAYER_DAMAGE, source=None, target=self, player=self, damage=-actual_delta)

        # === HEALTH_CHANGED ===
        if game:
            from .constants import EVENT_HEALTH_CHANGED
            game.emit_event(
                EVENT_HEALTH_CHANGED,
                source=None,
                target=self,
                player=self,
                delta=actual_delta,
                old=self.health - actual_delta,
                new=self.health,
            )

        self._check_underworld_candle()

        if self.health <= 0:
            print(f"{self.name} 战败！")
            return True
        return False

    def lose_hp(self, amount: int) -> bool:
        """【流失生命值】：不受坚韧/伤害替换影响，不触发'受到伤害时'效果（如血契2级、player_damage 事件）。
        抽干卡组的疲劳惩罚、血契1级沉浸度、以及卡牌中'失去X点HP/生命值'的效果应使用此方法。"""
        if amount <= 0:
            return False
        self.health -= amount
        print(f"{self.name} 失去 {amount} 点生命值，剩余 {self.health} HP")

        self._check_underworld_candle()

        if self.health <= 0:
            print(f"{self.name} 战败！")
            return True
        return False

    def _check_underworld_candle(self):
        """冥刻3级：HP≤20给烛烟，HP≤10给大团烛烟。"""
        from .card_db import Pack
        if self.immersion_points.get(Pack.UNDERWORLD, 0) >= 3:
            if self.health <= 20 and not self._underworld_candle_20_given:
                self._underworld_candle_20_given = True
                _give_card_to_hand(self, "烛烟", "冥刻沉浸度触发")
            if self.health <= 10 and not self._underworld_candle_10_given:
                self._underworld_candle_10_given = True
                _give_card_to_hand(self, "大团烛烟", "冥刻沉浸度触发")

    def health_max_change(self, delta: int) -> bool:
        self.health_max += delta
        if self.health > self.health_max:
            self.health = self.health_max
        if delta >= 0:
            print(f"{self.name} 生命上限增加 {delta}，当前生命 {self.health}")
        else:
            print(f"{self.name} 生命上限减少 {-delta}，当前生命 {self.health}")
        if self.health <= 0:
            print(f"{self.name} 战败！")
            return True
        return False

    def draw_card(self, amount: int, game: Optional["Game"] = None):
        drawn_names = []
        while amount > 0:
            if game and game.game_over:
                break
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
            if game:
                game.emit_event(EVENT_DRAW, player=self, card=card)
        if drawn_names:
            print(f"  {self.name} 抽取了: {', '.join(drawn_names)}")

    def t_point_change(self, delta: int):
        self.t_point += delta
        if self.t_point < 0:
            self.t_point = 0
        if delta != 0:
            self.t_changed_this_round = True

    def c_point_change(self, delta: int):
        game = getattr(self.board_ref, "game_ref", None)

        # === BEFORE_C_CHANGE ===
        if game and delta != 0:
            from .constants import EVENT_BEFORE_C_CHANGE
            event = game.emit_event(
                EVENT_BEFORE_C_CHANGE,
                source=None,
                target=self,
                player=self,
                delta=delta,
            )
            if getattr(event, "cancelled", False):
                return
            delta = event.get("delta", delta)

        self.c_point += delta
        if self.c_point < 0:
            self.c_point = 0
        if self.c_point_max > 0 and self.c_point > self.c_point_max:
            self.c_point = self.c_point_max

        # === C_CHANGED ===
        if game and delta != 0:
            from .constants import EVENT_C_CHANGED
            game.emit_event(
                EVENT_C_CHANGED,
                source=None,
                target=self,
                player=self,
                delta=delta,
                old=self.c_point - delta,
                new=self.c_point,
            )

    def get_valid_targets(self, card: Card):
        if callable(card.targets):
            return card.targets(self, self.board_ref if self.board_ref else None)
        return card.targets

    def exchange_mineral(self, mineral_card: MineralCard, game: Optional["Game"] = None) -> bool:
        """花费兑换费用获取一张矿物卡并加入手牌。"""
        if not mineral_card.exchange_cost.can_afford(self):
            return False
        if not mineral_card.exchange_cost.pay(self):
            return False
        self.card_hand.append(mineral_card)
        print(f"  {self.name} 兑换了 [{mineral_card.name}]")
        if game:
            game.emit_event("mineral_exchanged", player=self, card=mineral_card)
        return True

    def _get_play_cost(self, card):
        """获取经过修正后的实际支付费用。"""
        cost = card.cost.copy()
        from .cards import MinionCard, Strategy
        if isinstance(card, (MinionCard, Strategy)):
            for fn in self._cost_modifiers:
                fn(card, cost)
        return cost

    def card_can_play(self, serial: int, target: Any) -> tuple[bool, str]:
        if serial < 1 or serial > len(self.card_hand):
            return False, "手牌序号无效"
        card = self.card_hand[serial - 1]
        cost = self._get_play_cost(card)
        ok, reason = cost.can_afford_detail(self)
        if not ok:
            return False, reason
        if card.can_play is False:
            return False, "该卡牌当前无法打出（can_play=False）"
        # 绝缘：策略卡无法以对方的绝缘异象为直接目标
        from .cards import Strategy, Minion
        if isinstance(card, Strategy) and isinstance(target, Minion):
            if target.keywords.get("绝缘", False) and target.owner != self:
                return False, f"{target.name} 具有绝缘，无法被策略选中"
        valid_targets = self.get_valid_targets(card)
        if target not in valid_targets:
            return False, "目标位置无效"
        return True, ""

    def play_card(self, serial: int, target: Any, game: "Game", bluff: bool = False, extra_targets: Optional[List[Any]] = None) -> bool:
        ok, reason = self.card_can_play(serial, target)
        if not ok:
            print(f"  {reason}")
            return False
        card = self.card_hand[serial - 1]

        # 支付费用（普通资源+CT+矿物）
        cost = self._get_play_cost(card)
        if not cost.pay(self):
            return False

        if isinstance(card, MinionCard):
            def deploy_fn():
                effect = card.effect(player=self, target=target, game=game, extra_targets=extra_targets)
                if effect:
                    if card in self.card_hand:
                        self.card_hand.remove(card)
                    if card.echo_level > 0:
                        echo_card = MinionCard(
                            name=card.name,
                            owner=self,
                            cost=Cost(t=2),
                            targets=card.targets,
                            attack=1,
                            health=1,
                            special=card.special,
                            keywords=card.keywords.copy() if card.keywords else None,
                        )
                        echo_card.echo_level = card.echo_level - 1
                        self.card_hand.append(echo_card)
                        print(f"  {self.name} 获得回响 [{echo_card.name}]（回响 {echo_card.echo_level}）")
                else:
                    # 部署失败，回滚费用（简化）
                    self.t_point_change(cost.t)
                    self.b_point += cost.b
                    self.s_point += cost.s
                    self.c_point_change(cost.c)
            game.effect_queue.resolve(f"部署 [{card.name}]", deploy_fn)
            return True

        elif isinstance(card, (Strategy, MineralCard)):
            is_mineral = isinstance(card, MineralCard)

            def play_fn():
                effect = card.effect(player=self, target=target, game=game, extra_targets=extra_targets)
                if effect:
                    if card in self.card_hand:
                        self.card_hand.remove(card)
                    self.card_dis.append(card)
                    game.emit_event("card_played", player=self, card=card)
                    if is_mineral:
                        print(f"  {self.name} 因打出矿物，失去所有剩余 C 点")
                        self.c_point = 0
                    if card.echo_level > 0:
                        import copy
                        echo_card = copy.copy(card)
                        echo_card.echo_level = card.echo_level - 1
                        self.card_hand.append(echo_card)
                        print(f"  {self.name} 获得回响 [{echo_card.name}]（回响 {echo_card.echo_level}）")
                else:
                    # 效果失败，回滚费用（简化）
                    self.t_point_change(card.cost.t)
                    self.b_point += card.cost.b
                    self.s_point += card.cost.s
                    self.c_point_change(card.cost.c)
            game.effect_queue.resolve(f"打出 [{card.name}]", play_fn)
            return True

        elif isinstance(card, Conspiracy):
            if bluff:
                print(f"  {self.name} 假装激活了 [{card.name}]（虚张声势）")
                return True
            else:
                def activate_fn():
                    print(f"  {self.name} 暗中激活了阴谋 [{card.name}]")
                    if card in self.card_hand:
                        self.card_hand.remove(card)
                    self.active_conspiracies.append(card)
                    # 注册到事件总线（通配符监听器）
                    game.register_conspiracy(card, self)
                game.effect_queue.resolve(f"激活阴谋 [{card.name}]", activate_fn)
                return True

        return True

    def request_sacrifice(self, required_blood: int) -> Optional[List["Minion"]]:
        """请求玩家选择献祭目标。若外部未注入选择器，返回 None。"""
        if self.sacrifice_chooser:
            return self.sacrifice_chooser(required_blood)
        return None

    def reset_turn_flags(self):
        self.t_changed_this_round = False
        self.bell = False
        self.braked = False
