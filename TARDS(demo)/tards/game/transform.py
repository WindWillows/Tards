from typing import Any, Callable, Dict, List, Optional
from ..core.board import Board
from ..cards import MineralCard, Minion, MinionCard, Strategy, Conspiracy
from ..data.card_db import DEFAULT_REGISTRY, CardType, Pack
from ..constants import (
    EVENT_BELL,
    EVENT_BRAKE,
    EVENT_CARD_PLAYED,
    EVENT_CONSPIRACY_TRIGGERED,
    EVENT_DEATH,
    EVENT_DEPLOYED,
    EVENT_DRAW,
    EVENT_PHASE_END,
    EVENT_PHASE_START,
    EVENT_PLAYER_DAMAGE,
    EVENT_SACRIFICE,
    EVENT_TURN_END,
    EVENT_TURN_START,
)
from ..effect_queue import EffectQueue
from ..events import EventBus, GameEvent
from ..core.fusion import FusionSystem
from ..core.game_history import GameHistory
from ..core.game_logger import GameLogger
from ..core.player import Player
from ..core.targeting import TargetingRequest, TargetingSystem

class TransformMixin:

    def transform_minion(self, old_minion: "Minion", new_card_def, preserve_summon_turn: bool = True) -> Optional["Minion"]:
        """通用异象变化/替换框架：将 old_minion 替换为 new_card_def 定义的新异象，位置不变。"""
        from ..data.card_db import CardType
        if new_card_def.card_type != CardType.MINION:
            print(f"  错误：{new_card_def.name} 不是异象类型，无法替换")
            return None
        next_card = new_card_def.to_game_card(old_minion.owner)
        new_minion = Minion(
            name=next_card.name,
            owner=old_minion.owner,
            position=old_minion.position,
            attack=next_card.attack,
            health=next_card.health,
            source_card=next_card,
            board=self.board,
            keywords=next_card.keywords.copy(),
            on_turn_start=getattr(next_card, 'on_turn_start', None),
            on_turn_end=getattr(next_card, 'on_turn_end', None),
            on_phase_start=getattr(next_card, 'on_phase_start', None),
            on_phase_end=getattr(next_card, 'on_phase_end', None),
            statue_top=getattr(next_card, 'statue_top', False),
            statue_bottom=getattr(next_card, 'statue_bottom', False),
            statue_pair=getattr(next_card, 'statue_pair', None),
            on_statue_activate=getattr(next_card, 'on_statue_activate', None),
            on_statue_fuse=getattr(next_card, 'on_statue_fuse', None),
        )
        if preserve_summon_turn:
            new_minion.summon_turn = old_minion.summon_turn
        new_minion._transformed_from = old_minion
        if self.board.replace_minion(old_minion.position, new_minion):
            on_evolve = getattr(next_card, 'on_evolve_fn', None)
            if on_evolve:
                on_evolve(new_minion, old_minion.owner, self)
            return new_minion
        return None

    def move_minion(self, minion: "Minion", new_pos: Any, allow_cross_side: bool = False) -> bool:
        """安全移动异象到新的空格子。"""
        if not minion or not minion.is_alive():
            return False
        return self.board.move_minion(minion, new_pos, allow_cross_side=allow_cross_side)

    def swap_minions(self, m1: "Minion", m2: "Minion") -> bool:
        """安全交换两个异象的位置。"""
        if not m1 or not m2:
            return False
        return self.board.swap_minions(m1, m2)

    def _check_fusion_edges(self, event_data: Dict[str, Any]):
        """在部署事件后检查是否形成了新的异象融合边。"""
        self.fusion_system.scan_after_deploy(event_data)

    def _resolve_fusions(self):
        """结算待处理的异象融合。"""
        self.fusion_system.resolve_ready()

    def _check_statue_pair(self, event_data: Dict[str, Any]):
        """兼容旧接口：雕像配对现在由通用融合系统处理。"""
        self._check_fusion_edges(event_data)

    def _resolve_statue_fusions(self):
        """兼容旧接口：雕像融合现在由通用融合系统处理。"""
        self._resolve_fusions()

