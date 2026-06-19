# -*- coding: utf-8 -*-
"""弃置/移除/磨牌展示控制器。

原位于 BattleFrame 中的揭示队列与展示面板逻辑，现在集中到这里。
"""

from __future__ import annotations

import tkinter as tk
from typing import TYPE_CHECKING, Any, List, Optional

from tards.data.card_db import DEFAULT_REGISTRY
from tards.constants import EVENT_CARD_PLAYED, EVENT_DISCARDED, EVENT_MILLED
from gui.battle.render_utils import calc_tab_width, draw_minion_stat_badges

if TYPE_CHECKING:
    from tkinter import Canvas


class RevealController:
    """管理右下角揭示/展示面板的控制器。"""

    def __init__(self, frame: Any):
        self.frame = frame
        self.reveal_frame: Optional[tk.LabelFrame] = None
        self.reveal_canvas: Optional[tk.Canvas] = None
        self.reveal_label: Optional[tk.Label] = None

    # ------------------------------------------------------------------
    # UI 构建
    # ------------------------------------------------------------------
    def build_ui(self, parent: tk.Widget) -> None:
        """在父容器（右侧面板）中创建展示面板。"""
        from gui.theme import UI_THEME

        self.reveal_frame = tk.LabelFrame(
            parent, text="展示", font=("Microsoft YaHei", 10),
            bg=UI_THEME["bg_panel"], fg=UI_THEME["text_secondary"],
        )
        self.reveal_frame.pack(fill=tk.X, pady=(0, 5))
        self.reveal_frame.pack_forget()  # 初始隐藏

        self.reveal_canvas = tk.Canvas(
            self.reveal_frame, width=90, height=144, highlightthickness=0, bd=0,
            bg=UI_THEME["bg_panel"],
        )
        self.reveal_canvas.pack(padx=5, pady=5)

        self.reveal_label = tk.Label(
            self.reveal_frame, text="", font=("Microsoft YaHei", 10),
            bg=UI_THEME["bg_panel"], fg=UI_THEME["text_primary"],
        )
        self.reveal_label.pack(padx=5, pady=(0, 5))

        self.frame.state._reveal_queue = []
        self.frame.state._is_revealing = False

    # ------------------------------------------------------------------
    # 监听注册
    # ------------------------------------------------------------------
    def register(self, game: Any) -> None:
        """注册弃置/移除/磨牌展示监听器（仅一次）。"""
        if not game:
            return
        if getattr(self.frame.state, "_reveal_listeners_registered", False):
            return

        from gui.theme import UI_THEME

        print(f"[Reveal] 注册展示监听器到游戏 {id(game)}")

        def on_reveal_event(event: Any) -> None:
            event_type = event.type
            card = event.get("card")
            player = event.get("player")
            print(
                f"[Reveal] 收到事件: {event_type}, "
                f"card={getattr(card, 'name', None)}, "
                f"player={getattr(player, 'name', None)}"
            )
            if not card:
                return
            if event_type == EVENT_DISCARDED:
                label = "弃置"
                if player:
                    self.frame.state._last_discarded_info[player.name] = (
                        card.name, UI_THEME["accent"]
                    )
            elif event_type == EVENT_MILLED:
                label = "磨牌"
            elif event_type == "card_removed_from_deck":
                label = "移除"
            else:
                label = "展示"
            # 仅将数据放入队列，不操作 GUI（线程安全）
            self.frame.state._reveal_queue.append((label, card, player))
            print(f"[Reveal] 已加入队列，当前队列长度: {len(self.frame.state._reveal_queue)}")

        def on_card_played(event: Any) -> None:
            card = event.get("card")
            player = event.get("player")
            if card and player:
                # 策略/阴谋正常打出进入弃牌堆 → 黑色
                self.frame.state._last_discarded_info[player.name] = (
                    card.name, UI_THEME["text_primary"]
                )

        game.register_listener(EVENT_DISCARDED, on_reveal_event)
        game.register_listener(EVENT_MILLED, on_reveal_event)
        game.register_listener("card_removed_from_deck", on_reveal_event)
        game.register_listener(EVENT_CARD_PLAYED, on_card_played)

        self.frame.state._reveal_listeners_registered = True

    def reset(self) -> None:
        """新对局开始时重置监听器注册状态。"""
        self.frame.state._reveal_listeners_registered = False

    # ------------------------------------------------------------------
    # 队列展示
    # ------------------------------------------------------------------
    def try_show(self) -> None:
        """轮询入口：检查队列并展示下一张卡牌。"""
        if self.frame.state._is_revealing:
            return
        if not self.frame.state._reveal_queue:
            return
        print(
            f"[Reveal] _try_show_reveal: 队列长度={len(self.frame.state._reveal_queue)}, "
            f"_is_revealing={self.frame.state._is_revealing}"
        )
        self._show_next()

    def queue(self, items: List[Any]) -> None:
        """将卡牌加入展示队列。

        支持两种格式：
        - 字符串列表（卡牌名称，向后兼容）
        - (label, card, player) 元组列表（事件驱动）
        """
        for item in items:
            self.frame.state._reveal_queue.append(item)
        # 不立即触发展示，由 try_show 轮询处理（线程安全）

    def _show_next(self) -> None:
        """展示队列中的下一张卡牌。"""
        try:
            print("[Reveal] === _show_next_reveal START ===")
            print(
                f"[Reveal]   queue_len={len(self.frame.state._reveal_queue)}, "
                f"_is_revealing={self.frame.state._is_revealing}"
            )
            print(f"[Reveal]   reveal_frame.winfo_exists={self.reveal_frame.winfo_exists()}")
            if not self.frame.state._reveal_queue:
                print("[Reveal]   队列空，直接返回")
                self.frame.state._is_revealing = False
                self.reveal_frame.pack_forget()
                return

            self.frame.state._is_revealing = True
            item = self.frame.state._reveal_queue.pop(0)
            print(f"[Reveal]   popped item={item}")

            # 兼容旧格式（仅字符串名称）
            if isinstance(item, str):
                name = item
                label = "展示"
                player_name = ""
                card = None
                card_def = DEFAULT_REGISTRY.get(name)
                if card_def:
                    from tards.cards import Card
                    card = Card.from_definition(card_def)
            else:
                label, card, player = item
                player_name = getattr(player, "name", "未知")
                name = getattr(card, "name", "未知")
            print(f"[Reveal]   label={label}, name={name}, player_name={player_name}, card={card}")

            if card:
                print("[Reveal]   开始渲染卡牌...")
                self._render_card(self.reveal_canvas, card)
                print("[Reveal]   卡牌渲染完成")
            else:
                print("[Reveal]   card为None，清空canvas")
                self.reveal_canvas.delete("all")

            print("[Reveal]   设置label文本...")
            if player_name:
                self.reveal_label.config(text=f"{player_name} {label}: {name}")
            else:
                self.reveal_label.config(text=f"{label}: {name}")
            print("[Reveal]   label文本已设置")

            print("[Reveal]   调用 reveal_frame.pack()...")
            self.reveal_frame.pack(fill=tk.X, pady=(0, 5))
            print("[Reveal]   reveal_frame.pack() 完成")
            self.frame.update_idletasks()
            print(
                f"[Reveal]   update_idletasks 后 reveal_frame.winfo_viewable="
                f"{self.reveal_frame.winfo_viewable()}"
            )
            print(
                f"[Reveal]   update_idletasks 后 reveal_frame.winfo_width="
                f"{self.reveal_frame.winfo_width()}"
            )
            print(
                f"[Reveal]   update_idletasks 后 reveal_frame.winfo_height="
                f"{self.reveal_frame.winfo_height()}"
            )
            print("[Reveal]   设置 after(1500, _finish_reveal)...")
            self.frame.after(1500, self._finish)
            print("[Reveal] === _show_next_reveal END ===")
        except Exception as e:
            print(f"[Reveal] _show_next_reveal 异常: {e}")
            import traceback
            traceback.print_exc()
            self.frame.state._is_revealing = False

    def _finish(self) -> None:
        """当前卡牌展示结束，标记为可继续。"""
        print("[Reveal] === _finish_reveal START ===")
        self.frame.state._is_revealing = False
        print(f"[Reveal]   queue_len={len(self.frame.state._reveal_queue)}")
        if not self.frame.state._reveal_queue:
            print("[Reveal]   队列空，隐藏 reveal_frame")
            self.reveal_frame.pack_forget()
            self.reveal_canvas.delete("all")
            self.reveal_label.config(text="")
        print("[Reveal] === _finish_reveal END ===")

    # ------------------------------------------------------------------
    # 卡牌渲染
    # ------------------------------------------------------------------
    def _render_card(self, canvas: "Canvas", card: Any, cw: int = 90, ch: int = 144) -> None:
        """在指定 Canvas 上渲染一张静态展示卡牌。"""
        from gui.theme import UI_THEME

        print(f"[Reveal] _render_reveal_card 开始: card={getattr(card, 'name', 'unknown')}")
        canvas.delete("all")
        try:
            cost_str = str(card.cost)
            print(f"[Reveal]   cost_str={cost_str}")
            TAB_W = calc_tab_width(cost_str)
            TAB_H = 16
            TAB_SLANT = max(5, TAB_W // 6)
            border_color = UI_THEME["card_border_default"]
            border_width = 1
            print(f"[Reveal]   TAB_W={TAB_W}, TAB_SLANT={TAB_SLANT}")

            # 稀有度渐变背景
            rarity_colors = self.frame._get_card_rarity_gradient_colors(card)
            bg_colors = rarity_colors if rarity_colors else UI_THEME["rarity_none"]
            print(f"[Reveal]   bg_colors={bg_colors}")

            # _PIL_AVAILABLE 是 BattleFrame 模块级变量
            if getattr(self.frame, "_PIL_AVAILABLE", False):
                photo = self.frame._create_tab_gradient_photo(
                    cw, ch, bg_colors[0], bg_colors[1],
                    tab_w=TAB_W, tab_h=TAB_H, slant=TAB_SLANT, radius=2
                )
                print(f"[Reveal]   photo={photo is not None}")
                if photo:
                    canvas.create_image(cw // 2, ch // 2, image=photo, tags="rarity_bg")
                    canvas.rarity_bg_image = photo

            # 费用标签
            label_points = [0, 0, TAB_W, 0, TAB_W + TAB_SLANT, TAB_H, 0, TAB_H]
            canvas.create_polygon(
                label_points, fill=UI_THEME["card_tab_default"], outline="", tags="cost_tab"
            )
            print("[Reveal]   费用标签绘制完成")

            # 边框
            r = 2
            shape_points = [
                0, 0, TAB_W, 0, TAB_W + TAB_SLANT, TAB_H,
                cw - r, TAB_H, cw, TAB_H + r, cw, ch - r,
                cw - r, ch, r, ch, 0, ch - r, 0, TAB_H,
            ]
            canvas.create_polygon(
                shape_points, fill="", outline=border_color, width=border_width,
                joinstyle=tk.MITER, tags="card_border"
            )
            print("[Reveal]   边框绘制完成")

            # 肖像
            from tards.assets import get_asset_manager
            am = get_asset_manager()
            img = None
            if getattr(card, "asset_id", None):
                img = am.get_card_face(card.asset_id, cw - 4, ch - 4)
            print(f"[Reveal]   asset_id={getattr(card, 'asset_id', None)}, img={img is not None}")
            if img:
                canvas.create_image(cw // 2, ch // 2, image=img, tags="card_img")
                canvas.image = img

            # 费用文字
            cost_cx = (TAB_W + TAB_SLANT) // 2
            cost_cy = TAB_H // 2
            canvas.create_text(
                cost_cx, cost_cy, text=cost_str, fill="white",
                font=("Microsoft YaHei", 8, "bold"), tags="card_text"
            )
            print("[Reveal]   费用文字绘制完成")

            # 名称
            name = card.name
            canvas.create_text(
                cw // 2, 20 + TAB_H, text=name, fill=UI_THEME["card_text_name"],
                font=("Microsoft YaHei", 9, "bold"), tags="card_text"
            )
            print(f"[Reveal]   名称绘制完成: {name}")

            # 类型由卡牌外形区分；异象卡用左/下角彩色徽章显示攻击/生命
            from tards.cards import MinionCard
            if isinstance(card, MinionCard):
                draw_minion_stat_badges(
                    canvas, card.attack, card.health, cw, ch, offset_y=0
                )
            print("[Reveal]   底部攻防徽章绘制完成")
            print("[Reveal] _render_reveal_card 完成")
        except Exception as e:
            print(f"[Reveal] [_render_reveal_card] 渲染异常 [{getattr(card, 'name', 'unknown')}]: {e}")
            import traceback
            traceback.print_exc()
