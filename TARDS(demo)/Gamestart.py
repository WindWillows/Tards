#!/usr/bin/env python3
"""
Tards 可视化客户端 (Tkinter) + 联机对战
支持：卡组构筑与保存、IP 直连对战、信息不透明。
"""

import os

# ------------------------------------------------------------------
# 自动依赖检查与安装（首次运行时）
# ------------------------------------------------------------------
def _ensure_dependencies():
    """检查核心依赖，缺失时自动调用 pip 安装。"""
    import importlib.util
    import subprocess

    deps = [
        ("PIL", "Pillow"),          # 卡牌图像渲染
    ]
    missing = []
    for module, package in deps:
        if importlib.util.find_spec(module) is None:
            missing.append(package)
    if missing:
        print(f"[首次启动] 检测到缺失依赖: {', '.join(missing)}")
        print("正在自动安装，请稍候...")
        try:
            subprocess.check_call(
                [sys.executable, "-m", "pip", "install", *missing],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.STDOUT,
            )
            print("依赖安装完成，正在启动...\n")
        except Exception as e:
            print(f"自动安装失败: {e}")
            print("请手动运行: pip install " + " ".join(missing))
            input("按回车键退出...")
            sys.exit(1)

_ensure_dependencies()
import random
import re
import socket
import sys
import threading
import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk
from typing import Any, Callable, Dict, List, Optional

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
from tards.constants import EVENT_DISCARDED, EVENT_MILLED, EVENT_CARD_PLAYED
from tards.assets import get_asset_manager
from tards.card_db import DEFAULT_REGISTRY, Pack, CardType, Rarity
from tards.deck import Deck
from tards.deck_io import list_saved_decks, load_deck, save_deck
from tards.feedback import (
    create_feedback,
    send_feedback,
    save_feedback_local,
    load_feedback_config,
    save_feedback_config,
)
try:
    from PIL import Image, ImageDraw, ImageTk
    _PIL_AVAILABLE = True
except Exception:
    _PIL_AVAILABLE = False

from tards.game_logger import GameLogger
from tards.net_game import NetworkDuel
from tards.targeting import (
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
from gui.battle.input_controller import InputController
from gui.dialogs import (
    SacrificeDialog,
    DiscoverDialog,
    ChoiceDialog,
    EffectTargetDialog,
    FeedbackDialog,
    NumericChoiceDialog,
)
from gui.tooltip import Tooltip
from local_duel import LocalDuel
from gui.menu_frame import MenuFrame
from gui.deck_builder_frame import DeckBuilderFrame
from gui.lobby_frame import LobbyFrame

# =============================================================================
# 卡牌关联关系（自动生成 + 手动补充）
# =============================================================================
_CARD_RELATIONS: dict[str, list[str]] = {}

def _build_card_relations():
    """从卡牌描述中提取引号内的卡牌名，构建关联关系映射。"""
    import re
    pattern = re.compile(r'[""""](.+?)[""""]')
    for card in DEFAULT_REGISTRY.all_cards():
        desc = getattr(card, "description", "") or ""
        related = set()
        for m in pattern.finditer(desc):
            name = m.group(1)
            if name != card.name and DEFAULT_REGISTRY.get(name):
                related.add(name)
        if related:
            _CARD_RELATIONS[card.name] = list(related)
    # 手动补充 description 中未明确提及的关系
    manual = {
        "铁心": ["环丁二烯", "配体"],
        "血渍怀表": ["钝锈指针"],
        "钝锈指针": ["含垢齿轮"],
        "烈焰人": ["烈焰粉"],
        "凋零骷髅": ["凋零骷髅头"],
        "猪灵弓兵": ["光灵箭"],
        "蜘蛛": ["蜘蛛眼"],
        "僵尸村民": ["金苹果"],
        "书": ["附魔书"],
        "附魔台": ["附魔书"],
        "饵钓": ["书"],
        "复制技术": ["轰击", "制导技术"],
        "制导技术": ["矢量炮", "珍珠塔"],
        "轰击": ["TNT炮"],
        "遗迹机关": ["绊线钩"],
        "保卫要塞": ["蠹虫"],
        "虫蚀石头": ["蠹虫"],
        "蠹虫": ["蠹虫"],
        "蛀蚀": ["蠹虫"],
        "高山": ["铁锭"],
        "松鼠球": ["松鼠"],
        "松鼠罐": ["松鼠"],
        "13号孩子": ["13号"],
        "13号": ["13号孩子"],
        "河狸": ["河坝"],
        "猹": ["西瓜"],
        "奇怪的蛹": ["巨蛾"],
        "石钱子": ["断尾"],
        "断尾": ["石钱子"],
        "蚁穴": ["兵蚁"],
        "松鼠瓶": ["松鼠"],
        "树洞": ["松鼠"],
        "骨王": ["骨王之赏", "骨王之惠"],
        "蜡烛": ["烛烟"],
        "屠刀": ["松鼠"],
        "林鼠": ["松鼠"],
    }
    for name, rels in manual.items():
        existing = set(_CARD_RELATIONS.get(name, []))
        existing.update(rels)
        _CARD_RELATIONS[name] = list(existing)

_build_card_relations()

# 全局事件：用于后台游戏线程通知 GUI 刷新
import threading
gui_refresh_event = threading.Event()



# ========== 主应用 ==========
class TardsApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Tards")
        self.root.geometry("1200x800")
        self._current_frame: Optional[tk.Frame] = None
        self.show_menu()

    def _switch_frame(self, frame_class, **kwargs):
        if self._current_frame:
            self._current_frame.destroy()
        self._current_frame = frame_class(self.root, self, **kwargs)
        self._current_frame.pack(fill=tk.BOTH, expand=True)

    def show_menu(self):
        self._switch_frame(MenuFrame)

    def show_deck_builder(self, deck_name: Optional[str] = None):
        self._switch_frame(DeckBuilderFrame, deck_name=deck_name)

    def show_lobby(self, is_host: bool):
        self._switch_frame(LobbyFrame, is_host=is_host)

    def start_battle(self, duel: NetworkDuel, local_player: Player, opponent: Player):
        self._switch_frame(BattleFrame, duel=duel, local_player=local_player, opponent=opponent)

    def start_local_battle(self, duel: LocalDuel, local_player: Player, opponent: Player):
        self._switch_frame(BattleFrame, duel=duel, local_player=local_player, opponent=opponent)


# ========== 主菜单 ==========
# ========== 卡组构筑 ==========
# ========== 联机大厅 ==========
# 虚张声势功能已注释（BluffDialog）
# class BluffDialog(tk.Toplevel):
#     def __init__(self, parent, card_name: str, on_choice: Callable[[bool], None]):
#         super().__init__(parent)
#         self.title("阴谋激活")
#         self.geometry("300x150")
#         self.on_choice = on_choice
#         self.resizable(False, False)
#         self.transient(parent)
#         self.grab_set()
#         self.protocol("WM_DELETE_WINDOW", lambda: self._choose(False))
#         tk.Label(self, text=f"[{card_name}]\n选择激活方式", font=("Microsoft YaHei", 12)).pack(pady=10)
#         btn_frame = tk.Frame(self)
#         btn_frame.pack(pady=10)
#         tk.Button(btn_frame, text="真正激活", width=10, font=("Microsoft YaHei", 10, "bold"),
#                   bg="#e3f2fd", activebackground="#bbdefb",
#                   command=lambda: self._choose(True)).pack(side=tk.LEFT, padx=5)
#         tk.Button(btn_frame, text="虚张声势", width=10, font=("Microsoft YaHei", 10),
#                   bg="#ffebee", activebackground="#ffcdd2",
#                   command=lambda: self._choose(False)).pack(side=tk.LEFT, padx=5)
#
#     def _choose(self, is_true: bool):
#         self.on_choice(is_true)
#         self.grab_release()
#         self.destroy()



# ========== 对战界面 ==========
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
        self.duel = duel
        self.local_player = local_player
        self.opponent = opponent

        self.selected_card_idx: Optional[int] = None
        self.selected_card: Optional[Any] = None
        self.valid_targets: List[Any] = []
        self._tooltip: Optional[Tooltip] = None
        self._tooltip_source: Optional[Any] = None
        self._pending_play_data: Optional[Dict[str, Any]] = None
        self._game_thread: Optional[threading.Thread] = None
        self._targeting_source_minion: Optional[Minion] = None
        self._current_targeting_mode: Optional[str] = None
        self._dragging_card = None

        # 指向模式状态（新版）
        self._in_targeting_mode: bool = False
        self._targeting_valid_targets: List[Any] = []
        self._targeting_on_confirm: Optional[Callable[[Any], None]] = None
        self._targeting_on_cancel: Optional[Callable[[], None]] = None

        # 献祭选择模式状态
        self._in_sacrifice_mode: bool = False
        self._sacrifice_candidates: List[Minion] = []
        self._selected_sacrifices: List[Minion] = []
        self._sacrifice_required: int = 0
        self._sacrifice_serial: Optional[int] = None
        self._sacrifice_card: Optional[Any] = None
        self._sacrifice_active: Optional[Any] = None

        self._dragging_serial = None
        self._drag_start_x = 0
        self._drag_start_y = 0
        self._drag_label = None

        # 棋盘尺寸（随 Canvas 大小动态调整）
        self.cell_size = self.CELL_SIZE
        self.board_offset_x = self.BOARD_OFFSET_X
        self.board_offset_y = self.BOARD_OFFSET_Y

        # 手牌/费用变化闪烁追踪
        self._prev_hand_card_ids = set()
        self._prev_res_values = {}
        self._last_discarded_info = {}  # {player_name: (card_name, color)} 上一张弃牌信息
        self._history_phase = None
        self._history_action_counter = 0

        # Mulligan（开局手牌调整）状态
        self._mulligan_overlay: Optional[tk.Frame] = None
        self._mulligan_player: Optional[Player] = None
        self._mulligan_selected_indices: set = set()
        self._mulligan_waiting_remote = False

        self._build_ui()
        self.board_renderer.draw_grid()
        self._start_game_thread()
        self._schedule_refresh()
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
        if (new_cell != self.cell_size or
            new_offset_x != self.board_offset_x or
            new_offset_y != self.board_offset_y):
            self.cell_size = new_cell
            self.board_offset_x = new_offset_x
            self.board_offset_y = new_offset_y
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
            cell_size=self.cell_size,
            board_offset_x=self.board_offset_x,
            board_offset_y=self.board_offset_y,
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

        # ===== 弃置/移除/磨牌展示面板 =====
        self.reveal_frame = tk.LabelFrame(right, text="展示", font=("Microsoft YaHei", 10),
                                          bg=UI_THEME["bg_panel"], fg=UI_THEME["text_secondary"])
        self.reveal_frame.pack(fill=tk.X, pady=(0, 5))
        self.reveal_frame.pack_forget()  # 初始隐藏
        self.reveal_canvas = tk.Canvas(self.reveal_frame, width=90, height=144, highlightthickness=0, bd=0,
                                       bg=UI_THEME["bg_panel"])
        self.reveal_canvas.pack(padx=5, pady=5)
        self.reveal_label = tk.Label(self.reveal_frame, text="", font=("Microsoft YaHei", 10),
                                     bg=UI_THEME["bg_panel"], fg=UI_THEME["text_primary"])
        self.reveal_label.pack(padx=5, pady=(0, 5))
        self._reveal_queue: list = []
        self._is_revealing = False

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
        hand_bottom_row = tk.Frame(right, bg=UI_THEME["bg_main"])
        hand_bottom_row.pack(fill=tk.X, pady=5)

        # 左侧：附加手牌槽（约占 55%）
        self.extra_hand_frame = tk.LabelFrame(hand_bottom_row, text="附加手牌槽",
                                              bg=UI_THEME["bg_panel"], fg=UI_THEME["text_secondary"])
        self.extra_hand_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
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

        # 右侧：当前玩家资源面板（约占 45%，随 current_player 切换）
        self.res_panel = tk.LabelFrame(hand_bottom_row, text="当前资源",
                                       bg=UI_THEME["bg_panel"], fg=UI_THEME["text_secondary"])
        self.res_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(5, 0))
        res_row1 = tk.Frame(self.res_panel, bg=UI_THEME["bg_panel"])
        res_row1.pack(fill=tk.X, padx=5, pady=(5, 2))
        self.res_t_label = tk.Label(res_row1, text="T: -/-", font=("Microsoft YaHei", 10, "bold"),
                                    bg=UI_THEME["bg_panel"], fg=UI_THEME["res_t"])
        self.res_t_label.pack(side=tk.LEFT, padx=(0, 8))
        self.res_c_label = tk.Label(res_row1, text="C: -/-", font=("Microsoft YaHei", 10, "bold"),
                                    bg=UI_THEME["bg_panel"], fg=UI_THEME["res_c"])
        self.res_c_label.pack(side=tk.LEFT, padx=(0, 8))
        self.res_b_label = tk.Label(res_row1, text="B: 0", font=("Microsoft YaHei", 10, "bold"),
                                    bg=UI_THEME["bg_panel"], fg=UI_THEME["res_b"])
        self.res_b_label.pack(side=tk.LEFT, padx=(0, 8))
        self.res_sacrifice_label = tk.Label(res_row1, text="可献祭: 0", font=("Microsoft YaHei", 9),
                                            bg=UI_THEME["bg_panel"], fg=UI_THEME["res_b"])
        self.res_sacrifice_label.pack(side=tk.LEFT, padx=(0, 8))
        self.res_s_label = tk.Label(res_row1, text="S: 0", font=("Microsoft YaHei", 10, "bold"),
                                    bg=UI_THEME["bg_panel"], fg=UI_THEME["res_s"])
        self.res_s_label.pack(side=tk.LEFT, padx=(0, 8))
        res_row2 = tk.Frame(self.res_panel, bg=UI_THEME["bg_panel"])
        res_row2.pack(fill=tk.X, padx=5, pady=(0, 5))
        self.res_deck_label = tk.Label(res_row2, text="抽牌堆:0", font=("Microsoft YaHei", 9),
                                       bg=UI_THEME["bg_panel"], fg=UI_THEME["text_secondary"])
        self.res_deck_label.pack(side=tk.LEFT, padx=(0, 8))
        self.res_dis_label = tk.Label(res_row2, text="弃牌堆:0", font=("Microsoft YaHei", 9),
                                      bg=UI_THEME["bg_panel"], fg=UI_THEME["text_secondary"])
        self.res_dis_label.pack(side=tk.LEFT, padx=(0, 8))

        res_row3 = tk.Frame(self.res_panel, bg=UI_THEME["bg_panel"])
        res_row3.pack(fill=tk.X, padx=5, pady=(0, 5))
        self.res_conspiracy_label = tk.Label(res_row3, text="阴谋序列:0", font=("Microsoft YaHei", 9),
                                             bg=UI_THEME["bg_panel"], fg=UI_THEME["text_secondary"])
        self.res_conspiracy_label.pack(side=tk.LEFT, padx=(0, 8))

        # 按钮区分组：主操作 / 兑换 / 系统
        btn_frame = tk.Frame(right, bg=UI_THEME["bg_main"])
        btn_frame.pack(fill=tk.X, pady=5)

        # 主操作组（最醒目）
        main_grp = tk.LabelFrame(btn_frame, text="操作", bg=UI_THEME["bg_panel"], fg=UI_THEME["text_secondary"],
                                  font=("Microsoft YaHei", 8), padx=4, pady=2)
        main_grp.pack(side=tk.LEFT, padx=(0, 6))
        self.bell_btn = tk.Button(main_grp, text="拍铃", bg=UI_THEME["btn_warning_bg"], fg=UI_THEME["btn_warning_fg"],
                                   activebackground=UI_THEME["btn_warning_active"],
                                   font=("Microsoft YaHei", 10, "bold"),
                                   width=6, height=1, relief=tk.RAISED, bd=1)
        self.bell_btn.pack(side=tk.LEFT, padx=2)
        self.bell_btn.bind("<Double-Button-1>", lambda e: self._on_bell())
        self.brake_btn = tk.Button(main_grp, text="拉闸", bg=UI_THEME["btn_secondary_bg"], fg=UI_THEME["btn_secondary_fg"],
                                    activebackground=UI_THEME["btn_secondary_active"],
                                    font=("Microsoft YaHei", 10, "bold"),
                                    width=6, height=1, relief=tk.RAISED, bd=1)
        self.brake_btn.pack(side=tk.LEFT, padx=2)
        self.brake_btn.bind("<Double-Button-1>", lambda e: self._on_brake())

        # 兑换组（中等）
        ex_grp = tk.LabelFrame(btn_frame, text="兑换", bg=UI_THEME["bg_panel"], fg=UI_THEME["text_secondary"],
                                font=("Microsoft YaHei", 8), padx=4, pady=2)
        ex_grp.pack(side=tk.LEFT, padx=(0, 6))
        self.exchange_btn = tk.Button(ex_grp, text="矿物", bg="#fef3c7", fg=UI_THEME["res_mineral"],
                                       activebackground="#fde68a", font=("Microsoft YaHei", 9),
                                       width=5, relief=tk.RAISED, bd=1, command=self._toggle_mineral_bar)
        self.exchange_btn.pack(side=tk.LEFT, padx=2)
        self.exchange_squirrel_btn = tk.Button(ex_grp, text="松鼠", bg="#fef3c7", fg=UI_THEME["res_mineral"],
                                                activebackground="#fde68a", font=("Microsoft YaHei", 9),
                                                width=5, relief=tk.RAISED, bd=1, command=self._on_exchange_squirrel)
        self.exchange_squirrel_btn.pack(side=tk.LEFT, padx=2)
        self.squirrel_draw_var = tk.BooleanVar(value=False)
        self.squirrel_draw_cb = tk.Checkbutton(ex_grp, text="抽", bg=UI_THEME["bg_panel"], fg=UI_THEME["res_mineral"],
                                                variable=self.squirrel_draw_var,
                                                command=self._on_toggle_squirrel_draw,
                                                font=("Microsoft YaHei", 9), selectcolor=UI_THEME["bg_panel"])
        self.squirrel_draw_cb.pack(side=tk.LEFT, padx=2)

        # 矿物展开面板（点击"矿物"后展开，显示4个快捷兑换按钮）
        self.mineral_bar = tk.Frame(right, bg=UI_THEME["bg_main"])
        self._mineral_buttons: Dict[str, tk.Button] = {}
        mineral_specs = [
            ("I", "铁锭"),
            ("G", "金锭"),
            ("D", "钻石"),
            ("M", "青金石"),
        ]
        for mtype, mname in mineral_specs:
            btn = tk.Button(self.mineral_bar, text=mname, font=("Microsoft YaHei", 9),
                            width=6, bg="#fef3c7", fg=UI_THEME["res_mineral"],
                            activebackground="#fde68a", relief=tk.RAISED, bd=1,
                            command=lambda n=mname: self._do_exchange_mineral(n))
            btn.pack(side=tk.LEFT, padx=3)
            self._mineral_buttons[mtype] = btn

        # 系统组（弱化）
        sys_grp = tk.Frame(btn_frame, bg=UI_THEME["bg_main"])
        sys_grp.pack(side=tk.LEFT)
        self.cancel_btn = tk.Button(sys_grp, text="取消", bg=UI_THEME["btn_secondary_bg"], fg=UI_THEME["btn_secondary_fg"],
                                     activebackground=UI_THEME["btn_secondary_active"],
                                     font=("Microsoft YaHei", 9), relief=tk.RAISED, bd=1,
                                     width=5, command=self._on_cancel)
        self.cancel_btn.pack(side=tk.LEFT, padx=2)
        self.terminate_btn = tk.Button(sys_grp, text="终止", bg=UI_THEME["btn_danger_bg"], fg=UI_THEME["btn_danger_fg"],
                                        activebackground=UI_THEME["btn_danger_active"],
                                        font=("Microsoft YaHei", 9), relief=tk.RAISED, bd=1,
                                        width=5, command=self._on_terminate_game)
        self.terminate_btn.pack(side=tk.LEFT, padx=2)
        self.feedback_btn = tk.Button(sys_grp, text="反馈", bg=UI_THEME["btn_secondary_bg"], fg=UI_THEME["btn_secondary_fg"],
                                       activebackground=UI_THEME["btn_secondary_active"],
                                       font=("Microsoft YaHei", 9), relief=tk.RAISED, bd=1,
                                       width=5, command=self._on_feedback)
        self.feedback_btn.pack(side=tk.LEFT, padx=2)

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




    def _add_history(self, text: str, is_play: bool = False):
        """添加一条操作历史记录。
        
        is_play=True 表示这是一张实际打出的牌（打出、兑换等），会在 action phase 内计数序号。
        拍铃会重置计数器，标志新一轮次的开始。
        """
        if not self.duel.game:
            return
        turn = self.duel.game.current_turn
        phase = self.duel.game.current_phase
        phase_map = {"draw": "抽牌", "action": "出牌", "resolve": "结算", "start": "开始", "end": "结束"}
        phase_text = phase_map.get(phase, phase)

        # 进入新的 phase 时重置计数器
        if phase != self._history_phase:
            self._history_phase = phase
            if phase == "action":
                self._history_action_counter = 0

        # 拍铃标志新一轮次开始，重置计数器
        if text == "拍铃":
            self._history_action_counter = 0

        player_name = self.duel.game.current_player.name if self.duel.game.current_player else "?"

        if is_play and phase == "action":
            self._history_action_counter += 1
            prefix = f"{player_name}·#{self._history_action_counter} "
        else:
            prefix = f"{player_name} "

        entry = f"回合{turn} [{phase_text}] {prefix}{text}"
        self.history_list.insert(tk.END, entry)
        if self.history_list.size() > 50:
            self.history_list.delete(0)
        self.history_list.see(tk.END)

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
        active = self.local_player if isinstance(self.duel, NetworkDuel) else game.current_player
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
                flash = id(card) not in self._prev_hand_card_ids
                self._render_hand_card(zone["inner"], card, idx, serial, active, card_type_colors, am, cw, ch, flash=flash)
                current_card_ids.add(id(card))
                serial += 1

        self._prev_hand_card_ids = current_card_ids

    # ========== Mulligan（开局手牌调整）UI ==========
    def _show_mulligan(self, player: Player):
        """显示开局手牌调整界面。"""
        if self._mulligan_overlay:
            self._hide_mulligan()
        self._mulligan_player = player
        self._mulligan_selected_indices = set()
        self._mulligan_waiting_remote = False

        # 覆盖层
        overlay = tk.Frame(self, bg=UI_THEME["text_primary"])
        overlay.place(relx=0, rely=0, relwidth=1, relheight=1)
        self._mulligan_overlay = overlay

        # 中央面板
        panel = tk.Frame(overlay, bg=UI_THEME["bg_panel"], bd=2, relief=tk.RIDGE)
        panel.place(relx=0.5, rely=0.5, anchor="center", width=700, height=400)

        # 标题
        title_text = f"调整初始手牌 - {player.name}"
        tk.Label(panel, text=title_text, font=("Microsoft YaHei", 16, "bold"),
                 bg=UI_THEME["bg_panel"], fg=UI_THEME["text_primary"]).pack(pady=(15, 5))
        tk.Label(panel, text="点击卡牌选择要替换的牌，确认后洗回牌库并重新抽取",
                 font=("Microsoft YaHei", 10), bg=UI_THEME["bg_panel"],
                 fg=UI_THEME["text_secondary"]).pack(pady=(0, 10))

        # 手牌区
        hand_frame = tk.Frame(panel, bg=UI_THEME["bg_panel"])
        hand_frame.pack(pady=10)
        self._mulligan_hand_frame = hand_frame

        self._refresh_mulligan_cards()

        # 提示与按钮区
        self._mulligan_bottom_frame = tk.Frame(panel, bg=UI_THEME["bg_panel"])
        self._mulligan_bottom_frame.pack(pady=10)

        self._mulligan_hint_label = tk.Label(self._mulligan_bottom_frame, text="",
                                             font=("Microsoft YaHei", 10), bg=UI_THEME["bg_panel"],
                                             fg=UI_THEME["accent"])
        self._mulligan_hint_label.pack(pady=(0, 5))

        self._mulligan_confirm_btn = tk.Button(
            self._mulligan_bottom_frame, text="确认替换",
            font=("Microsoft YaHei", 12), width=12,
            bg=UI_THEME["btn_primary_bg"], fg=UI_THEME["btn_primary_fg"],
            activebackground=UI_THEME["btn_primary_active"], relief=tk.RAISED, bd=2,
            command=self._on_mulligan_confirm,
        )
        self._mulligan_confirm_btn.pack(pady=5)

    def _refresh_mulligan_cards(self):
        """刷新 mulligan 手牌显示。"""
        if not self._mulligan_overlay or not self._mulligan_player:
            return
        frame = self._mulligan_hand_frame
        for w in list(frame.winfo_children()):
            w.destroy()

        from tards.cards import MinionCard as MC, Strategy as ST, Conspiracy as CO, MineralCard as MI
        card_type_colors = {MC: "#eff6ff", ST: "#f0fdf4", CO: "#faf5ff", MI: "#fefce8"}
        am = get_asset_manager()
        cw = self.HAND_CARD_WIDTH
        ch = self.HAND_CARD_HEIGHT

        for i, card in enumerate(self._mulligan_player.card_hand):
            selected = i in self._mulligan_selected_indices
            self._render_mulligan_card(frame, card, i, selected, card_type_colors, am, cw, ch)

    def _render_mulligan_card(self, parent, card, idx, selected, card_type_colors, am, cw, ch):
        """渲染单张 mulligan 卡牌（委托给 CardRenderer）。"""
        self.card_renderer.render_mulligan_card(parent, card, idx, selected, cw, ch)

    def _on_mulligan_card_click(self, idx: int):
        """切换 mulligan 卡牌选中状态。"""
        if idx in self._mulligan_selected_indices:
            self._mulligan_selected_indices.remove(idx)
        else:
            self._mulligan_selected_indices.add(idx)
        self._refresh_mulligan_cards()

    def _on_mulligan_confirm(self):
        """确认 mulligan 选择。"""
        if not self._mulligan_overlay:
            return
        indices = sorted(self._mulligan_selected_indices)
        if isinstance(self.duel, NetworkDuel):
            self._mulligan_waiting_remote = True
            self._mulligan_confirm_btn.config(state=tk.DISABLED, text="等待对手调整...")
            self._mulligan_hint_label.config(text="已提交选择，等待对手完成调整...")
            self.duel.submit_local_mulligan(indices)
        else:
            self.duel.submit_local_mulligan(indices)
            self._hide_mulligan()

    def _hide_mulligan(self):
        """隐藏 mulligan 界面。"""
        if self._mulligan_overlay:
            self._mulligan_overlay.destroy()
            self._mulligan_overlay = None
        self._mulligan_player = None
        self._mulligan_selected_indices = set()
        self._mulligan_waiting_remote = False


    def _render_info(self):
        """刷新玩家信息与资源面板（委托给 InfoRenderer）。"""
        self.info_renderer.render()


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



    def _refresh_mineral_bar(self):
        """根据当前玩家资源刷新4个矿物按钮的可用状态。"""
        active = self.duel.game and self.duel.game.current_player
        if not active:
            for btn in self._mineral_buttons.values():
                btn.config(state=tk.DISABLED, bg=UI_THEME["btn_secondary_active"], fg=UI_THEME["text_muted"])
            return

        from tards.card_db import Pack
        can_exchange = active.immersion_points.get(Pack.DISCRETE, 0) >= 1

        for mtype, btn in self._mineral_buttons.items():
            target_name = None
            for name, card_def in DEFAULT_REGISTRY._cards.items():
                if card_def.card_type == CardType.MINERAL and card_def.mineral_type == mtype:
                    target_name = name
                    break
            if not target_name or not can_exchange:
                btn.config(state=tk.DISABLED, bg=UI_THEME["btn_secondary_active"], fg=UI_THEME["text_muted"])
                continue
            tmp_card = DEFAULT_REGISTRY.get(target_name).to_game_card(active)
            if tmp_card.exchange_cost.can_afford(active):
                btn.config(state=tk.NORMAL, bg="#fef3c7", fg=UI_THEME["res_mineral"])
            else:
                btn.config(state=tk.DISABLED, bg=UI_THEME["btn_secondary_active"], fg=UI_THEME["text_muted"])

    def _do_exchange_mineral(self, name: str) -> None:
        """直接兑换指定名称的矿物，收起展开面板。"""
        active = self.duel.game and self.duel.game.current_player
        if not active:
            return
        if isinstance(self.duel, NetworkDuel) and active != self.local_player:
            return
        self.duel.submit_local_action({"type": "exchange", "card_name": name})
        self._add_history(f"兑换矿物 [{name}]", is_play=True)
        self.hint_label.config(text=f"已兑换 {name}")
        self.after(1500, self._reset_guide_hint)
        # 收起展开面板
        if self.mineral_bar.winfo_ismapped():
            self.mineral_bar.pack_forget()
            self.exchange_btn.config(bg="#fef3c7")


    def _on_toggle_squirrel_draw(self):
        active = self.duel.game and self.duel.game.current_player
        if not active:
            return
        if isinstance(self.duel, NetworkDuel) and active != self.local_player:
            return
        active.squirrel_draw_enabled = self.squirrel_draw_var.get()
        state = "开启" if active.squirrel_draw_enabled else "关闭"
        print(f"  {active.name} 抽松鼠选项已{state}")

    def _on_exchange_squirrel(self):
        active = self.duel.game and self.duel.game.current_player
        if not active:
            return
        if isinstance(self.duel, NetworkDuel) and active != self.local_player:
            return
        from tards.card_db import Pack
        if active.immersion_points.get(Pack.UNDERWORLD, 0) < 2:
            messagebox.showinfo("兑换松鼠", "你需要至少2级冥刻沉浸度才能兑换松鼠")
            return
        if active.squirrel_exchanged_this_turn:
            messagebox.showinfo("兑换松鼠", "本回合已兑换过松鼠")
            return
        if not active.squirrel_deck:
            messagebox.showinfo("兑换松鼠", "松鼠牌堆已空")
            return
        if active.t_point < 1:
            messagebox.showinfo("兑换松鼠", "T点不足（需要1T）")
            return
        self.duel.submit_local_action({"type": "exchange_squirrel"})
        self._add_history("兑换松鼠", is_play=True)

    def _on_exchange_mineral(self, mineral_type: str):
        """按快捷键直接兑换指定矿物（I/G/D/M）。"""
        active = self.duel.game and self.duel.game.current_player
        if not active:
            return
        if isinstance(self.duel, NetworkDuel) and active != self.local_player:
            return
        from tards.card_db import Pack
        if active.immersion_points.get(Pack.DISCRETE, 0) < 1:
            messagebox.showinfo("兑换矿物", "你没有离散沉浸度，无法兑换矿物")
            return

        # 查找对应 mineral_type 的可兑换矿物
        target_name = None
        for name, card_def in DEFAULT_REGISTRY._cards.items():
            if card_def.card_type == CardType.MINERAL and card_def.mineral_type == mineral_type:
                tmp_card = card_def.to_game_card(active)
                if tmp_card.exchange_cost.can_afford(active):
                    target_name = name
                    break

        if not target_name:
            mineral_names = {"I": "铁锭", "G": "金锭", "D": "钻石", "M": "青金石"}
            messagebox.showinfo("兑换矿物", f"当前无法兑换{mineral_names.get(mineral_type, mineral_type)}")
            return

        self._do_exchange_mineral(target_name)

    def _clear_selection(self):
        self.selected_card_idx = None
        self.selected_card = None
        self.valid_targets = []
        self._pending_sacrifices = []
        self._render_hand()
        self._render_board()

    def _schedule_refresh(self):
        try:
            self._try_refresh()
        except Exception as e:
            print(f"[_schedule_refresh] 异常: {e}")
            import traceback
            traceback.print_exc()
        try:
            self._try_show_reveal()
        except Exception as e:
            print(f"[_schedule_refresh] _try_show_reveal 异常: {e}")
            import traceback
            traceback.print_exc()
        self.after(200, self._schedule_refresh)

    def _try_refresh(self):
        try:
            # 注册弃置/移除/磨牌展示监听器（只需一次）
            if not getattr(self, '_reveal_listeners_registered', False):
                if self.duel and getattr(self.duel, 'game', None):
                    self._register_reveal_listeners()
                    self._reveal_listeners_registered = True

            # 网络对局：每 200ms 无条件刷新，确保对手操作可见
            need_refresh = gui_refresh_event.is_set() or isinstance(self.duel, NetworkDuel)
            if need_refresh:
                gui_refresh_event.clear()
                try:
                    self._render_info()
                except Exception as e:
                    print(f"[_try_refresh] _render_info 异常: {e}")
                    import traceback
                    traceback.print_exc()
                try:
                    self._render_board()
                except Exception as e:
                    print(f"[_try_refresh] _render_board 异常: {e}")
                    import traceback
                    traceback.print_exc()
                try:
                    self._render_hand()
                except Exception as e:
                    print(f"[_try_refresh] _render_hand 异常: {e}")
                    import traceback
                    traceback.print_exc()
                if self.duel.game:
                    active = self.duel.game.current_player
                    if not active:
                        self.hint_label.config(text="游戏加载中...")
                    elif isinstance(self.duel, NetworkDuel):
                        if active == self.local_player:
                            self.hint_label.config(text="轮到你的行动")
                        else:
                            self.hint_label.config(text=f"等待 {active.name} 行动...")
                    else:
                        self.hint_label.config(text=f"轮到 {active.name} 行动")
        except Exception as e:
            print(f"[_try_refresh] 外层异常: {e}")
            import traceback
            traceback.print_exc()
        # Mulligan 结束后自动隐藏覆盖层
        if self._mulligan_overlay and self.duel.game and self.duel.game.current_turn > 0:
            self._hide_mulligan()

        if self.duel.game and self.duel.game.current_turn > 0:
            phase_map = {
                "draw": "抽牌阶段",
                "action": "出牌阶段",
                "resolve": "结算阶段",
                "start": "结算阶段开始",
                "end": "结算阶段结束",
            }
            phase_text = phase_map.get(self.duel.game.current_phase, self.duel.game.current_phase or "")
            turn = self.duel.game.current_turn
            phase = self.duel.game.current_phase
            if phase == "resolve":
                self.phase_label.config(text=f"回合 {turn} | {phase_text}", bg=UI_THEME["btn_danger_bg"], fg=UI_THEME["btn_danger_fg"], font=("Microsoft YaHei", 16, "bold"))
            elif phase == "action":
                self.phase_label.config(text=f"回合 {turn} | {phase_text}", bg="#dcfce7", fg=UI_THEME["success_dark"], font=("Microsoft YaHei", 14, "bold"))
            else:
                self.phase_label.config(text=f"回合 {turn} | {phase_text}", bg=UI_THEME["bg_main"], fg=UI_THEME["danger"], font=("Microsoft YaHei", 14, "bold"))
            self.app.root.title(f"Tards 对战 - 回合{turn} {phase_text}")
        else:
            self.phase_label.config(text="等待游戏开始...")
            self.app.root.title("Tards 对战 - 等待游戏开始")
        # 动态显示/隐藏沉浸度相关按钮（根据当前回合玩家）
        from tards.card_db import Pack
        if self.duel.game and self.duel.game.current_player:
            current = self.duel.game.current_player
            has_discrete = current.immersion_points.get(Pack.DISCRETE, 0) >= 1
            has_underworld = current.immersion_points.get(Pack.UNDERWORLD, 0) >= 2
            if has_discrete:
                self.exchange_btn.pack(side=tk.LEFT, padx=5)
            else:
                self.exchange_btn.pack_forget()
            # 松鼠按钮：有冥刻沉浸度时始终显示，但T点不足/已兑换/牌堆空时灰掉
            if has_underworld:
                self.exchange_squirrel_btn.pack(side=tk.LEFT, padx=5)
                can_squirrel = (current.t_point >= 1 and
                                not current.squirrel_exchanged_this_turn and
                                current.squirrel_deck)
                if can_squirrel:
                    self.exchange_squirrel_btn.config(state=tk.NORMAL, bg="#fef3c7", fg=UI_THEME["res_mineral"])
                else:
                    self.exchange_squirrel_btn.config(state=tk.DISABLED, bg=UI_THEME["btn_secondary_active"], fg=UI_THEME["text_muted"])
            else:
                self.exchange_squirrel_btn.pack_forget()
        elif self.local_player:
            # 游戏未开始时，默认显示本地玩家的按钮
            has_discrete = self.local_player.immersion_points.get(Pack.DISCRETE, 0) >= 1
            has_underworld = self.local_player.immersion_points.get(Pack.UNDERWORLD, 0) >= 2
            if has_discrete:
                self.exchange_btn.pack(side=tk.LEFT, padx=5)
            else:
                self.exchange_btn.pack_forget()
            if has_underworld:
                self.exchange_squirrel_btn.pack(side=tk.LEFT, padx=5)
                can_squirrel = (self.local_player.t_point >= 1 and
                                not self.local_player.squirrel_exchanged_this_turn and
                                self.local_player.squirrel_deck)
                if can_squirrel:
                    self.exchange_squirrel_btn.config(state=tk.NORMAL, bg="#dbeafe", fg=UI_THEME["accent_dark"])
                else:
                    self.exchange_squirrel_btn.config(state=tk.DISABLED, bg=UI_THEME["btn_secondary_active"], fg=UI_THEME["text_muted"])
            else:
                self.exchange_squirrel_btn.pack_forget()

    def _start_game_thread(self):
        # 清理上局可能遗留的全局事件，避免新游戏初期就误触发 _render_info
        gui_refresh_event.clear()
        # 清理手牌/费用闪烁追踪状态
        self._prev_hand_card_ids.clear()
        self._prev_res_values.clear()
        self._last_discarded_info.clear()
        self._history_phase = None
        self._history_action_counter = 0
        # 重置展示监听器注册标志，确保新游戏重新注册
        self._reveal_listeners_registered = False

        self.duel.local_turn_callback = lambda: gui_refresh_event.set()
        self.duel.game_over_callback = lambda winner: self.after(0, lambda: self._on_gameover(winner))
        self.duel.discover_request_callback = lambda names: self.after(0, lambda: self._show_discover(names))
        self.duel.choice_request_callback = lambda options, title: self.after(0, lambda: self._show_choice(options, title))
        self.duel.targeting_request_callback = lambda req, vt: self.after(0, lambda: self._show_targeting(req, vt))
        self.duel.mulligan_request_callback = lambda player: self.after(0, lambda: self._show_mulligan(player))
        self.local_player.sacrifice_chooser = self._make_sacrifice_chooser()
        self.opponent.sacrifice_chooser = self._make_sacrifice_chooser()

        def run():
            import time
            # 创建结构化对局日志记录器
            is_local = isinstance(self.duel, LocalDuel)

            def ui_callback(line: str):
                self.after(0, lambda l=line: self._log(l))

            logger = GameLogger.create_for_battle(ui_callback=ui_callback if is_local else None)
            self._log_path = logger.file_path
            try:
                print("[GameThread] 游戏线程启动，准备运行 duel.run_game", file=sys.stderr)
                self.duel.resolve_step_callback = lambda: (
                    gui_refresh_event.set(),
                    time.sleep(0.4),
                )
                self.duel.run_game(self.opponent, logger=logger)
                print("[GameThread] duel.run_game 已返回", file=sys.stderr)
            except Exception as e:
                import traceback
                error_msg = f"游戏线程异常: {e}\n{traceback.format_exc()}"
                print(error_msg, file=sys.stderr)
                logger.log_error(error_msg)
                self.after(0, lambda: messagebox.showerror("游戏错误", error_msg))
            finally:
                self.duel.resolve_step_callback = None
                logger.close()

        self._game_thread = threading.Thread(target=run, daemon=True)
        self._game_thread.start()







    def _move_tooltip(self, x, y):
        if self._tooltip:
            self._tooltip.move(x, y)

    def _hide_tooltip(self):
        if self._tooltip:
            self._tooltip.destroy()
            self._tooltip = None
        self._tooltip_source = None

    def _on_terminate_game(self):
        """终止当前对局并返回主菜单。日志已由 GameLogger 自动保存。"""
        if messagebox.askyesno("终止游戏", "确定要终止当前对局吗？\n日志将保存到 logs/ 目录。"):
            # 1. 标记游戏结束
            if self.duel.game:
                self.duel.game.game_over = True
            # 2. 解除 action_provider 的阻塞（ LocalDuel ）
            if hasattr(self.duel, "_local_action_event"):
                self.duel._local_action = {"type": "brake"}
                self.duel._local_action_event.set()
            # 3. 解除 discover 的阻塞
            if hasattr(self.duel, "_discover_event"):
                self.duel._discover_event.set()
            # 4. 等待线程结束
            if self._game_thread and self._game_thread.is_alive():
                self._game_thread.join(timeout=2.0)
            # 5. 返回菜单
            log_info = f"\n日志已保存到 logs/ 目录。"
            messagebox.showinfo("游戏已终止", f"对局已手动终止。{log_info}")
            if hasattr(self.duel, "close"):
                self.duel.close()
            self.app.show_menu()

    def _on_feedback(self):
        """打开反馈对话框，提交问题描述和日志到反馈服务器。"""
        player_name = self.local_player.name

        def do_submit(description: str, server_addr: str):
            host, port_str = server_addr.rsplit(":", 1)
            port = int(port_str)

            # 组装反馈数据
            entry = create_feedback(player_name, description)

            # 尝试发送到服务器
            success = send_feedback(entry, host, port, timeout=5.0)
            if success:
                messagebox.showinfo("反馈已发送", f"反馈已成功发送到 {server_addr}")
                self.hint_label.config(text=f"[反馈] 已发送到 {server_addr}", fg=UI_THEME["success"])
            else:
                # 发送失败，询问是否本地备份
                if messagebox.askyesno(
                    "发送失败",
                    f"无法连接到反馈服务器 {server_addr}\n是否保存到本地备份？",
                ):
                    path = save_feedback_local(entry)
                    messagebox.showinfo("本地备份", f"反馈已保存到:\n{path}")
                    self.hint_label.config(text=f"[反馈] 已本地备份: {path}", fg=UI_THEME["warning_dark"])
                else:
                    self.hint_label.config(text="[反馈] 发送失败，未保存", fg=UI_THEME["danger"])

        FeedbackDialog(self, player_name, do_submit)

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

    def _register_reveal_listeners(self):
        """注册弃置/移除/磨牌展示监听器（仅一次）。"""
        game = self.duel.game
        if not game:
            return
        print(f"[Reveal] 注册展示监听器到游戏 {id(game)}")

        def on_reveal_event(event):
            event_type = event.type
            card = event.get("card")
            player = event.get("player")
            print(f"[Reveal] 收到事件: {event_type}, card={getattr(card, 'name', None)}, player={getattr(player, 'name', None)}")
            if not card:
                return
            if event_type == EVENT_DISCARDED:
                label = "弃置"
                # 记录弃牌信息（蓝色）
                if player:
                    self._last_discarded_info[player.name] = (card.name, UI_THEME["accent"])
            elif event_type == EVENT_MILLED:
                label = "磨牌"
            elif event_type == "card_removed_from_deck":
                label = "移除"
            else:
                label = "展示"
            # 仅将数据放入队列，不操作 GUI（线程安全）
            self._reveal_queue.append((label, card, player))
            print(f"[Reveal] 已加入队列，当前队列长度: {len(self._reveal_queue)}")

        def on_card_played(event):
            card = event.get("card")
            player = event.get("player")
            if card and player:
                # 策略/阴谋正常打出进入弃牌堆 → 黑色
                self._last_discarded_info[player.name] = (card.name, UI_THEME["text_primary"])

        game.register_listener(EVENT_DISCARDED, on_reveal_event)
        game.register_listener(EVENT_MILLED, on_reveal_event)
        game.register_listener("card_removed_from_deck", on_reveal_event)
        game.register_listener(EVENT_CARD_PLAYED, on_card_played)

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

    def _try_show_reveal(self):
        """轮询入口：每 200ms 检查一次队列并展示下一张卡牌。"""
        if self._is_revealing:
            return
        if not self._reveal_queue:
            return
        print(f"[Reveal] _try_show_reveal: 队列长度={len(self._reveal_queue)}, _is_revealing={self._is_revealing}")
        self._show_next_reveal()

    def _queue_reveal(self, items: list):
        """将卡牌加入展示队列。

        支持两种格式：
        - 字符串列表（卡牌名称，向后兼容）
        - (label, card, player) 元组列表（事件驱动）
        """
        for item in items:
            self._reveal_queue.append(item)
        # 不立即触发展示，由 _try_show_reveal 轮询处理（线程安全）

    def _show_next_reveal(self):
        """展示队列中的下一张卡牌。"""
        try:
            print(f"[Reveal] === _show_next_reveal START ===")
            print(f"[Reveal]   queue_len={len(self._reveal_queue)}, _is_revealing={self._is_revealing}")
            print(f"[Reveal]   reveal_frame.winfo_exists={self.reveal_frame.winfo_exists()}")
            if not self._reveal_queue:
                print(f"[Reveal]   队列空，直接返回")
                self._is_revealing = False
                self.reveal_frame.pack_forget()
                return
            self._is_revealing = True
            item = self._reveal_queue.pop(0)
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
                print(f"[Reveal]   开始渲染卡牌...")
                self._render_reveal_card(self.reveal_canvas, card)
                print(f"[Reveal]   卡牌渲染完成")
            else:
                print(f"[Reveal]   card为None，清空canvas")
                self.reveal_canvas.delete("all")

            print(f"[Reveal]   设置label文本...")
            if player_name:
                self.reveal_label.config(text=f"{player_name} {label}: {name}")
            else:
                self.reveal_label.config(text=f"{label}: {name}")
            print(f"[Reveal]   label文本已设置")

            print(f"[Reveal]   调用 reveal_frame.pack()...")
            self.reveal_frame.pack(fill=tk.X, pady=(0, 5))
            print(f"[Reveal]   reveal_frame.pack() 完成")
            self.update_idletasks()
            print(f"[Reveal]   update_idletasks 后 reveal_frame.winfo_viewable={self.reveal_frame.winfo_viewable()}")
            print(f"[Reveal]   update_idletasks 后 reveal_frame.winfo_width={self.reveal_frame.winfo_width()}")
            print(f"[Reveal]   update_idletasks 后 reveal_frame.winfo_height={self.reveal_frame.winfo_height()}")
            print(f"[Reveal]   设置 after(1500, _finish_reveal)...")
            self.after(1500, self._finish_reveal)
            print(f"[Reveal] === _show_next_reveal END ===")
        except Exception as e:
            print(f"[Reveal] _show_next_reveal 异常: {e}")
            import traceback
            traceback.print_exc()
            self._is_revealing = False

    def _finish_reveal(self):
        """当前卡牌展示结束，标记为可继续（轮询会处理下一张）。"""
        print(f"[Reveal] === _finish_reveal START ===")
        self._is_revealing = False
        print(f"[Reveal]   queue_len={len(self._reveal_queue)}")
        if not self._reveal_queue:
            print(f"[Reveal]   队列空，隐藏 reveal_frame")
            self.reveal_frame.pack_forget()
            self.reveal_canvas.delete("all")
            self.reveal_label.config(text="")
        print(f"[Reveal] === _finish_reveal END ===")

    def _on_gameover(self, winner_name: Optional[str]):
        msg = f"游戏结束！胜者: {winner_name}" if winner_name else "游戏结束：平局"
        messagebox.showinfo("对战结束", msg)
        if hasattr(self.duel, "close"):
            self.duel.close()
        self.app.show_menu()


def main():
    root = tk.Tk()
    app = TardsApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
