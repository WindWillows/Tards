"""玩家信息与资源面板渲染器。

原位于 Gamestart.py::BattleFrame._render_info，提取到此模块以减少 BattleFrame 体积。
"""

from typing import Any, Dict, Optional

import tkinter as tk

from tards.card_db import Pack
from tards.net_game import NetworkDuel
from gui.theme import UI_THEME


class InfoRenderer:
    """负责更新对战双方信息面板与右侧资源面板。"""

    def __init__(self, frame: Any):
        self.frame = frame

    def render(self) -> None:
        """刷新所有玩家信息与资源显示。"""
        if not self.frame.duel.game:
            return

        self._render_player_panels()
        self._render_resource_panel()
        self._sync_squirrel_checkbox()

    def _render_player_panels(self) -> None:
        """更新顶部双方信息面板。"""
        for pname, widgets in self.frame.info_labels.items():
            player = None
            if self.frame.duel.game.p1.name == pname:
                player = self.frame.duel.game.p1
            elif self.frame.duel.game.p2.name == pname:
                player = self.frame.duel.game.p2
            if not player:
                continue

            is_current = self.frame.duel.game.current_player == player
            is_target = (
                self.frame._in_targeting_mode
                and player in self.frame._targeting_valid_targets
            )

            # 背景色
            if is_target:
                bg = UI_THEME["btn_warning_bg"]
            elif is_current:
                bg = "#dcfce7"
            elif getattr(player, "braked", False):
                bg = UI_THEME["btn_danger_bg"]
            else:
                bg = UI_THEME["bg_main"]

            for key in [
                "frame", "row0", "row1", "row2", "row_shown", "right_info",
                "dot", "name_label", "hp_frame", "hp_label",
                "dis_label", "conspiracy_label", "shown_label", "last_dis_label",
            ]:
                if key in widgets:
                    widgets[key].config(bg=bg)
            for key in ["deck_badge", "hand_label"]:
                if key in widgets:
                    widgets[key].config(bg=bg)
            # 恢复手牌 badge 背景色
            if "hand_label" in widgets:
                widgets["hand_label"].config(bg="#dbeafe")

            # 回合标记 + 名字
            active_mark = "● " if is_current else ""
            widgets["name_label"].config(text=f"{active_mark}{pname}")

            # HP
            widgets["hp_bar"].config(maximum=player.health_max, value=player.health)
            widgets["hp_label"].config(text=f"{player.health}/{player.health_max}")

            # 资源（Canvas 圆角方块，通过 itemconfig 更新文字）
            res_data = [
                ("t", player.t_point, player.t_point_max, widgets.get("t_cvs"), widgets.get("t_text")),
                ("c", player.c_point, player.c_point_max, widgets.get("c_cvs"), widgets.get("c_text")),
                ("b", player.b_point, None, widgets.get("b_cvs"), widgets.get("b_text")),
                ("s", player.s_point, None, widgets.get("s_cvs"), widgets.get("s_text")),
            ]
            for key, val, val_max, cvs, text_id in res_data:
                if cvs is None or text_id is None:
                    continue
                old_val = self.frame._prev_res_values.get((pname, key))
                if old_val is not None and val != old_val:
                    # 数值变化时闪烁：白色 → 黄色 → 白色
                    def _flash(c=cvs, t=text_id, orig="white"):
                        c.itemconfig(t, fill="yellow")
                        c.after(150, lambda: c.itemconfig(t, fill=orig))
                        c.after(300, lambda: c.itemconfig(t, fill="yellow"))
                        c.after(450, lambda: c.itemconfig(t, fill=orig))

                    _flash()
                self.frame._prev_res_values[(pname, key)] = val
                prefix = {"t": "T", "c": "C", "b": "B", "s": "S"}[key]
                if val_max is not None:
                    cvs.itemconfig(text_id, text=f"{prefix} {val}/{val_max}")
                else:
                    cvs.itemconfig(text_id, text=f"{prefix} {val}")

            # 牌组信息
            hand_count = len(player.card_hand)
            mineral_count = len(player.extra_hand)
            if player.extra_hand_max > 0 and mineral_count > 0:
                hand_text = f"手牌 {hand_count}+{mineral_count}"
            else:
                hand_text = f"手牌 {hand_count}"
            widgets["hand_label"].config(text=hand_text)
            widgets["deck_badge"].config(text=f"牌库 {len(player.card_deck)}")
            widgets["dis_label"].config(text=f"弃牌 {len(player.card_dis)}")
            widgets["conspiracy_label"].config(text=f"阴谋 {len(player.active_conspiracies)}")

            # 已展示给对手的牌
            shown_names = [c.name for c in player.card_hand if getattr(c, "_shown_to_opponent", False)]
            if shown_names:
                widgets["shown_label"].config(text=f"已展示: {', '.join(shown_names)}")
            else:
                widgets["shown_label"].config(text="")

            # 上一张弃牌
            last_dis_label = widgets.get("last_dis_label")
            if last_dis_label:
                card_dis = player.card_dis
                if card_dis:
                    last_card = card_dis[-1]
                    last_info = self.frame._last_discarded_info.get(pname)
                    if last_info and last_info[0] == last_card.name:
                        card_name, color = last_info
                    else:
                        card_name = last_card.name
                        color = UI_THEME["text_primary"]
                        self.frame._last_discarded_info[pname] = (card_name, color)
                    last_dis_label.config(text=f"上一张: {card_name}", fg=color)
                else:
                    last_dis_label.config(text="")

            # 弃牌堆 badge 状态
            discard_badge = widgets.get("discard_badge")
            if discard_badge:
                discard_badge.config(text=f"弃牌堆 {len(player.card_dis)}")

    def _render_resource_panel(self) -> None:
        """更新右侧'当前资源'面板（网络对局显示本地玩家，本地对局显示当前回合玩家）。"""
        game = self.frame.duel.game
        active = game.current_player if game else None
        display_player = self.frame.local_player if isinstance(self.frame.duel, NetworkDuel) else active
        if not display_player:
            if hasattr(self.frame, "res_panel") and self.frame.res_panel.winfo_exists():
                self.frame.res_panel.config(text="当前资源")
            return

        for key, val, lbl in [
            ("res_t", display_player.t_point, self.frame.res_t_label),
            ("res_c", display_player.c_point, self.frame.res_c_label),
            ("res_b", display_player.b_point, self.frame.res_b_label),
            ("res_s", display_player.s_point, self.frame.res_s_label),
        ]:
            old_val = self.frame._prev_res_values.get(key)
            if old_val is not None and val != old_val:
                flash_color = "#4caf50" if val > old_val else "#f44336"
                self.frame._flash_res_label(lbl, flash_color, times=2, interval=150)
            self.frame._prev_res_values[key] = val

        self.frame.res_t_label.config(text=f"T:{display_player.t_point}/{display_player.t_point_max}")
        self.frame.res_c_label.config(text=f"C:{display_player.c_point}/{display_player.c_point_max}")
        if self.frame._in_sacrifice_mode and self.frame._sacrifice_active == display_player:
            selected_blood = sum(m.keywords.get("丰饶", 1) for m in self.frame._selected_sacrifices)
            total_blood = display_player.b_point + selected_blood
            self.frame.res_b_label.config(text=f"B:{total_blood}/{self.frame._sacrifice_required}")
        else:
            self.frame.res_b_label.config(text=f"B:{display_player.b_point}")
        has_underworld = display_player.immersion_points.get(Pack.UNDERWORLD, 0) >= 1
        if has_underworld:
            self.frame.res_sacrifice_label.config(text=f"可献祭:{self.frame._get_available_blood(display_player)}")
            if not self.frame.res_sacrifice_label.winfo_ismapped():
                self.frame.res_sacrifice_label.pack(side=tk.LEFT, padx=(0, 8))
        else:
            self.frame.res_sacrifice_label.pack_forget()
        self.frame.res_s_label.config(text=f"S:{display_player.s_point}")
        self.frame.res_deck_label.config(text=f"抽牌堆:{len(display_player.card_deck)}")
        self.frame.res_dis_label.config(text=f"弃牌堆:{len(display_player.card_dis)}")
        self.frame.res_conspiracy_label.config(text=f"阴谋序列:{len(display_player.active_conspiracies)}")
        self.frame.res_panel.config(text=f"{display_player.name} 的资源")

    def _sync_squirrel_checkbox(self) -> None:
        """同步"抽松鼠"复选框状态（仅本地玩家可操作）。"""
        game = self.frame.duel.game
        active = game.current_player if game else None
        if active and (not isinstance(self.frame.duel, NetworkDuel) or active == self.frame.local_player):
            has_underworld = active.immersion_points.get(Pack.UNDERWORLD, 0) >= 1
            if has_underworld and active.squirrel_deck:
                self.frame.squirrel_draw_cb.pack(side=tk.LEFT)
                self.frame.squirrel_draw_var.set(active.squirrel_draw_enabled)
            else:
                self.frame.squirrel_draw_cb.pack_forget()
        else:
            self.frame.squirrel_draw_cb.pack_forget()
