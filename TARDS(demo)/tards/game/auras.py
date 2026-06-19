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

class AuraMixin:

    def refresh_all_auras(self):
        """刷新全场异象的临时光环（具有）效果。"""
        for m in list(self.board.minion_place.values()):
            if m.is_alive():
                m.recalculate()

