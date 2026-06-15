# -*- coding: utf-8 -*-
"""Mulligan（开局手牌调整）控制器。

原位于 BattleFrame 中的 Mulligan 覆盖层、手牌渲染与选择确认逻辑，
现在集中到这里。
"""

from __future__ import annotations

import tkinter as tk
from typing import Any, Optional

from gui.theme import UI_THEME
from gui.battle.render_utils import calc_tab_width
from tards.asset_manager import get_asset_manager


class MulliganController:
    """管理开局手牌调整覆盖层的控制器。"""

    def __init__(self, frame: Any):
        self.frame = frame
        self._panel: Optional[tk.Frame] = None
        self._hand_frame: Optional[tk.Frame] = None
        self._bottom_frame: Optional[tk.Frame] = None
        self._hint_label: Optional[tk.Label] = None
        self._confirm_btn: Optional[tk.Button] = None

    # ------------------------------------------------------------------
    # 公开接口
    # ------------------------------------------------------------------
    def is_active(self) -> bool:
        return bool(self.frame.state._mulligan_overlay)

    def show(self, player: Any) -> None:
        """显示开局手牌调整界面。"""
        self.hide()
        self.frame.state._mulligan_player = player
        self.frame.state._mulligan_selected_indices = set()
        self.frame.state._mulligan_waiting_remote = False

        # 覆盖层
        overlay = tk.Frame(self.frame, bg=UI_THEME["text_primary"])
        overlay.place(relx=0, rely=0, relwidth=1, relheight=1)
        self.frame.state._mulligan_overlay = overlay

        # 中央面板
        self._panel = tk.Frame(overlay, bg=UI_THEME["bg_panel"], bd=2, relief=tk.RIDGE)
        self._panel.place(relx=0.5, rely=0.5, anchor="center", width=700, height=400)

        # 标题
        title_text = f"调整初始手牌 - {player.name}"
        tk.Label(
            self._panel, text=title_text, font=("Microsoft YaHei", 16, "bold"),
            bg=UI_THEME["bg_panel"], fg=UI_THEME["text_primary"]
        ).pack(pady=(15, 5))
        tk.Label(
            self._panel, text="点击卡牌选择要替换的牌，确认后洗回牌库并重新抽取",
            font=("Microsoft YaHei", 10), bg=UI_THEME["bg_panel"],
            fg=UI_THEME["text_secondary"]
        ).pack(pady=(0, 10))

        # 手牌区
        self._hand_frame = tk.Frame(self._panel, bg=UI_THEME["bg_panel"])
        self._hand_frame.pack(pady=10)

        self._refresh_cards()

        # 提示与按钮区
        self._bottom_frame = tk.Frame(self._panel, bg=UI_THEME["bg_panel"])
        self._bottom_frame.pack(pady=10)

        self._hint_label = tk.Label(
            self._bottom_frame, text="", font=("Microsoft YaHei", 10),
            bg=UI_THEME["bg_panel"], fg=UI_THEME["accent"]
        )
        self._hint_label.pack(pady=(0, 5))

        self._confirm_btn = tk.Button(
            self._bottom_frame, text="确认替换",
            font=("Microsoft YaHei", 12), width=12,
            bg=UI_THEME["btn_primary_bg"], fg=UI_THEME["btn_primary_fg"],
            activebackground=UI_THEME["btn_primary_active"], relief=tk.RAISED, bd=2,
            command=self.confirm,
        )
        self._confirm_btn.pack(pady=5)

    def hide(self) -> None:
        """隐藏 mulligan 界面并清理状态。"""
        if self.frame.state._mulligan_overlay:
            self.frame.state._mulligan_overlay.destroy()
            self.frame.state._mulligan_overlay = None
        self.frame.state._mulligan_player = None
        self.frame.state._mulligan_selected_indices = set()
        self.frame.state._mulligan_waiting_remote = False
        self._panel = None
        self._hand_frame = None
        self._bottom_frame = None
        self._hint_label = None
        self._confirm_btn = None

    def confirm(self) -> None:
        """确认 mulligan 选择。"""
        if not self.frame.state._mulligan_overlay:
            return
        indices = sorted(self.frame.state._mulligan_selected_indices)
        if self.frame.duel.mulligan_waits_for_remote:
            self.frame.state._mulligan_waiting_remote = True
            if self._confirm_btn and self._hint_label:
                self._confirm_btn.config(state=tk.DISABLED, text="等待对手调整...")
                self._hint_label.config(text="已提交选择，等待对手完成调整...")
            self.frame.duel.submit_local_mulligan(indices)
        else:
            self.frame.duel.submit_local_mulligan(indices)
            self.hide()

    # ------------------------------------------------------------------
    # 内部渲染
    # ------------------------------------------------------------------
    def _refresh_cards(self) -> None:
        """刷新 mulligan 手牌显示。"""
        if not self.frame.state._mulligan_overlay or not self.frame.state._mulligan_player:
            return
        frame = self._hand_frame
        if frame is None:
            return
        for w in list(frame.winfo_children()):
            w.destroy()

        from tards.cards import MinionCard as MC, Strategy as ST, Conspiracy as CO, MineralCard as MI
        card_type_colors = {MC: "#eff6ff", ST: "#f0fdf4", CO: "#faf5ff", MI: "#fefce8"}
        am = get_asset_manager()
        cw = self.frame.HAND_CARD_WIDTH
        ch = self.frame.HAND_CARD_HEIGHT

        for i, card in enumerate(self.frame.state._mulligan_player.card_hand):
            selected = i in self.frame.state._mulligan_selected_indices
            self._render_card(frame, card, i, selected, card_type_colors, am, cw, ch)

    def _on_card_click(self, idx: int) -> None:
        """切换 mulligan 卡牌选中状态。"""
        if idx in self.frame.state._mulligan_selected_indices:
            self.frame.state._mulligan_selected_indices.remove(idx)
        else:
            self.frame.state._mulligan_selected_indices.add(idx)
        self._refresh_cards()

    def _render_card(self, parent: tk.Widget, card: Any, idx: int, selected: bool,
                     card_type_colors: dict, am: Any, cw: int, ch: int) -> None:
        """渲染单张 mulligan 卡牌。"""
        try:
            frame_bd = 3 if selected else 0
            frame_bg = UI_THEME["success"] if selected else UI_THEME["bg_panel"]
            frame = tk.Frame(parent, bg=frame_bg, bd=frame_bd)
            frame.pack(side=tk.LEFT, padx=4)
            cvs = tk.Canvas(frame, width=cw, height=ch, highlightthickness=0, bd=0, bg=UI_THEME["bg_panel"])
            cvs.pack(padx=2, pady=2)

            cost_str = str(card.cost)
            TAB_W = calc_tab_width(cost_str)
            TAB_H = 16
            TAB_SLANT = max(5, TAB_W // 6)
            card_x1, card_y1 = 0, 0
            card_x2, card_y2 = cw, ch

            # 带标签形状的稀有度渐变背景
            rarity_colors = self.frame._get_card_rarity_gradient_colors(card)
            bg_colors = rarity_colors if rarity_colors else UI_THEME["rarity_none"]
            if getattr(self.frame, "_PIL_AVAILABLE", False):
                photo = self.frame._create_tab_gradient_photo(
                    cw, ch,
                    bg_colors[0], bg_colors[1],
                    tab_w=TAB_W, tab_h=TAB_H, slant=TAB_SLANT, radius=2
                )
                if photo:
                    cvs.create_image(cw // 2, ch // 2, image=photo, tags="rarity_bg")
                    cvs.rarity_bg_image = photo

            # 标签区域填充（mulligan 无"可打出"状态，始终深灰）
            label_points = [
                card_x1, card_y1,
                card_x1 + TAB_W, card_y1,
                card_x1 + TAB_W + TAB_SLANT, card_y1 + TAB_H,
                card_x1, card_y1 + TAB_H,
            ]
            cvs.create_polygon(label_points, fill=UI_THEME["card_tab_default"], outline="", tags="cost_tab")

            # 整体外形边框（带标签的微圆角矩形）
            r = 2
            body_y1 = card_y1 + TAB_H
            shape_points = [
                card_x1, card_y1,
                card_x1 + TAB_W, card_y1,
                card_x1 + TAB_W + TAB_SLANT, body_y1,
                card_x2 - r, body_y1,
                card_x2, body_y1 + r,
                card_x2, card_y2 - r,
                card_x2 - r, card_y2,
                card_x1 + r, card_y2,
                card_x1, card_y2 - r,
                card_x1, body_y1,
            ]
            border_color = UI_THEME["success"] if selected else UI_THEME["card_border_default"]
            border_width = 2 if selected else 1
            cvs.create_polygon(
                shape_points, fill="", outline=border_color, width=border_width,
                joinstyle=tk.MITER, tags="card_border"
            )

            img = None
            if getattr(card, "asset_id", None):
                img = am.get_card_face(card.asset_id, cw - 4, ch - 4)
            if img:
                cvs.create_image(cw // 2, ch // 2, image=img, tags="card_img")
                cvs.image = img

            # 费用文字（标签内，白色）
            cost_cx = card_x1 + (TAB_W + TAB_SLANT) // 2
            cost_cy = card_y1 + TAB_H // 2
            cvs.create_text(cost_cx, cost_cy, text=cost_str, fill="white",
                            font=("Microsoft YaHei", 8, "bold"), tags="card_text")

            name = card.name
            stats = ""
            from tards.cards import MinionCard as MC, Strategy as ST, Conspiracy as CO, MineralCard as MI
            if isinstance(card, MC):
                stats = f"{card.attack}/{card.health}"
            bottom_text = stats
            if isinstance(card, ST):
                bottom_text = "【策略】"
            elif isinstance(card, CO):
                bottom_text = "【阴谋】"
            elif isinstance(card, MI):
                bottom_text = "【矿物】"
            elif isinstance(card, MC):
                bottom_text = f"【异象】{stats}"
            cvs.create_text(cw // 2, 20 + TAB_H, text=name, fill=UI_THEME["card_text_name"],
                            font=("Microsoft YaHei", 9, "bold"), tags="card_text")
            cvs.create_text(cw // 2, ch - 12, text=bottom_text, fill=UI_THEME["card_text_type"],
                            font=("Microsoft YaHei", 8), tags="card_text")
            cvs.bind("<Button-1>", lambda e, i=idx: self._on_card_click(i))
        except Exception as e:
            print(f"[_render_mulligan_card] 渲染卡牌异常 [{getattr(card, 'name', 'unknown')}]: {e}")
            import traceback
            traceback.print_exc()
