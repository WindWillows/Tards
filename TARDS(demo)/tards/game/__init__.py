from .core import CoreMixin
from .events import EventMixin
from .auras import AuraMixin
from .transform import TransformMixin
from .phases import PhaseMixin
from .combat import CombatMixin
from .utils import UtilsMixin

class Game(
    CoreMixin,
    EventMixin,
    AuraMixin,
    TransformMixin,
    PhaseMixin,
    CombatMixin,
    UtilsMixin,
):
    """网络/本地对战的核心游戏控制器。"""
    pass

__all__ = ["Game"]
