"""本地对战控制器。

原位于 Gamestart.py，现独立出来供菜单/大厅等模块使用。
接口与 NetworkDuel 保持一致，用于人机测试或本地双人对打。
"""

from __future__ import annotations

import random
import threading
from typing import Any, Callable, Dict, List, Optional

from tards import Game, Player


class LocalDuel:
    """本地对战控制器（人机测试），接口与 NetworkDuel 保持一致。"""

    def __init__(self, local_player: Player, local_deck_list: list):
        self.local_player = local_player
        self.local_deck_list = local_deck_list

        self.game: Optional[Game] = None
        self.local_turn_callback: Optional[Callable[[], None]] = None
        self.game_over_callback: Optional[Callable[[Optional[str]], None]] = None
        self.discover_request_callback: Optional[Callable[[list], None]] = None
        self.resolve_step_callback: Optional[Callable[[], None]] = None

        self._local_action: Optional[Dict[str, Any]] = None
        self._local_action_event = threading.Event()
        self._local_turn_event = threading.Event()

        self._discover_names: Optional[list] = None
        self._discover_result: Optional[str] = None
        self._discover_event = threading.Event()

        self._choice_options: Optional[list] = None
        self._choice_result: Optional[str] = None
        self._choice_event = threading.Event()
        self._choice_title: str = "抉择"

        self.targeting_request_callback: Optional[Callable[[Any, List[Any]], None]] = None
        self._targeting_request: Optional[Any] = None
        self._targeting_valid_targets: Optional[List[Any]] = None
        self._targeting_result: Optional[Any] = None
        self._targeting_event = threading.Event()

        self.mulligan_request_callback: Optional[Callable[[Player], None]] = None
        self._mulligan_player: Optional[Player] = None
        self._mulligan_indices: Optional[List[int]] = None
        self._mulligan_event = threading.Event()

    def run_game(self, opponent: Player, logger=None):
        self.game = Game(
            self.local_player,
            opponent,
            action_provider=self._make_action_provider(),
            discover_provider=self._make_discover_provider(),
            targeting_provider=self._make_targeting_provider(),
            mulligan_provider=self._make_mulligan_provider(),
            logger=logger,
        )
        self.game.choice_provider = self._make_choice_provider()
        self.game.resolve_step_callback = self.resolve_step_callback
        self.game.resolve_column_delay = getattr(self, "resolve_column_delay", 0.0)
        self.game.start_game()
        if self.game_over_callback and self.game.game_over:
            self.game_over_callback(self.game.winner.name if self.game.winner else None)

    def _make_action_provider(self):
        def provider(game, active, opponent):
            if self.local_turn_callback:
                self.local_turn_callback()
            self._local_turn_event.set()
            # 超时轮询，避免 GUI 未响应时永久阻塞
            while not self._local_action_event.wait(timeout=5.0):
                if game.game_over:
                    self._local_turn_event.clear()
                    return None
            self._local_action_event.clear()
            self._local_turn_event.clear()
            return self._local_action
        return provider

    def _make_discover_provider(self):
        def provider(game, player, candidates, count):
            names = [getattr(d, "name", str(d)) for d in candidates]
            self._discover_names = names
            self._discover_result = None
            self._discover_event.clear()
            if self.discover_request_callback:
                self.discover_request_callback(names)
                # 超时轮询，允许游戏结束时退出等待
                while not self._discover_event.wait(timeout=5.0):
                    if game.game_over:
                        return candidates[0] if candidates else None
                chosen_name = self._discover_result if self._discover_result is not None else names[0]
            else:
                # 无 GUI 回调时回退随机选择（避免死锁）
                chosen_name = random.choice(names)
            for d in candidates:
                if getattr(d, "name", str(d)) == chosen_name:
                    return d
            return candidates[0] if candidates else None
        return provider

    def submit_local_discover(self, chosen: str):
        self._discover_result = chosen
        self._discover_event.set()

    def _make_choice_provider(self):
        def provider(game, player, options, title):
            self._choice_options = options
            self._choice_result = None
            self._choice_title = title
            self._choice_event.clear()
            if self.choice_request_callback:
                self.choice_request_callback(options, title)
            # 超时轮询，允许游戏结束时退出等待
            while not self._choice_event.wait(timeout=5.0):
                if game.game_over:
                    return options[0] if options else None
            return self._choice_result if self._choice_result in options else options[0]
        return provider

    def _make_targeting_provider(self):
        def provider(game, request, valid_targets):
            # 本地对战（人机测试/双人对战）：无论哪个玩家回合，都交给 GUI 让玩家选择
            self._targeting_request = request
            self._targeting_valid_targets = valid_targets
            self._targeting_result = None
            self._targeting_event.clear()
            if self.targeting_request_callback:
                self.targeting_request_callback(request, valid_targets)
            # 超时轮询，允许游戏结束时退出等待
            while not self._targeting_event.wait(timeout=5.0):
                if game.game_over:
                    return None
            return self._targeting_result
        return provider

    def submit_local_targeting(self, target: Any):
        """GUI 调用：提交本地玩家的指向选择。"""
        self._targeting_result = target
        self._targeting_event.set()

    def submit_local_mulligan(self, indices: List[int]):
        """GUI 调用：提交本地玩家的开局手牌调整选择。"""
        self._mulligan_indices = indices
        self._mulligan_event.set()

    def submit_local_choice(self, chosen: str):
        self._choice_result = chosen
        self._choice_event.set()

    def submit_local_action(self, action: Dict[str, Any]):
        self._local_action = action
        self._local_action_event.set()

    def is_local_turn(self) -> bool:
        return self._local_turn_event.is_set()

    def _make_mulligan_provider(self):
        def provider(game, players):
            for player in players:
                self._mulligan_player = player
                self._mulligan_indices = None
                self._mulligan_event.clear()
                if self.mulligan_request_callback:
                    self.mulligan_request_callback(player)
                # 超时轮询，允许游戏结束时退出等待
                while not self._mulligan_event.wait(timeout=5.0):
                    if game.game_over:
                        return
                indices = self._mulligan_indices or []
                cards = [player.card_hand[i] for i in indices
                         if 0 <= i < len(player.card_hand)]
                player.mulligan(cards, game=game)
        return provider

    def close(self):
        self._local_action_event.set()
        self._discover_event.set()
        self._choice_event.set()
        self._targeting_event.set()
        self._mulligan_event.set()
