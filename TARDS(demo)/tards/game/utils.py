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

class UtilsMixin:

    def request_choice(self, player: "Player", options: List[str], title: str = "抉择") -> Optional[str]:
        """请求玩家从多个选项中选择一个。无 provider 时随机选择。"""
        if not options:
            return None
        if len(options) == 1:
            return options[0]
        if self.choice_provider:
            result = self.choice_provider(self, player, options, title)
            return result if result in options else options[0]
        import random
        return random.choice(options)

    def show_hand(self, player: Player):
        if not player.card_hand:
            print(f"    手牌: (空)")
            return
        parts = []
        for i, c in enumerate(player.card_hand, 1):
            if isinstance(c, MinionCard):
                parts.append(f"[{i}]{c.name}({c.cost} {c.attack}/{c.health})")
            else:
                parts.append(f"[{i}]{c.name}({c.cost})")
        print(f"    手牌: {' | '.join(parts)}")
        # 活跃阴谋对对手隐藏，这里仅打印自己的
        if player.active_conspiracies:
            print(f"    活跃阴谋: {', '.join(c.name for c in player.active_conspiracies)}")

    def _fmt_target(self, target: Any) -> str:
        if isinstance(target, tuple):
            r, c = target
            col_name = Board.COL_NAMES[c] if 0 <= c < 5 else str(c)
            return f"({r},{col_name})"
        if isinstance(target, Minion):
            return target.name
        if isinstance(target, Player):
            return target.name
        return str(target)

    def compute_sync_hash(self) -> str:
        """计算当前游戏状态的轻量 hash，用于联机同步校验。"""
        import hashlib
        parts = []
        parts.append(str(self.current_turn))
        for p in (self.p1, self.p2):
            parts.append(p.name)
            parts.append(str(p.health))
            parts.append(str(p.t_point))
            parts.append(str(p.c_point))
            parts.append(str(p.s_point))
            parts.append(str(p.b_point))
            parts.append(str(len(p.card_hand)))
            parts.append(str(len(p.card_deck)))
            for c in p.card_hand:
                parts.append(getattr(c, "name", "?"))
        for pos, m in sorted(self.board.minion_place.items()):
            if m.is_alive():
                parts.append(f"{getattr(m,'_sync_id','?')}:{m.name}:{m.current_health}:{pos}")
        raw = "|".join(parts)
        return hashlib.md5(raw.encode("utf-8")).hexdigest()[:8]

    def check_game_over(self) -> bool:
        if self.game_over:
            return True
        p1_dead = self.p1.health <= 0
        p2_dead = self.p2.health <= 0
        if p1_dead and p2_dead:
            print("\n双方同时倒下，平局！")
            self.game_over = True
            return True
        elif p1_dead:
            print(f"\n{self.p2.name} 获得胜利！")
            self.game_over = True
            self.winner = self.p2
            return True
        elif p2_dead:
            print(f"\n{self.p1.name} 获得胜利！")
            self.game_over = True
            self.winner = self.p1
            return True
        return False

    def develop_card(
        self,
        player: Player,
        pool_defs: List[Any],
        count: int = 3,
        modify_fn=None,
        overflow_to_discard: bool = True,
        return_card: bool = False,
        allow_statue: bool = False,
    ):
        """开发机制：从 pool_defs 的副本中随机抽取 count 张不同候选，让玩家选择一张生成到手牌。

        若设置了 discover_provider，则将已生成的候选列表交给 provider 处理选择，
        以便网络对战时同步候选列表。

        规则：
        - 候选数量固定为 count 张（默认 3），不重复。
        - 开发不会减少源池中的牌数量（使用副本）。
        - 手牌满时按爆牌处理（移入弃牌堆），除非 overflow_to_discard=False（洗入卡组）。
        - 离散3级沉浸度：开发时 +1HP。
        - 冥刻雕像类异象默认无法通过开发获得，除非 allow_statue=True（木雕师）。

        Args:
            modify_fn: 可选回调，接收生成的 Card 对象，可在加入手牌前修改其属性。
            overflow_to_discard: 手牌满时的处理方式。True=弃置（默认），False=洗入卡组。
            return_card: 为 True 时返回生成的 Card 对象（失败返回 None）；默认返回 bool。
            allow_statue: 是否允许雕像类异象进入开发候选。默认 False。
        """
        import random
        if not pool_defs:
            return None if return_card else False
        pool_copy = list(pool_defs)
        if not allow_statue:
            pool_copy = [
                c for c in pool_copy
                if not (getattr(c, "statue_top", False) or getattr(c, "statue_bottom", False))
            ]
        n = min(count, len(pool_copy))
        if n <= 0:
            return None if return_card else False
        candidates = random.sample(pool_copy, n)

        if self.discover_provider:
            result = self.discover_provider(self, player, candidates, count)
        else:
            # AI 默认策略：随机选一张
            result = random.choice(candidates)

        if result:
            card = result.to_game_card(player)
            actual = player.add_card_to_hand(card, game=self, reason="开发：获得")
            if actual and modify_fn:
                modify_fn(actual)
            if not actual:
                if overflow_to_discard:
                    print(f"  {player.name} 开发但手牌已满：{card.name} 被弃置")
                else:
                    player.card_deck.append(card)
                    random.shuffle(player.card_deck)
                    from card_pools.effect_utils import clear_shown_in_deck
                    clear_shown_in_deck(player)
                    print(f"  {player.name} 开发但手牌已满：{card.name} 洗入卡组")

            # 离散3级：开发一张牌时，+1HP
            if player.immersion_points.get(Pack.DISCRETE, 0) >= 3:
                player.health_change(1)

            # 调用通用开发回调（由附魔台等卡牌通过 effect_fn 注册）
            for cb in list(player._on_develop_callbacks):
                try:
                    cb(player, self)
                except Exception as e:
                    print(f"  [开发回调错误] {e}")

            # 发射通用开发事件
            from ..constants import EVENT_DEVELOPED
            self.emit_event(EVENT_DEVELOPED, player=player, card=card)

            return card if return_card else True

        return None if return_card else False

    def print_result(self):
        if self.winner:
            print(f"\n>>> 最终胜者: {self.winner.name} <<<")
        elif self.game_over:
            print("\n>>> 游戏结束：平局 <<<")
        else:
            print("\n>>> 游戏中断 <<<")

