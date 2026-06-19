#!/usr/bin/env python3
"""对战界面主框架 (BattleFrame)。

从 Gamestart.py 拆分而来，集中管理对战 UI 的渲染、交互与状态刷新。
"""

from __future__ import annotations

import os
import random
import re
import socket
import sys
import threading
import time
import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional, Tuple

from tards import (
    Cost,
    Game,
    Minion,
    MinionCard,
    Player,
    Strategy,
    Conspiracy,
    MineralCard,
    target_friendly_positions,
    target_enemy_minions,
    target_any_minion,
    target_self,
    target_none,
)
from tards.constants import (
    EVENT_DISCARDED,
    EVENT_MILLED,
    EVENT_CARD_PLAYED,
    EVENT_CONSPIRACY_TRIGGERED,
    EVENT_DAMAGED,
    EVENT_DEATH,
    EVENT_PLAYER_DAMAGE,
    EVENT_HEALTH_CHANGED,
)
from tards.assets import get_asset_manager
from tards.data.card_db import DEFAULT_REGISTRY, Pack, CardType, Rarity
from tards.data.deck import Deck
from tards.data.deck_io import list_saved_decks, load_deck, save_deck
try:
    from PIL import Image, ImageDraw, ImageTk
    _PIL_AVAILABLE = True
except Exception:
    _PIL_AVAILABLE = False

from tards.core.targeting import (
    TargetingRequest,
    get_attack_target_candidates,
)

# 导入卡包池以注册所有卡牌到 DEFAULT_REGISTRY
import card_pools

# GUI 共享主题与工具函数
from gui.theme import UI_THEME, _RULES_TEXT
from gui.utils import _insert_rule_text, _insert_rich_detail, _deck_defs_list
from gui.battle.render_utils import (
    calc_tab_width,
    create_gradient_photo,
    create_minion_portrait_photo,
    create_tab_gradient_photo,
    get_minion_attack_color,
    get_minion_hp_color,
    interpolate_color,
    rounded_rect,
)
from gui.battle.render_mixin import RenderMixin
from gui.battle.board_renderer import BoardRenderer
from gui.battle.info_renderer import InfoRenderer
from gui.battle.card_renderer import CardRenderer
from gui.battle.detail_renderer import DetailRenderer
from gui.battle.state import BattleState
from gui.battle.duel_adapter import DuelAdapter
from gui.battle.input_controller import InputController
from gui.battle.mulligan_controller import MulliganController
from gui.battle.reveal_controller import RevealController
from gui.battle.action_controller import ActionController
from gui.battle.game_loop_controller import GameLoopController, gui_refresh_event
from gui.battle.event_history_controller import EventHistoryController
from gui.dialogs import (
    SacrificeDialog,
    DiscoverDialog,
    ChoiceDialog,
    EffectTargetDialog,
    NumericChoiceDialog,
)
from gui.tooltip import Tooltip

if TYPE_CHECKING:
    from Gamestart import TardsApp

class BattleFrame(tk.Frame, RenderMixin):

    CELL_SIZE = 80
    MINION_SIZE = 59               # 场上异象显示方块边长（约 +5%）
    MINION_STAT_BAR_HEIGHT = 17    # 攻击/HP 栏高度
    MINION_STAT_BAR_SLANT = 6      # 攻击/HP 栏斜切宽度
    MINION_KEYWORD_BOX = 15        # 外部状态小方框边长（15×15 像素画基准）
    MINION_KEYWORD_GAP = 1         # 外部状态小方框间距
    MINION_OFFSET_X = -5           # 异象整体向左偏移像素数
    MINION_CORNER_LEG = 10         # 左下角敌我缺角/标记直角边长
    COL_NAMES = ["高地", "山脊", "中路", "河岸", "水路"]
    HAND_CARD_WIDTH = 90
    HAND_CARD_HEIGHT = 144
    BOARD_COLS = 5
    BOARD_ROWS = 5
    BOARD_OFFSET_X = 50
    BOARD_OFFSET_Y = 40

    def __init__(self, parent, app: TardsApp, duel: Any, local_player: Player, opponent: Player):
        super().__init__(parent)
        self.app = app
        self.local_player = local_player
        self.opponent = opponent

        # 统一状态容器与对战适配器
        self.state = BattleState()
        self.duel = DuelAdapter(duel)

        # 子控制器
        self.input_controller: Optional[InputController] = None
        self.mulligan_controller: Optional[MulliganController] = None
        self.reveal_controller: Optional[RevealController] = None
        self.action_controller: Optional[ActionController] = None
        self.game_loop_controller: Optional[GameLoopController] = None
        self.event_history_controller: Optional[EventHistoryController] = None

        self._build_ui()
        self.board_renderer.draw_grid()
        self.game_loop_controller.start_game_thread()
        self.game_loop_controller.schedule_refresh()
        self._bind_shortcuts()

    def _display_row(self, logic_r: int) -> int:
        """将逻辑行坐标转换为显示行坐标。

        side=1（Client/后手）时翻转视角：自己的半场始终显示在屏幕下方。
        """
        if self.local_player and self.local_player.side == 1:
            return self.BOARD_ROWS - 1 - logic_r
        return logic_r

    def _logic_row(self, display_r: int) -> int:
        """将显示行坐标转换回逻辑行坐标（_display_row 的逆运算）。"""
        if self.local_player and self.local_player.side == 1:
            return self.BOARD_ROWS - 1 - display_r
        return display_r

    def _bind_shortcuts(self):
        """绑定键盘快捷键与全局拖拽事件。"""
        self.bind_all("<Key>", self._on_key_press)
        self.bind_all("<B1-Motion>", self._on_drag_motion)
        self.bind_all("<ButtonRelease-1>", self._on_drag_release)

    def _on_key_press(self, event):
        """处理键盘快捷键（委托给 InputController）。"""
        self.input_controller.on_key_press(event)

    def _auto_fill_attack_targets(self):
        """一键自动为所有能攻击的异象填充默认攻击目标。"""
        self.input_controller.auto_fill_attack_targets()


    def _auto_fill_effect_targets(self):
        """一键自动为所有有效果预设能力的异象填充默认效果目标。"""
        self.input_controller.auto_fill_effect_targets()


    # ===== 拖拽出牌 =====
    def _on_drag_start(self, event, card, serial):
        """记录拖拽起始状态。"""
        self.input_controller.on_drag_start(event, card, serial)


    def _on_drag_motion(self, event):
        """拖拽中显示跟随标签或卡牌缩略图。"""
        self.input_controller.on_drag_motion(event)


    def _on_drag_release(self, event):
        """释放时判断是否在棋盘内，尝试直接出牌。"""
        self.input_controller.on_drag_release(event)


    def _try_play_at_position(self, serial, target):
        """尝试在指定格子直接部署卡牌（仅支持无需献祭/指向的异象卡）。"""
        self.input_controller.try_play_at_position(serial, target)


    def _on_board_resize(self, event):
        """棋盘 Canvas 大小变化时重新计算单元格尺寸并重绘。

        限制最大 cell_size 为 80（原始大小），只在小窗口时自动缩小，
        避免全屏时棋盘过大遮挡信息面板。
        """
        w, h = event.width, event.height
        if w < 200 or h < 200:
            return
        margin = 20
        label_h = 25  # 底部列名标签高度
        new_cell = min((w - margin * 2) // self.BOARD_COLS,
                       (h - margin * 2 - label_h) // self.BOARD_ROWS)
        # 最大 105px，最小 40px
        new_cell = max(min(new_cell, 105), 40)
        new_offset_x = (w - self.BOARD_COLS * new_cell) // 2
        new_offset_y = (h - self.BOARD_ROWS * new_cell - label_h) // 2
        if (new_cell != self.state.cell_size or
            new_offset_x != self.state.board_offset_x or
            new_offset_y != self.state.board_offset_y):
            self.state.cell_size = new_cell
            self.state.board_offset_x = new_offset_x
            self.state.board_offset_y = new_offset_y
            self.board_renderer.update_dimensions(new_cell, new_offset_x, new_offset_y)
            self.board_renderer.draw_grid()
            if self.duel.game:
                self._render_board()


    # ------------------------------------------------------------------
    # 静态辅助：颜色与绘制
    # ------------------------------------------------------------------
    def _build_ui(self):
        self.config(bg=UI_THEME["bg_main"])

        # 左侧整体（垂直布局：对手信息 + 棋盘 + 本地玩家信息）
        left = tk.Frame(self, bg=UI_THEME["bg_main"])
        left.place(relx=0.01, rely=0.01, relwidth=0.48, relheight=0.98)

        # 对手信息（棋盘上方）
        self.opponent_info = self._build_player_info_panel(left, self.opponent, is_local=False)

        # 棋盘（自适应大小）
        self.canvas = tk.Canvas(left, width=500, height=500, bg=UI_THEME["bg_canvas"], highlightthickness=0, bd=0)
        self.canvas.pack(fill=tk.BOTH, expand=True, pady=2)
        self.canvas.bind("<Button-1>", self._on_canvas_click)
        self.canvas.bind("<Configure>", self._on_board_resize)

        # 棋盘渲染器
        self.board_renderer = BoardRenderer(
            canvas=self.canvas,
            cell_size=self.state.cell_size,
            board_offset_x=self.state.board_offset_x,
            board_offset_y=self.state.board_offset_y,
            col_names=self.COL_NAMES,
            minion_size=self.MINION_SIZE,
            minion_corner_leg=self.MINION_CORNER_LEG,
            keyword_box=self.MINION_KEYWORD_BOX,
            keyword_gap=self.MINION_KEYWORD_GAP,
            display_row_fn=self._display_row,
        )

        # 信息面板渲染器
        self.info_renderer = InfoRenderer(self)

        # 卡牌渲染器
        self.card_renderer = CardRenderer(self)

        # 详情文本渲染器
        self.detail_renderer = DetailRenderer(self)

        # 输入/事件控制器
        self.input_controller = InputController(self)
        self.mulligan_controller = MulliganController(self)
        self.reveal_controller = RevealController(self)
        self.action_controller = ActionController(self)
        self.game_loop_controller = GameLoopController(self)
        self.event_history_controller = EventHistoryController(self)

        # 本地玩家信息（棋盘下方）
        self.local_info = self._build_player_info_panel(left, self.local_player, is_local=True)

        self.info_labels = {
            self.opponent.name: self.opponent_info,
            self.local_player.name: self.local_info,
        }

        # 右侧
        right = tk.Frame(self, bg=UI_THEME["bg_main"])
        right.place(relx=0.50, rely=0.01, relwidth=0.48, relheight=0.98)

        # 阶段显示
        self.phase_label = tk.Label(right, text="等待游戏开始...", font=("Microsoft YaHei", 14, "bold"),
                                    bg=UI_THEME["bg_main"], fg=UI_THEME["accent"])
        self.phase_label.pack(fill=tk.X, pady=(0, 5))

        # 最近动作事件条
        self.event_bar_label = tk.Label(right, text="", font=("Microsoft YaHei", 10),
                                        bg=UI_THEME["bg_main"], fg=UI_THEME["log_event"])
        self.event_bar_label.pack(fill=tk.X, pady=(0, 5))

        # ===== 弃置/移除/磨牌展示面板 =====
        self.reveal_controller.build_ui(right)

        # ===== 动态手牌区 =====
        # 每个 zone: (label, frame_attr, inner_attr, canvas_attr, player_attr, player_max_attr)
        # 未来添加奇迹手牌区等只需追加条目
        self.hand_zones = []

        # 1) 普通手牌区（始终显示）
        self.hand_frame = tk.LabelFrame(right, text="手牌",
                                        bg=UI_THEME["bg_panel"], fg=UI_THEME["text_secondary"])
        self.hand_frame.pack(fill=tk.X, pady=5)
        hand_canvas = tk.Canvas(self.hand_frame, height=self.HAND_CARD_HEIGHT + 10,
                                bg=UI_THEME["bg_panel"], highlightthickness=0, bd=0)
        hbar = tk.Scrollbar(self.hand_frame, orient=tk.HORIZONTAL, command=hand_canvas.xview)
        hand_canvas.configure(xscrollcommand=hbar.set)
        hbar.pack(side=tk.BOTTOM, fill=tk.X)
        hand_canvas.pack(side=tk.TOP, fill=tk.X, expand=True)
        self.hand_inner = tk.Frame(hand_canvas, bg=UI_THEME["bg_panel"])
        hand_canvas.create_window((0, 0), window=self.hand_inner, anchor="nw")
        self.hand_inner.bind("<Configure>", lambda e, c=hand_canvas: c.configure(scrollregion=c.bbox("all")))
        self.hand_zones.append({
            "label": "手牌",
            "frame": self.hand_frame,
            "inner": self.hand_inner,
            "player_attr": "card_hand",
            "always_show": True,
        })

        # 2) 附加手牌槽 + 当前玩家资源面板（横向排列）
        self.hand_bottom_row = tk.Frame(right, bg=UI_THEME["bg_main"])
        self.hand_bottom_row.pack(fill=tk.X, pady=5)

        # 左侧：附加手牌槽（约占 55%）
        self.extra_hand_frame = tk.LabelFrame(self.hand_bottom_row, text="附加手牌槽",
                                              bg=UI_THEME["bg_panel"], fg=UI_THEME["text_secondary"])
        self.extra_hand_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # 右侧：当前玩家资源面板（约占 45%，随 current_player 切换）
        self.res_panel = tk.LabelFrame(self.hand_bottom_row, text="当前资源",
                                       bg=UI_THEME["bg_panel"], fg=UI_THEME["text_secondary"])
        self.res_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(5, 0))
        res_row1 = tk.Frame(self.res_panel, bg=UI_THEME["bg_panel"])
        res_row1.pack(fill=tk.X, padx=5, pady=(5, 2))
        self.res_t_label = tk.Label(res_row1, text="T: -/-", font=("Microsoft YaHei", 10, "bold"),
                                    fg=UI_THEME["res_t"], bg=UI_THEME["bg_panel"])
        self.res_t_label.pack(side=tk.LEFT, padx=(0, 8))
        self.res_c_label = tk.Label(res_row1, text="C: -/-", font=("Microsoft YaHei", 10, "bold"),
                                    fg=UI_THEME["res_c"], bg=UI_THEME["bg_panel"])
        self.res_c_label.pack(side=tk.LEFT, padx=(0, 8))
        self.res_b_label = tk.Label(res_row1, text="B: 0", font=("Microsoft YaHei", 10, "bold"),
                                    fg=UI_THEME["res_b"], bg=UI_THEME["bg_panel"])
        self.res_b_label.pack(side=tk.LEFT, padx=(0, 8))
        self.res_sacrifice_label = tk.Label(res_row1, text="可献祭: 0", font=("Microsoft YaHei", 9),
                                            fg="#9c27b0", bg=UI_THEME["bg_panel"])
        self.res_sacrifice_label.pack(side=tk.LEFT, padx=(0, 8))
        self.res_s_label = tk.Label(res_row1, text="S: 0", font=("Microsoft YaHei", 10, "bold"),
                                    fg=UI_THEME["res_s"], bg=UI_THEME["bg_panel"])
        self.res_s_label.pack(side=tk.LEFT, padx=(0, 8))
        res_row2 = tk.Frame(self.res_panel, bg=UI_THEME["bg_panel"])
        res_row2.pack(fill=tk.X, padx=5, pady=(0, 5))
        self.res_deck_label = tk.Label(res_row2, text="抽牌堆:0", font=("Microsoft YaHei", 9),
                                       bg=UI_THEME["bg_panel"], fg=UI_THEME["text_primary"])
        self.res_deck_label.pack(side=tk.LEFT, padx=(0, 8))
        self.res_dis_label = tk.Label(res_row2, text="弃牌堆:0", font=("Microsoft YaHei", 9),
                                      bg=UI_THEME["bg_panel"], fg=UI_THEME["text_primary"])
        self.res_dis_label.pack(side=tk.LEFT, padx=(0, 8))

        res_row3 = tk.Frame(self.res_panel, bg=UI_THEME["bg_panel"])
        res_row3.pack(fill=tk.X, padx=5, pady=(0, 5))
        self.res_conspiracy_label = tk.Label(res_row3, text="阴谋序列:0", font=("Microsoft YaHei", 9),
                                             bg=UI_THEME["bg_panel"], fg=UI_THEME["text_primary"])
        self.res_conspiracy_label.pack(side=tk.LEFT, padx=(0, 8))

        # 按钮区分组：主操作 / 兑换 / 系统
        btn_frame = tk.Frame(right, bg=UI_THEME["bg_main"])
        btn_frame.pack(fill=tk.X, pady=5)

        # 主操作组（最醒目）
        main_grp = tk.LabelFrame(btn_frame, text="操作", bg=UI_THEME["bg_panel"], fg=UI_THEME["text_secondary"],
                                 font=("Microsoft YaHei", 8), padx=4, pady=2)
        main_grp.pack(side=tk.LEFT, padx=(0, 6))
        self.bell_btn = tk.Button(main_grp, text="拍铃", bg=UI_THEME["btn_warning_bg"], fg=UI_THEME["btn_warning_fg"],
                                  activebackground=UI_THEME["btn_warning_active"], font=("Microsoft YaHei", 10, "bold"),
                                  width=6, height=1)
        self.bell_btn.pack(side=tk.LEFT, padx=2)
        self.bell_btn.bind("<Double-Button-1>", lambda e: self.action_controller.on_bell())
        self.brake_btn = tk.Button(main_grp, text="拉闸", bg=UI_THEME["btn_secondary_bg"], fg=UI_THEME["btn_secondary_fg"],
                                   activebackground=UI_THEME["btn_secondary_active"], font=("Microsoft YaHei", 10, "bold"),
                                   width=6, height=1)
        self.brake_btn.pack(side=tk.LEFT, padx=2)
        self.brake_btn.bind("<Double-Button-1>", lambda e: self.action_controller.on_brake())

        # 兑换组（中等）
        ex_grp = tk.LabelFrame(btn_frame, text="兑换", bg=UI_THEME["bg_panel"], fg=UI_THEME["text_secondary"],
                               font=("Microsoft YaHei", 8), padx=4, pady=2)
        ex_grp.pack(side=tk.LEFT, padx=(0, 6))
        self.exchange_btn = tk.Button(ex_grp, text="矿物", bg="#fff9c4", fg="#f57f17",
                                      activebackground="#fff59d", font=("Microsoft YaHei", 9),
                                      width=5, command=self.action_controller.toggle_mineral_bar)
        self.exchange_btn.pack(side=tk.LEFT, padx=2)
        self.exchange_squirrel_btn = tk.Button(ex_grp, text="松鼠", bg="#fff9c4", fg="#f57f17",
                                               activebackground="#fff59d", font=("Microsoft YaHei", 9),
                                               width=5, command=self.action_controller.on_exchange_squirrel)
        self.exchange_squirrel_btn.pack(side=tk.LEFT, padx=2)
        self.squirrel_draw_var = tk.BooleanVar(value=False)
        self.squirrel_draw_cb = tk.Checkbutton(ex_grp, text="抽", bg=UI_THEME["bg_panel"], fg="#f57f17",
                                               variable=self.squirrel_draw_var,
                                               command=self.action_controller.on_toggle_squirrel_draw,
                                               font=("Microsoft YaHei", 9),
                                               selectcolor=UI_THEME["bg_panel"])
        self.squirrel_draw_cb.pack(side=tk.LEFT, padx=2)

        # 矿物展开面板（点击"矿物"后展开，显示4个快捷兑换按钮）
        self.mineral_bar = tk.Frame(right, bg=UI_THEME["bg_main"])
        self.state._mineral_buttons = {}
        mineral_specs = [
            ("I", "铁锭"),
            ("G", "金锭"),
            ("D", "钻石"),
            ("M", "青金石"),
        ]
        for mtype, mname in mineral_specs:
            btn = tk.Button(self.mineral_bar, text=mname, font=("Microsoft YaHei", 9),
                            width=6, bg="#fff9c4", fg="#f57f17",
                            activebackground="#fff59d",
                            command=lambda n=mname: self.action_controller.do_exchange_mineral(n))
            btn.pack(side=tk.LEFT, padx=3)
            self.state._mineral_buttons[mtype] = btn

        # 系统组（弱化）
        sys_grp = tk.Frame(btn_frame, bg=UI_THEME["bg_main"])
        sys_grp.pack(side=tk.LEFT)
        self.cancel_btn = tk.Button(sys_grp, text="取消", bg=UI_THEME["btn_secondary_bg"], fg=UI_THEME["btn_secondary_fg"],
                                    activebackground=UI_THEME["btn_secondary_active"], font=("Microsoft YaHei", 9),
                                    width=5, command=self.action_controller.on_cancel)
        self.cancel_btn.pack(side=tk.LEFT, padx=2)
        self.terminate_btn = tk.Button(sys_grp, text="终止", bg=UI_THEME["btn_danger_bg"], fg=UI_THEME["btn_danger_fg"],
                                       activebackground=UI_THEME["btn_danger_active"], font=("Microsoft YaHei", 9),
                                       width=5, command=self.action_controller.on_terminate_game)
        self.terminate_btn.pack(side=tk.LEFT, padx=2)
        self.feedback_btn = tk.Button(sys_grp, text="反馈", bg=UI_THEME["btn_secondary_bg"], fg=UI_THEME["btn_secondary_fg"],
                                      activebackground=UI_THEME["btn_secondary_active"], font=("Microsoft YaHei", 9),
                                      width=5, command=self._on_feedback)
        self.feedback_btn.pack(side=tk.LEFT, padx=2)
        self.extra_hand_canvas = tk.Canvas(self.extra_hand_frame, height=self.HAND_CARD_HEIGHT + 10,
                                           bg=UI_THEME["bg_panel"], highlightthickness=0, bd=0)
        mineral_hbar = tk.Scrollbar(self.extra_hand_frame, orient=tk.HORIZONTAL, command=self.extra_hand_canvas.xview)
        self.extra_hand_canvas.configure(xscrollcommand=mineral_hbar.set)
        mineral_hbar.pack(side=tk.BOTTOM, fill=tk.X)
        self.extra_hand_canvas.pack(side=tk.TOP, fill=tk.X, expand=True)
        self.extra_hand_inner = tk.Frame(self.extra_hand_canvas, bg=UI_THEME["bg_panel"])
        self.extra_hand_canvas.create_window((0, 0), window=self.extra_hand_inner, anchor="nw")
        self.extra_hand_inner.bind("<Configure>", lambda e, c=self.extra_hand_canvas: c.configure(scrollregion=c.bbox("all")))
        self.hand_zones.append({
            "label": "附加手牌槽",
            "frame": self.extra_hand_frame,
            "inner": self.extra_hand_inner,
            "player_attr": "extra_hand",
            "max_attr": "extra_hand_max",
        })

        self.hint_label = tk.Label(right, text="等待游戏开始...", fg=UI_THEME["accent"],
                                   bg=UI_THEME["bg_main"], wraplength=500)
        self.hint_label.pack(fill=tk.X, pady=5)

        # 卡牌详情文本栏（悬停时显示）
        detail_frame = tk.LabelFrame(right, text="卡牌详情",
                                     bg=UI_THEME["bg_panel"], fg=UI_THEME["text_secondary"])
        detail_frame.pack(fill=tk.X, pady=5)
        self.detail_text = tk.Text(detail_frame, height=8, wrap=tk.WORD,
                                   font=("Microsoft YaHei", 10), state=tk.DISABLED,
                                   bg=UI_THEME["bg_main"], fg=UI_THEME["text_primary"], relief=tk.FLAT, bd=0)
        self.detail_text.pack(fill=tk.X, padx=5, pady=5)
        self.detail_text.config(state=tk.NORMAL)
        _insert_rich_detail(self.detail_text, "悬停卡牌查看详情")
        self.detail_text.config(state=tk.DISABLED)

        # 操作历史
        history_frame = tk.LabelFrame(right, text="操作历史",
                                      bg=UI_THEME["bg_panel"], fg=UI_THEME["text_secondary"])
        history_frame.pack(fill=tk.X, pady=5)
        self.history_list = tk.Listbox(history_frame, height=5, font=("Microsoft YaHei", 9),
                                       bg=UI_THEME["bg_main"], fg=UI_THEME["text_primary"],
                                       selectbackground=UI_THEME["accent"], selectforeground="white")
        self.history_list.pack(fill=tk.X, padx=5, pady=2)

        # 日志
        log_frame = tk.LabelFrame(right, text="日志",
                                  bg=UI_THEME["bg_panel"], fg=UI_THEME["text_secondary"])
        log_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        self.log_text = scrolledtext.ScrolledText(log_frame, state=tk.DISABLED, wrap=tk.WORD,
                                                  bg=UI_THEME["bg_main"], fg=UI_THEME["text_primary"],
                                                  relief=tk.FLAT, bd=0)
        self.log_text.pack(fill=tk.BOTH, expand=True)
        self.log_text.tag_config("death", foreground=UI_THEME["log_death"], font=("Microsoft YaHei", 9, "bold"))
        self.log_text.tag_config("damage", foreground=UI_THEME["log_damage"])
        self.log_text.tag_config("victory", foreground=UI_THEME["log_victory"], font=("Microsoft YaHei", 10, "bold"))

        # 让附加手牌槽+资源面板行与手牌区严格等高
        self.update_idletasks()
        self.hand_bottom_row.config(height=self.hand_frame.winfo_reqheight())
        self.hand_bottom_row.pack_propagate(False)

        # 费用支付预览标签（悬停手牌时显示打出后的资源变化）
        self.cost_preview_label = tk.Label(right, text="", font=("Microsoft YaHei", 9),
                                           bg=UI_THEME["bg_main"], fg=UI_THEME["text_secondary"])
        self.cost_preview_label.pack(fill=tk.X, pady=(0, 5))

    def _show_cost_preview(self, card: Any, serial: int) -> None:
        """悬停手牌时预览打出该牌后的资源变化（委托给 EventHistoryController）。"""
        self.event_history_controller.show_cost_preview(card, serial)


    def _clear_cost_preview(self) -> None:
        """清除费用支付预览（委托给 EventHistoryController）。"""
        self.event_history_controller.clear_cost_preview()


    def _add_recent_event(self, text: str, positions: Optional[List[Tuple[int, int]]] = None) -> None:
        """记录一条最近发生的事件（委托给 EventHistoryController）。"""
        self.event_history_controller.add_recent_event(text, positions)


    def _refresh_event_bar(self) -> None:
        """刷新顶部最近动作事件条（委托给 EventHistoryController）。"""
        self.event_history_controller.refresh_event_bar()


    def _expire_recent_events(self) -> None:
        """清除 2.5 秒前的事件（委托给 EventHistoryController）。"""
        self.event_history_controller.expire_recent_events()


    def _add_history(self, text: str, is_play: bool = False,
                       player_name: Optional[str] = None,
                       turn: Optional[int] = None,
                       phase: Optional[str] = None):
        """添加一条操作历史记录（委托给 EventHistoryController）。"""
        self.event_history_controller.add_history(text, is_play, player_name, turn, phase)


    def _preview_deploy_positions(self, serial: int):
        """悬停手牌时预览合法目标位置（委托给 BoardRenderer）。"""
        self.board_renderer.preview_deploy_positions(self, serial)




    # ------------------------------------------------------------------
    # 场上异象新版 1/2/3/4 区域绘制
    # ------------------------------------------------------------------






    def _render_board(self):
        """绘制整个棋盘（委托给 BoardRenderer）。"""
        self.board_renderer.render_board(self)

    def _update_detail_text(self, card):
        """在右侧文本栏中显示卡牌/异象信息（委托给 DetailRenderer）。"""
        self.detail_renderer.render(card)






    # ===== 稀有度渐变背景（统一引用主题色板） =====
    _RARITY_GRADIENTS = {
        Rarity.GOLD:   UI_THEME["rarity_gold"],
        Rarity.SILVER: UI_THEME["rarity_silver"],
        Rarity.BRONZE: UI_THEME["rarity_bronze"],
        Rarity.IRON:   UI_THEME["rarity_iron"],
    }

    # 折痕颜色（背面, 正面, 折痕线）— 与稀有度主色调协调
    _FOLD_COLORS = {
        Rarity.GOLD:   UI_THEME["fold_gold"],
        Rarity.SILVER: UI_THEME["fold_silver"],
        Rarity.BRONZE: UI_THEME["fold_bronze"],
        Rarity.IRON:   UI_THEME["fold_iron"],
        None:          UI_THEME["fold_none"],
    }


    def _render_hand_card(self, parent, card, idx, serial, active, card_type_colors, am, cw, ch, flash=False):
        """渲染单张手牌卡牌（委托给 CardRenderer）。"""
        self.card_renderer.render_hand_card(parent, card, idx, serial, active, flash=flash)

    def _render_reveal_card(self, canvas, card, cw=90, ch=144):
        """在指定 Canvas 上渲染一张静态展示卡牌（委托给 CardRenderer）。"""
        self.card_renderer.render_reveal_card(canvas, card, cw=cw, ch=ch)

    def _render_hand(self):
        game = self.duel.game
        if not game:
            return
        # 网络对局始终显示本地玩家手牌；本地对局显示当前回合玩家手牌
        active = self.local_player if self.duel.is_remote else game.current_player
        if not active:
            return
        card_type_colors = {
            MinionCard: "#eff6ff",
            Strategy: "#f0fdf4",
            Conspiracy: "#faf5ff",
            MineralCard: "#fefce8",
        }
        am = get_asset_manager()
        cw = self.HAND_CARD_WIDTH
        ch = self.HAND_CARD_HEIGHT

        current_card_ids = set()
        serial = 1
        for zi, zone in enumerate(self.hand_zones):
            # 清空 zone
            for w in list(zone["inner"].winfo_children()):
                w.destroy()

            cards = getattr(active, zone["player_attr"])
            always_show = zone.get("always_show", False)
            if not always_show:
                max_val = getattr(active, zone.get("max_attr", ""), 0)
                if max_val <= 0:
                    zone["frame"].pack_forget()
                    continue
                # 重新 pack（只在被隐藏过的情况下）
                if not zone["frame"].winfo_ismapped():
                    zone["frame"].pack(fill=tk.BOTH, expand=True, side=tk.LEFT)

            for i, card in enumerate(cards):
                idx = serial - 1  # 0-based index for click handler
                flash = id(card) not in self.state._prev_hand_card_ids
                self._render_hand_card(zone["inner"], card, idx, serial, active, card_type_colors, am, cw, ch, flash=flash)
                current_card_ids.add(id(card))
                serial += 1

        self.state._prev_hand_card_ids = current_card_ids

    # ========== Mulligan（开局手牌调整）UI ==========
    def _show_mulligan(self, player: Player):
        """显示开局手牌调整界面（委托给 MulliganController）。"""
        self.mulligan_controller.show(player)


    def _refresh_mulligan_cards(self):
        """刷新 mulligan 手牌显示（委托给 MulliganController）。"""
        self.mulligan_controller._refresh_cards()


    def _render_mulligan_card(self, parent, card, idx, selected, card_type_colors, am, cw, ch):
        """渲染单张 mulligan 卡牌（委托给 CardRenderer）。"""
        self.card_renderer.render_mulligan_card(parent, card, idx, selected, cw, ch)


    def _on_mulligan_card_click(self, idx: int):
        """切换 mulligan 卡牌选中状态（委托给 MulliganController）。"""
        self.mulligan_controller._on_card_click(idx)


    def _on_mulligan_confirm(self):
        """确认 mulligan 选择（委托给 MulliganController）。"""
        self.mulligan_controller.confirm()


    def _hide_mulligan(self):
        """隐藏 mulligan 界面（委托给 MulliganController）。"""
        self.mulligan_controller.hide()


    def _render_info(self):
        """刷新玩家信息与资源面板（委托给 InfoRenderer）。"""
        self.info_renderer.render()

    def _flash_res_label(self, widget, flash_color, times=2, interval=150):
        """同时闪烁 Label 的背景和前景色，效果更明显。"""
        if not widget.winfo_exists():
            return
        original_fg = widget.cget("fg")
        original_bg = widget.cget("bg")
        flash_fg = "#ffffff" if flash_color == "#f44336" else "#000000"

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

    def _get_available_blood(self, player):
        """计算场上友方异象可提供的献祭B点总和。"""
        if not self.duel.game:
            return 0
        minions = self.duel.game.board.get_minions_of_player(player)
        return sum(m.keywords.get("丰饶", 1) for m in minions if m.is_alive())

    def _on_minion_click(self, minion: Minion):
        # 1. 献祭选择模式：选择/取消祭品
        self.input_controller.on_minion_click(minion)


    def _on_minion_double_click(self, minion: Minion):
        """双击异象：
        - 若已在攻击指向模式且来源是该异象 → 切换到效果预设模式
        - 否则同单击逻辑（进入预设）
        """
        self.input_controller.on_minion_double_click(minion)


    def _on_player_label_click(self, player: Optional[Player]):
        self.input_controller.on_player_label_click(player)


    def _enter_local_targeting(self, valid_targets: List[Any], on_confirm: Callable[[Any], None],
                                on_cancel: Optional[Callable[[], None]] = None, prompt: str = "请选择目标"):
        """进入本地指向模式（用于 action 阶段的主目标选择或攻击预设）。"""
        self.input_controller.enter_local_targeting(valid_targets, on_confirm, on_cancel, prompt)


    def _show_targeting(self, request: TargetingRequest, valid_targets: List[Any]):
        """响应 targeting_request 事件，渲染指向选项。"""
        self.input_controller.show_targeting(request, valid_targets)


    def _enter_sacrifice_mode(self, serial: int, card, active, required_blood: int):
        """进入献祭选择模式：玩家点击场上友方异象作为祭品。"""
        self.input_controller.enter_sacrifice_mode(serial, card, active, required_blood)


    def _exit_sacrifice_mode(self):
        """退出献祭选择模式。"""
        self.input_controller.exit_sacrifice_mode()


    def _confirm_sacrifice(self):
        """确认当前选择的献祭，进入部署位置选择。"""
        self.input_controller.confirm_sacrifice()


    def _exit_targeting_mode(self, preserve_pending=False):
        self.input_controller.exit_targeting_mode(preserve_pending)


    def _clear_attack_targets(self, pos):
        """清除指定异象的预设攻击目标。"""
        self.input_controller.clear_attack_targets(pos)


    def _clear_effect_target(self, pos):
        """清除指定异象的预设效果目标。"""
        self.input_controller.clear_effect_target(pos)


    def _handle_board_unit_click(self, target, mode="attack"):
        """处理玩家点击场上自己的异象（攻击预设或效果预设）。"""
        self.input_controller.handle_board_unit_click(target, mode)


    def _on_hand_card_click(self, idx: int):
        # 防重复点击/按键：出牌流程进行中时忽略新输入
        self.input_controller.on_hand_card_click(idx)



    def _enter_deploy_targeting(self, serial: int, card, active):
        """进入异象卡部署位置选择。"""
        self.input_controller.enter_deploy_targeting(serial, card, active)


    def _enter_effect_targeting(self, serial: int, card, active):
        """进入策略/矿物卡效果目标选择。"""
        self.input_controller.enter_effect_targeting(serial, card, active)


    def _flash_invalid_at(self, target):
        """在指定位置闪烁红色边框，提示非法操作。"""
        self.input_controller.flash_invalid_at(target)


    def _on_canvas_click(self, event):
        self.input_controller.on_canvas_click(event)


    def _submit_play(self, serial: int, target: Any):
        self.input_controller.submit_play(serial, target)


    def _reset_guide_hint(self):
        """根据当前阶段恢复引导文字。"""
        self.input_controller.reset_guide_hint()


    def _on_bell(self):
        # 防重复点击/按键
        self.input_controller.on_bell()


    def _on_brake(self):
        # 防重复点击/按键
        self.input_controller.on_brake()


    def _on_cancel(self):
        self.input_controller.on_cancel()

    def _toggle_mineral_bar(self):
        """展开/收起矿物快捷兑换面板。"""
        self.action_controller.toggle_mineral_bar()

    def _set_btn_disabled(self, btn: tk.Button) -> None:
        """将按钮设为不可用并显示灰色。"""
        self.action_controller.set_btn_disabled(btn)

    def _set_btn_enabled(self, btn: tk.Button, bg: str, fg: str) -> None:
        """将按钮设为可用并恢复指定配色。"""
        self.action_controller.set_btn_enabled(btn, bg, fg)

    def _refresh_action_buttons(self) -> None:
        """根据当前游戏状态启用/禁用拍铃、拉闸、取消选择、终止按钮。"""
        self.action_controller.refresh_action_buttons()

    def _refresh_mineral_bar(self):
        """根据当前玩家资源刷新4个矿物按钮的可用状态。"""
        self.action_controller.refresh_mineral_bar()

    def _do_exchange_mineral(self, name: str) -> None:
        """直接兑换指定名称的矿物，收起展开面板。"""
        self.action_controller.do_exchange_mineral(name)

    def _on_toggle_squirrel_draw(self):
        """切换抽松鼠选项。"""
        self.action_controller.on_toggle_squirrel_draw()

    def _on_feedback(self):
        """反馈按钮（功能已移除）。"""
        messagebox.showinfo("反馈", "反馈功能已移除")

    def _on_exchange_squirrel(self):
        """兑换松鼠。"""
        self.action_controller.on_exchange_squirrel()

    def _on_exchange_mineral(self, mineral_type: str):
        """按快捷键直接兑换指定矿物（I/G/D/M）。"""
        self.action_controller.on_exchange_mineral(mineral_type)

    def _clear_selection(self):
        self.state.selected_card_idx = None
        self.state.selected_card = None
        self.state.valid_targets = []
        self.state._pending_sacrifices = []
        self._render_hand()
        self._render_board()

    def _schedule_refresh(self):
        """刷新循环入口（委托给 GameLoopController）。"""
        self.game_loop_controller.schedule_refresh()

    def _try_refresh(self):
        """尝试刷新 UI（委托给 GameLoopController）。"""
        self.game_loop_controller.try_refresh()

    def _start_game_thread(self):
        """启动后台游戏线程（委托给 GameLoopController）。"""
        self.game_loop_controller.start_game_thread()

    def _move_tooltip(self, x, y):
        if self._tooltip:
            self._tooltip.move(x, y)

    def _hide_tooltip(self):
        if self._tooltip:
            self._tooltip.destroy()
            self._tooltip = None
        self._tooltip_source = None

    def _on_terminate_game(self):
        """终止当前对局并返回主菜单（委托给 ActionController）。"""
        self.action_controller.on_terminate_game()

    def _show_toast(self, text: str, bg_color: str = "", duration_ms: int = 1500):
        """在屏幕中央显示一个临时浮层提示，duration_ms 后自动消失。"""
        toast = tk.Toplevel(self)
        toast.overrideredirect(True)
        toast.attributes("-topmost", True)
        if not bg_color:
            bg_color = UI_THEME["btn_warning_bg"]
        label = tk.Label(toast, text=text, font=("Microsoft YaHei", 14, "bold"),
                         bg=bg_color, fg=UI_THEME["text_primary"], padx=20, pady=10,
                         relief="solid", bd=1)
        label.pack()
        toast.update_idletasks()
        x = self.winfo_rootx() + (self.winfo_width() // 2) - (toast.winfo_width() // 2)
        y = self.winfo_rooty() + (self.winfo_height() // 3) - (toast.winfo_height() // 2)
        toast.geometry(f"+{x}+{y}")
        self.after(duration_ms, toast.destroy)

    def _show_discard_pile(self, player):
        """弹出窗口展示玩家的弃牌堆（单列列表）。"""
        top = tk.Toplevel(self)
        top.title(f"{player.name} 的弃牌堆")
        top.geometry("360x400")
        top.transient(self)
        top.grab_set()

        top.config(bg=UI_THEME["bg_main"])
        title = tk.Label(top, text=f"{player.name} 的弃牌堆（{len(player.card_dis)} 张）",
                         font=("Microsoft YaHei", 13, "bold"),
                         bg=UI_THEME["bg_main"], fg=UI_THEME["text_primary"])
        title.pack(pady=(10, 5))

        # 滚动区域
        outer = tk.Frame(top, bg=UI_THEME["bg_main"])
        outer.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        canvas = tk.Canvas(outer, highlightthickness=0, bg=UI_THEME["bg_panel"])
        scrollbar = tk.Scrollbar(outer, orient=tk.VERTICAL, command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        inner = tk.Frame(canvas, bg=UI_THEME["bg_panel"])
        canvas.create_window((0, 0), window=inner, anchor="nw")

        # 单列布局（从最新到最旧）
        card_dis = list(player.card_dis)
        if not card_dis:
            empty_label = tk.Label(inner, text="弃牌堆为空", font=("Microsoft YaHei", 11),
                                   fg=UI_THEME["text_muted"], bg=UI_THEME["bg_panel"])
            empty_label.pack(pady=20)
        else:
            for card in reversed(card_dis):
                cost_str = str(getattr(card, "cost", "?"))
                name = getattr(card, "name", "未知")
                text = f"{name} ({cost_str})"
                lbl = tk.Label(inner, text=text, font=("Microsoft YaHei", 10),
                               bg=UI_THEME["bg_main"], fg=UI_THEME["text_primary"], anchor="w",
                               padx=8, pady=4, relief=tk.RIDGE, bd=1)
                lbl.pack(fill=tk.X, pady=2)

        inner.update_idletasks()
        canvas.config(scrollregion=canvas.bbox("all"))

        # 关闭按钮
        tk.Button(top, text="关闭", command=top.destroy, font=("Microsoft YaHei", 10),
                  bg=UI_THEME["btn_secondary_bg"], fg=UI_THEME["btn_secondary_fg"],
                  activebackground=UI_THEME["btn_secondary_active"], relief=tk.RAISED, bd=1).pack(pady=(5, 10))

    def _on_gameover(self, winner_name: Optional[str]):
        """游戏结束回调（委托给 GameLoopController）。"""
        self.game_loop_controller.on_gameover(winner_name)

    def _on_disconnect(self):
        """对手断开连接时安全退出到主菜单（委托给 GameLoopController）。"""
        self.game_loop_controller.on_disconnect()



# ------------------------------------------------------------------
# 为 BattleFrame 动态生成访问 BattleState 的属性委托。
# 这样旧代码（renderers / 测试）仍可像访问 frame 属性一样读写状态，
# 同时状态实际集中存放在 frame.state 中。
# ------------------------------------------------------------------
_STATE_ATTRS = [
    "selected_card_idx", "selected_card", "valid_targets",
    "_tooltip", "_tooltip_source",
    "_game_thread",
    "_targeting_source_minion", "_current_targeting_mode", "_in_targeting_mode",
    "_targeting_valid_targets", "_targeting_on_confirm", "_targeting_on_cancel",
    "_in_sacrifice_mode", "_sacrifice_candidates", "_selected_sacrifices",
    "_sacrifice_required", "_sacrifice_serial", "_sacrifice_card", "_sacrifice_active",
    "_pending_sacrifices",
    "_dragging_card", "_dragging_serial", "_drag_start_x", "_drag_start_y", "_drag_label",
    "cell_size", "board_offset_x", "board_offset_y",
    "_prev_hand_card_ids", "_prev_res_values", "_last_discarded_info",
    "_history_phase", "_history_action_counter", "_recent_events",
    "_mulligan_overlay", "_mulligan_player", "_mulligan_selected_indices", "_mulligan_waiting_remote",
    "_reveal_listeners_registered", "_reveal_queue", "_is_revealing",
    "_is_playing_card", "_is_belling", "_is_braking",
    "_minion_image_refs", "_tile_image_refs", "_mineral_buttons",
]


def _make_state_property(name: str):
    def getter(self):
        return getattr(self.state, name)

    def setter(self, value):
        setattr(self.state, name, value)

    return property(getter, setter)


for _attr in _STATE_ATTRS:
    setattr(BattleFrame, _attr, _make_state_property(_attr))
