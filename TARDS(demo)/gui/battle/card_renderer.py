"""卡牌渲染器。

负责渲染手牌、mulligan 卡牌、揭示卡牌等，减少 Gamestart.py 中 BattleFrame 的体积。
"""

from typing import Any, Dict, Optional

import tkinter as tk

try:
    from PIL import Image, ImageDraw, ImageTk
    _PIL_AVAILABLE = True
except Exception:  # pragma: no cover
    Image = ImageDraw = ImageTk = None  # type: ignore
    _PIL_AVAILABLE = False

from tards import MinionCard, Strategy, Conspiracy, MineralCard
from tards.assets import get_asset_manager
from tards.card_db import DEFAULT_REGISTRY
from gui.theme import UI_THEME
from gui.battle.render_utils import (
    calc_tab_width,
    create_tab_gradient_photo,
    create_strategy_gradient_photo,
    draw_minion_stat_badges,
)


class CardRenderer:
    """负责各类卡牌的 Canvas 渲染。"""

    def __init__(self, frame: Any):
        self.frame = frame

    # ------------------------------------------------------------------
    # 通用卡牌底层绘制
    # ------------------------------------------------------------------
    def _draw_card_base(
        self,
        cvs: tk.Canvas,
        card: Any,
        cw: int,
        ch: int,
        cost_str: str,
        border_color: str,
        border_width: int,
        tab_fill: str,
        offset_y: int = 0,
    ) -> None:
        """绘制卡牌通用底层：稀有度渐变、费用标签、边框。"""
        card_x1, card_y1 = 0, 0
        card_x2, card_y2 = cw, ch

        TAB_W = calc_tab_width(cost_str)
        TAB_H = 16
        TAB_SLANT = max(5, TAB_W // 6)

        rarity_colors = self.frame._get_card_rarity_gradient_colors(card)
        bg_colors = rarity_colors if rarity_colors else UI_THEME["rarity_none"]

        # 策略卡：左上角斜切 + 底部尖角盾牌形
        if isinstance(card, Strategy):
            self._draw_strategy_card_base(
                cvs, card_x1, card_y1, card_x2, card_y2,
                bg_colors, border_color, border_width, tab_fill, offset_y,
                cost_str,
            )
            return

        # 带标签形状的稀有度渐变背景
        if _PIL_AVAILABLE:
            photo = create_tab_gradient_photo(
                cw, ch,
                bg_colors[0], bg_colors[1],
                tab_w=TAB_W, tab_h=TAB_H, slant=TAB_SLANT, radius=2
            )
            if photo:
                cvs.create_image(
                    cw // 2,
                    ch // 2 + offset_y,
                    image=photo, tags="rarity_bg"
                )
                cvs.rarity_bg_image = photo

        # 标签区域填充
        label_points = [
            card_x1, card_y1 + offset_y,
            card_x1 + TAB_W, card_y1 + offset_y,
            card_x1 + TAB_W + TAB_SLANT, card_y1 + TAB_H + offset_y,
            card_x1, card_y1 + TAB_H + offset_y,
        ]
        cvs.create_polygon(label_points, fill=tab_fill, outline="", tags="cost_tab")

        # 整体外形边框
        r = 2
        body_y1 = card_y1 + TAB_H + offset_y
        y2o = card_y2 + offset_y
        shape_points = [
            card_x1, card_y1 + offset_y,
            card_x1 + TAB_W, card_y1 + offset_y,
            card_x1 + TAB_W + TAB_SLANT, body_y1,
            card_x2 - r, body_y1,
            card_x2, body_y1 + r,
            card_x2, y2o - r,
            card_x2 - r, y2o,
            card_x1 + r, y2o,
            card_x1, y2o - r,
            card_x1, body_y1,
        ]
        cvs.create_polygon(shape_points, fill="", outline=border_color, width=border_width,
                           joinstyle=tk.MITER, tags="card_border")

    def _draw_strategy_card_base(
        self,
        cvs: tk.Canvas,
        x1: int,
        y1: int,
        x2: int,
        y2: int,
        bg_colors,
        border_color: str,
        border_width: int,
        tab_fill: str,
        offset_y: int,
        cost_str: str,
    ) -> None:
        """绘制策略卡底层：上半部分与普通卡牌一致，底部为尖角 V 形。"""
        cw = x2 - x1
        ch = y2 - y1
        TAB_W = calc_tab_width(cost_str)
        TAB_H = 16
        TAB_SLANT = max(5, TAB_W // 6)
        POINT_DEPTH = 12
        r = 2
        body_y1 = y1 + TAB_H + offset_y
        y2o = y2 + offset_y

        if _PIL_AVAILABLE:
            photo = create_strategy_gradient_photo(
                cw, ch,
                bg_colors[0], bg_colors[1],
                tab_w=TAB_W, tab_h=TAB_H, slant=TAB_SLANT,
                point_depth=POINT_DEPTH, radius=r,
            )
            if photo:
                cvs.create_image(
                    cw // 2,
                    ch // 2 + offset_y,
                    image=photo, tags="rarity_bg",
                )
                cvs.rarity_bg_image = photo

        # 费用标签（与普通卡牌一致）
        label_points = [
            x1, y1 + offset_y,
            x1 + TAB_W, y1 + offset_y,
            x1 + TAB_W + TAB_SLANT, body_y1,
            x1, body_y1,
        ]
        cvs.create_polygon(label_points, fill=tab_fill, outline="", tags="cost_tab")

        # 外形边框：顶部同普通卡，底部尖角
        shape_points = [
            x1, y1 + offset_y,
            x1 + TAB_W, y1 + offset_y,
            x1 + TAB_W + TAB_SLANT, body_y1,
            x2 - r, body_y1,
            x2, body_y1 + r,
            x2, y2 - r - POINT_DEPTH + offset_y,
            x2 - r, y2 - POINT_DEPTH + offset_y,
            (x1 + x2) // 2, y2o,
            x1 + r, y2 - POINT_DEPTH + offset_y,
            x1, y2 - r - POINT_DEPTH + offset_y,
            x1, body_y1,
        ]
        cvs.create_polygon(shape_points, fill="", outline=border_color, width=border_width,
                           joinstyle=tk.MITER, tags="card_border")

    def _draw_card_face(self, cvs: tk.Canvas, card: Any, cw: int, ch: int) -> None:
        """绘制卡牌肖像。"""
        am = get_asset_manager()
        img = None
        if getattr(card, "asset_id", None):
            img = am.get_card_face(card.asset_id, cw - 4, ch - 4)
        if img:
            cvs.create_image(cw // 2, ch // 2, image=img, tags="card_img")
            cvs.image = img

    def _draw_card_text(
        self,
        cvs: tk.Canvas,
        card: Any,
        cw: int,
        ch: int,
        cost_str: str,
        offset_y: int = 0,
        bottom_y: int = 0,
    ) -> None:
        """绘制卡牌费用、名称、底部攻防徽章。"""
        TAB_W = calc_tab_width(cost_str)
        TAB_H = 16
        TAB_SLANT = max(5, TAB_W // 6)

        cost_cx = (TAB_W + TAB_SLANT) // 2
        cost_cy = TAB_H // 2 + offset_y
        cvs.create_text(cost_cx, cost_cy, text=cost_str, fill="white",
                        font=("Microsoft YaHei", 8, "bold"), tags="card_text")

        name = card.name
        cvs.create_text(cw // 2, 20 + TAB_H, text=name, fill=UI_THEME["card_text_name"],
                        font=("Microsoft YaHei", 9, "bold"), tags="card_text")
        # 类型由卡牌外形区分；异象卡用左/下角彩色徽章显示攻击/生命
        if isinstance(card, MinionCard):
            draw_minion_stat_badges(
                cvs, card.attack, card.health, cw, ch, offset_y=offset_y
            )

    # ------------------------------------------------------------------
    # 手牌渲染
    # ------------------------------------------------------------------
    def render_hand_card(
        self,
        parent: tk.Widget,
        card: Any,
        idx: int,
        serial: int,
        active: Any,
        flash: bool = False,
    ) -> None:
        """渲染单张手牌卡牌。"""
        """渲染单张手牌卡牌。"""
        try:
            cw = self.frame.HAND_CARD_WIDTH
            ch = self.frame.HAND_CARD_HEIGHT

            # 计算可用 B 点（含场上可献祭异象）
            available_blood = self.frame._get_available_blood(active)
            original_b = active.b_point
            active.b_point = original_b + available_blood
            effective_cost = active._get_play_cost(card)
            cost_ok, _ = effective_cost.can_afford_detail(active)
            active.b_point = original_b
            can_play_now = (
                cost_ok
                and not self.frame._in_targeting_mode
                and self.frame.duel.game
                and self.frame.duel.game.current_phase == "action"
            )

            frame = tk.Frame(parent, bd=0)
            frame.pack(side=tk.LEFT, padx=6, pady=2)
            if flash:
                self.frame._flash_widget_bg(frame, UI_THEME["kw_vision"], times=2, interval=150)

            cvs = tk.Canvas(frame, width=cw, height=ch, highlightthickness=0, bd=0)
            cvs.pack()

            cost_str = str(effective_cost)

            # 计算状态 → 边框样式
            is_selected = self.frame.selected_card_idx == idx
            is_valid_target = (
                self.frame._in_targeting_mode
                and card in self.frame._targeting_valid_targets
            )
            if is_selected:
                border_color = UI_THEME["card_border_selected"]
                border_width = 3
                offset_y = 0
            elif is_valid_target:
                border_color = UI_THEME["card_border_target"]
                border_width = 3
                offset_y = 0
            else:
                border_color = UI_THEME["card_border_default"]
                border_width = 1
                offset_y = 1

            tab_fill = UI_THEME["card_tab_playable"] if can_play_now else UI_THEME["card_tab_default"]
            self._draw_card_base(cvs, card, cw, ch, cost_str, border_color, border_width, tab_fill, offset_y)
            self._draw_card_face(cvs, card, cw, ch)
            self._draw_card_text(cvs, card, cw, ch, cost_str, offset_y, bottom_y=cw - 14)

            # 已激活的阴谋：红色边框
            if isinstance(card, Conspiracy) and card in active.active_conspiracies:
                shape = cvs.find_withtag("card_border")
                if shape:
                    cvs.itemconfig(shape[-1], outline=UI_THEME["danger"], width=3)

            # 已被对手见过的牌：左下角折痕效果
            if getattr(card, "_shown_to_opponent", False):
                self._draw_shown_fold(cvs, card, cw, ch, offset_y)

            # 堆叠数量
            stack_count = getattr(card, "stack_count", 1)
            if stack_count > 1:
                cvs.create_oval(cw - 22, ch - 22 + offset_y, cw - 2, ch - 2 + offset_y,
                                fill=UI_THEME["card_stack_bg"], outline="white", width=2, tags="stack_count")
                cvs.create_text(cw - 12, ch - 12 + offset_y, text=str(stack_count), fill="white",
                                font=("Microsoft YaHei", 9, "bold"), tags="stack_count")

            cvs.bind("<Button-1>", lambda e, i=idx: self.frame._on_hand_card_click(i))
            cvs.bind("<ButtonPress-1>", lambda e, c=card, s=serial: self.frame._on_drag_start(e, c, s))
            cvs.bind("<Enter>", lambda e, c=card, s=serial: self._on_hand_enter(c, s))
            cvs.bind("<Leave>", lambda e: (self.frame._hide_tooltip(), self.frame._clear_preview(), self.frame._clear_detail_text()))
            cvs.bind("<Motion>", lambda e, c=card: self.frame._move_tooltip(e.x_root, e.y_root))
        except Exception as e:
            # noqa: BLE001 (legacy pattern)
            print(f"[_render_hand_card] 渲染卡牌异常 [{getattr(card, 'name', 'unknown')}]: {e}")
            import traceback
            traceback.print_exc()

    def _on_hand_enter(self, card: Any, serial: str) -> None:
        """鼠标进入手牌：先更新右侧面板详情，再尝试高亮可部署位置。"""
        self.frame._update_detail_text(card)
        try:
            self.frame._preview_deploy_positions(serial)
        except Exception as exc:  # noqa: BLE001 (预览失败不应影响详情展示)
            print(f"[警告] 预览部署位置失败 [{getattr(card, 'name', serial)}]: {exc}")

    def _draw_shown_fold(self, cvs: tk.Canvas, card: Any, cw: int, ch: int, offset_y: int) -> None:
        """绘制已展示给对手的折痕标记。"""
        fold_rarity = getattr(card, "rarity", None)
        if fold_rarity is None and DEFAULT_REGISTRY:
            defn = DEFAULT_REGISTRY.get(card.name)
            if defn:
                fold_rarity = defn.rarity
        back_color, front_color, line_color = self.frame._FOLD_COLORS.get(
            fold_rarity, self.frame._FOLD_COLORS[None]
        )
        cvs.create_polygon(0, ch - 6 + offset_y, 0, ch + offset_y, 12, ch + offset_y,
                           fill=back_color, outline="", tags="shown_mark")
        cvs.create_polygon(0, ch - 12 + offset_y, 0, ch - 6 + offset_y, 12, ch + offset_y,
                           fill=front_color, outline="", tags="shown_mark")
        cvs.create_line(0, ch - 6 + offset_y, 12, ch + offset_y,
                        fill=line_color, width=1, tags="shown_mark")

    # ------------------------------------------------------------------
    # Mulligan 卡牌渲染
    # ------------------------------------------------------------------
    def render_mulligan_card(
        self,
        parent: tk.Widget,
        card: Any,
        idx: int,
        selected: bool,
        cw: int,
        ch: int,
    ) -> None:
        """渲染单张 mulligan 卡牌。"""
        try:
            frame_bd = 3 if selected else 0
            frame_bg = UI_THEME["success"] if selected else UI_THEME["bg_panel"]
            frame = tk.Frame(parent, bg=frame_bg, bd=frame_bd)
            frame.pack(side=tk.LEFT, padx=4)
            cvs = tk.Canvas(frame, width=cw, height=ch, highlightthickness=0, bd=0, bg=UI_THEME["bg_panel"])
            cvs.pack(padx=2, pady=2)

            cost_str = str(card.cost)
            border_color = UI_THEME["success"] if selected else UI_THEME["card_border_default"]
            border_width = 2 if selected else 1
            tab_fill = UI_THEME["card_tab_default"]

            self._draw_card_base(cvs, card, cw, ch, cost_str, border_color, border_width, tab_fill, offset_y=0)
            self._draw_card_face(cvs, card, cw, ch)
            self._draw_card_text(cvs, card, cw, ch, cost_str, offset_y=0, bottom_y=ch - 12)

            cvs.bind("<Button-1>", lambda e, i=idx: self.frame._on_mulligan_card_click(i))
        except Exception as e:
            # noqa: BLE001 (legacy pattern)
            print(f"[_render_mulligan_card] 渲染卡牌异常 [{getattr(card, 'name', 'unknown')}]: {e}")
            import traceback
            traceback.print_exc()

    # ------------------------------------------------------------------
    # 揭示卡牌渲染
    # ------------------------------------------------------------------
    def render_reveal_card(self, canvas: tk.Canvas, card: Any, cw: int = 90, ch: int = 144) -> None:
        """在指定 Canvas 上渲染一张静态展示卡牌（用于弃置/移除/磨牌展示）。"""
        print(f"[Reveal] _render_reveal_card 开始: card={getattr(card, 'name', 'unknown')}")
        canvas.delete("all")
        try:
            cost_str = str(card.cost)
            print(f"[Reveal]   cost_str={cost_str}")
            border_color = UI_THEME["card_border_default"]
            border_width = 1

            self._draw_card_base(canvas, card, cw, ch, cost_str, border_color, border_width,
                                 UI_THEME["card_tab_default"], offset_y=0)
            self._draw_card_face(canvas, card, cw, ch)
            self._draw_card_text(canvas, card, cw, ch, cost_str, offset_y=0, bottom_y=ch - 14)
            print(f"[Reveal] _render_reveal_card 完成")
        except Exception as e:
            # noqa: BLE001 (legacy pattern)
            print(f"[Reveal] [_render_reveal_card] 渲染异常 [{getattr(card, 'name', 'unknown')}]: {e}")
            import traceback
            traceback.print_exc()
