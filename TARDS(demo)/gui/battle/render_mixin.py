"""BattleFrame 共用的渲染与 UI 辅助方法 Mixin。

原位于 Gamestart.py::BattleFrame，提取到此 mixin 以减少 BattleFrame 体积，
并为后续 InputController 复用做准备。
"""

from typing import Any, Callable, Dict, List, Optional

import tkinter as tk
from tkinter import ttk

try:
    from PIL import Image, ImageDraw, ImageTk
    _PIL_AVAILABLE = True
except Exception:  # pragma: no cover
    Image = ImageDraw = ImageTk = None  # type: ignore
    _PIL_AVAILABLE = False

from tards.cards import MineralCard
from tards.card_db import DEFAULT_REGISTRY
from gui.theme import UI_THEME
from gui.utils import _insert_rich_detail
from gui.battle.render_utils import rounded_rect, calc_tab_width


class RenderMixin:
    """提供 BattleFrame 共用的渲染/绘制/日志辅助方法。"""

    def _build_player_info_panel(self, parent, player, is_local):
        """构建单个玩家信息面板（紧凑卡片式），返回包含所有 widget 的字典。"""
        frame = tk.Frame(parent, height=155, bg=UI_THEME["bg_panel"],
                         highlightthickness=1, highlightbackground=UI_THEME["border"])
        frame.pack_propagate(False)
        frame.pack(fill=tk.X, pady=2)

        # 行0：名字（左） + 右侧信息区（手牌/牌库/弃牌堆，垂直排列）
        panel_bg = UI_THEME["bg_panel"]
        row0 = tk.Frame(frame, bg=panel_bg)
        row0.pack(fill=tk.X, padx=10, pady=(6, 2))

        dot_color = UI_THEME["success"] if is_local else UI_THEME["enemy"]
        dot = tk.Label(row0, text="●", font=("Microsoft YaHei", 8),
                       bg=panel_bg, fg=dot_color)
        dot.pack(side=tk.LEFT)

        name_label = tk.Label(row0, text=player.name, font=("Microsoft YaHei", 13, "bold"),
                              bg=panel_bg, fg=UI_THEME["text_primary"], anchor="w")
        name_label.pack(side=tk.LEFT, padx=(2, 0))

        # 右侧信息容器（水平：牌库 / 弃牌堆 / 手牌 + 上一张）
        right_info = tk.Frame(row0, bg=panel_bg)
        right_info.pack(side=tk.RIGHT)

        deck_badge = tk.Label(right_info, text="牌库 0", font=("Microsoft YaHei", 11, "bold"),
                              bg=UI_THEME["bg_main"], fg=UI_THEME["text_secondary"], padx=8, pady=2)
        deck_badge.pack(side=tk.LEFT, padx=(0, 6))

        discard_badge = tk.Label(right_info, text="弃牌堆 0", font=("Microsoft YaHei", 11, "bold"),
                                 bg=UI_THEME["bg_main"], fg=UI_THEME["text_secondary"], padx=8, pady=2)
        discard_badge.pack(side=tk.LEFT, padx=(0, 6))
        discard_badge.bind("<Button-1>", lambda e, p=player: self._show_discard_pile(p))

        hand_label = tk.Label(right_info, text="手牌 0", font=("Microsoft YaHei", 11, "bold"),
                              bg="#dbeafe", fg=UI_THEME["accent_dark"], padx=8, pady=2)
        hand_label.pack(side=tk.LEFT)

        last_dis_label = tk.Label(right_info, text="", font=("Microsoft YaHei", 9),
                                  bg=panel_bg, fg=UI_THEME["text_primary"], anchor="w")
        last_dis_label.pack(side=tk.LEFT, padx=(8, 0), fill=tk.X, expand=True)

        # 行1：HP 条
        row1 = tk.Frame(frame, bg=panel_bg)
        row1.pack(fill=tk.X, padx=10, pady=(2, 2))

        hp_frame = tk.Frame(row1, bg=panel_bg)
        hp_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)

        hp_bar = ttk.Progressbar(hp_frame, length=140, mode="determinate", maximum=30)
        hp_bar.pack(side=tk.LEFT)

        hp_label = tk.Label(hp_frame, text="30/30", font=("Microsoft YaHei", 11, "bold"),
                            bg=panel_bg, fg=UI_THEME["danger"])
        hp_label.pack(side=tk.LEFT, padx=(6, 0))

        # 行2：资源圆角彩色方块（带 T/C/B/S 标注）
        row2 = tk.Frame(frame, bg=panel_bg)
        row2.pack(fill=tk.X, padx=10, pady=(4, 2))

        def _res_badge(parent, color, width=56):
            """返回一个 Canvas，内含圆角矩形背景 + 文字占位。"""
            h = 26
            cvs = tk.Canvas(parent, width=width, height=h, bg=panel_bg, highlightthickness=0, bd=0)
            rounded_rect(cvs, 1, 1, width - 1, h - 1, radius=5,
                                       fill=color, outline="", tags="bg")
            text_id = cvs.create_text(width // 2, h // 2, text="-", fill="white",
                                       font=("Microsoft YaHei", 9, "bold"), tags="text")
            return cvs, text_id

        t_cvs, t_text = _res_badge(row2, UI_THEME["res_t"], width=58)
        t_cvs.pack(side=tk.LEFT, padx=(0, 5))
        c_cvs, c_text = _res_badge(row2, UI_THEME["res_c"], width=58)
        c_cvs.pack(side=tk.LEFT, padx=(0, 5))
        b_cvs, b_text = _res_badge(row2, UI_THEME["res_b"], width=46)
        b_cvs.pack(side=tk.LEFT, padx=(0, 5))
        s_cvs, s_text = _res_badge(row2, UI_THEME["res_s"], width=46)
        s_cvs.pack(side=tk.LEFT, padx=(0, 10))

        # 弃牌、阴谋小字放在资源右侧
        dis_label = tk.Label(row2, text="弃牌 0", font=("Microsoft YaHei", 9),
                             bg=panel_bg, fg=UI_THEME["text_secondary"])
        dis_label.pack(side=tk.LEFT, padx=(0, 8))

        con_label = tk.Label(row2, text="阴谋 0", font=("Microsoft YaHei", 9),
                             bg=panel_bg, fg=UI_THEME["text_secondary"])
        con_label.pack(side=tk.LEFT, padx=(0, 8))

        # 行3：已展示给对手的牌
        row_shown = tk.Frame(frame, bg=panel_bg)
        row_shown.pack(fill=tk.X, padx=10, pady=(2, 4))
        shown_label = tk.Label(row_shown, text="", font=("Microsoft YaHei", 8),
                               bg=panel_bg, fg=UI_THEME["warning_dark"], anchor="w")
        shown_label.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # 点击绑定
        clickable = [frame, row0, row1, row2, row_shown, dot, name_label, hand_label, deck_badge,
                     hp_frame, hp_bar, hp_label,
                     dis_label, con_label, shown_label, last_dis_label]
        for w in clickable:
            w.bind("<Button-1>", lambda e, p=player: self._on_player_label_click(p))
        # 按钮本身不绑定点击背景色（已绑定 command）

        return {
            "frame": frame, "row0": row0, "row1": row1, "row2": row2, "row_shown": row_shown,
            "right_info": right_info,
            "name_label": name_label, "hand_label": hand_label, "deck_badge": deck_badge,
            "hp_frame": hp_frame, "hp_bar": hp_bar, "hp_label": hp_label,
            "t_cvs": t_cvs, "t_text": t_text,
            "c_cvs": c_cvs, "c_text": c_text,
            "b_cvs": b_cvs, "b_text": b_text,
            "s_cvs": s_cvs, "s_text": s_text,
            "dis_label": dis_label,
            "conspiracy_label": con_label, "shown_label": shown_label,
            "discard_badge": discard_badge, "last_dis_label": last_dis_label,
        }

    def _calc_deploy_range(self, card, active, sacrifices):
        """计算考虑祭品移除后的部署合法范围。返回合法位置列表。"""
        if not self.duel.game:
            return []
        valid = []
        for t in active.get_valid_targets(card):
            if isinstance(t, tuple) and self.duel.game.board.is_valid_deploy(t, active, card, ignored_minions=sacrifices):
                existing = self.duel.game.board.get_minion_at(t)
                if existing is None or (
                    ("漂浮物" in existing.keywords and existing.owner == active) or
                    ("藤蔓" in card.keywords and existing.owner == active)
                ):
                    valid.append(t)
        # 祭品自身所在格不能作为部署目标
        for m in sacrifices:
            if m.position and m.position in valid:
                valid.remove(m.position)
        return valid

    def _card_display_text(self, card) -> str:
        name = card.name
        cost = str(card.cost)
        if isinstance(card, MinionCard):
            return f"{name}\n{cost}费 {card.attack}/{card.health}"
        return f"{name}\n{cost}费"

    def _clear_detail_text(self):
        if not hasattr(self, "detail_text"):
            return
        self.detail_text.config(state=tk.NORMAL)
        _insert_rich_detail(self.detail_text, "悬停卡牌查看详情")
        self.detail_text.config(state=tk.DISABLED)

    def _clear_preview(self):
        """清除部署位置预览。"""
        self.canvas.delete("preview_hint")

    def _flash_label_fg(self, widget, flash_color, times=2, interval=150):
        """让 Label 的前景(文字)色闪烁指定次数后恢复原始颜色。"""
        if not widget.winfo_exists():
            return
        original_fg = widget.cget("fg")

        def step(count=0):
            if not widget.winfo_exists():
                return
            if count >= times * 2:
                widget.config(fg=original_fg)
                return
            widget.config(fg=flash_color if count % 2 == 0 else original_fg)
            widget.after(interval, lambda: step(count + 1))

        step()

    def _flash_res_label(self, widget, flash_color, times=2, interval=150):
        """同时闪烁 Label 的背景和前景色，效果更明显。"""
        if not widget.winfo_exists():
            return
        original_fg = widget.cget("fg")
        original_bg = widget.cget("bg")
        # 深色闪色配白字，浅色闪色配黑字
        flash_fg = UI_THEME["btn_primary_fg"] if flash_color == UI_THEME["danger"] else UI_THEME["text_primary"]

        def step(count=0):
            if not widget.winfo_exists():
                return
            if count >= times * 2:
                widget.config(fg=original_fg, bg=original_bg)
                return
            if count % 2 == 0:
                widget.config(fg=flash_fg, bg=flash_color)
            else:
                widget.config(fg=original_fg, bg=original_bg)
            widget.after(interval, lambda: step(count + 1))

        step()

    def _flash_widget_bg(self, widget, flash_color, times=2, interval=150):
        """让 widget 的背景色闪烁指定次数后恢复原始颜色。"""
        if not widget.winfo_exists():
            return
        original_bg = widget.cget("bg")

        def step(count=0):
            if not widget.winfo_exists():
                return
            if count >= times * 2:
                widget.config(bg=original_bg)
                return
            widget.config(bg=flash_color if count % 2 == 0 else original_bg)
            widget.after(interval, lambda: step(count + 1))

        step()

    def _fmt_keywords(self, keywords: dict, minion_name: str = "") -> str:
        parts = []
        for k, v in keywords.items():
            if v is True:
                parts.append(k)
            elif callable(v):
                # callable 值（如亡语函数）：只显示关键词名
                parts.append(k)
            elif isinstance(v, (int, float, str)):
                parts.append(f"{k}{v}")
            else:
                # 跳过其他非基本类型（如对象引用）
                continue
        return " ".join(parts)

    def _get_available_blood(self, player):
        """计算场上友方异象可提供的献祭B点总和。"""
        if not self.duel.game:
            return 0
        minions = self.duel.game.board.get_minions_of_player(player)
        return sum(m.keywords.get("丰饶", 1) for m in minions if m.is_alive())

    def _get_card_rarity_gradient_colors(self, card):
        """返回卡牌稀有度渐变颜色 (c1, c2)，无稀有度返回 None。"""
        # 矿物卡无稀有度
        if isinstance(card, MineralCard):
            return None

        rarity = getattr(card, "rarity", None)
        is_token = getattr(card, "is_token", None)

        # 回查注册表
        if (rarity is None or is_token is None) and card.name and DEFAULT_REGISTRY:
            defn = DEFAULT_REGISTRY.get(card.name)
            if defn:
                if rarity is None:
                    rarity = defn.rarity
                if is_token is None:
                    is_token = defn.is_token

        if is_token:
            return None
        if rarity is None:
            return None
        return self._RARITY_GRADIENTS.get(rarity)

    def _get_minion_pending_stars(self, minion):
        """计算异象在行动阶段还需要选择多少次攻击目标。返回 0 表示不需要星号。"""
        game = self.duel.game
        if not game or game.current_phase != "action":
            return 0
        if minion.owner != game.current_player:
            return 0
        if not minion.can_attack_this_turn(game.current_turn):
            return 0

        # 计算需要预设的攻击次数
        needed = 0
        multi_attack = minion.keywords.get("高频", 0)
        if isinstance(multi_attack, int) and multi_attack > 0:
            needed = multi_attack
        elif minion.keywords.get("视野", 0) > 0:
            needed = 1

        if needed <= 0:
            return 0

        pending = getattr(minion, "_pending_attack_targets", None)
        if pending and isinstance(pending, list):
            needed = max(0, needed - len(pending))
        return needed

    def _log(self, msg: str):
        self.log_text.config(state=tk.NORMAL)
        tag = None
        if "死亡" in msg or "消灭" in msg or "阵亡" in msg:
            tag = "death"
        elif "胜利" in msg or "平局" in msg or "获得胜利" in msg:
            tag = "victory"
        elif "伤害" in msg or "受到" in msg and "点" in msg:
            tag = "damage"
        start_idx = self.log_text.index(tk.END)
        self.log_text.insert(tk.END, msg + "\n")
        if tag:
            end_idx = self.log_text.index(tk.END)
            self.log_text.tag_add(tag, start_idx, end_idx)
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)

    def _make_sacrifice_chooser(self):
        import threading
        def chooser(required_blood: int):
            if not self.duel.game:
                return []
            active = self.duel.game.current_player
            if not active:
                return []
            minions = list(self.duel.game.board.get_minions_of_player(active))
            if not minions:
                return []
            event = threading.Event()
            result: List[Minion] = []
            def on_confirm(selected: List[Minion]):
                nonlocal result
                result = selected
                event.set()
            self.after(0, lambda: SacrificeDialog(self, minions, required_blood, on_confirm))
            event.wait()
            return result
        return chooser

    def _show_card_tooltip(self, event, card):
        # 浮窗已禁用，详情信息改由右侧固定面板显示
        pass

    def _show_choice(self, options: List[str], title: str):
        def on_choose(o: str):
            self.duel.submit_local_choice(o)
        ChoiceDialog(self, title, options, on_choose)

    def _show_discover(self, names: List[str]):
        def on_choose(n: str):
            self.duel.submit_local_discover(n)
        DiscoverDialog(self, names, on_choose)

    def _show_minion_tooltip(self, event, minion):
        # 浮窗已禁用，详情信息改由右侧固定面板显示
        pass

