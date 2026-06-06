"""Tards 测试脚手架 — 快速搭建可控的游戏状态。"""

from __future__ import annotations

from typing import Any, List, Optional, Tuple

# 自动注册所有卡包（副作用：填充 DEFAULT_REGISTRY）
import card_pools.blood
import card_pools.discrete
import card_pools.general
import card_pools.underworld

from tards.cards import Minion, Strategy
from tards.constants import EVENT_CARD_PLAYED, EVENT_PHASE_START
from tards.game import Game
from tards.player import Player


class GameHarness:
    """一键创建游戏实例，提供快捷的战场/手牌/阶段操作。"""

    def __init__(self, p1_name: str = "p1", p2_name: str = "p2") -> None:
        self.p1 = Player(0, p1_name, "d1", [])
        self.p2 = Player(1, p2_name, "d2", [])
        self.game = Game(self.p1, self.p2)
        self.players = (self.p1, self.p2)

    # ------------------------------------------------------------------
    # 战场操作
    # ------------------------------------------------------------------

    def deploy(
        self,
        name: str,
        player: Player,
        position: Tuple[int, int],
    ) -> Optional[Minion]:
        """在指定位置召唤异象（执行 special，不扣费用）。

        若目标位置已被占用，先移除旧异象（不触发亡语）。
        """
        from card_pools.effect_utils import summon_minion_by_name

        if position in self.game.board.minion_place:
            self.game.board.remove_minion(position)
        return summon_minion_by_name(self.game, name, player, position)

    def at(self, position: Tuple[int, int]) -> Optional[Minion]:
        """获取指定位置的异象。"""
        return self.game.board.get_minion_at(position)

    def enemies_of(self, player: Player) -> List[Minion]:
        """获取指定玩家的所有敌方存活异象。"""
        return [
            m for m in self.game.board.minion_place.values()
            if m.owner != player and m.is_alive()
        ]

    def clear_board(self) -> None:
        """清空战场（不触发亡语）。"""
        for pos in list(self.game.board.minion_place.keys()):
            self.game.board.remove_minion(pos)

    # ------------------------------------------------------------------
    # 手牌操作
    # ------------------------------------------------------------------

    def give_hand(self, player: Player, *names: str) -> None:
        """将指定名称的卡牌加入玩家手牌。"""
        from card_pools.effect_utils import create_card_by_name

        for name in names:
            card = create_card_by_name(name, player)
            if card is None:
                raise ValueError(f"注册表中不存在卡牌 [{name}]")
            player.add_card_to_hand(card, game=self.game, emit_events=False)

    def _find_in_hand(self, player: Player, name: str) -> Any:
        """在手牌中按名称查找卡牌。"""
        for card in player.card_hand:
            if card.name == name:
                return card
        raise ValueError(f"{player.name} 手牌中没有 [{name}]")

    def play_strategy(
        self,
        player: Player,
        name: str,
        target: Any = None,
        extra_targets: Optional[List[Any]] = None,
    ) -> bool:
        """从手牌打出一张策略卡（模拟核心流程，不检查费用/合法性）。

        流程：移出手牌 → 进入 resolving → 执行 effect →
              成功则移入弃牌堆 + 发射 EVENT_CARD_PLAYED。
        """
        card = self._find_in_hand(player, name)
        player._remove_card_from_hand(card)
        card.move_to("resolving", self.game)

        effect = card.effect(
            player=player, target=target, game=self.game,
            extra_targets=extra_targets or [],
        )
        if effect:
            card.move_to("discard", self.game)
            player.card_dis.append(card)
            self.game.emit_event(EVENT_CARD_PLAYED, player=player, card=card)
        return bool(effect)

    def play_minion(
        self,
        player: Player,
        name: str,
        position: Tuple[int, int],
        extra_targets: Optional[List[Any]] = None,
    ) -> bool:
        """从手牌部署一张异象卡（模拟核心流程，不检查费用/合法性）。"""
        card = self._find_in_hand(player, name)
        player._remove_card_from_hand(card)
        card.move_to("resolving", self.game)

        effect = card.effect(
            player=player, target=position, game=self.game,
            extra_targets=extra_targets or [],
        )
        if effect:
            card.move_to("board", self.game)
            self.game.emit_event(EVENT_CARD_PLAYED, player=player, card=card)
        return bool(effect)

    # ------------------------------------------------------------------
    # 阶段与回合
    # ------------------------------------------------------------------

    def resolve_phase(self, first: Player, second: Player) -> None:
        """发射结算阶段开始事件（不执行完整攻击结算）。"""
        self.game.emit_event(
            EVENT_PHASE_START,
            phase=self.game.PHASE_RESOLVE,
            first=first,
            second=second,
        )

    def advance_turn(self) -> None:
        """推进到下一回合（仅增加计数器与历史归档）。"""
        self.game.current_turn += 1
        self.game.history.advance_turn(self.game.current_turn)

    def start_turn(self, first: Player, second: Player) -> None:
        """发射回合开始事件。"""
        from tards.constants import EVENT_TURN_START
        self.game.emit_event(EVENT_TURN_START, first=first, second=second)

    def end_turn(self, first: Player, second: Player) -> None:
        """发射回合结束事件。"""
        from tards.constants import EVENT_TURN_END
        self.game.emit_event(EVENT_TURN_END, first=first, second=second)
