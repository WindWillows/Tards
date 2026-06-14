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
class BattleFrame(tk.Frame):

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
        self._draw_board_grid()
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
        """处理键盘快捷键。"""
        key = event.keysym
        # Escape: 取消当前指向或清除选择
        if key == "Escape":
            self._on_cancel()
            return
        # b: 拉闸
        if key.lower() == "b":
            self._on_brake()
            return
        # space: 拍铃（或确认 mulligan）
        if key == "space":
            if self._mulligan_overlay and not self._mulligan_waiting_remote:
                self._on_mulligan_confirm()
            else:
                self._on_bell()
            return
        # Return: 确认指向选择（如果处于指向模式且只有一个合法目标）
        # 或确认献祭选择
        if key == "Return":
            if self._in_sacrifice_mode:
                self._confirm_sacrifice()
                return
            if self._in_targeting_mode and len(self._targeting_valid_targets) == 1:
                target = self._targeting_valid_targets[0]
                self._in_targeting_mode = False
                on_confirm = self._targeting_on_confirm
                self._targeting_on_confirm = None
                self._targeting_on_cancel = None
                self._targeting_valid_targets = []
                self.hint_label.config(text="", font=("Microsoft YaHei", 10), fg=UI_THEME["accent"])
                if on_confirm:
                    on_confirm(target)
            return
        # a: 自动填充所有攻击目标
        if key.lower() == "a":
            self._auto_fill_attack_targets()
            return
        # e: 自动填充所有效果目标
        if key.lower() == "e":
            self._auto_fill_effect_targets()
            return
        # s: 兑换松鼠
        if key.lower() == "s":
            self._on_exchange_squirrel()
            return
        # i/g/d/m: 直接兑换对应矿物（铁锭/金矿/钻石/青金石）
        mineral_keys = {"i": "I", "g": "G", "d": "D", "m": "M"}
        if key.lower() in mineral_keys:
            self._on_exchange_mineral(mineral_keys[key.lower()])
            return
        # 1~0: 选择对应手牌（1~9 → serial 1~9，0 → serial 10）
        # 同时支持小键盘 KP_1 ~ KP_0
        key_map = {
            "1": 1, "2": 2, "3": 3, "4": 4, "5": 5,
            "6": 6, "7": 7, "8": 8, "9": 9, "0": 10,
            "KP_1": 1, "KP_2": 2, "KP_3": 3, "KP_4": 4, "KP_5": 5,
            "KP_6": 6, "KP_7": 7, "KP_8": 8, "KP_9": 9, "KP_0": 10,
        }
        if key in key_map:
            serial = key_map[key]
            idx = serial - 1
            self._on_hand_card_click(idx)
            return

    def _auto_fill_attack_targets(self):
        """一键自动为所有能攻击的异象填充默认攻击目标。"""
        if not self.duel.game or self.duel.game.current_phase != "action":
            return
        active = self.duel.game.current_player
        if not active:
            return
        if isinstance(self.duel, NetworkDuel) and active != self.local_player:
            return
        filled = 0
        for (r, c), m in self.duel.game.board.minion_place.items():
            if m.owner != active:
                continue
            if not m.can_attack_this_turn(self.duel.game.current_turn):
                continue
            vision = m.keywords.get("视野", 0)
            multi = m.keywords.get("高频", 0)
            count = multi if isinstance(multi, int) and multi > 0 else 1
            if vision <= 0 and (not isinstance(multi, int) or multi <= 0):
                continue
            # 已有预设则跳过
            existing = getattr(m, "_pending_attack_targets", None)
            if existing and isinstance(existing, list) and len(existing) >= count:
                continue
            candidates = get_attack_target_candidates(m, self.duel.game)
            if not candidates:
                continue
            need = count - (len(existing) if existing else 0)
            selected = (existing or []) + candidates[:need]
            self.duel.submit_local_action({
                "type": "set_attack_targets",
                "pos": m.position,
                "targets": selected,
            })
            filled += 1
        if filled > 0:
            self.hint_label.config(text=f"已为 {filled} 个异象自动填充攻击目标")
            self.after(1500, self._reset_guide_hint)
        else:
            self.hint_label.config(text="没有需要填充的攻击目标")
            self.after(1000, self._reset_guide_hint)

    def _auto_fill_effect_targets(self):
        """一键自动为所有有效果预设能力的异象填充默认效果目标。"""
        if not self.duel.game or self.duel.game.current_phase != "action":
            return
        active = self.duel.game.current_player
        if not active:
            return
        if isinstance(self.duel, NetworkDuel) and active != self.local_player:
            return
        filled = 0
        for (r, c), m in self.duel.game.board.minion_place.items():
            if m.owner != active:
                continue
            scope_fn = getattr(m, '_effect_target_scope_fn', None)
            if not scope_fn:
                continue
            # 已有预设则跳过
            if getattr(m, '_pending_effect_target', None) is not None:
                continue
            candidates = scope_fn(active, self.duel.game.board)
            if not candidates:
                continue
            import random
            selected = random.choice(candidates)
            self.duel.submit_local_action({
                "type": "set_effect_target",
                "pos": m.position,
                "target": selected,
            })
            filled += 1
        if filled > 0:
            self.hint_label.config(text=f"已为 {filled} 个异象自动填充效果目标")
            self.after(1500, self._reset_guide_hint)
        else:
            self.hint_label.config(text="没有需要填充的效果目标")
            self.after(1000, self._reset_guide_hint)

    # ===== 拖拽出牌 =====
    def _on_drag_start(self, event, card, serial):
        """记录拖拽起始状态。"""
        self._dragging_card = card
        self._dragging_serial = serial
        self._drag_start_x = event.x_root
        self._drag_start_y = event.y_root

    def _on_drag_motion(self, event):
        """拖拽中显示跟随标签或卡牌缩略图。"""
        if not self._dragging_card:
            return
        if self._drag_label:
            self._drag_label.destroy()
        am = get_asset_manager()
        img = None
        asset_id = getattr(self._dragging_card, "asset_id", None)
        if asset_id:
            img = am.get_thumbnail(asset_id, 80, 110)
        if img:
            self._drag_label = tk.Label(self, image=img, bg=UI_THEME["bg_panel"], relief=tk.RIDGE, bd=1)
            self._drag_label.image = img
        else:
            name = getattr(self._dragging_card, "name", "未知")
            self._drag_label = tk.Label(
                self, text=name, bg=UI_THEME["btn_warning_bg"], fg=UI_THEME["btn_warning_fg"],
                font=("Microsoft YaHei", 10, "bold"),
                relief=tk.RIDGE, bd=1
            )
        self._drag_label.place(
            x=event.x_root - self.winfo_rootx(),
            y=event.y_root - self.winfo_rooty()
        )

    def _on_drag_release(self, event):
        """释放时判断是否在棋盘内，尝试直接出牌。"""
        if self._drag_label:
            self._drag_label.destroy()
            self._drag_label = None
        if not self._dragging_card:
            return
        # 拖拽距离过短视为点击，走正常的点击出牌流程
        dist = ((event.x_root - self._drag_start_x) ** 2 +
                (event.y_root - self._drag_start_y) ** 2) ** 0.5
        if dist < 20:
            serial = self._dragging_serial
            self._dragging_card = None
            self._dragging_serial = None
            if serial is not None:
                self._on_hand_card_click(serial - 1)
            return
        # 判断释放位置是否在棋盘内
        canvas_x = event.x_root - self.canvas.winfo_rootx() - self.board_offset_x
        canvas_y = event.y_root - self.canvas.winfo_rooty() - self.board_offset_y
        board_w = self.BOARD_COLS * self.cell_size
        board_h = self.BOARD_ROWS * self.cell_size
        if 0 <= canvas_x < board_w and 0 <= canvas_y < board_h:
            c = int(canvas_x // self.cell_size)
            display_r = int(canvas_y // self.cell_size)
            logic_r = self._logic_row(display_r)
            self._try_play_at_position(self._dragging_serial, (logic_r, c))
        self._dragging_card = None
        self._dragging_serial = None

    def _try_play_at_position(self, serial, target):
        """尝试在指定格子直接部署卡牌（仅支持无需献祭/指向的异象卡）。"""
        if not self.duel.game:
            return
        active = self.duel.game.current_player
        card = active._get_hand_card(serial) if active else None
        if card is None:
            return
        from tards.cards import MinionCard
        if not isinstance(card, MinionCard):
            self.hint_label.config(text="只能拖拽部署异象卡")
            self.after(800, self._reset_guide_hint)
            return
        if card.cost.b > 0:
            self.hint_label.config(text="需要献祭的卡牌无法拖拽部署")
            self.after(800, self._reset_guide_hint)
            return
        stages = list(getattr(card, "extra_targeting_stages", []))
        if stages:
            self.hint_label.config(text="需要指向的卡牌无法拖拽部署")
            self.after(800, self._reset_guide_hint)
            return
        if not self.duel.game.board.is_valid_deploy(target, active, card):
            self._flash_invalid_at(target)
            return
        existing = self.duel.game.board.get_minion_at(target)
        if existing and not (
            ("漂浮物" in existing.keywords and existing.owner == active) or
            ("藤蔓" in card.keywords and existing.owner == active)
        ):
            self._flash_invalid_at(target)
            return
        self._submit_play(serial, target)

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
            self._draw_board_grid()
            if self.duel.game:
                self._render_board()

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
            BattleFrame._rounded_rect(cvs, 1, 1, width - 1, h - 1, radius=5,
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

    # ------------------------------------------------------------------
    # 静态辅助：颜色与绘制
    # ------------------------------------------------------------------
    @staticmethod
    def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))  # type: ignore[return-value]

    @staticmethod
    def _rgb_to_hex(rgb: tuple[int, int, int]) -> str:
        return '#{:02x}{:02x}{:02x}'.format(*rgb)

    @classmethod
    def _interpolate_color(cls, c1: str, c2: str, t: float) -> str:
        r1, g1, b1 = cls._hex_to_rgb(c1)
        r2, g2, b2 = cls._hex_to_rgb(c2)
        return cls._rgb_to_hex((
            int(r1 + (r2 - r1) * t),
            int(g1 + (g2 - g1) * t),
            int(b1 + (b2 - b1) * t),
        ))

    @staticmethod
    def _rounded_rect(canvas: tk.Canvas, x1: int, y1: int, x2: int, y2: int,
                      radius: int, **kwargs: Any) -> int:
        """在 Canvas 上绘制圆角多边形（smooth=True 实现圆角）。"""
        points = [
            x1 + radius, y1,
            x2 - radius, y1,
            x2, y1,
            x2, y1 + radius,
            x2, y2 - radius,
            x2, y2,
            x2 - radius, y2,
            x1 + radius, y2,
            x1, y2,
            x1, y2 - radius,
            x1, y1 + radius,
            x1, y1,
        ]
        return canvas.create_polygon(points, smooth=True, **kwargs)

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
        """悬停手牌时预览合法目标位置（绿色虚线方框）。

        支持：异象卡的合法部署位置、策略卡的单指向合法目标。
        """
        if not self.duel.game:
            return
        # 与 _render_hand 保持一致：网络对局用 local_player，本地对局用 current_player
        active = self.local_player if isinstance(self.duel, NetworkDuel) else self.duel.game.current_player
        card = active._get_hand_card(serial) if active else None
        if card is None:
            return

        valid = []
        if isinstance(card, MinionCard):
            # 异象卡：合法部署位置（空位）
            valid = []
            for t in active.get_valid_targets(card):
                if isinstance(t, tuple) and self.duel.game.board.is_valid_deploy(t, active, card):
                    existing = self.duel.game.board.get_minion_at(t)
                    if existing is None or (
                        ("漂浮物" in existing.keywords and existing.owner == active) or
                        ("藤蔓" in card.keywords and existing.owner == active)
                    ):
                        valid.append(t)
        elif isinstance(card, Strategy):
            # 策略卡：单指向的合法目标（位置或异象）
            valid = [t for t in active.get_valid_targets(card)
                     if t is not None]

        for target in valid:
            if isinstance(target, tuple) and len(target) == 2:
                logic_r, c = target
                display_r = self._display_row(logic_r)
                cx = c * self.cell_size + self.cell_size // 2 + self.board_offset_x
                cy = display_r * self.cell_size + self.cell_size // 2 + self.board_offset_y
                self.canvas.create_rectangle(cx - 38, cy - 38, cx + 38, cy + 38,
                                             outline=UI_THEME["deploy_preview"], width=2, dash=(4, 4),
                                             tags="preview_hint")
            elif hasattr(target, "position") and target.position:
                logic_r, c = target.position
                display_r = self._display_row(logic_r)
                cx = c * self.cell_size + self.cell_size // 2 + self.board_offset_x
                cy = display_r * self.cell_size + self.cell_size // 2 + self.board_offset_y
                self.canvas.create_rectangle(cx - 38, cy - 38, cx + 38, cy + 38,
                                             outline=UI_THEME["deploy_preview"], width=2, dash=(4, 4),
                                             tags="preview_hint")

    def _clear_preview(self):
        """清除部署位置预览。"""
        self.canvas.delete("preview_hint")

    def _draw_board_grid(self):
        am = get_asset_manager()
        # 清理旧网格（避免 resize 时重叠绘制）
        self.canvas.delete("board_grid")
        for r in range(5):
            for c in range(5):
                self.canvas.delete(f"cell_{r}_{c}")
        self._tile_image_refs = {}

        # 半场渐变配色（从上到下）：敌方淡蓝、中立纯白、友方暖黄
        GRADIENT_STEPS = 10
        row_top_colors = {
            0: UI_THEME["board_enemy_top"],
            1: UI_THEME["board_enemy_top"],
            2: UI_THEME["board_neutral"],
            3: UI_THEME["board_friendly_top"],
            4: UI_THEME["board_friendly_top"],
        }
        row_bottom_colors = {
            0: UI_THEME["board_enemy_bottom"],
            1: UI_THEME["board_enemy_bottom"],
            2: UI_THEME["board_neutral"],
            3: UI_THEME["board_friendly_bottom"],
            4: UI_THEME["board_friendly_bottom"],
        }

        for logic_r in range(5):
            for c in range(5):
                display_r = self._display_row(logic_r)
                x1 = c * self.cell_size + self.board_offset_x
                y1 = display_r * self.cell_size + self.board_offset_y
                x2 = x1 + self.cell_size
                y2 = y1 + self.cell_size
                terrain_id = None
                if display_r in (0, 1):
                    terrain_id = "terrain_enemy"
                elif display_r == 2:
                    terrain_id = "terrain_neutral"
                elif display_r in (3, 4):
                    terrain_id = "terrain_friendly"

                # 绘制垂直渐变背景（用细条模拟）
                top_c = row_top_colors[display_r]
                bot_c = row_bottom_colors[display_r]
                step_h = self.cell_size / GRADIENT_STEPS
                for i in range(GRADIENT_STEPS):
                    t = i / GRADIENT_STEPS
                    color = self._interpolate_color(top_c, bot_c, t)
                    sy1 = int(y1 + i * step_h)
                    sy2 = int(y1 + (i + 1) * step_h)
                    self.canvas.create_rectangle(x1, sy1, x2, sy2, fill=color, outline="", tags=f"cell_{logic_r}_{c}")

                # 尝试加载地形纹理（覆盖在渐变之上，半透明）
                if terrain_id:
                    tile = am.get_board_tile(terrain_id, self.cell_size)
                    if tile:
                        self._tile_image_refs[(logic_r, c)] = tile
                        self.canvas.create_image(x1 + self.cell_size // 2, y1 + self.cell_size // 2,
                                                 image=tile, tags=f"cell_{logic_r}_{c}")

                # 格子边框（内阴影感）
                self.canvas.create_rectangle(x1, y1, x2, y2, outline=UI_THEME["board_line"], width=1, tags=f"cell_{logic_r}_{c}")

        # 列名标签（带主题色底）
        col_label_colors = UI_THEME["board_label_bg"]
        for c, name in enumerate(self.COL_NAMES):
            x1 = c * self.cell_size + self.board_offset_x
            x2 = x1 + self.cell_size
            label_y = 5 * self.cell_size + self.board_offset_y
            label_bg = col_label_colors[c % len(col_label_colors)]
            self.canvas.create_rectangle(x1, label_y, x2, label_y + 22, fill=label_bg, outline=UI_THEME["border_strong"], width=1, tags="board_grid")
            self.canvas.create_text(x1 + self.cell_size // 2, label_y + 11, text=name, anchor=tk.CENTER,
                                    font=("Microsoft YaHei", 10, "bold"), fill=UI_THEME["board_label_text"], tags="board_grid")

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

    # ------------------------------------------------------------------
    # 场上异象新版 1/2/3/4 区域绘制
    # ------------------------------------------------------------------

    def _get_minion_attack_color(self, m: "Minion") -> str:
        """返回 1 号攻击三角区域背景色。"""
        if m.current_attack > m.base_attack:
            return UI_THEME["minion_atk_boost"]
        if m.current_attack < m.base_attack:
            return UI_THEME["minion_atk_low"]
        return UI_THEME["minion_atk_eq"]

    def _get_minion_hp_color(self, m: "Minion") -> str:
        """返回 2 号 HP 三角区域背景色。"""
        if m.current_health < m.current_max_health:
            return UI_THEME["minion_hp_injured"]
        if m.current_max_health > m.base_max_health:
            return UI_THEME["minion_hp_boost"]
        return UI_THEME["minion_hp_eq"]

    def _create_minion_portrait_photo(self, size: int, color1: str, color2: str,
                                      is_enemy: bool = False, corner_leg: int = 10):
        """生成异象 3 号区域渐变图。敌方在友方视角下左下角裁掉一个小三角。"""
        if not _PIL_AVAILABLE or size <= 0:
            return None

        def _hex_to_rgb(h):
            h = h.lstrip("#")
            return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))

        c1 = _hex_to_rgb(color1)
        c2 = _hex_to_rgb(color2)

        grad = Image.new("RGB", (size, size))
        pixels = grad.load()
        max_sum = size + size - 2
        for y in range(size):
            for x in range(size):
                t = (x + y) / max_sum if max_sum > 0 else 0
                r = int(c1[0] + (c2[0] - c1[0]) * t)
                g = int(c1[1] + (c2[1] - c1[1]) * t)
                b = int(c1[2] + (c2[2] - c1[2]) * t)
                pixels[x, y] = (r, g, b)

        mask = Image.new("L", (size, size), 0)
        draw = ImageDraw.Draw(mask)
        if is_enemy:
            points = [
                (0, 0),
                (size - 1, 0),
                (size - 1, size - 1),
                (corner_leg, size - 1),
                (0, size - 1 - corner_leg),
            ]
        else:
            points = [
                (0, 0),
                (size - 1, 0),
                (size - 1, size - 1),
                (0, size - 1),
            ]
        draw.polygon(points, fill=255)

        r_band, g_band, b_band = grad.split()
        img = Image.merge("RGBA", (r_band, g_band, b_band, mask))
        return ImageTk.PhotoImage(img)

    def _draw_minion_portrait(self, canvas, cx: int, cy: int, m: "Minion",
                              x1: int, y1: int, x2: int, y2: int, tag: str,
                              is_enemy: bool = False, display_r: int = 0):
        """绘制 3 号区域：淡色渐变背景 + 异象名称，后续可替换为正方形美术画幅。

        美术接口约定：只要在这个 bbox 内绘制内容即可；1/2/4 号区域会在上层覆盖。
        敌方在友方视角下左下角会被裁掉（缺角标记）。
        """
        size = x2 - x1
        bg_colors = (UI_THEME["minion_bg_top"], UI_THEME["minion_bg_bottom"])

        photo = self._create_minion_portrait_photo(
            size, bg_colors[0], bg_colors[1],
            is_enemy=is_enemy, corner_leg=self.MINION_CORNER_LEG
        )
        if photo:
            ref_key = f"{tag}_portrait"
            self._minion_image_refs[ref_key] = photo
            canvas.create_image((x1 + x2) // 2, (y1 + y2) // 2,
                                image=photo, tags=(tag, "minion", "portrait"))
        else:
            # PIL 不可用时回退：绘制多边形
            if is_enemy:
                points = [x1, y1, x2, y1, x2, y2, x1 + self.MINION_CORNER_LEG, y2,
                          x1, y2 - self.MINION_CORNER_LEG]
            else:
                points = [x1, y1, x2, y1, x2, y2, x1, y2]
            canvas.create_polygon(points, fill=UI_THEME["minion_bg"], outline="",
                                  tags=(tag, "minion", "portrait"))

        # 名称（自动换行，限制在 3 号区域内）
        canvas.create_text((x1 + x2) // 2, (y1 + y2) // 2, text=m.name,
                           fill="black", font=("Microsoft YaHei", 9, "bold"),
                           width=max(10, size - 8), justify=tk.CENTER,
                           tags=(tag, "minion", "portrait_text"))

    def _draw_minion_keyword_bar(self, canvas, cx: int, cy: int, m: "Minion", tag: str):
        """绘制 4 号区域：附着在正方形右侧外部的小方框，每个词条/状态一个字，按词条类型着色。"""
        r = self.MINION_SIZE // 2
        box = self.MINION_KEYWORD_BOX
        gap = self.MINION_KEYWORD_GAP
        start_x = cx + r + gap
        start_y = cy - r

        # 词条/状态配色（背景，前景文字）
        keyword_styles = {
            "恐惧": (UI_THEME["kw_fear"], "white"),
            "冰冻": (UI_THEME["kw_frozen"], "white"),
            "眩晕": (UI_THEME["kw_stun"], "white"),
            "休眠": (UI_THEME["kw_dormant"], "white"),
            "亡语": (UI_THEME["kw_deathrattle"], "white"),
            "迅捷": (UI_THEME["kw_swift"], "white"),
            "潜水": (UI_THEME["kw_dive"], "white"),
            "潜行": (UI_THEME["kw_stealth"], "white"),
            "成长": (UI_THEME["kw_grow"], "white"),
            "视野": (UI_THEME["kw_vision"], "black"),
            "高频": (UI_THEME["kw_multi"], "white"),
            "防空": (UI_THEME["kw_anti_air"], "white"),
            "尖刺": (UI_THEME["kw_thorns"], "black"),
            "穿刺": (UI_THEME["kw_pierce"], "white"),
            "串击": (UI_THEME["kw_chain"], "white"),
            "横扫": (UI_THEME["kw_sweep"], "white"),
            "丰饶": (UI_THEME["kw_fertility"], "white"),
            "献祭": (UI_THEME["kw_sacrifice"], "white"),
            "协同": (UI_THEME["kw_synergy"], "white"),
            "独行": (UI_THEME["kw_solo"], "white"),
        }
        default_style = (UI_THEME["minion_bar_bg"], "black")

        # 收集有效词条/状态，优先显示控制类状态
        priority = {
            "恐惧": 0, "冰冻": 0, "眩晕": 0, "休眠": 0,
            "亡语": 1, "迅捷": 1, "潜行": 1, "潜水": 1,
            "成长": 2, "视野": 3, "高频": 3, "先攻": 3,
        }
        active = []
        for k, v in m.display_keywords.items():
            if v is False or v is None:
                continue
            if isinstance(v, int) and v == 0:
                continue
            # 默认值为 1 的“丰饶/献祭”不显示
            if k in ("丰饶", "献祭") and v == 1:
                continue
            active.append((k, v))
        active.sort(key=lambda x: priority.get(x[0], 99))

        am = get_asset_manager()
        # 按可用高度截断
        max_boxes = max(1, self.MINION_SIZE // (box + gap))
        for i, (k, v) in enumerate(active[:max_boxes]):
            x1 = start_x
            y1 = start_y + i * (box + gap)
            x2 = x1 + box
            y2 = y1 + box
            icon = am.get_icon(k, box)
            if icon is not None:
                # 像素图标优先显示，保留引用防止被 GC
                ref_key = f"{tag}_kw_{i}"
                self._minion_image_refs[ref_key] = icon
                canvas.create_image(x1, y1, image=icon, anchor=tk.NW,
                                    tags=(tag, "minion", "keyword_icon"))
            else:
                bg, fg = keyword_styles.get(k, default_style)
                canvas.create_rectangle(x1, y1, x2, y2,
                                        fill=bg, outline=UI_THEME["border"], width=1,
                                        tags=(tag, "minion", "keyword_box"))
                canvas.create_text((x1 + x2) // 2, (y1 + y2) // 2, text=k[0],
                                   fill=fg, font=("Microsoft YaHei", 8, "bold"),
                                   tags=(tag, "minion", "keyword_text"))

    def _render_board(self):
        # 如果当前浮窗对应的异象已离开战场，自动隐藏浮窗
        if self._tooltip_source and isinstance(self._tooltip_source, Minion):
            if self._tooltip_source not in self.duel.game.board.minion_place.values():
                self._hide_tooltip()
        self.canvas.delete("minion")
        self.canvas.delete("target_hint")
        self.canvas.delete("deploy_preview")
        if not self.duel.game:
            return
        self._minion_image_refs = {}
        for (logic_r, c), m in self.duel.game.board.minion_place.items():
            display_r = self._display_row(logic_r)
            cx = c * self.cell_size + self.cell_size // 2 + self.board_offset_x + self.MINION_OFFSET_X
            cy = display_r * self.cell_size + self.cell_size // 2 + self.board_offset_y
            tag = f"minion_{logic_r}_{c}"
            # 清除该 tag 上所有旧事件绑定（避免 _render_board 重绘后累积触发）
            for seq in ("<Enter>", "<Leave>", "<Motion>", "<Button-1>", "<Double-Button-1>"):
                self.canvas.tag_unbind(tag, seq)
            # 敌我视角：敌方异象在友方视角下左下角缺角
            is_enemy = (m.owner.side != self.local_player.side)

            r = self.MINION_SIZE // 2
            bh = self.MINION_STAT_BAR_HEIGHT
            slant = self.MINION_STAT_BAR_SLANT

            def _stat_bar_width(text) -> int:
                return max(21, len(str(text)) * 9 + 11)

            # 3 号区域：淡色渐变背景 + 名称（美术接口）
            self._draw_minion_portrait(self.canvas, cx, cy, m,
                                       cx - r, cy - r, cx + r, cy + r, tag,
                                       is_enemy=is_enemy, display_r=display_r)

            # 1 号区域：左上角攻击栏（动态宽度梯形）
            atk_w = _stat_bar_width(m.attack)
            atk_color = self._get_minion_attack_color(m)
            atk_points = [
                cx - r, cy - r,
                cx - r + atk_w, cy - r,
                cx - r + atk_w - slant, cy - r + bh,
                cx - r, cy - r + bh,
            ]
            self.canvas.create_polygon(atk_points, fill=atk_color, outline="",
                                       tags=(tag, "minion", "atk_bar"))
            atk_cx = cx - r + atk_w / 2 - slant / 4
            atk_cy = cy - r + bh / 2 - 1
            self.canvas.create_text(atk_cx, atk_cy, text=str(m.attack), fill="black",
                                    font=("Small Fonts", 11, "bold"),
                                    tags=(tag, "minion", "atk_text"))

            # 2 号区域：右下角 HP 栏（动态宽度梯形）
            hp_w = _stat_bar_width(m.health)
            hp_color = self._get_minion_hp_color(m)
            hp_points = [
                cx + r - hp_w + slant, cy + r - bh,
                cx + r, cy + r - bh,
                cx + r, cy + r,
                cx + r - hp_w, cy + r,
            ]
            self.canvas.create_polygon(hp_points, fill=hp_color, outline="",
                                       tags=(tag, "minion", "hp_bar"))
            hp_cx = cx + r - hp_w / 2 + slant / 4
            hp_cy = cy + r - bh / 2 - 1
            self.canvas.create_text(hp_cx, hp_cy, text=str(m.health), fill="black",
                                    font=("Small Fonts", 11, "bold"),
                                    tags=(tag, "minion", "hp_text"))

            # 4 号区域：附着在正方形右侧外部的词条/状态小方框
            self._draw_minion_keyword_bar(self.canvas, cx, cy, m, tag)


            self.canvas.tag_bind(tag, "<Enter>", lambda e, mm=m: (self._show_minion_tooltip(e, mm), self._update_detail_text(mm)))
            self.canvas.tag_bind(tag, "<Leave>", lambda e: self._hide_tooltip())
            self.canvas.tag_bind(tag, "<Motion>", lambda e: self._move_tooltip(e.x_root, e.y_root))
            self.canvas.tag_bind(tag, "<Button-1>", lambda e, mm=m: self._on_minion_click(mm))
            self.canvas.tag_bind(tag, "<Double-Button-1>", lambda e, mm=m: self._on_minion_double_click(mm))
            # 如果当前在指向模式中且该异象是合法目标，高亮边框
            if self._in_targeting_mode:
                is_target = m in self._targeting_valid_targets
                if is_target:
                    self.canvas.create_rectangle(cx - 32, cy - 27, cx + 32, cy + 27, outline=UI_THEME["card_border_target"], width=4, tags="target_hint")
            # 献祭选择模式：合法祭品黄框，已选祭品绿框，左上角显示丰饶等级
            if self._in_sacrifice_mode and m in self._sacrifice_candidates:
                is_selected = m in self._selected_sacrifices
                color = UI_THEME["success"] if is_selected else UI_THEME["card_border_target"]
                self.canvas.create_rectangle(cx - 32, cy - 27, cx + 32, cy + 27, outline=color, width=4, tags="target_hint")
                # 左上角显示丰饶等级
                fertility = m.keywords.get("丰饶", 1)
                self.canvas.create_text(cx - 24, cy - 20, text=str(fertility), fill="white",
                                        font=("Microsoft YaHei", 9, "bold"),
                                        tags=(tag, "minion", "sacrifice_fertility"))
                # 丰饶等级背景小圆
                self.canvas.create_oval(cx - 30, cy - 26, cx - 18, cy - 14,
                                        fill=UI_THEME["danger"], outline="white", width=1,
                                        tags=(tag, "minion", "sacrifice_fertility"))
                # 重新画文字在最上层
                self.canvas.create_text(cx - 24, cy - 20, text=str(fertility), fill="white",
                                        font=("Microsoft YaHei", 9, "bold"),
                                        tags=(tag, "minion", "sacrifice_fertility"))
            # 阿拉伯数字：行动阶段中仍需选择攻击目标的次数
            stars = self._get_minion_pending_stars(m)
            if stars > 0:
                self.canvas.create_text(cx + 22, cy - 18, text=str(stars), fill=UI_THEME["kw_vision"],
                                        font=("Microsoft YaHei", 12, "bold"), tags=(tag, "minion", "pending_star"))
            # 关键词/状态已改到 4 号区域竖条显示
            # 清除攻击预设按钮（右下角小红叉）
            pending = getattr(m, "_pending_attack_targets", None)
            if pending and isinstance(pending, list) and len(pending) > 0:
                clear_x = cx + 22
                clear_y = cy + 18
                clear_tag = f"clear_pending_{logic_r}_{c}"
                self.canvas.tag_unbind(clear_tag, "<Button-1>")
                self.canvas.create_rectangle(clear_x - 6, clear_y - 6, clear_x + 6, clear_y + 6,
                                             fill=UI_THEME["danger"], outline="white", width=1,
                                             tags=(clear_tag, "minion"))
                self.canvas.create_text(clear_x, clear_y, text="×", fill="white",
                                        font=("Microsoft YaHei", 8, "bold"),
                                        tags=(clear_tag, "minion"))
                self.canvas.tag_bind(clear_tag, "<Button-1>",
                                     lambda e, pos=m.position: self._clear_attack_targets(pos))
            # 清除效果预设按钮（左下角小蓝叉）
            effect_pending = getattr(m, "_pending_effect_target", None)
            if effect_pending is not None:
                clear_x = cx - 22
                clear_y = cy + 18
                clear_tag = f"clear_effect_{logic_r}_{c}"
                self.canvas.tag_unbind(clear_tag, "<Button-1>")
                self.canvas.create_rectangle(clear_x - 6, clear_y - 6, clear_x + 6, clear_y + 6,
                                             fill=UI_THEME["accent"], outline="white", width=1,
                                             tags=(clear_tag, "minion"))
                self.canvas.create_text(clear_x, clear_y, text="×", fill="white",
                                        font=("Microsoft YaHei", 8, "bold"),
                                        tags=(clear_tag, "minion"))
                self.canvas.tag_bind(clear_tag, "<Button-1>",
                                     lambda e, pos=m.position: self._clear_effect_target(pos))
            # 可交互指示器（行动阶段中可设置攻击目标的异象）
            if (self.duel.game and self.duel.game.current_phase == "action"
                    and m.owner == self.duel.game.current_player
                    and m.can_attack_this_turn(self.duel.game.current_turn)):
                vision = m.keywords.get("视野", 0)
                multi = m.keywords.get("高频", 0)
                if vision > 0 or (isinstance(multi, int) and multi > 0):
                    self.canvas.create_oval(cx + 18, cy - 22, cx + 26, cy - 14,
                                            fill=UI_THEME["success"], outline="white", width=1,
                                            tags=(tag, "minion", "interactive_dot"))
            # 可交互指示器（行动阶段中可设置效果目标的异象）
            if (self.duel.game and self.duel.game.current_phase == "action"
                    and m.owner == self.duel.game.current_player):
                scope_fn = getattr(m, '_effect_target_scope_fn', None)
                if scope_fn and getattr(m, '_pending_effect_target', None) is None:
                    self.canvas.create_oval(cx - 26, cy - 22, cx - 18, cy - 14,
                                            fill=UI_THEME["accent"], outline="white", width=1,
                                            tags=(tag, "minion", "interactive_dot"))
        # 绘制攻击预设连线
        for (logic_r, c), m in self.duel.game.board.minion_place.items():
            pending = getattr(m, "_pending_attack_targets", None)
            if not pending or not isinstance(pending, list):
                continue
            display_r = self._display_row(logic_r)
            x1 = c * self.cell_size + self.cell_size // 2 + self.board_offset_x
            y1 = display_r * self.cell_size + self.cell_size // 2 + self.board_offset_y
            for target in pending:
                if hasattr(target, "position") and target.position:
                    t_logic_r, tc = target.position
                    t_display_r = self._display_row(t_logic_r)
                    x2 = tc * self.cell_size + self.cell_size // 2 + self.board_offset_x
                    y2 = t_display_r * self.cell_size + self.cell_size // 2 + self.board_offset_y
                    self.canvas.create_line(x1, y1, x2, y2,
                                            fill=UI_THEME["kw_vision"], dash=(4, 4), width=2,
                                            arrow=tk.LAST, tags=("target_arrow", "minion"))
        # 绘制效果预设连线（预输入阶段）
        for (logic_r, c), m in self.duel.game.board.minion_place.items():
            pending = getattr(m, "_pending_effect_target", None)
            if pending is None:
                continue
            # 隐藏预输入：只有所有者可见（如鮟鱇）
            hidden = getattr(m, '_hidden_effect_pending', False)
            if hidden and m.owner != self.local_player:
                continue
            display_r = self._display_row(logic_r)
            x1 = c * self.cell_size + self.cell_size // 2 + self.board_offset_x
            y1 = display_r * self.cell_size + self.cell_size // 2 + self.board_offset_y
            target = pending
            if hasattr(target, "position") and target.position:
                t_logic_r, tc = target.position
                t_display_r = self._display_row(t_logic_r)
                x2 = tc * self.cell_size + self.cell_size // 2 + self.board_offset_x
                y2 = t_display_r * self.cell_size + self.cell_size // 2 + self.board_offset_y
                self.canvas.create_line(x1, y1, x2, y2,
                                        fill=UI_THEME["accent"], dash=(4, 4), width=2,
                                        arrow=tk.LAST, tags=("target_arrow", "minion"))
        # 绘制已完成指向的锁定连线（所有人可见，如鮟鱇）
        for (logic_r, c), m in self.duel.game.board.minion_place.items():
            locked = getattr(m, "_ankang_locked_target", None)
            if locked is None:
                continue
            display_r = self._display_row(logic_r)
            x1 = c * self.cell_size + self.cell_size // 2 + self.board_offset_x
            y1 = display_r * self.cell_size + self.cell_size // 2 + self.board_offset_y
            target = locked
            if hasattr(target, "position") and target.position:
                t_logic_r, tc = target.position
                t_display_r = self._display_row(t_logic_r)
                x2 = tc * self.cell_size + self.cell_size // 2 + self.board_offset_x
                y2 = t_display_r * self.cell_size + self.cell_size // 2 + self.board_offset_y
                self.canvas.create_line(x1, y1, x2, y2,
                                        fill=UI_THEME["accent"], dash=(4, 4), width=2,
                                        arrow=tk.LAST, tags=("target_arrow", "minion"))
        # 献祭模式：实时预览部署合法范围（与部署模式统一黄框样式）
        if self._in_sacrifice_mode and self._sacrifice_card and self._sacrifice_active:
            preview = self._calc_deploy_range(self._sacrifice_card, self._sacrifice_active, self._selected_sacrifices)
            for (pr, pc) in preview:
                p_display_r = self._display_row(pr)
                vcx = pc * self.cell_size + self.cell_size // 2 + self.board_offset_x
                vcy = p_display_r * self.cell_size + self.cell_size // 2 + self.board_offset_y
                self.canvas.create_rectangle(vcx - 38, vcy - 38, vcx + 38, vcy + 38,
                                             outline=UI_THEME["kw_vision"], width=4,
                                             fill="#fffbeb", stipple="gray50",
                                             tags="deploy_preview")
        # 高亮指向来源异象（金色发光边框）
        if self._targeting_source_minion and self._targeting_source_minion.position:
            sr, sc = self._targeting_source_minion.position
            s_display_r = self._display_row(sr)
            scx = sc * self.cell_size + self.cell_size // 2 + self.board_offset_x
            scy = s_display_r * self.cell_size + self.cell_size // 2 + self.board_offset_y
            self.canvas.create_rectangle(scx - 34, scy - 29, scx + 34, scy + 29,
                                         outline=UI_THEME["kw_vision"], width=4, tags="target_hint")
        # 高亮合法目标（位置）——黄色方框
        if self.valid_targets:
            for t in self.valid_targets:
                if isinstance(t, tuple) and len(t) == 2:
                    vr, vc = t
                    v_display_r = self._display_row(vr)
                    vcx = vc * self.cell_size + self.cell_size // 2 + self.board_offset_x
                    vcy = v_display_r * self.cell_size + self.cell_size // 2 + self.board_offset_y
                    self.canvas.create_rectangle(vcx - 38, vcy - 38, vcx + 38, vcy + 38,
                                                 outline=UI_THEME["kw_vision"], width=4,
                                                 fill="#fffbeb", stipple="gray50",
                                                 tags="target_hint")

    def _update_detail_text(self, card):
        """在右侧文本栏中显示卡牌/异象信息（悬停时触发）。"""
        if not hasattr(self, "detail_text"):
            return

        from tards.cards import Minion, MinionCard
        from tards.card_db import Pack
        is_minion = isinstance(card, Minion)

        # 判断是否为冥刻异象（仅冥刻卡包的异象过滤献祭1/丰饶1）
        is_underworld = False
        if is_minion and hasattr(card, "source_card") and card.source_card:
            is_underworld = getattr(card.source_card, "pack", None) == Pack.UNDERWORLD

        # 获取描述：优先从 card 本身，其次从 source_card，最后从注册表
        desc = getattr(card, "description", "")
        if not desc and is_minion and hasattr(card, "source_card") and card.source_card:
            desc = getattr(card.source_card, "description", "")
        if not desc and DEFAULT_REGISTRY:
            lookup_name = card.name
            if is_minion and hasattr(card, "source_card") and card.source_card:
                lookup_name = card.source_card.name
            card_def = DEFAULT_REGISTRY.get(lookup_name)
            if card_def:
                desc = getattr(card_def, "description", "")

        lines = [f"【{card.name}】"]

        if is_minion:
            # 异象：显示当前攻防（含临时变化）和基础值
            base_atk = card.base_attack
            base_hp = card.base_health
            cur_atk = card.current_attack
            cur_hp = card.current_health
            max_hp = card.current_max_health

            atk_str = str(cur_atk)
            if cur_atk != base_atk:
                atk_str += f" (基础{base_atk})"

            hp_str = str(cur_hp)
            if max_hp != card.base_max_health:
                hp_str += f"/{max_hp} (基础{base_hp})"
            elif cur_hp != base_hp:
                hp_str += f" (基础{base_hp})"

            lines.append(f"攻击/生命: {atk_str} / {hp_str}")

            # 费用（从 source_card 获取）
            cost = getattr(card, "cost", None)
            if cost is None and hasattr(card, "source_card") and card.source_card:
                cost = card.source_card.cost
            if cost is not None:
                lines.append(f"费用: {cost}")

            # 关键词
            kw_dict = card.display_keywords
        else:
            # 手牌
            lines.append(f"费用: {getattr(card, 'cost', '?')}")
            if isinstance(card, MinionCard):
                lines.append(f"攻击/生命: {card.attack}/{card.health}")
            kw_dict = getattr(card, "keywords", None) or {}

        if kw_dict:
            if is_minion and is_underworld:
                kw = " ".join(
                    f"{k}{v if v is not True else ''}"
                    for k, v in kw_dict.items()
                    if not (k in ("丰饶", "献祭") and v == 1)
                )
            else:
                kw = " ".join(f"{k}{v if v is not True else ''}" for k, v in kw_dict.items())
            if kw:
                lines.append(f"关键词: {kw}")

        # 场上临时赋予的效果（不包括永久攻防增减）
        if is_minion:
            # 临时关键词
            temp_kw = getattr(card, "temp_keywords", None)
            if temp_kw:
                if is_underworld:
                    kw_text = " ".join(
                        f"{k}{v if v is not True else ''}"
                        for k, v in temp_kw.items()
                        if not (k in ("丰饶", "献祭") and v == 1)
                    )
                else:
                    kw_text = " ".join(f"{k}{v if v is not True else ''}" for k, v in temp_kw.items())
                if kw_text:
                    lines.append(f"临时效果: {kw_text}")

            # 注入的回合回调（如被赋予的亡语等）
            injected_start = getattr(card, "_injected_turn_start", []) or []
            injected_end = getattr(card, "_injected_turn_end", []) or []
            for fn in injected_start:
                src = getattr(fn, "_source_name", "未知")
                desc = getattr(fn, "__name__", "结算阶段开始效果")
                lines.append(f"效果【{src}】：{desc}")
            for fn in injected_end:
                src = getattr(fn, "_source_name", "未知")
                desc = getattr(fn, "__name__", "结算阶段结束效果")
                lines.append(f"效果【{src}】：{desc}")

            # 光环效果（来自其他异象的攻击力/生命/关键词修饰）
            aura_providers = [
                (getattr(card, "_aura_attack_provider", None), "攻击力光环"),
                (getattr(card, "_aura_max_health_provider", None), "最大生命光环"),
                (getattr(card, "_aura_keyword_provider", None), "关键词光环"),
            ]
            for prov, label in aura_providers:
                if prov:
                    for entry in prov._entries:
                        src = getattr(entry.source, "name", str(entry.source)) if entry.source else "未知"
                        lines.append(f"效果【{src}】：{label}")

            # EventBus 监听器效果（策略/异象注入的触发效果）
            if self.duel.game and hasattr(self.duel.game, "history"):
                for entry in self.duel.game.history.get_listeners_by_owner(card):
                    src = getattr(entry.callback, "_source_name",
                                  getattr(entry.callback, "__name__", "未知"))
                    eff_desc = getattr(entry.callback, "_description", entry.event_type)
                    lines.append(f"效果【{src}】：{eff_desc}")

            # 指向状态
            pending_atks = getattr(card, "_pending_attack_targets", None)
            if pending_atks and isinstance(pending_atks, list) and len(pending_atks) > 0:
                target_names = []
                for t in pending_atks:
                    if hasattr(t, "name"):
                        target_names.append(t.name)
                    elif isinstance(t, tuple) and len(t) == 2:
                        target_names.append(f"({t[0]},{t[1]})")
                    else:
                        target_names.append(str(t))
                lines.append(f"攻击指向: {' → '.join(target_names)}")

            pending_effect = getattr(card, "_pending_effect_target", None)
            if pending_effect is not None:
                eff_name = getattr(pending_effect, "name", str(pending_effect))
                lines.append(f"效果指向: {eff_name}")

            locked_target = getattr(card, "_ankang_locked_target", None)
            if locked_target is not None:
                locked_name = getattr(locked_target, "name", str(locked_target))
                lines.append(f"锁定目标: {locked_name}")

            # 被哪些异象指向（攻击目标 + 效果目标 + 通用实例属性反向查找）
            pointed_by = []
            if self.duel.game and self.duel.game.board:
                for m in self.duel.game.board.minion_place.values():
                    if m is card:
                        continue
                    m_pending = getattr(m, "_pending_attack_targets", None)
                    if m_pending and isinstance(m_pending, list) and card in m_pending:
                        pointed_by.append(m.name)
                        continue
                    m_effect = getattr(m, "_pending_effect_target", None)
                    if m_effect is card:
                        pointed_by.append(m.name)
                        continue
                    # 通用反向查找：检查其他异象的实例属性是否引用本异象
                    for val in vars(m).values():
                        if val is card:
                            pointed_by.append(m.name)
                            break
                        if isinstance(val, (list, tuple, set)) and card in val:
                            pointed_by.append(m.name)
                            break
            if pointed_by:
                lines.append(f"被指向: {', '.join(pointed_by)}")

            # 藤蔓覆盖
            vine = getattr(card, "vine_overlay", None)
            if vine:
                lines.append(f"藤蔓覆盖: {vine.name} ({vine.current_health}/{vine.current_max_health})")

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

    def _get_available_blood(self, player):
        """计算场上友方异象可提供的献祭B点总和。"""
        if not self.duel.game:
            return 0
        minions = self.duel.game.board.get_minions_of_player(player)
        return sum(m.keywords.get("丰饶", 1) for m in minions if m.is_alive())

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

    @staticmethod
    def _calc_tab_width(cost_str: str, base: int = 28, char_px: int = 6, padding: int = 10) -> int:
        """根据费用字符串长度计算左上角标签宽度。"""
        return max(base, len(cost_str) * char_px + padding)

    def _create_gradient_photo(self, width, height, color1, color2, radius=6):
        """生成圆角斜向渐变 PIL Image，返回 tk.PhotoImage。"""
        if not _PIL_AVAILABLE or width <= 0 or height <= 0:
            return None

        def _hex_to_rgb(h):
            h = h.lstrip("#")
            return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))

        c1 = _hex_to_rgb(color1)
        c2 = _hex_to_rgb(color2)

        # 1. 创建渐变
        grad = Image.new("RGB", (width, height))
        pixels = grad.load()
        max_sum = width + height - 2
        for y in range(height):
            for x in range(width):
                t = (x + y) / max_sum if max_sum > 0 else 0
                r = int(c1[0] + (c2[0] - c1[0]) * t)
                g = int(c1[1] + (c2[1] - c1[1]) * t)
                b = int(c1[2] + (c2[2] - c1[2]) * t)
                pixels[x, y] = (r, g, b)

        # 2. 遮罩改为完整矩形（覆盖整个 Canvas，无透明区域）
        mask = Image.new("L", (width, height), 255)
        r_band, g_band, b_band = grad.split()
        img = Image.merge("RGBA", (r_band, g_band, b_band, mask))
        return ImageTk.PhotoImage(img)

    def _create_tab_gradient_photo(self, width, height, color1, color2, tab_w=28, tab_h=16, slant=5, radius=2):
        """生成带左上角标签的圆角斜向渐变 PIL Image，返回 tk.PhotoImage。
        radius 为微圆角偏移量（极小，仅对直角做略微修正）。"""
        if not _PIL_AVAILABLE or width <= 0 or height <= 0:
            return None

        def _hex_to_rgb(h):
            h = h.lstrip("#")
            return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))

        c1 = _hex_to_rgb(color1)
        c2 = _hex_to_rgb(color2)

        # 1. 创建渐变
        grad = Image.new("RGB", (width, height))
        pixels = grad.load()
        max_sum = width + height - 2
        for y in range(height):
            for x in range(width):
                t = (x + y) / max_sum if max_sum > 0 else 0
                r = int(c1[0] + (c2[0] - c1[0]) * t)
                g = int(c1[1] + (c2[1] - c1[1]) * t)
                b = int(c1[2] + (c2[2] - c1[2]) * t)
                pixels[x, y] = (r, g, b)

        # 2. 创建带标签形状的遮罩（透明区域仅限标签凹口和微圆角角落）
        mask = Image.new("L", (width, height), 0)
        draw = ImageDraw.Draw(mask)
        x1, y1 = 0, 0
        x2, y2 = width - 1, height - 1
        body_y1 = y1 + tab_h
        r = radius

        # 主体微圆角矩形（左上被标签替代）
        body_points = [
            (x1 + tab_w + slant, body_y1),
            (x2 - r, body_y1),
            (x2, body_y1 + r),
            (x2, y2 - r),
            (x2 - r, y2),
            (x1 + r, y2),
            (x1, y2 - r),
            (x1, body_y1),
        ]
        draw.polygon(body_points, fill=255)

        # 标签梯形
        draw.polygon([
            (x1, y1),
            (x1 + tab_w, y1),
            (x1 + tab_w + slant, body_y1),
            (x1, body_y1),
        ], fill=255)

        r_band, g_band, b_band = grad.split()
        img = Image.merge("RGBA", (r_band, g_band, b_band, mask))
        return ImageTk.PhotoImage(img)

    def _render_hand_card(self, parent, card, idx, serial, active, card_type_colors, am, cw, ch, flash=False):
        """渲染单张手牌卡牌。"""
        try:
            # 计算可用B点（含场上可献祭异象）
            available_blood = self._get_available_blood(active)
            from tards.player import Player as PlayerCls
            original_b = active.b_point
            active.b_point = original_b + available_blood
            effective_cost = active._get_play_cost(card)
            cost_ok, _ = effective_cost.can_afford_detail(active)
            active.b_point = original_b
            can_play_now = (cost_ok and not self._in_targeting_mode
                            and self.duel.game
                            and self.duel.game.current_phase == "action")
            # 统一白色外框，不再用 Frame 背景做状态指示（太粗）
            frame = tk.Frame(parent, bd=0)
            frame.pack(side=tk.LEFT, padx=6, pady=2)
            if flash:
                self._flash_widget_bg(frame, UI_THEME["kw_vision"], times=2, interval=150)

            # Canvas 尺寸精确贴合卡牌外接矩形，不留空白
            cvs = tk.Canvas(frame, width=cw, height=ch, highlightthickness=0, bd=0)
            cvs.pack()

            # 卡牌本体（从 Canvas 左上角开始）
            card_x1, card_y1 = 0, 0
            card_x2, card_y2 = cw, ch

            # 费用与标签参数（动态宽度，防止长费用被截断）
            cost_str = str(effective_cost)
            TAB_W = self._calc_tab_width(cost_str)
            TAB_H = 16
            TAB_SLANT = max(5, TAB_W // 6)

            # 状态判断 → 边框样式
            is_selected = (self.selected_card_idx == idx)
            is_valid_target = (self._in_targeting_mode and card in self._targeting_valid_targets)
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

            # 带标签形状的稀有度渐变背景
            rarity_colors = self._get_card_rarity_gradient_colors(card)
            bg_colors = rarity_colors if rarity_colors else UI_THEME["rarity_none"]
            if _PIL_AVAILABLE:
                photo = self._create_tab_gradient_photo(
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

            # 标签区域填充（可打出提示器：绿色 / 默认深灰）
            label_points = [
                card_x1, card_y1 + offset_y,
                card_x1 + TAB_W, card_y1 + offset_y,
                card_x1 + TAB_W + TAB_SLANT, card_y1 + TAB_H + offset_y,
                card_x1, card_y1 + TAB_H + offset_y,
            ]
            tab_fill = UI_THEME["card_tab_playable"] if can_play_now else UI_THEME["card_tab_default"]
            cvs.create_polygon(label_points, fill=tab_fill, outline="", tags="cost_tab")

            # 整体外形边框（带标签的圆角矩形，微圆角：仅用斜切做略微修正）
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

            img = None
            if getattr(card, "asset_id", None):
                img = am.get_card_face(card.asset_id, cw - 4, ch - 4)
            if img:
                cvs.create_image(cw // 2, ch // 2, image=img, tags="card_img")
                cvs.image = img

            # 费用文字（标签内，白色）
            cost_cx = card_x1 + (TAB_W + TAB_SLANT) // 2
            cost_cy = card_y1 + TAB_H // 2 + offset_y
            cvs.create_text(cost_cx, cost_cy, text=cost_str, fill="white",
                            font=("Microsoft YaHei", 8, "bold"), tags="card_text")

            name = card.name
            stats = ""
            if isinstance(card, MinionCard):
                stats = f"{card.attack}/{card.health}"
            cvs.create_text(cw // 2, 20 + TAB_H, text=name, fill=UI_THEME["card_text_name"],
                            font=("Microsoft YaHei", 9, "bold"), tags="card_text")
            bottom_text = stats
            if isinstance(card, Strategy):
                bottom_text = "【策略】"
            elif isinstance(card, Conspiracy):
                bottom_text = "【阴谋】"
            elif isinstance(card, MineralCard):
                bottom_text = "【矿物】"
            elif isinstance(card, MinionCard):
                bottom_text = f"【异象】{stats}"
            cvs.create_text(cw // 2, ch - 14, text=bottom_text, fill=UI_THEME["card_text_type"],
                            font=("Microsoft YaHei", 8), tags="card_text")

            # 已激活的阴谋：红色边框（带标签形状，跟随卡牌 offset_y）
            if isinstance(card, Conspiracy) and card in active.active_conspiracies:
                cvs.create_polygon(shape_points, fill="", outline=UI_THEME["danger"], width=3,
                                   tags="activated_mark")

            # 已被对手见过的牌：左下角折痕效果（颜色随稀有度自适应）
            if getattr(card, "_shown_to_opponent", False):
                off = offset_y
                # 获取卡牌稀有度以匹配折痕色调
                fold_rarity = getattr(card, "rarity", None)
                if fold_rarity is None and DEFAULT_REGISTRY:
                    defn = DEFAULT_REGISTRY.get(card.name)
                    if defn:
                        fold_rarity = defn.rarity
                back_color, front_color, line_color = self._FOLD_COLORS.get(
                    fold_rarity, self._FOLD_COLORS[None]
                )
                # 背面阴影（大三角形下半部分）
                cvs.create_polygon(0, ch - 6 + off, 0, ch + off, 12, ch + off,
                                   fill=back_color, outline="", tags="shown_mark")
                # 折起正面（大三角形上半部分，浅色覆盖）
                cvs.create_polygon(0, ch - 12 + off, 0, ch - 6 + off, 12, ch + off,
                                   fill=front_color, outline="", tags="shown_mark")
                # 折痕线
                cvs.create_line(0, ch - 6 + off, 12, ch + off,
                                fill=line_color, width=1, tags="shown_mark")

            stack_count = getattr(card, "stack_count", 1)
            if stack_count > 1:
                cvs.create_oval(cw - 22, ch - 22 + offset_y, cw - 2, ch - 2 + offset_y,
                                fill=UI_THEME["card_stack_bg"], outline="white", width=2, tags="stack_count")
                cvs.create_text(cw - 12, ch - 12 + offset_y, text=str(stack_count), fill="white",
                                font=("Microsoft YaHei", 9, "bold"), tags="stack_count")
            cvs.bind("<Button-1>", lambda e, idx=idx: self._on_hand_card_click(idx))
            cvs.bind("<ButtonPress-1>", lambda e, c=card, s=serial: self._on_drag_start(e, c, s))
            cvs.bind("<Enter>", lambda e, c=card, s=serial: (self._show_card_tooltip(e, c), self._preview_deploy_positions(s), self._update_detail_text(c)))
            cvs.bind("<Leave>", lambda e: (self._hide_tooltip(), self._clear_preview(), self._clear_detail_text()))
            cvs.bind("<Motion>", lambda e, c=card: self._move_tooltip(e.x_root, e.y_root))
        except Exception as e:
            print(f"[_render_hand_card] 渲染卡牌异常 [{getattr(card, 'name', 'unknown')}]: {e}")
            import traceback
            traceback.print_exc()

    def _render_reveal_card(self, canvas, card, cw=90, ch=144):
        """在指定 Canvas 上渲染一张静态展示卡牌（用于弃置/移除/磨牌展示）。"""
        print(f"[Reveal] _render_reveal_card 开始: card={getattr(card, 'name', 'unknown')}")
        canvas.delete("all")
        try:
            cost_str = str(card.cost)
            print(f"[Reveal]   cost_str={cost_str}")
            TAB_W = self._calc_tab_width(cost_str)
            TAB_H = 16
            TAB_SLANT = max(5, TAB_W // 6)
            border_color = UI_THEME["card_border_default"]
            border_width = 1
            print(f"[Reveal]   TAB_W={TAB_W}, TAB_SLANT={TAB_SLANT}")

            # 稀有度渐变背景
            rarity_colors = self._get_card_rarity_gradient_colors(card)
            bg_colors = rarity_colors if rarity_colors else UI_THEME["rarity_none"]
            print(f"[Reveal]   bg_colors={bg_colors}, _PIL_AVAILABLE={_PIL_AVAILABLE}")
            if _PIL_AVAILABLE:
                photo = self._create_tab_gradient_photo(
                    cw, ch, bg_colors[0], bg_colors[1],
                    tab_w=TAB_W, tab_h=TAB_H, slant=TAB_SLANT, radius=2
                )
                print(f"[Reveal]   photo={photo is not None}")
                if photo:
                    canvas.create_image(cw // 2, ch // 2, image=photo, tags="rarity_bg")
                    canvas.rarity_bg_image = photo

            # 费用标签
            label_points = [0, 0, TAB_W, 0, TAB_W + TAB_SLANT, TAB_H, 0, TAB_H]
            canvas.create_polygon(label_points, fill=UI_THEME["card_tab_default"], outline="", tags="cost_tab")
            print(f"[Reveal]   费用标签绘制完成")

            # 边框
            r = 2
            shape_points = [
                0, 0, TAB_W, 0, TAB_W + TAB_SLANT, TAB_H,
                cw - r, TAB_H, cw, TAB_H + r, cw, ch - r,
                cw - r, ch, r, ch, 0, ch - r, 0, TAB_H,
            ]
            canvas.create_polygon(shape_points, fill="", outline=border_color, width=border_width,
                                  joinstyle=tk.MITER, tags="card_border")
            print(f"[Reveal]   边框绘制完成")

            # 肖像
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
            canvas.create_text(cost_cx, cost_cy, text=cost_str, fill="white",
                               font=("Microsoft YaHei", 8, "bold"), tags="card_text")
            print(f"[Reveal]   费用文字绘制完成")

            # 名称
            name = card.name
            canvas.create_text(cw // 2, 20 + TAB_H, text=name, fill=UI_THEME["card_text_name"],
                               font=("Microsoft YaHei", 9, "bold"), tags="card_text")
            print(f"[Reveal]   名称绘制完成: {name}")

            # 底部类型
            from tards.cards import MinionCard, Strategy, Conspiracy, MineralCard
            stats = ""
            if isinstance(card, MinionCard):
                stats = f"{card.attack}/{card.health}"
            bottom_text = stats
            if isinstance(card, Strategy):
                bottom_text = "【策略】"
            elif isinstance(card, Conspiracy):
                bottom_text = "【阴谋】"
            elif isinstance(card, MineralCard):
                bottom_text = "【矿物】"
            elif isinstance(card, MinionCard):
                bottom_text = f"【异象】{stats}"
            canvas.create_text(cw // 2, ch - 14, text=bottom_text, fill=UI_THEME["card_text_type"],
                               font=("Microsoft YaHei", 8), tags="card_text")
            print(f"[Reveal]   底部类型绘制完成: {bottom_text}")
            print(f"[Reveal] _render_reveal_card 完成")
        except Exception as e:
            print(f"[Reveal] [_render_reveal_card] 渲染异常 [{getattr(card, 'name', 'unknown')}]: {e}")
            import traceback
            traceback.print_exc()

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
        """渲染单张 mulligan 卡牌。"""
        try:
            frame_bd = 3 if selected else 0
            frame_bg = UI_THEME["success"] if selected else UI_THEME["bg_panel"]
            frame = tk.Frame(parent, bg=frame_bg, bd=frame_bd)
            frame.pack(side=tk.LEFT, padx=4)
            cvs = tk.Canvas(frame, width=cw, height=ch, highlightthickness=0, bd=0, bg=UI_THEME["bg_panel"])
            cvs.pack(padx=2, pady=2)

            cost_str = str(card.cost)
            TAB_W = self._calc_tab_width(cost_str)
            TAB_H = 16
            TAB_SLANT = max(5, TAB_W // 6)
            card_x1, card_y1 = 0, 0
            card_x2, card_y2 = cw, ch

            # 带标签形状的稀有度渐变背景
            rarity_colors = self._get_card_rarity_gradient_colors(card)
            bg_colors = rarity_colors if rarity_colors else UI_THEME["rarity_none"]
            if _PIL_AVAILABLE:
                photo = self._create_tab_gradient_photo(
                    cw, ch,
                    bg_colors[0], bg_colors[1],
                    tab_w=TAB_W, tab_h=TAB_H, slant=TAB_SLANT, radius=2
                )
                if photo:
                    cvs.create_image(
                        cw // 2,
                        ch // 2,
                        image=photo, tags="rarity_bg"
                    )
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
            cvs.create_polygon(shape_points, fill="", outline=border_color, width=border_width,
                               joinstyle=tk.MITER, tags="card_border")

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
            cvs.bind("<Button-1>", lambda e, i=idx: self._on_mulligan_card_click(i))
        except Exception as e:
            print(f"[_render_mulligan_card] 渲染卡牌异常 [{getattr(card, 'name', 'unknown')}]: {e}")
            import traceback
            traceback.print_exc()

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

    def _card_display_text(self, card) -> str:
        name = card.name
        cost = str(card.cost)
        type_icon = ""
        if isinstance(card, MinionCard):
            type_icon = "【异象】"
        elif isinstance(card, Strategy):
            type_icon = "【策略】"
        elif isinstance(card, Conspiracy):
            type_icon = "【阴谋】"
        elif isinstance(card, MineralCard):
            type_icon = "【矿物】"
        if isinstance(card, MinionCard):
            return f"{type_icon}{name}\n{cost}费 {card.attack}/{card.health}"
        return f"{type_icon}{name}\n{cost}费"

    def _render_info(self):
        if not self.duel.game:
            return
        from tards.card_db import Pack
        for pname, widgets in self.info_labels.items():
            player = None
            if self.duel.game.p1.name == pname:
                player = self.duel.game.p1
            elif self.duel.game.p2.name == pname:
                player = self.duel.game.p2
            if not player:
                continue

            is_current = self.duel.game.current_player == player
            is_target = self._in_targeting_mode and player in self._targeting_valid_targets

            # 背景色
            if is_target:
                bg = UI_THEME["btn_warning_bg"]
            elif is_current:
                bg = "#dcfce7"
            elif getattr(player, "braked", False):
                bg = UI_THEME["btn_danger_bg"]
            else:
                bg = UI_THEME["bg_main"]

            for key in ["frame", "row0", "row1", "row2", "row_shown", "right_info",
                        "dot", "name_label", "hp_frame", "hp_label",
                        "dis_label", "conspiracy_label", "shown_label", "last_dis_label"]:
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
                old_val = self._prev_res_values.get((pname, key))
                if old_val is not None and val != old_val:
                    # 数值变化时闪烁：白色 → 黄色 → 白色
                    def _flash(c=cvs, t=text_id, orig="white"):
                        c.itemconfig(t, fill="yellow")
                        c.after(150, lambda: c.itemconfig(t, fill=orig))
                        c.after(300, lambda: c.itemconfig(t, fill="yellow"))
                        c.after(450, lambda: c.itemconfig(t, fill=orig))
                    _flash()
                self._prev_res_values[(pname, key)] = val
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
                    last_info = self._last_discarded_info.get(pname)
                    if last_info and last_info[0] == last_card.name:
                        card_name, color = last_info
                    else:
                        # 未追踪到的路径，默认黑色
                        card_name = last_card.name
                        color = UI_THEME["text_primary"]
                        self._last_discarded_info[pname] = (card_name, color)
                    last_dis_label.config(text=f"上一张: {card_name}", fg=color)
                else:
                    last_dis_label.config(text="")

            # 弃牌堆 badge 状态
            discard_badge = widgets.get("discard_badge")
            if discard_badge:
                discard_badge.config(text=f"弃牌堆 {len(player.card_dis)}")

        # 更新右侧"当前资源"面板（网络对局显示本地玩家，本地对局显示当前回合玩家）
        game = self.duel.game
        active = game.current_player if game else None
        # 网络对局中始终显示本地玩家资源，方便玩家随时查看自己的费用决策
        display_player = self.local_player if isinstance(self.duel, NetworkDuel) else active
        if display_player:
            for key, val, lbl in [
                ("res_t", display_player.t_point, self.res_t_label),
                ("res_c", display_player.c_point, self.res_c_label),
                ("res_b", display_player.b_point, self.res_b_label),
                ("res_s", display_player.s_point, self.res_s_label),
            ]:
                old_val = self._prev_res_values.get(key)
                if old_val is not None and val != old_val:
                    flash_color = UI_THEME["success"] if val > old_val else UI_THEME["danger"]
                    self._flash_res_label(lbl, flash_color, times=2, interval=150)
                self._prev_res_values[key] = val

            self.res_t_label.config(text=f"T:{display_player.t_point}/{display_player.t_point_max}")
            self.res_c_label.config(text=f"C:{display_player.c_point}/{display_player.c_point_max}")
            # B点显示：献祭模式下显示 x/y（当前可用/所需），否则显示 x
            if self._in_sacrifice_mode and self._sacrifice_active == display_player:
                selected_blood = sum(m.keywords.get("丰饶", 1) for m in self._selected_sacrifices)
                total_blood = display_player.b_point + selected_blood
                self.res_b_label.config(text=f"B:{total_blood}/{self._sacrifice_required}")
            else:
                self.res_b_label.config(text=f"B:{display_player.b_point}")
            has_underworld = display_player.immersion_points.get(Pack.UNDERWORLD, 0) >= 1
            if has_underworld:
                self.res_sacrifice_label.config(text=f"可献祭:{self._get_available_blood(display_player)}")
                if not self.res_sacrifice_label.winfo_ismapped():
                    self.res_sacrifice_label.pack(side=tk.LEFT, padx=(0, 8))
            else:
                self.res_sacrifice_label.pack_forget()
            self.res_s_label.config(text=f"S:{display_player.s_point}")
            self.res_deck_label.config(text=f"抽牌堆:{len(display_player.card_deck)}")
            self.res_dis_label.config(text=f"弃牌堆:{len(display_player.card_dis)}")
            self.res_conspiracy_label.config(text=f"阴谋序列:{len(display_player.active_conspiracies)}")
            self.res_panel.config(text=f"{display_player.name} 的资源")
        else:
            self.res_panel.config(text="当前资源")

        # 同步"抽松鼠"复选框状态（仅本地玩家可操作）
        if active and (not isinstance(self.duel, NetworkDuel) or active == self.local_player):
            has_underworld = active.immersion_points.get(Pack.UNDERWORLD, 0) >= 1
            if has_underworld and active.squirrel_deck:
                self.squirrel_draw_cb.pack(side=tk.LEFT, padx=5)
                self.squirrel_draw_var.set(active.squirrel_draw_enabled)
            else:
                self.squirrel_draw_cb.pack_forget()
        else:
            self.squirrel_draw_cb.pack_forget()

    def _on_minion_click(self, minion: Minion):
        # 1. 献祭选择模式：选择/取消祭品
        if self._in_sacrifice_mode:
            if minion in self._sacrifice_candidates:
                if minion in self._selected_sacrifices:
                    self._selected_sacrifices.remove(minion)
                else:
                    self._selected_sacrifices.append(minion)
                self._render_board()
                self._render_info()
                total = sum(m.keywords.get("丰饶", 1) for m in self._selected_sacrifices)
                if total >= self._sacrifice_required:
                    self._confirm_sacrifice()
                return "break"
            return

        # 2. 指向模式：确认合法目标
        if self._in_targeting_mode:
            if minion in self._targeting_valid_targets:
                self._in_targeting_mode = False
                on_confirm = self._targeting_on_confirm
                self._targeting_on_confirm = None
                self._targeting_on_cancel = None
                self._targeting_valid_targets = []
                self.hint_label.config(text="", font=("Microsoft YaHei", 10), fg=UI_THEME["accent"])
                self._render_board()
                self._render_info()
                if on_confirm:
                    on_confirm(minion)
                return "break"
            # 非法目标，不阻止传播，让 _on_canvas_click 处理错误提示
            return

        # 3. 非指向模式：检查是否进入预设
        if not self.duel.game:
            return
        if self.duel.game.current_phase != "action":
            return
        active = self.duel.game.current_player
        if not active:
            return
        # 网络对战中，只能操作本地玩家；本地测试中，当前回合玩家均可操作
        if isinstance(self.duel, NetworkDuel) and minion.owner != self.local_player:
            return
        if minion.owner != active:
            return
        # 若正在选手牌目标，不干扰
        if self.selected_card is not None:
            return

        has_attack = minion.keywords.get("视野", 0) > 0
        has_effect = getattr(minion, '_effect_target_scope_fn', None) is not None

        entered = False
        if has_attack and has_effect:
            # 两者都有，优先攻击模式
            self._handle_board_unit_click(minion.position, mode="attack")
            entered = True
        elif has_attack:
            self._handle_board_unit_click(minion.position, mode="attack")
            entered = True
        elif has_effect:
            self._handle_board_unit_click(minion.position, mode="effect")
            entered = True

        if entered:
            return "break"

    def _on_minion_double_click(self, minion: Minion):
        """双击异象：
        - 若已在攻击指向模式且来源是该异象 → 切换到效果预设模式
        - 否则同单击逻辑（进入预设）
        """
        if not self.duel.game:
            return "break"
        active = self.duel.game.current_player
        if not active:
            return "break"
        # 网络对战中，只能操作本地玩家；本地测试中，当前回合玩家均可操作
        if isinstance(self.duel, NetworkDuel) and minion.owner != self.local_player:
            return "break"
        if minion.owner != active:
            return "break"
        if self.duel.game.current_phase != "action":
            return "break"

        # 已在攻击指向模式且来源是该异象 → 切换到效果
        if (self._in_targeting_mode
                and getattr(self, '_current_targeting_mode', None) == "attack"
                and self._targeting_source_minion is minion):
            has_effect = getattr(minion, '_effect_target_scope_fn', None) is not None
            if has_effect:
                self._exit_targeting_mode()
                self._handle_board_unit_click(minion.position, mode="effect")
            return "break"

        # 已在其它指向模式，忽略
        if self._in_targeting_mode:
            return "break"

        # 非指向模式，双击同单击
        self._on_minion_click(minion)
        return "break"

    def _on_player_label_click(self, player: Optional[Player]):
        if not self._in_targeting_mode or not player:
            return
        if player in self._targeting_valid_targets:
            self._in_targeting_mode = False
            on_confirm = self._targeting_on_confirm
            self._targeting_on_confirm = None
            self._targeting_on_cancel = None
            self._targeting_valid_targets = []
            self.hint_label.config(text="", font=("Microsoft YaHei", 10), fg=UI_THEME["accent"])
            self._render_board()
            self._render_info()
            if on_confirm:
                on_confirm(player)

    def _enter_local_targeting(self, valid_targets: List[Any], on_confirm: Callable[[Any], None],
                                on_cancel: Optional[Callable[[], None]] = None, prompt: str = "请选择目标"):
        """进入本地指向模式（用于 action 阶段的主目标选择或攻击预设）。"""
        self._in_targeting_mode = True
        self._targeting_valid_targets = valid_targets
        self._targeting_on_confirm = on_confirm
        self._targeting_on_cancel = on_cancel
        self.valid_targets = valid_targets
        self.hint_label.config(text=prompt, font=("Microsoft YaHei", 12, "bold"), fg=UI_THEME["danger"])
        self._render_board()
        self._render_info()
        self._render_hand()

    def _show_targeting(self, request: TargetingRequest, valid_targets: List[Any]):
        """响应 targeting_request 事件，渲染指向选项。"""
        if not valid_targets:
            # 无合法目标，直接取消
            if request.on_cancel:
                request.on_cancel()
            if hasattr(self.duel, 'submit_local_targeting'):
                self.duel.submit_local_targeting(None)
            return

        # 数字选项：弹出 NumericChoiceDialog
        if request.numeric_options is not None:
            def on_choose(val: int):
                if hasattr(self.duel, 'submit_local_targeting'):
                    self.duel.submit_local_targeting(val)
            NumericChoiceDialog(self, request.prompt, request.numeric_options, on_choose)
            return

        # 对象选项：进入本地指向模式
        self._enter_local_targeting(
            valid_targets=valid_targets,
            on_confirm=lambda target: (
                self.duel.submit_local_targeting(target) if hasattr(self.duel, 'submit_local_targeting') else None
            ),
            on_cancel=lambda: (
                self.duel.submit_local_targeting(None) if hasattr(self.duel, 'submit_local_targeting') else None
            ),
            prompt=request.prompt,
        )

    def _enter_sacrifice_mode(self, serial: int, card, active, required_blood: int):
        """进入献祭选择模式：玩家点击场上友方异象作为祭品。"""
        self._in_sacrifice_mode = True
        self._sacrifice_serial = serial
        self._sacrifice_card = card
        self._sacrifice_active = active
        self._sacrifice_required = required_blood
        self._sacrifice_candidates = list(self.duel.game.board.get_minions_of_player(active)) if self.duel.game else []
        self._selected_sacrifices = []
        self._pending_sacrifices = []
        self.hint_label.config(
            text=f"请选择献祭异象（需要{required_blood}点鲜血）| 点击选择/取消 | Enter确认 | ESC取消",
            font=("Microsoft YaHei", 11, "bold"), fg=UI_THEME["danger"]
        )
        self._render_board()
        self._render_info()
        self._render_hand()

    def _exit_sacrifice_mode(self):
        """退出献祭选择模式。"""
        self._in_sacrifice_mode = False
        self._sacrifice_candidates = []
        self._selected_sacrifices = []
        self._sacrifice_required = 0
        self._sacrifice_serial = None
        self._sacrifice_card = None
        self._sacrifice_active = None
        # 注意：_pending_sacrifices 不在这里清除，因为 _confirm_sacrifice 需要保留它传递给 _enter_deploy_targeting
        self.hint_label.config(text="", font=("Microsoft YaHei", 10), fg=UI_THEME["accent"])
        self._render_board()
        self._render_info()
        self._render_hand()

    def _confirm_sacrifice(self):
        """确认当前选择的献祭，进入部署位置选择。"""
        total = sum(m.keywords.get("丰饶", 1) for m in self._selected_sacrifices)
        if total < self._sacrifice_required:
            self.hint_label.config(text=f"献祭不足，已选{total}点，还需{self._sacrifice_required - total}点", fg=UI_THEME["danger"])
            self.after(1000, lambda: self.hint_label.config(fg=UI_THEME["danger"]))
            return
        self._pending_sacrifices = list(self._selected_sacrifices)
        serial = self._sacrifice_serial
        card = self._sacrifice_card
        active = self._sacrifice_active
        self._exit_sacrifice_mode()
        self._enter_deploy_targeting(serial, card, active)

    def _exit_targeting_mode(self, preserve_pending=False):
        self._in_targeting_mode = False
        self._targeting_valid_targets = []
        self._targeting_on_confirm = None
        self._targeting_on_cancel = None
        self.valid_targets = []
        self._pending_play_data = None
        self.selected_card = None
        self.selected_card_idx = None
        self._targeting_source_minion = None
        self._current_targeting_mode = None
        if not preserve_pending:
            self._pending_sacrifices = []
        self.hint_label.config(text="", font=("Microsoft YaHei", 10), fg=UI_THEME["accent"])
        self._render_hand()
        self._render_board()
        self._render_info()

    def _clear_attack_targets(self, pos):
        """清除指定异象的预设攻击目标。"""
        if not self.duel.game:
            return
        active = self.duel.game.current_player
        if not active:
            return
        if isinstance(self.duel, NetworkDuel) and active != self.local_player:
            return
        m = self.duel.game.board.get_minion_at(pos)
        if not m or m.owner != active:
            return
        self.duel.submit_local_action({
            "type": "set_attack_targets",
            "pos": pos,
            "targets": [],
        })

    def _clear_effect_target(self, pos):
        """清除指定异象的预设效果目标。"""
        if not self.duel.game:
            return
        active = self.duel.game.current_player
        if not active:
            return
        if isinstance(self.duel, NetworkDuel) and active != self.local_player:
            return
        m = self.duel.game.board.get_minion_at(pos)
        if not m or m.owner != active:
            return
        self.duel.submit_local_action({
            "type": "set_effect_target",
            "pos": pos,
            "target": None,
        })

    def _handle_board_unit_click(self, target, mode="attack"):
        """处理玩家点击场上自己的异象（攻击预设或效果预设）。"""
        if not self.duel.game:
            return
        active = self.duel.game.current_player
        if not active:
            return
        m = self.duel.game.board.get_minion_at(target)
        if not m:
            return
        # 网络对战中，只能操作本地玩家；本地测试中，当前回合玩家均可操作
        if isinstance(self.duel, NetworkDuel) and m.owner != self.local_player:
            return
        if m.owner != active:
            return

        if mode == "attack":
            vision = m.keywords.get("视野", 0)
            if vision <= 0:
                return
            multi_attack = m.keywords.get("高频", 0)
            atk_candidates = get_attack_target_candidates(m, self.duel.game)
            if not atk_candidates:
                return

            # 攻击目标预设：多目标简化为单目标多次提交（保持向后兼容）
            count = multi_attack if isinstance(multi_attack, int) and multi_attack > 0 else 1
            selected_atks: List[Any] = []

            def pick_next():
                if len(selected_atks) >= count:
                    self.duel.submit_local_action({
                        "type": "set_attack_targets",
                        "pos": m.position,
                        "targets": selected_atks,
                    })
                    self._exit_targeting_mode()
                    return
                self._enter_local_targeting(
                    valid_targets=atk_candidates,
                    on_confirm=lambda t: (selected_atks.append(t), pick_next()),
                    on_cancel=self._exit_targeting_mode,
                    prompt=f"请选择 {m.name} 的攻击目标 ({len(selected_atks)+1}/{count})",
                )

            self._targeting_source_minion = m
            self._current_targeting_mode = "attack"
            pick_next()

        elif mode == "effect":
            scope_fn = getattr(m, '_effect_target_scope_fn', None)
            if not scope_fn:
                return
            candidates = scope_fn(active, self.duel.game.board)
            if not candidates:
                return

            count = 1
            selected_effect: List[Any] = []

            def pick_next_effect():
                if len(selected_effect) >= count:
                    self.duel.submit_local_action({
                        "type": "set_effect_target",
                        "pos": m.position,
                        "target": selected_effect[0],
                    })
                    self._exit_targeting_mode()
                    return
                self._enter_local_targeting(
                    valid_targets=candidates,
                    on_confirm=lambda t: (selected_effect.append(t), pick_next_effect()),
                    on_cancel=self._exit_targeting_mode,
                    prompt=f"请选择 {m.name} 的效果目标",
                )

            self._targeting_source_minion = m
            self._current_targeting_mode = "effect"
            pick_next_effect()

    def _on_hand_card_click(self, idx: int):
        # 防重复点击/按键：出牌流程进行中时忽略新输入
        if getattr(self, "_is_playing_card", False):
            return
        self._is_playing_card = True
        self.after(500, lambda: setattr(self, "_is_playing_card", False))

        active = self.duel.game and self.duel.game.current_player
        serial = idx + 1
        card = active._get_hand_card(serial) if active else None
        if card is None:
            # 手牌序号无效，立即解锁防重复标记
            self._is_playing_card = False
            print(f"  [GUI] 点击手牌无效: serial={serial}, idx={idx}")
            return
        # 网络对战中，只能操作本地玩家；本地测试中，当前回合玩家均可操作
        if isinstance(self.duel, NetworkDuel) and active != self.local_player:
            self._is_playing_card = False
            return

        # 若当前处于指向模式且该手牌是合法目标，选择它作为指向目标
        if self._in_targeting_mode and card in self._targeting_valid_targets:
            self._in_targeting_mode = False
            on_confirm = self._targeting_on_confirm
            self._targeting_on_confirm = None
            self._targeting_on_cancel = None
            self._targeting_valid_targets = []
            self.hint_label.config(text="", font=("Microsoft YaHei", 10), fg=UI_THEME["accent"])
            self._render_board()
            self._render_info()
            self._render_hand()
            if on_confirm:
                on_confirm(card)
            return

        # Conspiracy：直接暗中激活（虚张声势功能已注释）
        if isinstance(card, Conspiracy):
            valid = [t for t in active.get_valid_targets(card) if active.card_can_play(serial, t)[0]]
            if len(valid) == 1 and valid[0] is None:
                self._submit_play(serial, None)
            elif valid:
                self._enter_local_targeting(
                    valid_targets=valid,
                    on_confirm=lambda t: self._submit_play(serial, t),
                    on_cancel=self._exit_targeting_mode,
                    prompt=f"请选择 [{card.name}] 的目标",
                )
            else:
                self._submit_play(serial, None)
            return

        # 异象卡：先处理献祭，再选择部署位置
        if isinstance(card, MinionCard):
            if card.cost.b > 0:
                # 若当前B点已足够，直接部署，无需献祭
                if active.b_point >= card.cost.b:
                    self._enter_deploy_targeting(serial, card, active)
                    return
                # B点不足，需要献祭补充差额
                need = card.cost.b - active.b_point
                minions = list(self.duel.game.board.get_minions_of_player(active)) if self.duel.game else []
                if not minions:
                    self.hint_label.config(text="B点不足，且场上没有可献祭的友方异象")
                    return
                self._enter_sacrifice_mode(serial, card, active, need)
                return
            self._enter_deploy_targeting(serial, card, active)
            return

        # 策略/矿物卡：选择效果主目标
        self._enter_effect_targeting(serial, card, active)

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

    def _enter_deploy_targeting(self, serial: int, card, active):
        """进入异象卡部署位置选择。"""
        sacrifices = getattr(self, "_pending_sacrifices", [])
        valid = self._calc_deploy_range(card, active, sacrifices)
        if not valid:
            self._submit_play(serial, None)
            return
        # 单目标自动确认
        if len(valid) == 1:
            self._submit_play(serial, valid[0])
            return
        self._enter_local_targeting(
            valid_targets=valid,
            on_confirm=lambda t: self._submit_play(serial, t),
            on_cancel=self._exit_targeting_mode,
            prompt=f"[{card.name}] 请选择部署位置",
        )

    def _enter_effect_targeting(self, serial: int, card, active):
        """进入策略/矿物卡效果目标选择。"""
        valid = [t for t in active.get_valid_targets(card) if active.card_can_play(serial, t)[0]]
        if not valid:
            self._submit_play(serial, None)
            return
        # 唯一目标是 None（非指向性）
        if len(valid) == 1 and valid[0] is None:
            self._submit_play(serial, None)
            return
        # 单目标自动确认
        if len(valid) == 1:
            self._submit_play(serial, valid[0])
            return
        self._enter_local_targeting(
            valid_targets=valid,
            on_confirm=lambda t: self._submit_play(serial, t),
            on_cancel=self._exit_targeting_mode,
            prompt=f"[{card.name}] 请选择效果目标",
        )

    def _flash_invalid_at(self, target):
        """在指定位置闪烁红色边框，提示非法操作。"""
        if not self.duel.game:
            return
        if isinstance(target, tuple) and len(target) == 2:
            logic_r, c = target
        elif hasattr(target, "position") and target.position:
            logic_r, c = target.position
        else:
            return
        display_r = self._display_row(logic_r)
        cx = c * self.cell_size + self.cell_size // 2 + self.board_offset_x
        cy = display_r * self.cell_size + self.cell_size // 2 + self.board_offset_y
        flash = self.canvas.create_rectangle(cx - 40, cy - 40, cx + 40, cy + 40,
                                             outline=UI_THEME["danger"], width=4,
                                             tags="flash_hint")
        self.after(200, lambda: self.canvas.delete("flash_hint"))

    def _on_canvas_click(self, event):
        active = self.duel.game and self.duel.game.current_player
        if not active:
            return
        # 网络对战中，只能操作本地玩家；本地测试中，当前回合玩家均可操作
        if isinstance(self.duel, NetworkDuel) and active != self.local_player:
            return
        c = (event.x - self.board_offset_x) // self.cell_size
        display_r = (event.y - self.board_offset_y) // self.cell_size
        logic_r = self._logic_row(display_r)
        target = (logic_r, c)

        # 0. 献祭选择模式：点击空白格子非法，点击异象由 _on_minion_click 处理
        if self._in_sacrifice_mode:
            self._flash_invalid_at(target)
            self.hint_label.config(text="请点击友方异象作为祭品", fg=UI_THEME["danger"])
            self.after(500, lambda: self.hint_label.config(fg=UI_THEME["danger"]) if self.hint_label else None)
            return

        # 1. 如果处于指向模式，优先处理目标选择
        if self._in_targeting_mode:
            clicked_target = None
            if target in self._targeting_valid_targets:
                clicked_target = target
            else:
                if self.duel.game:
                    m = self.duel.game.board.get_minion_at(target)
                    if m and m in self._targeting_valid_targets:
                        clicked_target = m
            if clicked_target is not None:
                self._in_targeting_mode = False
                on_confirm = self._targeting_on_confirm
                self._targeting_on_confirm = None
                self._targeting_on_cancel = None
                self._targeting_valid_targets = []
                self.hint_label.config(text="", font=("Microsoft YaHei", 10), fg=UI_THEME["accent"])
                self._render_board()
                self._render_info()
                if on_confirm:
                    on_confirm(clicked_target)
            else:
                self._flash_invalid_at(target)
                self.hint_label.config(text="点击的不是合法目标", fg=UI_THEME["danger"])
                self.after(500, lambda: self.hint_label.config(fg=UI_THEME["accent"]) if self.hint_label else None)
            return

        # 2. 手牌选择中的原有逻辑
        if isinstance(self.selected_card, MinionCard):
            if target in self.valid_targets:
                self._submit_play(self.selected_card_idx + 1, target)
            else:
                self._flash_invalid_at(target)
                self.hint_label.config(text="点击的不是合法目标", fg=UI_THEME["danger"])
                self.after(1000, self._reset_guide_hint)
            return
        clicked = None
        if self.duel.game:
            clicked = self.duel.game.board.get_minion_at(target)
        for t in self.valid_targets:
            if t == target or (isinstance(t, Minion) and clicked is t):
                self._submit_play(self.selected_card_idx + 1, t)
                return
        self._flash_invalid_at(target)
        self.hint_label.config(text="点击的不是合法目标", fg=UI_THEME["danger"])
        self.after(1000, self._reset_guide_hint)

    def _submit_play(self, serial: int, target: Any):
        active = self.duel.game.current_player if self.duel.game else None
        card_name = "未知卡牌"
        is_conspiracy = False
        card = active._get_hand_card(serial) if active else None
        if card:
            card_name = card.name
            is_conspiracy = isinstance(card, Conspiracy)
            if card.cost.b >= 3:
                if not messagebox.askyesno("确认出牌", f"确定要打出 [{card.name}] 吗？\n费用: {card.cost}"):
                    # 取消时不应清除 _pending_sacrifices，保留供重新选择
                    self._exit_targeting_mode(preserve_pending=True)
                    return
        # 在 _exit_targeting_mode 之前读取 sacrifices，否则会被清空
        sacrifices = getattr(self, "_pending_sacrifices", None)
        self._exit_targeting_mode()
        action = {"type": "play", "serial": serial, "target": target}
        if sacrifices:
            action["sacrifices"] = sacrifices
            self._pending_sacrifices = []
        self._clear_selection()
        # 阴谋激活视觉反馈
        if is_conspiracy:
            self._show_toast(f"阴谋 [{card_name}] 已暗中激活", UI_THEME["btn_secondary_bg"], 1500)
        self.duel.submit_local_action(action)
        self._add_history(f"打出 [{card_name}]", is_play=True)
        self.hint_label.config(text="已出牌，等待结果...")
        self.after(2000, self._reset_guide_hint)

    def _reset_guide_hint(self):
        """根据当前阶段恢复引导文字。"""
        if not self.duel.game or not self.hint_label:
            return
        phase = self.duel.game.current_phase
        if phase == "action":
            if self._in_targeting_mode:
                self.hint_label.config(text="指向模式：点击目标确认 | Enter确认 | ESC取消", fg=UI_THEME["danger"], font=("Microsoft YaHei", 12, "bold"))
            else:
                self.hint_label.config(text="出牌阶段：点击手牌出牌 | 点击异象设攻击目标 | 双击拍铃/拉闸 | B拉闸 Space拍铃 | 1~9快捷选牌 | ESC取消", fg=UI_THEME["accent"], font=("Microsoft YaHei", 10))
        elif phase == "resolve":
            self.hint_label.config(text="结算阶段进行中，请稍候...", fg=UI_THEME["danger_dark"], font=("Microsoft YaHei", 10))
        elif phase == "draw":
            self.hint_label.config(text="抽牌阶段...", fg=UI_THEME["accent_dark"], font=("Microsoft YaHei", 10))

    def _on_bell(self):
        # 防重复点击/按键
        if getattr(self, "_is_belling", False):
            return
        self._is_belling = True
        self.after(500, lambda: setattr(self, "_is_belling", False))

        active = self.duel.game and self.duel.game.current_player
        if not active:
            return
        if isinstance(self.duel, NetworkDuel) and active != self.local_player:
            return
        self._clear_selection()
        self.duel.submit_local_action({"type": "bell"})
        self._add_history("拍铃")
        self.hint_label.config(text="拍铃")
        self.after(1500, self._reset_guide_hint)

    def _on_brake(self):
        # 防重复点击/按键
        if getattr(self, "_is_braking", False):
            return
        self._is_braking = True
        self.after(500, lambda: setattr(self, "_is_braking", False))

        active = self.duel.game and self.duel.game.current_player
        if not active:
            return
        if isinstance(self.duel, NetworkDuel) and active != self.local_player:
            return
        self._clear_selection()
        self.duel.submit_local_action({"type": "brake"})
        self._add_history("拉闸")
        self.hint_label.config(text="拉闸")
        self.after(1500, self._reset_guide_hint)

    def _on_cancel(self):
        if self._in_sacrifice_mode:
            self._exit_sacrifice_mode()
            self._clear_selection()
            return
        if self._in_targeting_mode:
            on_cancel = self._targeting_on_cancel
            self._exit_targeting_mode()
            if on_cancel:
                on_cancel()
        else:
            self._clear_selection()

    def _toggle_mineral_bar(self):
        """展开/收起矿物快捷兑换面板。"""
        if self.mineral_bar.winfo_ismapped():
            self.mineral_bar.pack_forget()
            self.exchange_btn.config(bg="#fef3c7")
        else:
            self._refresh_mineral_bar()
            self.mineral_bar.pack(fill=tk.X, pady=(0, 5), before=self.hint_label)
            self.exchange_btn.config(bg="#fde68a")

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

    def _on_exchange(self):
        """旧版弹窗兑换（保留兼容，但主入口改为展开面板）。"""
        self._toggle_mineral_bar()

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

    def _show_discover(self, names: List[str]):
        def on_choose(n: str):
            self.duel.submit_local_discover(n)
        DiscoverDialog(self, names, on_choose)

    def _show_choice(self, options: List[str], title: str):
        def on_choose(o: str):
            self.duel.submit_local_choice(o)
        ChoiceDialog(self, title, options, on_choose)

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

    def _show_card_tooltip(self, event, card):
        # 浮窗已禁用，详情信息改由右侧固定面板显示
        pass

    def _show_minion_tooltip(self, event, minion):
        # 浮窗已禁用，详情信息改由右侧固定面板显示
        pass

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
