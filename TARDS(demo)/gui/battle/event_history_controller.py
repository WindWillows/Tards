"""事件与历史记录控制器。

负责操作历史 Listbox、顶部最近事件条、费用预览。
"""

from __future__ import annotations

import time
import tkinter as tk
from typing import Any, List, Optional, Tuple

from tards.net.net_game import NetworkDuel
from gui.theme import UI_THEME


class EventHistoryController:
    """管理对战界面的操作历史、最近事件条与费用预览。"""

    def __init__(self, frame: Any):
        self.frame = frame

    # ------------------------------------------------------------------
    # 操作历史
    # ------------------------------------------------------------------
    def add_history(self, text: str, is_play: bool = False,
                    player_name: Optional[str] = None,
                    turn: Optional[int] = None,
                    phase: Optional[str] = None) -> None:
        """添加一条操作历史记录。"""
        frame = self.frame
        if not frame.duel.game:
            return
        turn = turn if turn is not None else frame.duel.game.current_turn
        phase = phase if phase is not None else frame.duel.game.current_phase
        phase_map = {"draw": "抽牌", "action": "出牌", "resolve": "结算", "start": "开始", "end": "结束"}
        phase_text = phase_map.get(phase, phase)

        if phase != frame.state._history_phase:
            frame.state._history_phase = phase
            if phase == "action":
                frame.state._history_action_counter = 0

        if text == "拍铃":
            frame.state._history_action_counter = 0

        if player_name is None:
            player_name = frame.duel.game.current_player.name if frame.duel.game.current_player else "?"

        if is_play and phase == "action":
            frame.state._history_action_counter += 1
            prefix = f"{player_name}·#{frame.state._history_action_counter} "
        else:
            prefix = f"{player_name} "

        entry = f"回合{turn} [{phase_text}] {prefix}{text}"
        frame.history_list.insert(tk.END, entry)
        if frame.history_list.size() > 50:
            frame.history_list.delete(0)
        frame.history_list.see(tk.END)

    # ------------------------------------------------------------------
    # 最近事件条
    # ------------------------------------------------------------------
    def add_recent_event(self, text: str, positions: Optional[List[Tuple[int, int]]] = None) -> None:
        """记录一条最近发生的事件。"""
        frame = self.frame
        frame.state._recent_events.append({
            "time": time.time(),
            "text": text,
            "positions": positions or [],
        })
        if len(frame.state._recent_events) > 5:
            frame.state._recent_events = frame.state._recent_events[-5:]
        self.refresh_event_bar()

    def refresh_event_bar(self) -> None:
        """刷新顶部最近动作事件条。"""
        frame = self.frame
        if not frame.state._recent_events:
            frame.event_bar_label.config(text="")
            return
        latest = frame.state._recent_events[-1]
        frame.event_bar_label.config(text=f"最近：{latest['text']}")

    def expire_recent_events(self) -> None:
        """清除 2.5 秒前的事件。"""
        frame = self.frame
        now = time.time()
        cutoff = now - 2.5
        before = len(frame.state._recent_events)
        frame.state._recent_events = [e for e in frame.state._recent_events if e["time"] >= cutoff]
        if len(frame.state._recent_events) != before:
            self.refresh_event_bar()

    # ------------------------------------------------------------------
    # 费用预览
    # ------------------------------------------------------------------
    def show_cost_preview(self, card: Any, serial: int) -> None:
        """悬停手牌时预览打出该牌后的资源变化。"""
        frame = self.frame
        if not frame.duel.game or not card:
            return
        active = frame.duel.game.current_player
        if not active:
            return
        if frame.duel.is_remote and active != frame.local_player:
            return
        if frame.duel.game.current_phase != "action":
            return

        cost = active._get_play_cost(card)

        remaining_t_after_t = active.t_point - cost.t
        pay_c_for_ct = min(active.c_point, cost.ct)
        pay_t_for_ct = cost.ct - pay_c_for_ct
        new_t = active.t_point - cost.t - pay_t_for_ct
        new_c = active.c_point - cost.c - pay_c_for_ct
        new_b = max(0, active.b_point - cost.b)
        new_s = active.s_point - cost.s

        def fmt_change(old: int, new: int, label: str, color: str) -> str:
            if old == new:
                return f"{label}:{new}"
            return f"{label}:{old}→{new}"

        parts = [
            fmt_change(active.t_point, new_t, "T", UI_THEME["res_t"]),
            fmt_change(active.c_point, new_c, "C", UI_THEME["res_c"]),
        ]
        if cost.b > 0 or active.b_point > 0:
            parts.append(fmt_change(active.b_point, new_b, "B", UI_THEME["res_b"]))
        if cost.s > 0 or active.s_point > 0:
            parts.append(fmt_change(active.s_point, new_s, "S", UI_THEME["res_s"]))

        preview_text = "打出后: " + "  ".join(parts)

        affordable, reason = cost.can_afford_detail(active)
        if not affordable:
            preview_text += f"  （无法支付：{reason}）"
            frame.cost_preview_label.config(fg=UI_THEME["danger"])
        else:
            frame.cost_preview_label.config(fg=UI_THEME["text_secondary"])

        if cost.minerals:
            mineral_parts = []
            for mtype, need in cost.minerals.items():
                mineral_parts.append(f"{need}{mtype}")
            preview_text += f"  需矿物: {', '.join(mineral_parts)}"

        frame.cost_preview_label.config(text=preview_text)

    def clear_cost_preview(self) -> None:
        """清除费用支付预览。"""
        frame = self.frame
        if getattr(frame, "cost_preview_label", None):
            frame.cost_preview_label.config(text="", fg=UI_THEME["text_secondary"])
