from typing import Any, Callable, Dict, List, Optional, TYPE_CHECKING
import inspect
from ..core.cost import Cost
from ..constants import EVENT_BEFORE_DEPLOY, EVENT_DEPLOYED, EVENT_AFTER_DEPLOY, EVENT_SACRIFICE
from .base import Card

if TYPE_CHECKING:
    from ..core.player import Player
    from ..core.board import Board
    from ..game import Game
    from .minion import Minion


class MinionCard(Card):
    """异象卡（异象卡）。

    策略化改造后，异象卡被视为一种特殊的策略卡：
      - 部署 = 对棋盘格的指向动作，起点 = 异象卡自身。
      - effect() 与 Strategy 同构，通过 effect_fn 执行实际逻辑。
      - 默认 effect_fn 为 _default_minion_effect，负责创建 Minion 并放置到战场。
      - 部署后的 special（部署效果）以新创建的异象为起点发起指向。
    """

    def __init__(
        self,
        name: str,
        owner: "Player",
        cost: Cost,
        targets: Callable[["Player", "Board"], List[Any]],
        attack: int,
        health: int,
        effect_fn: Optional[Callable[["Player", Any, "Game"], bool]] = None,
        special: Optional[Callable[["Minion", "Player", "Game"], Any]] = None,
        keywords: Optional[Dict[str, Any]] = None,
        on_turn_start: Optional[Callable] = None,
        on_turn_end: Optional[Callable] = None,
        on_phase_start: Optional[Callable] = None,
        on_phase_end: Optional[Callable] = None,
        tags: Optional[List[str]] = None,
        hidden_keywords: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(name, cost, targets, on_turn_start, on_turn_end, on_phase_start, on_phase_end)
        self.attack = attack
        self.health = health
        self.effect_fn = effect_fn
        self.special = special
        self.owner = owner
        self.keywords = keywords or {}
        self.evolve_to: Optional[str] = None
        self.tags = tags or []
        self.hidden_keywords = hidden_keywords or {}

    def effect(self, player: "Player", target: Any, game: "Game", extra_targets: Optional[List[Any]] = None) -> bool:
        """与 Strategy.effect() 同构：调用 effect_fn 执行部署逻辑。"""
        if self.effect_fn is None:
            return _default_minion_effect(player, target, game, extra_targets or [], self)
        sig = inspect.signature(self.effect_fn)
        param_count = len(sig.parameters)
        if param_count >= 5:
            return self.effect_fn(player, target, game, extra_targets or [], self)
        elif param_count >= 4:
            return self.effect_fn(player, target, game, extra_targets or [])
        else:
            return self.effect_fn(player, target, game)


def _default_minion_effect(player: "Player", target: Any, game: "Game",
                           extra_targets: Optional[List[Any]] = None,
                           card: Optional["MinionCard"] = None) -> bool:
    """默认异象部署效果。

    将部署建模为指向动作：TargetingAction(source=card, target=position)。
    部署后的 special（如有额外指向）以新创建的异象为起点。
    """
    if card is None:
        return False

    board = game.board
    if not board.target_check(target):
        return False
    sacrifices = getattr(card, '_preselected_sacrifices', None)
    if not board.is_valid_deploy(target, player, card, ignored_minions=sacrifices):
        print("  无法在此位置部署异象。")
        return False
    existing = board.get_minion_at(target)
    if existing is not None:
        # 漂浮物：允许在其上部署新异象
        if "漂浮物" in existing.keywords and existing.owner == player:
            pass
        # 藤蔓：允许覆盖友方异象
        elif "藤蔓" in card.keywords and existing.owner == player:
            pass
        else:
            print("  该格子已被占用")
            return False

    # 鲜血费用：执行献祭（消灭友方异象、触发事件，不管理 b_point）
    if card.cost.b > 0:
        # 优先使用 game.py 预选并暂存的献祭目标
        preselected = getattr(card, '_preselected_sacrifices', None) or []
        # play_card 正规流程会记录有多少 B 点来自非献祭来源（如血瓶），
        # 若未设置（例如直接调用 effect 的召唤效果）则默认为 0，按旧逻辑请求献祭。
        blood_from_b_point = getattr(card, '_blood_paid_from_b_point', 0)
        blood_from_preselected = sum(m.keywords.get("丰饶", 1) for m in preselected)
        total_available = blood_from_b_point + blood_from_preselected

        sacrifices = list(preselected)
        if total_available < card.cost.b:
            remaining = card.cost.b - total_available
            more = player.request_sacrifice(remaining)
            if more is None:
                print("  献祭不足，无法部署")
                return False
            sacrifices.extend(more)

        total_blood = sum(m.keywords.get("丰饶", 1) for m in sacrifices)
        for m in sacrifices:
            # 检查献祭次数
            if getattr(m, '_sacrifice_remaining', 0) <= 0:
                print(f"  {m.name} 献祭次数已耗尽，无法再献祭")
                return False
            # 免疫献祭消灭的异象不消耗献祭次数（如「猫」）
            if not getattr(m, '_immune_to_sacrifice', False):
                m._sacrifice_remaining -= 1
            blood = m.keywords.get("丰饶", 1)
            # 消灭异象并触发亡语（免疫献祭的异象除外）
            if getattr(m, '_immune_to_sacrifice', False):
                print(f"  献祭 {m.name}（免疫献祭，异象保留），获得 {blood}B")
            else:
                m.current_health = 0
                # 献祭需要立即从战场移除，避免在抉择/指向等阻塞效果期间
                # 祭品仍以 HP 0 的状态留在场上。
                m.minion_death(sync=True)
                print(f"  献祭 {m.name}，获得 {blood}B")
            game.emit_event(EVENT_SACRIFICE, minion=m, player=player, blood=blood,
                            required_blood=card.cost.b, total_blood=total_blood)

    # 回响：面板设为 1/1
    deploy_attack = 1 if card.keywords.get("回响", False) else card.attack
    deploy_health = 1 if card.keywords.get("回响", False) else card.health

    from ..core.targeting import TargetingAction
    from .minion import Minion
    minion = Minion(
        name=card.name,
        owner=player,
        position=target,
        attack=deploy_attack,
        health=deploy_health,
        source_card=card,
        board=board,
        keywords=card.keywords.copy(),
        on_turn_start=card.on_turn_start,
        on_turn_end=card.on_turn_end,
        on_phase_start=card.on_phase_start,
        on_phase_end=card.on_phase_end,
        statue_top=getattr(card, 'statue_top', False),
        statue_bottom=getattr(card, 'statue_bottom', False),
        statue_pair=getattr(card, 'statue_pair', None),
        on_statue_activate=getattr(card, 'on_statue_activate', None),
        on_statue_fuse=getattr(card, 'on_statue_fuse', None),
        tags=list(card.tags) if hasattr(card, 'tags') else [],
        hidden_keywords=getattr(card, 'hidden_keywords', None),
    )
    minion._extra_targets = extra_targets or []
    minion.asset_id = getattr(card, 'asset_id', None)

    # === BEFORE_DEPLOY 事件 ===
    deploy_event = game.emit_event(
        EVENT_BEFORE_DEPLOY,
        source=player,
        target=minion,
        player=player,
        minion=minion,
        card=card,
        position=target,
    )
    if getattr(deploy_event, "cancelled", False):
        print(f"  {minion.name} 的部署被取消")
        return False

    if board.place_minion(minion, target):
        # 应用部署增益（雕像等）
        for buff in getattr(player, '_deploy_buffs', []):
            buff(minion)
        print(f"  {player.name} 在 {target} 部署了 {minion.name}")
        minion.summon_turn = game.current_turn
        # 休眠：所有异象部署时具有休眠1（迅捷异象在 can_attack 中特殊处理）
        if "休眠" not in minion.base_keywords:
            minion.base_keywords["休眠"] = 1
            minion.recalculate()
        # 部署效果（special）— 先让新异象完成自身初始化（注册监听器等）
        if card.special:
            sig = inspect.signature(card.special)
            if len(sig.parameters) >= 4:
                special_result = card.special(minion, player, game, extra_targets or [])
            else:
                special_result = card.special(minion, player, game)
            if special_result is False:
                # special_fn 取消了部署（例如玩家取消指向），回滚
                board.remove_minion(minion.position)
                return False
        # 触发全局部署光环钩子（如侦测器等对其他异象部署作出反应）
        for hook in getattr(game, "deploy_hooks", []):
            hook(minion)
        game.emit_event(EVENT_DEPLOYED, minion=minion, player=player, card=card)

        # === AFTER_DEPLOY 事件 ===
        game.emit_event(
            EVENT_AFTER_DEPLOY,
            source=player,
            target=minion,
            player=player,
            minion=minion,
            card=card,
            position=target,
        )

        # 广播部署指向动作：起点 = 异象卡，目标 = 棋盘格
        game.emit_event(
            "targeting_action_executed",
            action=TargetingAction(source=card, target=target),
            minion=minion,
            player=player,
        )
        return True
    return False
