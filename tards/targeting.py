#!/usr/bin/env python3
"""通用目标选择器模块。

所有需要玩家选择目标的行为（策略卡、异象部署、场上异象技能、视野攻击预设等）
都通过 TargetingRequest 统一描述，由 TargetPicker 负责收集玩家输入。
"""

from dataclasses import dataclass, field
from typing import Any, Callable, List, Optional, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from .board import Board
    from .cards import Minion
    from .game import Game
    from .player import Player


@dataclass
class TargetingRequest:
    """统一的目标选择请求。任何需要指向的行为都打包成此对象。

    字段:
        valid_targets: 合法目标列表（位置、异象、玩家等）
        count: 需要选择的目标数量（默认1）
        allow_repeat: 是否允许重复选择同一目标
        prompt: 给玩家的提示文字
        on_confirm: 选择完成后回调，接收 [target, ...]
        on_cancel: 取消时回调
    """
    valid_targets: List[Any]
    count: int = 1
    allow_repeat: bool = False
    prompt: str = "请选择目标"
    on_confirm: Callable[[List[Any]], None] = field(default=lambda _: None)
    on_cancel: Callable[[], None] = field(default=lambda: None)


class TargetPicker:
    """负责收集玩家选择的一个或多个目标。"""

    def __init__(self, request: TargetingRequest):
        self.request = request
        self.selected: List[Any] = []

    def is_valid(self, target: Any) -> bool:
        if self.request.allow_repeat:
            return target in self.request.valid_targets
        return target in self.request.valid_targets and target not in self.selected

    def select(self, target: Any) -> bool:
        if not self.is_valid(target):
            return False
        self.selected.append(target)
        if len(self.selected) >= self.request.count:
            self.confirm()
        return True

    def confirm(self):
        self.request.on_confirm(list(self.selected))
        self.selected.clear()

    def cancel(self):
        self.request.on_cancel()
        self.selected.clear()

    def get_prompt(self) -> str:
        return f"{self.request.prompt} ({len(self.selected)}/{self.request.count})"


def get_attack_target_candidates(minion: "Minion", game: "Game") -> List[Any]:
    """返回该异象当前可以攻击的合法目标（包含敌方异象和敌方玩家）。

    有视野的异象可以攻击视野范围内的任意敌方异象（含潜水/潜行，因为指向发生在出牌阶段）；
    无视野的异象只能攻击同列最前排的敌方异象。
    """
    board = game.board
    vision_range = minion.keywords.get("视野", 0)
    base_col = minion.position[1]
    opponent = game.p2 if minion.owner == game.p1 else game.p1

    if vision_range > 0:
        enemies = [m for m in board.minion_place.values()
                   if m.owner != minion.owner and m.is_alive()
                   and abs(m.position[1] - base_col) <= vision_range]
        candidates = enemies + [opponent]
    else:
        front = board.get_front_minion(base_col, minion.owner, attacker=minion)
        candidates = [front] if front else [opponent]
    return candidates


# 注意：get_deploy_extra_targets 已废弃。
# 随从卡和策略卡统一使用 extra_targeting_stages 处理多阶段指向。
# 保留此函数签名作为兼容 shim，但实际行为为空。
def get_deploy_extra_targets(
    player: "Player",
    board: "Board",
    card: Any,
) -> Tuple[List[Any], int, bool]:
    """[已废弃] 随从卡统一使用 extra_targeting_stages 处理额外指向。"""
    return [], 0, False
