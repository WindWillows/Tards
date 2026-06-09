from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional, Tuple

if TYPE_CHECKING:
    from .game import Game
    from .player import Player
    from .cards import Minion


FusionAction = Callable[["Game", "FusionEdge", "Minion"], None]
FusionSpec = Dict[str, Any]


@dataclass
class FusionEdge:
    """A graph edge between two minions that can fuse."""

    kind: str
    owner: "Player"
    first: "Minion"
    second: "Minion"
    first_spec: FusionSpec
    second_spec: FusionSpec
    ready_turn: int
    matched: bool = True
    label: str = "融合"
    start_verb: str = "融合准备"
    complete_verb: str = "融合完成"
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def key(self) -> Tuple[str, int, int]:
        a, b = sorted((id(self.first), id(self.second)))
        return (self.kind, a, b)

    @property
    def participants(self) -> Tuple["Minion", "Minion"]:
        return (self.first, self.second)

    def spec_for(self, minion: "Minion") -> FusionSpec:
        if minion is self.first:
            return self.first_spec
        if minion is self.second:
            return self.second_spec
        raise KeyError("minion is not part of this fusion edge")

    def role(self, role_name: str) -> Optional["Minion"]:
        if self.first_spec.get("role") == role_name:
            return self.first
        if self.second_spec.get("role") == role_name:
            return self.second
        return None

    def ordered_participants(self) -> List[Tuple["Minion", FusionSpec]]:
        pairs = [(self.first, self.first_spec), (self.second, self.second_spec)]
        return sorted(pairs, key=lambda item: item[1].get("role_order", 100))

    def __getitem__(self, key: str) -> Any:
        """Legacy dict-style access for old statue tests and helpers."""
        if key == "top":
            return self.role("top")
        if key == "bottom":
            return self.role("bottom")
        if key in ("fuse_at_turn", "ready_turn"):
            return self.ready_turn
        if key == "owner":
            return self.owner
        raise KeyError(key)


class FusionSystem:
    """Graph-backed minion fusion system.

    Each live minion may expose one or more ``fusion_specs``. The system scans
    friendly minions after deployment, builds graph edges for compatible specs,
    and resolves ready edges at phase/turn boundaries.
    """

    def __init__(self, game: "Game"):
        self.game = game
        self.graph: Dict[int, Dict[int, FusionEdge]] = {}
        self.pending: List[FusionEdge] = []
        self._pending_keys: set[Tuple[str, int, int]] = set()

    def specs_for(self, minion: "Minion") -> List[FusionSpec]:
        specs = getattr(minion, "fusion_specs", None)
        if not specs:
            return []
        return [spec for spec in specs if spec.get("kind")]

    def scan_after_deploy(self, event_data: Dict[str, Any]) -> None:
        minion = event_data.get("minion")
        if not minion or not getattr(minion, "is_alive", lambda: False)():
            return
        player = event_data.get("player")
        if not player:
            return
        if not self.specs_for(minion):
            return

        for other in self.game.board.get_minions_of_player(player):
            if other is minion or not other.is_alive():
                continue
            edge = self._make_edge(minion, other, player)
            if not edge:
                continue
            self._add_edge(edge)
            if edge.key in self._pending_keys:
                continue
            self.pending.append(edge)
            self._pending_keys.add(edge.key)
            state = "配对" if edge.matched else "未配对"
            print(
                f"  {edge.label}{edge.start_verb}：{edge.first.name} + {edge.second.name}，"
                f"{state}，将于第 {edge.ready_turn} 回合结束时生效"
            )

    def rebuild_graph(self) -> None:
        self.graph.clear()
        for player in self.game.players:
            minions = [m for m in self.game.board.get_minions_of_player(player) if m.is_alive()]
            for i, first in enumerate(minions):
                for second in minions[i + 1:]:
                    edge = self._make_edge(first, second, player)
                    if edge:
                        self._add_edge(edge)

    def edge_between(self, first: "Minion", second: "Minion") -> Optional[FusionEdge]:
        return self.graph.get(id(first), {}).get(id(second))

    def resolve_ready(self) -> None:
        resolved: List[FusionEdge] = []
        for edge in list(self.pending):
            if not all(m.is_alive() for m in edge.participants):
                resolved.append(edge)
                continue
            if self.game.current_turn < edge.ready_turn:
                continue

            names = " + ".join(m.name for m in edge.participants)
            print(f"  {edge.label} [{names}] {edge.complete_verb}！")
            for minion, spec in edge.ordered_participants():
                for action in spec.get("actions", []):
                    label = action.get("label", f"{minion.name} {edge.label}")
                    fn = action.get("fn")
                    if not fn:
                        continue
                    self.game.effect_queue.queue(
                        label,
                        lambda m=minion, e=edge, f=fn: f(self.game, e, m),
                    )

            if edge.metadata.get("remove_after", True):
                self.game.effect_queue.queue(
                    f"移除{edge.label}组件",
                    lambda e=edge: self._remove_participants(e),
                )
            resolved.append(edge)

        for edge in resolved:
            self._remove_pending(edge)

    def _make_edge(
        self,
        first: "Minion",
        second: "Minion",
        owner: "Player",
    ) -> Optional[FusionEdge]:
        for first_spec in self.specs_for(first):
            for second_spec in self.specs_for(second):
                if not self._compatible(first, first_spec, second, second_spec):
                    continue
                return self._build_edge(first, first_spec, second, second_spec, owner)
        return None

    def _compatible(
        self,
        first: "Minion",
        first_spec: FusionSpec,
        second: "Minion",
        second_spec: FusionSpec,
    ) -> bool:
        if first.owner is not second.owner:
            return False
        if first_spec.get("kind") != second_spec.get("kind"):
            return False
        if first_spec.get("role") == second_spec.get("role"):
            return bool(first_spec.get("allow_same_role") and second_spec.get("allow_same_role"))

        first_allowed = first_spec.get("compatible_roles")
        if first_allowed is not None and second_spec.get("role") not in first_allowed:
            return False
        second_allowed = second_spec.get("compatible_roles")
        if second_allowed is not None and first_spec.get("role") not in second_allowed:
            return False

        for spec, other, other_spec in (
            (first_spec, second, second_spec),
            (second_spec, first, first_spec),
        ):
            can_fuse = spec.get("can_fuse_with")
            if can_fuse and not can_fuse(other, other_spec):
                return False
        return True

    def _build_edge(
        self,
        first: "Minion",
        first_spec: FusionSpec,
        second: "Minion",
        second_spec: FusionSpec,
        owner: "Player",
    ) -> FusionEdge:
        if second_spec.get("role_order", 100) < first_spec.get("role_order", 100):
            first, second = second, first
            first_spec, second_spec = second_spec, first_spec
        first_group = first_spec.get("group")
        second_group = second_spec.get("group")
        matched = first_group == second_group if first_group is not None and second_group is not None else True
        delay_key = "matched_delay" if matched else "unmatched_delay"
        delay = max(first_spec.get(delay_key, 0), second_spec.get(delay_key, 0))
        metadata = {
            "remove_after": first_spec.get("remove_after", second_spec.get("remove_after", True)),
            "group": first_group if first_group == second_group else None,
        }
        return FusionEdge(
            kind=first_spec["kind"],
            owner=owner,
            first=first,
            second=second,
            first_spec=first_spec,
            second_spec=second_spec,
            ready_turn=self.game.current_turn + delay,
            matched=matched,
            label=first_spec.get("label") or second_spec.get("label") or "融合",
            start_verb=first_spec.get("start_verb") or second_spec.get("start_verb") or "融合准备",
            complete_verb=first_spec.get("complete_verb") or second_spec.get("complete_verb") or "融合完成",
            metadata=metadata,
        )

    def _add_edge(self, edge: FusionEdge) -> None:
        a = id(edge.first)
        b = id(edge.second)
        self.graph.setdefault(a, {})[b] = edge
        self.graph.setdefault(b, {})[a] = edge

    def _remove_pending(self, edge: FusionEdge) -> None:
        if edge in self.pending:
            self.pending.remove(edge)
        self._pending_keys.discard(edge.key)
        self.graph.get(id(edge.first), {}).pop(id(edge.second), None)
        self.graph.get(id(edge.second), {}).pop(id(edge.first), None)

    def _remove_participants(self, edge: FusionEdge) -> None:
        for minion in edge.participants:
            if minion.is_alive() and getattr(minion, "position", None) is not None:
                self.game.board.remove_minion(minion.position)
