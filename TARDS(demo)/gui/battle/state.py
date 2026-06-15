"""对战界面状态容器。

原位于 BattleFrame.__init__ 及其方法中的各类状态变量，
现在集中到这里，便于后续拆分到不同 controller/view。

注意：当前版本只负责"把状态放在一起"，后续 controller 会逐步接管状态的生命周期方法。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set


@dataclass
class BattleState:
    """BattleFrame 运行期状态。"""

    # 选择 / 输入
    selected_card_idx: Optional[int] = None
    selected_card: Optional[Any] = None
    valid_targets: List[Any] = field(default_factory=list)

    # Tooltip
    _tooltip: Optional[Any] = None
    _tooltip_source: Optional[Any] = None

    # 待播放数据 / 游戏线程
    _pending_play_data: Optional[Dict[str, Any]] = None
    _game_thread: Optional[Any] = None

    # 指向模式
    _targeting_source_minion: Optional[Any] = None
    _current_targeting_mode: Optional[str] = None
    _in_targeting_mode: bool = False
    _targeting_valid_targets: List[Any] = field(default_factory=list)
    _targeting_on_confirm: Optional[Callable[[Any], None]] = None
    _targeting_on_cancel: Optional[Callable[[], None]] = None

    # 献祭模式
    _in_sacrifice_mode: bool = False
    _sacrifice_candidates: List[Any] = field(default_factory=list)
    _selected_sacrifices: List[Any] = field(default_factory=list)
    _sacrifice_required: int = 0
    _sacrifice_serial: Optional[int] = None
    _sacrifice_card: Optional[Any] = None
    _sacrifice_active: Optional[Any] = None
    _pending_sacrifices: List[Any] = field(default_factory=list)

    # 拖拽
    _dragging_card: Optional[Any] = None
    _dragging_serial: Optional[int] = None
    _drag_start_x: int = 0
    _drag_start_y: int = 0
    _drag_label: Optional[Any] = None

    # 棋盘几何（随 Canvas 大小动态调整）
    cell_size: int = 80
    board_offset_x: int = 50
    board_offset_y: int = 40

    # 手牌/费用变化闪烁追踪
    _prev_hand_card_ids: Set[Any] = field(default_factory=set)
    _prev_res_values: Dict[str, Any] = field(default_factory=dict)
    _last_discarded_info: Dict[str, Any] = field(default_factory=dict)
    _history_phase: Optional[str] = None
    _history_action_counter: int = 0

    # Mulligan（开局手牌调整）状态
    _mulligan_overlay: Optional[Any] = None
    _mulligan_player: Optional[Any] = None
    _mulligan_selected_indices: Set[int] = field(default_factory=set)
    _mulligan_waiting_remote: bool = False

    # 揭示系统状态
    _reveal_listeners_registered: bool = False
    _reveal_queue: List[Any] = field(default_factory=list)
    _is_revealing: bool = False

    # 输入防抖
    _is_playing_card: bool = False
    _is_belling: bool = False
    _is_braking: bool = False

    # 渲染引用缓存
    _minion_image_refs: Dict[str, Any] = field(default_factory=dict)
    _tile_image_refs: Dict[Any, Any] = field(default_factory=dict)
    _mineral_buttons: Dict[str, Any] = field(default_factory=dict)
