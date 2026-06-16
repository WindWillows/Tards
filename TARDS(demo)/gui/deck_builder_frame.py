"""卡组构筑界面。

原位于 Gamestart.py，现独立为单独的 Frame 模块。
"""

from __future__ import annotations

import os
import tkinter as tk
from tkinter import messagebox, ttk
from typing import TYPE_CHECKING, Optional

from tards import Minion, MinionCard
from tards.assets import get_asset_manager
from tards.card_db import DEFAULT_REGISTRY, Pack, CardType
from tards.cards import Conspiracy, MineralCard, Strategy
from tards.deck import Deck
from tards.deck_io import load_deck, save_deck

from gui.theme import UI_THEME
from gui.utils import _insert_rich_detail

if TYPE_CHECKING:
    from Gamestart import TardsApp


class DeckBuilderFrame(tk.Frame):
    def __init__(self, parent, app: "TardsApp", deck_name: Optional[str] = None):
        super().__init__(parent)
        self.app = app
        self._original_deck_name = deck_name or ""
        if deck_name:
            loaded = load_deck(deck_name, DEFAULT_REGISTRY)
            self.deck = loaded if loaded else Deck(name="新卡组", registry=DEFAULT_REGISTRY)
        else:
            self.deck = Deck(name="新卡组", registry=DEFAULT_REGISTRY)
        self._build()
        if deck_name:
            self._load_deck_data()
        else:
            self._refresh_available()
            self._refresh_deck_list()

    def _build(self):
        self.config(bg=UI_THEME["bg_main"])

        # ===== 顶部工具栏 =====
        top = tk.Frame(self, bg=UI_THEME["bg_main"])
        top.pack(fill=tk.X, padx=10, pady=5)
        tk.Button(top, text="← 返回主菜单", bg=UI_THEME["btn_secondary_bg"], fg=UI_THEME["btn_secondary_fg"],
                  activebackground=UI_THEME["btn_secondary_active"], relief=tk.RAISED, bd=1,
                  command=self.app.show_menu).pack(side=tk.LEFT)
        tk.Label(top, text="卡组名:", bg=UI_THEME["bg_main"], fg=UI_THEME["text_primary"]).pack(side=tk.LEFT, padx=5)
        self.name_entry = tk.Entry(top, width=20, bg=UI_THEME["bg_panel"], fg=UI_THEME["text_primary"],
                                   insertbackground=UI_THEME["text_primary"])
        self.name_entry.insert(0, self.deck.name)
        self.name_entry.pack(side=tk.LEFT, padx=5)
        tk.Button(top, text="保存卡组", bg=UI_THEME["btn_primary_bg"], fg=UI_THEME["btn_primary_fg"],
                  activebackground=UI_THEME["btn_primary_active"], relief=tk.RAISED, bd=1,
                  command=self._save_deck).pack(side=tk.LEFT, padx=10)
        tk.Button(top, text="删除卡组", bg=UI_THEME["btn_danger_bg"], fg=UI_THEME["btn_danger_fg"],
                  activebackground=UI_THEME["btn_danger_active"], relief=tk.RAISED, bd=1,
                  command=self._delete_deck).pack(side=tk.RIGHT, padx=10)
        self.is_test_var = tk.BooleanVar(value=self.deck.is_test_deck)
        self.test_check = tk.Checkbutton(top, text="测试卡组", variable=self.is_test_var,
                                         bg=UI_THEME["bg_main"], fg=UI_THEME["warning_dark"],
                                         selectcolor=UI_THEME["bg_panel"],
                                         font=("Microsoft YaHei", 10, "bold"), command=self._on_test_mode_change)
        self.test_check.pack(side=tk.LEFT, padx=10)

        self.validation_label = tk.Label(self, text="", fg=UI_THEME["danger"], bg=UI_THEME["bg_main"])
        self.validation_label.pack(fill=tk.X, padx=10)

        # ===== 主三栏布局 =====
        main_frame = tk.Frame(self, bg=UI_THEME["bg_main"])
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        main_frame.columnconfigure(0, weight=3, uniform="main")
        main_frame.columnconfigure(1, weight=3, uniform="main")
        main_frame.columnconfigure(2, weight=4, uniform="main")
        main_frame.rowconfigure(0, weight=1)

        # ===== 左列：当前卡组（可滚动按钮列表）=====
        deck_frame = tk.LabelFrame(main_frame, text="当前卡组",
                                   bg=UI_THEME["bg_panel"], fg=UI_THEME["text_secondary"])
        deck_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
        deck_frame.rowconfigure(0, weight=1)
        deck_frame.columnconfigure(0, weight=1)

        self.deck_list_canvas = tk.Canvas(deck_frame, bg=UI_THEME["bg_panel"], highlightthickness=0, bd=0)
        self.deck_list_canvas.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        deck_scroll = tk.Scrollbar(deck_frame, orient=tk.VERTICAL, command=self.deck_list_canvas.yview)
        deck_scroll.grid(row=0, column=1, sticky="ns", pady=5)
        self.deck_list_canvas.config(yscrollcommand=deck_scroll.set)

        self.deck_list_inner = tk.Frame(self.deck_list_canvas, bg=UI_THEME["bg_panel"])
        inner_id = self.deck_list_canvas.create_window((0, 0), window=self.deck_list_inner, anchor="nw")
        self.deck_list_inner.bind(
            "<Configure>",
            lambda e: self.deck_list_canvas.configure(scrollregion=self.deck_list_canvas.bbox("all"))
        )
        self.deck_list_canvas.bind(
            "<Configure>",
            lambda e, iid=inner_id: self.deck_list_canvas.itemconfig(iid, width=e.width)
        )
        self.deck_list_canvas.bind(
            "<MouseWheel>",
            lambda e: self.deck_list_canvas.yview_scroll(int(-e.delta / 120), "units")
        )

        self.deck_count_label = tk.Label(deck_frame, text="0 张", font=("Microsoft YaHei", 10, "bold"),
                                         bg=UI_THEME["bg_panel"], fg=UI_THEME["text_primary"])
        self.deck_count_label.grid(row=1, column=0, columnspan=2, sticky="ew", padx=5, pady=(0, 5))

        self._selected_deck_row = None
        self._selected_deck_row_bg = None
        self._selected_deck_card = None

        # ===== 中列：卡组属性 + 卡牌详情 =====
        center_frame = tk.Frame(main_frame, bg=UI_THEME["bg_main"])
        center_frame.grid(row=0, column=1, sticky="nsew", padx=5)
        center_frame.rowconfigure(0, weight=0)
        center_frame.rowconfigure(1, weight=1)
        center_frame.columnconfigure(0, weight=1)

        # 1. 卡组属性栏（沉浸度 + 统计 + 操作）
        attr_frame = tk.LabelFrame(center_frame, text="卡组属性",
                                   bg=UI_THEME["bg_panel"], fg=UI_THEME["text_secondary"])
        attr_frame.grid(row=0, column=0, sticky="new", pady=(0, 5))

        # 沉浸度调节（2 行 3 列）
        immersion_inner = tk.Frame(attr_frame, bg=UI_THEME["bg_panel"])
        immersion_inner.pack(fill=tk.X, padx=5, pady=2)
        self.imm_sliders = {}
        for i, pack in enumerate(Pack):
            f = tk.Frame(immersion_inner, bg=UI_THEME["bg_panel"])
            f.grid(row=i // 3, column=i % 3, padx=8, pady=2, sticky="n")
            tk.Label(f, text=pack.value, bg=UI_THEME["bg_panel"], fg=UI_THEME["text_primary"]).pack()
            var = tk.IntVar(value=0)
            sc = tk.Scale(f, from_=0, to=3, orient=tk.HORIZONTAL, variable=var,
                          bg=UI_THEME["bg_panel"], fg=UI_THEME["text_primary"],
                          highlightthickness=0, command=lambda _, p=pack: self._on_imm_change(p))
            sc.pack()
            self.imm_sliders[pack] = var

        # 分隔线
        tk.Frame(attr_frame, height=1, bg=UI_THEME["border"]).pack(fill=tk.X, padx=10, pady=2)

        # 统计信息与操作
        stats_inner = tk.Frame(attr_frame, bg=UI_THEME["bg_panel"])
        stats_inner.pack(fill=tk.X, padx=5, pady=2)
        bold = ("Microsoft YaHei", 10, "bold")
        self.deck_stats_type = tk.Label(stats_inner, text="类型: -", font=bold, anchor="w",
                                        bg=UI_THEME["bg_panel"], fg=UI_THEME["text_primary"])
        self.deck_stats_type.pack(fill=tk.X, pady=1)
        self.deck_stats_pack = tk.Label(stats_inner, text="卡包: -", font=bold, anchor="w",
                                        bg=UI_THEME["bg_panel"], fg=UI_THEME["text_primary"])
        self.deck_stats_pack.pack(fill=tk.X, pady=1)
        self.deck_stats_cost = tk.Label(stats_inner, text="平均费用: -", font=bold, anchor="w",
                                        bg=UI_THEME["bg_panel"], fg=UI_THEME["text_primary"])
        self.deck_stats_cost.pack(fill=tk.X, pady=1)
        btn_frame = tk.Frame(stats_inner, bg=UI_THEME["bg_panel"])
        btn_frame.pack(fill=tk.X, pady=(6, 2))
        tk.Button(btn_frame, text="移除所选", bg=UI_THEME["btn_secondary_bg"], fg=UI_THEME["btn_secondary_fg"],
                  activebackground=UI_THEME["btn_secondary_active"], relief=tk.RAISED, bd=1,
                  command=self._remove_selected).pack(side=tk.LEFT, padx=2)
        tk.Button(btn_frame, text="清空卡组", bg=UI_THEME["btn_danger_bg"], fg=UI_THEME["btn_danger_fg"],
                  activebackground=UI_THEME["btn_danger_active"], relief=tk.RAISED, bd=1,
                  command=self._clear_deck).pack(side=tk.LEFT, padx=2)

        # 2. 卡牌详情
        detail_frame = tk.LabelFrame(center_frame, text="卡牌详情",
                                     bg=UI_THEME["bg_panel"], fg=UI_THEME["text_secondary"])
        detail_frame.grid(row=1, column=0, sticky="nsew", pady=5)
        detail_frame.rowconfigure(1, weight=1)
        detail_frame.columnconfigure(0, weight=1)

        # 卡面立绘（正方形）
        self.detail_canvas = tk.Canvas(detail_frame, width=200, height=200,
                                       highlightthickness=1,
                                       highlightbackground=UI_THEME["border"],
                                       bg=UI_THEME["bg_main"])
        self.detail_canvas.grid(row=0, column=0, pady=(5, 0))

        self.detail_text = tk.Text(detail_frame, height=8, wrap=tk.WORD,
                                   font=("Microsoft YaHei", 10), state=tk.DISABLED,
                                   bg=UI_THEME["bg_main"], fg=UI_THEME["text_primary"], relief=tk.FLAT, bd=0)
        self.detail_text.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        self.detail_text.config(state=tk.NORMAL)
        _insert_rich_detail(self.detail_text, "单击左侧或右侧卡牌查看详情\n双击右侧卡牌加入卡组")
        self.detail_text.config(state=tk.DISABLED)

        self.related_btn = tk.Button(detail_frame, text="📎 相关卡牌索引", state=tk.DISABLED,
                                      bg=UI_THEME["btn_secondary_bg"], fg=UI_THEME["btn_secondary_fg"],
                                      activebackground=UI_THEME["btn_secondary_active"], relief=tk.RAISED, bd=1,
                                      command=self._show_related_cards_in_tab)
        self.related_btn.grid(row=2, column=0, sticky="se", padx=5, pady=(0, 5))
        self._current_detail_card = None
        self._draw_card_portrait(None)

        # ===== 右列：卡池与检索 =====
        pool_frame = tk.LabelFrame(main_frame, text="可用卡牌 (单击查看详情，双击加入卡组)",
                                   bg=UI_THEME["bg_panel"], fg=UI_THEME["text_secondary"])
        pool_frame.grid(row=0, column=2, sticky="nsew", padx=(5, 0))
        pool_frame.rowconfigure(2, weight=1)
        pool_frame.columnconfigure(0, weight=1)

        # 筛选
        filter_frame = tk.Frame(pool_frame, bg=UI_THEME["bg_panel"])
        filter_frame.pack(fill=tk.X, padx=5, pady=(5, 2))
        tk.Label(filter_frame, text="筛选:", bg=UI_THEME["bg_panel"], fg=UI_THEME["text_primary"]).pack(side=tk.LEFT)
        self.show_minion = tk.BooleanVar(value=True)
        self.show_strategy = tk.BooleanVar(value=True)
        self.show_conspiracy = tk.BooleanVar(value=True)
        self.hide_unimplemented = tk.BooleanVar(value=False)
        tk.Checkbutton(filter_frame, text="异象", variable=self.show_minion, command=self._refresh_available,
                       bg=UI_THEME["bg_panel"], fg=UI_THEME["text_primary"], selectcolor=UI_THEME["bg_panel"]).pack(side=tk.LEFT, padx=2)
        tk.Checkbutton(filter_frame, text="策略", variable=self.show_strategy, command=self._refresh_available,
                       bg=UI_THEME["bg_panel"], fg=UI_THEME["text_primary"], selectcolor=UI_THEME["bg_panel"]).pack(side=tk.LEFT, padx=2)
        tk.Checkbutton(filter_frame, text="阴谋", variable=self.show_conspiracy, command=self._refresh_available,
                       bg=UI_THEME["bg_panel"], fg=UI_THEME["text_primary"], selectcolor=UI_THEME["bg_panel"]).pack(side=tk.LEFT, padx=2)
        tk.Checkbutton(filter_frame, text="隐藏未实现", variable=self.hide_unimplemented, command=self._refresh_available,
                       bg=UI_THEME["bg_panel"], fg=UI_THEME["text_primary"], selectcolor=UI_THEME["bg_panel"]).pack(side=tk.LEFT, padx=(10, 0))
        tk.Label(filter_frame, text="排序:", bg=UI_THEME["bg_panel"], fg=UI_THEME["text_primary"]).pack(side=tk.LEFT, padx=(10, 0))
        self.sort_by = tk.StringVar(value="immersion")
        tk.Radiobutton(filter_frame, text="沉浸度", variable=self.sort_by, value="immersion", command=self._refresh_available,
                       bg=UI_THEME["bg_panel"], fg=UI_THEME["text_primary"], selectcolor=UI_THEME["bg_panel"]).pack(side=tk.LEFT, padx=2)
        tk.Radiobutton(filter_frame, text="费用", variable=self.sort_by, value="cost", command=self._refresh_available,
                       bg=UI_THEME["bg_panel"], fg=UI_THEME["text_primary"], selectcolor=UI_THEME["bg_panel"]).pack(side=tk.LEFT, padx=2)

        # 搜索
        search_frame = tk.Frame(pool_frame, bg=UI_THEME["bg_panel"])
        search_frame.pack(fill=tk.X, padx=5, pady=2)
        tk.Label(search_frame, text="搜索:", bg=UI_THEME["bg_panel"], fg=UI_THEME["text_primary"]).pack(side=tk.LEFT)
        self.search_var = tk.StringVar()
        self.search_entry = tk.Entry(search_frame, textvariable=self.search_var, width=24,
                                     bg=UI_THEME["bg_panel"], fg=UI_THEME["text_primary"],
                                     insertbackground=UI_THEME["text_primary"])
        self.search_entry.pack(side=tk.LEFT, padx=5)
        self.search_entry.bind("<KeyRelease>", lambda e: self._refresh_available())
        tk.Label(search_frame, text="#词条 按关键词/标签搜索",
                 fg=UI_THEME["text_muted"], bg=UI_THEME["bg_panel"], font=("Microsoft YaHei", 9)).pack(side=tk.LEFT, padx=5)

        # 卡池 Notebook
        self.notebook = ttk.Notebook(pool_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.pack_tabs = {}
        self.pack_canvases = {}
        self._button_pools = {}
        self._empty_labels = {}
        for pack in Pack:
            tab = tk.Frame(self.notebook, bg=UI_THEME["bg_panel"])
            self.notebook.add(tab, text=pack.value)
            canvas = tk.Canvas(tab, bg=UI_THEME["bg_panel"], highlightthickness=0, bd=0)
            scrollbar = tk.Scrollbar(tab, orient=tk.VERTICAL, command=canvas.yview)
            inner = tk.Frame(canvas, bg=UI_THEME["bg_panel"])
            inner.bind("<Configure>", lambda e, c=canvas: c.configure(scrollregion=c.bbox("all")))
            # 两列布局：列权重 10，间距权重 7（间距 = 0.7 × 列宽）
            inner.columnconfigure(0, weight=10, uniform="col")
            inner.columnconfigure(1, weight=7)
            inner.columnconfigure(2, weight=10, uniform="col")
            canvas.create_window((0, 0), window=inner, anchor="nw")
            canvas.configure(yscrollcommand=scrollbar.set)
            canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            self.pack_tabs[pack] = inner
            self.pack_canvases[pack] = canvas
            # 绑定鼠标滚轮
            canvas.bind("<MouseWheel>", lambda e, c=canvas: c.yview_scroll(int(-e.delta / 120), "units"))
            # 预创建空提示标签（缓存）
            lbl = tk.Label(inner, text="无可用卡牌（请分配沉浸点）",
                           bg=UI_THEME["bg_panel"], fg=UI_THEME["text_muted"])
            lbl.grid_remove()
            self._empty_labels[pack] = lbl

        # ===== 衍生卡 Tab（只读展示）=====
        token_tab = tk.Frame(self.notebook, bg=UI_THEME["bg_panel"])
        self.notebook.add(token_tab, text="衍生卡")
        token_canvas = tk.Canvas(token_tab, bg=UI_THEME["bg_panel"], highlightthickness=0, bd=0)
        token_scroll = tk.Scrollbar(token_tab, orient=tk.VERTICAL, command=token_canvas.yview)
        token_inner = tk.Frame(token_canvas, bg=UI_THEME["bg_panel"])
        token_inner.bind("<Configure>", lambda e, c=token_canvas: c.configure(scrollregion=c.bbox("all")))
        token_inner.columnconfigure(0, weight=10, uniform="col")
        token_inner.columnconfigure(1, weight=7)
        token_inner.columnconfigure(2, weight=10, uniform="col")
        token_canvas.create_window((0, 0), window=token_inner, anchor="nw")
        token_canvas.configure(yscrollcommand=token_scroll.set)
        token_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        token_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.pack_tabs["__token__"] = token_inner
        self.pack_canvases["__token__"] = token_canvas
        token_canvas.bind("<MouseWheel>", lambda e, c=token_canvas: c.yview_scroll(int(-e.delta / 120), "units"))
        token_lbl = tk.Label(token_inner, text="无可用卡牌（请分配沉浸点）",
                             bg=UI_THEME["bg_panel"], fg=UI_THEME["text_muted"])
        token_lbl.grid_remove()
        self._empty_labels["__token__"] = token_lbl

        # ===== 关联 Tab（动态填充）=====
        assoc_tab = tk.Frame(self.notebook, bg=UI_THEME["bg_panel"])
        self.notebook.add(assoc_tab, text="关联")
        assoc_canvas = tk.Canvas(assoc_tab, bg=UI_THEME["bg_panel"], highlightthickness=0, bd=0)
        assoc_scroll = tk.Scrollbar(assoc_tab, orient=tk.VERTICAL, command=assoc_canvas.yview)
        assoc_inner = tk.Frame(assoc_canvas, bg=UI_THEME["bg_panel"])
        assoc_inner.bind("<Configure>", lambda e, c=assoc_canvas: c.configure(scrollregion=c.bbox("all")))
        assoc_inner.columnconfigure(0, weight=10, uniform="col")
        assoc_inner.columnconfigure(1, weight=7)
        assoc_inner.columnconfigure(2, weight=10, uniform="col")
        assoc_canvas.create_window((0, 0), window=assoc_inner, anchor="nw")
        assoc_canvas.configure(yscrollcommand=assoc_scroll.set)
        assoc_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        assoc_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.pack_tabs["__assoc__"] = assoc_inner
        self.pack_canvases["__assoc__"] = assoc_canvas
        assoc_canvas.bind("<MouseWheel>", lambda e, c=assoc_canvas: c.yview_scroll(int(-e.delta / 120), "units"))
        self._association_mode = False
        self._last_normal_tab = None

    def _on_test_mode_change(self):
        """切换测试卡组模式时更新 Deck 对象和界面。"""
        self.deck.is_test_deck = self.is_test_var.get()
        self._refresh_available()
        self._refresh_deck_list()

    def _load_deck_data(self):
        """加载已有卡组后，同步界面状态。"""
        self.name_entry.delete(0, tk.END)
        self.name_entry.insert(0, self.deck.name)
        self.is_test_var.set(self.deck.is_test_deck)
        for pack in Pack:
            pts = self.deck.immersion_points.get(pack, 0)
            self.imm_sliders[pack].set(pts)
        self._refresh_available()
        self._refresh_deck_list()

    def _fmt_keywords(self, keywords: dict, minion_name: str = "") -> str:
        """格式化关键词字典为人类可读字符串。"""
        parts = []
        for k, v in keywords.items():
            if v is True:
                parts.append(k)
            elif callable(v):
                parts.append(k)
            elif isinstance(v, (int, float, str)):
                parts.append(f"{k}{v}")
            else:
                continue
        return " ".join(parts)

    def _show_card_detail(self, card):
        """在右侧固定详情面板中显示卡牌信息（非浮窗）。"""
        try:
            self._current_detail_card = card
            rarity_str = card.rarity.name if card.rarity else "-"
            lines = [f"【{card.name}】  [{card.pack.value} {card.immersion_display} {rarity_str}]"]
            lines.append(f"费用: {card.cost}  类型: {card.card_type.value}")
            if card.attack is not None:
                lines.append(f"攻击/生命: {card.attack}/{card.health}")
            if card.keywords:
                kw = self._fmt_keywords(card.keywords, card.name)
                lines.append(f"关键词: {kw}")
            if card.evolve_to:
                lines.append(f"成长为: {card.evolve_to}")
            # 效果描述（从卡包源文件解析的原始文本）
            desc = getattr(card, "description", "")
            if desc:
                lines.append(f"\n【效果】\n{desc}")
            else:
                lines.append("\n【效果】\n（暂无描述）")
            text = "\n".join(lines)
            self.detail_text.config(state=tk.NORMAL)
            _insert_rich_detail(self.detail_text, text)
            self.detail_text.config(state=tk.DISABLED)
            # 根据是否有相关卡牌启用/禁用按钮
            related = self._get_related_cards(card)
            if related:
                self.related_btn.config(state=tk.NORMAL)
            else:
                self.related_btn.config(state=tk.DISABLED)
            # 绘制卡面立绘
            self._draw_card_portrait(card)
        except Exception as e:
            print(f"[警告] 显示卡牌详情时出错: {e}")

    def _clear_card_detail(self):
        self.detail_text.config(state=tk.NORMAL)
        _insert_rich_detail(self.detail_text, "单击左侧卡牌查看详情\n双击加入卡组")
        self.detail_text.config(state=tk.DISABLED)
        self._current_detail_card = None
        self.related_btn.config(state=tk.DISABLED)
        self._draw_card_portrait(None)

    def _draw_card_portrait(self, card):
        """在 detail_canvas 中绘制正方形卡牌肖像/占位。"""
        if not hasattr(self, "detail_canvas"):
            return
        canvas = self.detail_canvas
        canvas.delete("all")
        size = int(canvas["width"])

        card_type_colors = {
            MinionCard: "#3b82f6",
            Strategy: "#10b981",
            Conspiracy: "#8b5cf6",
            MineralCard: "#f59e0b",
        }
        card_type = type(card)
        if isinstance(card, Minion):
            source = getattr(card, "source_card", None)
            if source:
                card_type = type(source)
        border_color = card_type_colors.get(card_type, UI_THEME["border"])

        pad = 3
        canvas.create_rectangle(
            pad, pad, size - pad, size - pad,
            outline=border_color, fill=UI_THEME["bg_panel"], width=2,
        )

        if card is None:
            canvas.create_text(
                size // 2, size // 2, text="选择卡牌查看卡面",
                fill=UI_THEME["text_secondary"],
                font=("Microsoft YaHei", 11),
                width=size - 20, justify=tk.CENTER,
            )
            return

        name = getattr(card, "name", "")
        if name:
            canvas.create_text(
                size // 2, size // 2 - 8, text=name,
                fill=UI_THEME["text_primary"],
                font=("Microsoft YaHei", 12, "bold"),
                width=size - 20, justify=tk.CENTER,
            )
            canvas.create_text(
                size // 2, size // 2 + 16, text="[卡面占位]",
                fill=UI_THEME["text_secondary"],
                font=("Microsoft YaHei", 9),
            )

        asset_id = getattr(card, "asset_id", None)
        if not asset_id:
            return
        am = get_asset_manager()
        img = am.get_card_portrait(asset_id, size - 8)
        if img:
            canvas.create_image(size // 2, size // 2, image=img, anchor=tk.CENTER)
            canvas.image = img

    def _get_related_cards(self, card):
        """获取与指定卡牌关联的其他卡牌列表（正向+反向）。"""
        desc = getattr(card, "description", "") or ""
        all_cards = DEFAULT_REGISTRY.all_cards()
        related = []

        # 正向：描述中提到的其他卡
        for other in all_cards:
            if other.name == card.name:
                continue
            if other.name in desc:
                related.append(other)

        # 特殊概念映射：描述中提到"附魔书"的卡与"书"关联
        if "附魔书" in desc:
            book = DEFAULT_REGISTRY.get("书")
            if book and book.name != card.name and book not in related:
                related.append(book)

        # evolve_to
        if card.evolve_to and DEFAULT_REGISTRY.get(card.evolve_to):
            evo = DEFAULT_REGISTRY.get(card.evolve_to)
            if evo not in related:
                related.append(evo)

        # 反向：哪些卡提到了当前卡（仅 token 卡）
        if card.is_token:
            for other in all_cards:
                if other.name == card.name:
                    continue
                other_desc = getattr(other, "description", "") or ""
                if card.name not in other_desc:
                    continue
                # 若描述中存在更长的卡名包含当前卡名，则视为更精确匹配，跳过
                has_longer = False
                for longer in all_cards:
                    if longer.name in (card.name, other.name):
                        continue
                    if card.name in longer.name and longer.name in other_desc:
                        has_longer = True
                        break
                if has_longer:
                    continue
                if other not in related:
                    related.append(other)

        # 过滤子串误匹配（如"蜘蛛"被"蜘蛛眼"覆盖）
        def _filter_substring(matches):
            by_len = sorted(matches, key=lambda c: len(c.name), reverse=True)
            filtered = []
            for c in by_len:
                if any(c.name in kept.name for kept in filtered):
                    continue
                filtered.append(c)
            return filtered

        related = _filter_substring(related)
        # 去重并排序
        seen = set()
        unique = []
        for c in related:
            if c.name not in seen:
                seen.add(c.name)
                unique.append(c)
        unique.sort(key=lambda c: (c.pack.value, c.name))
        return unique

    def _show_related_cards_in_tab(self):
        """在左侧"关联"Tab 中展示当前卡牌的相关卡牌。"""
        card = getattr(self, "_current_detail_card", None)
        if not card:
            return
        related = self._get_related_cards(card)
        if not related:
            return

        # 记录当前正常 Tab，以便返回
        try:
            self._last_normal_tab = self.notebook.select()
        except Exception:
            self._last_normal_tab = None

        assoc_inner = self.pack_tabs.get("__assoc__")
        if not assoc_inner:
            return

        # 清空关联 Tab（destroy 旧按钮）
        for w in assoc_inner.winfo_children():
            w.destroy()

        # 顶部标题栏 + 返回按钮
        header = tk.Frame(assoc_inner)
        header.grid(row=0, column=0, columnspan=3, sticky="ew", padx=2, pady=(4, 8))
        tk.Label(header, text=f"【{card.name}】的关联卡牌（{len(related)} 张）",
                 font=("Microsoft YaHei", 11, "bold")).pack(side=tk.LEFT)
        tk.Button(header, text="🔙 返回", command=self._return_from_association).pack(side=tk.RIGHT)

        # 两列布局展示相关卡牌
        for idx, rc in enumerate(related):
            info = f"[{rc.pack.value} {rc.cost}] {rc.name}"
            if rc.attack is not None:
                info += f" {rc.attack}/{rc.health}"
            btn = tk.Button(assoc_inner, text=info, anchor="w")
            row = (idx // 2) + 1  # 从第 1 行开始（第 0 行是标题）
            col = (idx % 2) * 2
            btn.grid(row=row, column=col, sticky="ew", padx=2, pady=1)
            btn.bind("<Button-1>", lambda e, c=rc: self._show_card_detail(c))

        self._association_mode = True
        # 自动切换到关联 Tab
        try:
            for t in self.notebook.tabs():
                if self.notebook.tab(t, "text") == "关联":
                    self.notebook.select(t)
                    break
        except Exception:
            pass

    def _return_from_association(self):
        """从关联结果视图返回正常卡池视图。"""
        self._association_mode = False
        assoc_inner = self.pack_tabs.get("__assoc__")
        if assoc_inner:
            for w in assoc_inner.winfo_children():
                w.destroy()
            tk.Label(assoc_inner, text='点击右侧"相关卡牌索引"查看关联卡牌',
                     fg="gray").grid(sticky="ew", padx=5, pady=5)
        # 切回之前的 Tab
        if self._last_normal_tab:
            try:
                self.notebook.select(self._last_normal_tab)
            except Exception:
                pass
        else:
            # 默认选择第一个 pack tab
            try:
                self.notebook.select(self.notebook.tabs()[0])
            except Exception:
                pass

    # ===== BattleFrame 卡牌详情大图 =====
    def _update_detail_text(self, card):
        """在右侧文本栏中显示卡牌信息（悬停时触发）。支持手牌(Card)和场上异象(Minion)。"""
        if not hasattr(self, "detail_text"):
            return

        # 获取描述：优先从 card 本身，其次从 source_card（场上异象），最后从注册表
        desc = getattr(card, "description", "")
        if not desc and hasattr(card, "source_card") and card.source_card:
            desc = getattr(card.source_card, "description", "")
        if not desc and DEFAULT_REGISTRY:
            card_def = DEFAULT_REGISTRY.get(card.name)
            if card_def:
                desc = getattr(card_def, "description", "")

        # 获取费用：手牌直接用 card.cost，场上异象从 source_card 获取
        cost = getattr(card, "cost", None)
        if cost is None and hasattr(card, "source_card"):
            cost = card.source_card.cost
        if cost is None:
            cost = "?"

        lines = [f"【{card.name}】  费用: {cost}"]

        if isinstance(card, Minion):
            lines.append(f"攻击/生命: {card.attack}/{card.health}")
            kw_dict = card.display_keywords
        elif isinstance(card, MinionCard):
            lines.append(f"攻击/生命: {card.attack}/{card.health}")
            kw_dict = getattr(card, "keywords", None) or {}
        else:
            kw_dict = getattr(card, "keywords", None) or {}

        if kw_dict:
            kw = self._fmt_keywords(kw_dict, getattr(card, 'name', ''))
            lines.append(f"关键词: {kw}")
        if desc:
            lines.append(f"\n【效果】\n{desc}")
        else:
            lines.append("\n【效果】\n（暂无描述）")

        text = "\n".join(lines)
        self.detail_text.config(state=tk.NORMAL)
        _insert_rich_detail(self.detail_text, text)
        self.detail_text.config(state=tk.DISABLED)

    def _clear_detail_text(self):
        if not hasattr(self, "detail_text"):
            return
        self.detail_text.config(state=tk.NORMAL)
        _insert_rich_detail(self.detail_text, "悬停卡牌查看详情")
        self.detail_text.config(state=tk.DISABLED)

    def _on_imm_change(self, pack: Pack):
        pts = self.imm_sliders[pack].get()
        self.deck.set_immersion(pack, pts)
        self._refresh_available()
        self._refresh_deck_list()

    def _cost_sort_key(self, c):
        from card_pools.effect_utils import convert_cost_to_t
        cost = c.cost
        # 使用折算费用（等效T点数），避免 1D(=4T) 排在 2T 前面
        return convert_cost_to_t(cost) + cost.ct

    def _refresh_available(self):
        for key, tab in self.pack_tabs.items():
            if key == "__assoc__":
                continue
            # 缓存模式：隐藏所有已有按钮和空提示，而非 destroy
            for btn in self._button_pools.get(key, []):
                btn.grid_remove()
            lbl = self._empty_labels.get(key)
            if lbl:
                lbl.grid_remove()

        type_filter = set()
        if self.show_minion.get():
            type_filter.add(CardType.MINION)
        if self.show_strategy.get():
            type_filter.add(CardType.STRATEGY)
        if self.show_conspiracy.get():
            type_filter.add(CardType.CONSPIRACY)
        sort_by = self.sort_by.get()
        is_test = self.deck.is_test_deck
        search_text = self.search_var.get().strip()
        search_term = search_text.lower()
        is_tag_search = search_term.startswith("#")
        if is_tag_search:
            search_term = search_term[1:].strip()

        for pack in Pack:
            pts = self.deck.immersion_points.get(pack, 0)
            def _is_implemented(c):
                if c.card_type == CardType.MINION:
                    return c.special_fn is not None
                if c.card_type == CardType.STRATEGY:
                    return c.effect_fn is not None
                if c.card_type == CardType.CONSPIRACY:
                    return c.effect_fn is not None
                return True

            cards = [
                c for c in DEFAULT_REGISTRY.by_pack(pack)
                if (is_test or c.immersion_level <= pts)
                and c.card_type in type_filter
                and c.card_type != CardType.MINERAL
                and not c.is_moment
                and not c.is_token
                and (not self.hide_unimplemented.get() or _is_implemented(c))
            ]
            # 应用搜索过滤
            if search_term:
                filtered = []
                for c in cards:
                    if is_tag_search:
                        # 词条搜索：关键词 + 标签 + 隐藏关键词
                        keyword_terms = [k.lower() for k in c.keywords.keys()]
                        tag_terms = [t.lower() for t in c.tags]
                        hidden_terms = [k.lower() for k in c.hidden_keywords.keys()]
                        all_terms = keyword_terms + tag_terms + hidden_terms
                        if any(search_term in term for term in all_terms):
                            filtered.append(c)
                    else:
                        # 名称搜索
                        if search_term in c.name.lower():
                            filtered.append(c)
                cards = filtered

            inner = self.pack_tabs[pack]
            buttons = self._button_pools.setdefault(pack, [])
            if not cards:
                lbl = self._empty_labels.get(pack)
                if lbl:
                    lbl.config(text="无匹配卡牌" if search_term else "无可用卡牌（请分配沉浸点）")
                    lbl.grid(sticky="ew", padx=5, pady=2)
                continue
            if sort_by == "cost":
                cards.sort(key=lambda c: (self._cost_sort_key(c), c.immersion_level, c.name))
            else:
                cards.sort(key=lambda c: (c.immersion_level, self._cost_sort_key(c), c.name))
            for idx, card in enumerate(cards):
                info = f"[{card.immersion_display} {card.cost}] {card.name}"
                if card.attack is not None:
                    info += f" {card.attack}/{card.health}"
                if idx < len(buttons):
                    btn = buttons[idx]
                    btn.config(text=info)
                else:
                    btn = tk.Button(inner, text=info, anchor="w")
                    buttons.append(btn)
                # 更新事件绑定（卡牌可能变化）
                btn.bind("<Button-1>", lambda e, c=card: self._show_card_detail(c))
                btn.bind("<Double-Button-1>", lambda e, c=card: (e.widget.event_generate("<ButtonRelease-1>"), self._add_card(c.name)))
                row = idx // 2
                col = (idx % 2) * 2  # 0 或 2，中间列 1 作为间距
                btn.grid(row=row, column=col, sticky="ew", padx=2, pady=1)

        # ===== 填充衍生卡 Tab（只读）=====
        token_inner = self.pack_tabs.get("__token__")
        if token_inner:
            # 只展示无法进入构筑的纯 token 卡（无稀有度 = 不可构筑）
            token_cards = [c for c in DEFAULT_REGISTRY.all_cards() if c.is_token and c.rarity is None]
            token_cards.sort(key=lambda c: (c.pack.value, c.name))
            token_buttons = self._button_pools.setdefault("__token__", [])
            for idx, card in enumerate(token_cards):
                info = f"[{card.pack.value} {card.cost}] {card.name}"
                if card.attack is not None:
                    info += f" {card.attack}/{card.health}"
                if idx < len(token_buttons):
                    btn = token_buttons[idx]
                    btn.config(text=info)
                else:
                    btn = tk.Button(token_inner, text=info, anchor="w")
                    token_buttons.append(btn)
                btn.bind("<Button-1>", lambda e, c=card: self._show_card_detail(c))
                row = idx // 2
                col = (idx % 2) * 2
                btn.grid(row=row, column=col, sticky="ew", padx=2, pady=1)

    def _add_card(self, name: str):
        card_def = DEFAULT_REGISTRY.get(name)
        if not card_def:
            return
        current = self.deck.get_card_count(name)
        # 测试卡组取消稀有度上限和40张限制
        if not self.deck.is_test_deck:
            if current >= card_def.rarity.value:
                self.after(10, lambda: messagebox.showwarning("提示", f"{card_def.rarity.name} 卡最多携带 {card_def.rarity.value} 张"))
                return
            if self.deck.total_cards() >= 40:
                self.after(10, lambda: messagebox.showwarning("提示", "卡组已满 40 张"))
                return
        self.deck.add_card(name)
        self._refresh_deck_list()

    def _remove_selected(self):
        name = getattr(self, "_selected_deck_card", None)
        if not name:
            return
        self.deck.remove_card(name, 1)
        self._selected_deck_card = None
        self._refresh_deck_list()

    def _create_deck_row(self, name: str, count: int, indent: bool = False):
        """在当前卡组列表中创建一个可点击的卡牌行。"""
        card_def = self.deck.registry.get(name)
        bg = self._rarity_bg(getattr(card_def, "rarity", None))
        fg = UI_THEME["text_primary"]

        row = tk.Frame(self.deck_list_inner, bg=bg, relief=tk.FLAT, bd=0, cursor="hand2")
        row.pack(fill=tk.X, pady=1)

        # 左侧选中指示条（默认与面板背景融合，选中时显示强调色）
        indicator = tk.Frame(row, width=4, bg=UI_THEME["bg_panel"])
        indicator.pack(side=tk.LEFT, fill=tk.Y)
        indicator.pack_propagate(False)
        row.indicator = indicator

        def on_click(event, n=name, r=row):
            self._select_deck_row(n, r)

        def on_double(event, n=name):
            self.deck.remove_card(n, 1)
            self._selected_deck_card = None
            self._refresh_deck_list()

        row.bind("<Button-1>", on_click)
        row.bind("<Double-Button-1>", on_double)

        pad_left = 15 if indent else 5
        name_lbl = tk.Label(row, text=name, bg=bg, fg=fg, cursor="hand2")
        name_lbl.pack(side=tk.LEFT, padx=(pad_left, 5))
        count_lbl = tk.Label(row, text=f"x{count}", bg=bg, fg=fg,
                             font=("Microsoft YaHei", 10, "bold"), cursor="hand2")
        count_lbl.pack(side=tk.RIGHT, padx=5)

        for w in (name_lbl, count_lbl):
            w.bind("<Button-1>", on_click)
            w.bind("<Double-Button-1>", on_double)

        return row

    def _select_deck_row(self, name: str, row: tk.Frame):
        """选中卡组列表中的一行并显示详情。"""
        prev = getattr(self, "_selected_deck_row", None)
        if prev and prev.winfo_exists():
            prev.indicator.config(bg=UI_THEME["bg_panel"])
        self._selected_deck_row = row
        self._selected_deck_row_bg = row.cget("bg")
        self._selected_deck_card = name
        row.indicator.config(bg=UI_THEME["accent"])
        card = DEFAULT_REGISTRY.get(name)
        if card:
            self._show_card_detail(card)

    def _rarity_bg(self, rarity) -> str:
        """根据稀有度返回按钮背景色（取渐变浅色端）。"""
        mapping = {
            "GOLD": UI_THEME["rarity_gold"][0],
            "SILVER": UI_THEME["rarity_silver"][0],
            "BRONZE": UI_THEME["rarity_bronze"][0],
            "IRON": UI_THEME["rarity_iron"][0],
        }
        return mapping.get(getattr(rarity, "name", "NONE"), UI_THEME["rarity_none"][0])

    def _clear_deck(self):
        self.deck.card_entries.clear()
        self._refresh_deck_list()

    def _refresh_deck_list(self):
        # 清空旧行并重置选中状态
        for w in self.deck_list_inner.winfo_children():
            w.destroy()
        self._selected_deck_row = None
        self._selected_deck_row_bg = None
        self._selected_deck_card = None

        # 按卡包分组；仅当卡组包含多个卡包时插入虚线分隔
        entries = list(self.deck.card_entries.items())
        if not entries:
            empty_lbl = tk.Label(self.deck_list_inner, text="卡组为空，双击右侧卡牌加入",
                                 bg=UI_THEME["bg_panel"], fg=UI_THEME["text_muted"])
            empty_lbl.pack(pady=10)

        groups: dict[str, list[tuple[str, int]]] = {}
        for name, count in entries:
            card_def = self.deck.registry.get(name)
            pname = card_def.pack.value if card_def and card_def.pack else "未知"
            groups.setdefault(pname, []).append((name, count))

        pack_order = {p.value: i for i, p in enumerate(Pack)}
        sorted_groups = sorted(groups.items(), key=lambda x: pack_order.get(x[0], 999))
        multi_pack = len(sorted_groups) > 1

        for idx, (pname, items) in enumerate(sorted_groups):
            if multi_pack:
                if idx > 0:
                    tk.Label(self.deck_list_inner, text="───────────────",
                             bg=UI_THEME["bg_panel"], fg=UI_THEME["text_muted"]).pack(fill=tk.X, pady=2)
                tk.Label(self.deck_list_inner, text=f"【{pname}】",
                         bg=UI_THEME["bg_panel"], fg=UI_THEME["text_primary"],
                         font=("Microsoft YaHei", 10, "bold")).pack(fill=tk.X, pady=(4, 0))
            for name, count in sorted(items):
                self._create_deck_row(name, count, indent=multi_pack)

        prefix = "[测试] " if self.deck.is_test_deck else ""
        total = self.deck.total_cards()
        self.deck_count_label.config(text=f"{prefix}{total} 张")

        # 计算并刷新统计信息
        from card_pools.effect_utils import convert_cost_to_t

        type_counts = {"异象": 0, "策略": 0, "阴谋": 0, "其他": 0}
        pack_counts: dict[str, int] = {}
        total_cost = 0.0

        for name, count in self.deck.card_entries.items():
            card_def = self.deck.registry.get(name)
            if not card_def:
                continue
            # 类型统计
            if card_def.card_type == CardType.MINION:
                type_counts["异象"] += count
            elif card_def.card_type == CardType.STRATEGY:
                type_counts["策略"] += count
            elif card_def.card_type == CardType.CONSPIRACY:
                type_counts["阴谋"] += count
            else:
                type_counts["其他"] += count
            # 卡包统计
            pname = card_def.pack.value if card_def.pack else "未知"
            pack_counts[pname] = pack_counts.get(pname, 0) + count
            # 费用统计
            total_cost += convert_cost_to_t(card_def.cost) * count

        # 类型文本
        type_parts = [f"{k} {v}" for k, v in type_counts.items() if v > 0]
        self.deck_stats_type.config(text=f"类型: {' | '.join(type_parts) if type_parts else '-'}")

        # 卡包文本
        pack_parts = [f"{k} {v}" for k, v in sorted(pack_counts.items()) if v > 0]
        self.deck_stats_pack.config(text=f"卡包: {' | '.join(pack_parts) if pack_parts else '-'}")

        # 平均费用
        avg_cost = round(total_cost / total, 1) if total > 0 else 0
        self.deck_stats_cost.config(text=f"平均费用: {avg_cost}T")

        # 验证信息
        errors = self.deck.validate()
        if errors:
            self.validation_label.config(text=" | ".join(errors), fg=UI_THEME["danger"])
        else:
            if self.deck.is_test_deck:
                self.validation_label.config(text="测试卡组（无构筑限制）", fg=UI_THEME["warning_dark"])
            else:
                self.validation_label.config(text="卡组合法", fg=UI_THEME["success"])

    def _save_deck(self):
        name = self.name_entry.get().strip()
        if not name:
            messagebox.showwarning("提示", "请输入卡组名")
            return
        errors = self.deck.validate()
        # 测试卡组允许保存（即使有不合法项）
        if errors and not self.deck.is_test_deck:
            messagebox.showwarning("校验失败", "\n".join(errors))
            return
        self.deck.name = name
        from tards.deck_io import DECKS_DIR
        existing = [f[:-5] for f in os.listdir(DECKS_DIR) if f.endswith(".json")]

        # 如果修改了卡组名，询问是否覆盖原卡组文件
        original = getattr(self, "_original_deck_name", "")
        if original and original != name and original in existing:
            if messagebox.askyesno("覆盖原卡组", f"已将卡组名从 [{original}] 改为 [{name}]，是否覆盖原卡组 [{original}]？"):
                old_path = os.path.join(DECKS_DIR, f"{original}.json")
                try:
                    os.remove(old_path)
                except Exception as e:
                    messagebox.showwarning("提示", f"删除原卡组失败: {e}")
                    return
                existing.remove(original)

        # 检查是否覆盖已有文件
        if name in existing:
            if not messagebox.askyesno("覆盖确认", f"卡组 [{name}] 已存在，是否覆盖？"):
                return
        path = save_deck(self.deck)
        self._original_deck_name = name
        msg = f"已保存到 {path}"
        if self.deck.is_test_deck:
            msg += "\n（测试卡组，仅可用于本地测试）"
        messagebox.showinfo("保存成功", msg)

    def _delete_deck(self):
        name = self.deck.name
        if not name or name == "新卡组":
            messagebox.showwarning("提示", "当前卡组尚未保存，无法删除")
            return
        if not messagebox.askyesno("删除确认", f"确定要删除卡组 [{name}] 吗？"):
            return
        from tards.deck_io import DECKS_DIR
        path = os.path.join(DECKS_DIR, f"{name}.json")
        if os.path.exists(path):
            os.remove(path)
            messagebox.showinfo("删除成功", f"卡组 [{name}] 已删除")
            self.app.show_menu()
        else:
            messagebox.showwarning("提示", f"卡组文件不存在: {path}")
