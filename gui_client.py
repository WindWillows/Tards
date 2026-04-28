#!/usr/bin/env python3
"""
Tards 可视化客户端 (Tkinter) + 联机对战
支持：卡组构筑与保存、IP 直连对战、信息不透明。
"""

import os
import random
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
from tards.assets import get_asset_manager
from tards.card_db import DEFAULT_REGISTRY, Pack, CardType
from tards.deck import Deck
from tards.deck_io import list_saved_decks, load_deck, save_deck
from tards.game_logger import BattleLogWriter
from tards.net_game import NetworkDuel
from tards.targeting import (
    TargetingRequest,
    TargetPicker,
    get_attack_target_candidates,
)

# 导入卡包池以注册所有卡牌到 DEFAULT_REGISTRY
import card_pools

# 全局事件：用于后台游戏线程通知 GUI 刷新
import threading
gui_refresh_event = threading.Event()


class Tooltip:
    """浮动提示框。"""
    def __init__(self, parent, text: str, x: int, y: int):
        self.tw = tk.Toplevel(parent)
        self.tw.wm_overrideredirect(True)
        self.tw.wm_geometry(f"+{x + 15}+{y + 15}")
        label = tk.Label(self.tw, text=text, justify=tk.LEFT,
                         background="#ffffe0", relief=tk.SOLID, borderwidth=1,
                         font=("Microsoft YaHei", 10))
        label.pack()

    def move(self, x: int, y: int):
        self.tw.wm_geometry(f"+{x + 15}+{y + 15}")

    def destroy(self):
        if self.tw and self.tw.winfo_exists():
            self.tw.destroy()


class LocalDuel:
    """本地对战控制器（人机测试），接口与 NetworkDuel 保持一致。"""

    def __init__(self, local_player: Player, local_deck_list: list):
        self.local_player = local_player
        self.local_deck_list = local_deck_list

        self.game: Optional[Game] = None
        self.local_turn_callback: Optional[Callable[[], None]] = None
        self.game_over_callback: Optional[Callable[[Optional[str]], None]] = None
        self.discover_request_callback: Optional[Callable[[list], None]] = None
        self.resolve_step_callback: Optional[Callable[[], None]] = None

        self._local_action: Optional[Dict[str, Any]] = None
        self._local_action_event = threading.Event()
        self._local_turn_event = threading.Event()

        self._discover_names: Optional[list] = None
        self._discover_result: Optional[str] = None
        self._discover_event = threading.Event()

        self._choice_options: Optional[list] = None
        self._choice_result: Optional[str] = None
        self._choice_event = threading.Event()
        self._choice_title: str = "抉择"

    def run_game(self, opponent: Player):
        self.game = Game(
            self.local_player,
            opponent,
            action_provider=self._make_action_provider(),
            discover_provider=self._make_discover_provider(),
        )
        self.game.choice_provider = self._make_choice_provider()
        self.game.resolve_step_callback = self.resolve_step_callback
        self.game.start_game()
        if self.game_over_callback and self.game.game_over:
            self.game_over_callback(self.game.winner.name if self.game.winner else None)

    def _make_action_provider(self):
        def provider(game, active, opponent):
            if self.local_turn_callback:
                self.local_turn_callback()
            self._local_turn_event.set()
            self._local_action_event.wait()
            self._local_action_event.clear()
            self._local_turn_event.clear()
            return self._local_action
        return provider

    def _make_discover_provider(self):
        def provider(game, player, candidates, count):
            names = [getattr(d, "name", str(d)) for d in candidates]
            self._discover_names = names
            self._discover_result = None
            self._discover_event.clear()
            if self.discover_request_callback:
                self.discover_request_callback(names)
                self._discover_event.wait()
                chosen_name = self._discover_result if self._discover_result is not None else names[0]
            else:
                # 无 GUI 回调时回退随机选择（避免死锁）
                import random
                chosen_name = random.choice(names)
            for d in candidates:
                if getattr(d, "name", str(d)) == chosen_name:
                    return d
            return candidates[0] if candidates else None
        return provider

    def submit_local_discover(self, chosen: str):
        self._discover_result = chosen
        self._discover_event.set()

    def _make_choice_provider(self):
        def provider(game, player, options, title):
            self._choice_options = options
            self._choice_result = None
            self._choice_title = title
            self._choice_event.clear()
            if self.choice_request_callback:
                self.choice_request_callback(options, title)
            self._choice_event.wait()
            return self._choice_result if self._choice_result in options else options[0]
        return provider

    def submit_local_choice(self, chosen: str):
        self._choice_result = chosen
        self._choice_event.set()

    def submit_local_action(self, action: Dict[str, Any]):
        self._local_action = action
        self._local_action_event.set()

    def is_local_turn(self) -> bool:
        return self._local_turn_event.is_set()

    def close(self):
        self._local_action_event.set()
        self._discover_event.set()



def _deck_defs_list(deck: Deck) -> List[Any]:
    """将 Deck 转换为 CardDefinition 列表，保留卡组顺序。"""
    defs = []
    for name, count in deck.card_entries.items():
        cd = DEFAULT_REGISTRY.get(name)
        if cd:
            for _ in range(count):
                defs.append(cd)
    return defs


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
class MenuFrame(tk.Frame):
    def __init__(self, parent, app: TardsApp):
        super().__init__(parent)
        self.app = app
        self._build()

    def _build(self):
        tk.Label(self, text="Tards", font=("Microsoft YaHei", 32, "bold")).pack(pady=40)
        tk.Button(self, text="构筑新卡组", font=("Microsoft YaHei", 16), width=20, command=self.app.show_deck_builder).pack(pady=10)
        tk.Button(self, text="编辑已有卡组", font=("Microsoft YaHei", 16), width=20, command=self._edit_existing_deck).pack(pady=10)
        tk.Button(self, text="本地测试", font=("Microsoft YaHei", 16), width=20, command=self._start_local_test).pack(pady=10)
        tk.Button(self, text="创建房间 (Host)", font=("Microsoft YaHei", 16), width=20, command=lambda: self.app.show_lobby(is_host=True)).pack(pady=10)
        tk.Button(self, text="加入房间 (Client)", font=("Microsoft YaHei", 16), width=20, command=lambda: self.app.show_lobby(is_host=False)).pack(pady=10)
        tk.Button(self, text="退出", font=("Microsoft YaHei", 16), width=20, command=self.app.root.quit).pack(pady=10)

    def _edit_existing_deck(self):
        win = tk.Toplevel(self)
        win.title("编辑已有卡组")
        win.geometry("300x150")
        win.resizable(False, False)
        tk.Label(win, text="选择要编辑的卡组:").pack(pady=5)
        combo = ttk.Combobox(win, values=list_saved_decks(), state="readonly", width=30)
        combo.pack(pady=5)
        if combo["values"]:
            combo.current(0)

        def load():
            name = combo.get()
            if not name:
                messagebox.showwarning("提示", "请先选择卡组")
                return
            win.destroy()
            self.app.show_deck_builder(deck_name=name)

        tk.Button(win, text="加载并编辑", font=("Microsoft YaHei", 12), command=load).pack(pady=10)

    def _start_local_test(self):
        win = tk.Toplevel(self)
        win.title("本地测试 (双人对打)")
        win.geometry("400x350")
        win.resizable(False, False)

        # 玩家1
        tk.Label(win, text="玩家1 名字:").pack(pady=(10, 0))
        name1_entry = tk.Entry(win, width=30)
        name1_entry.insert(0, "玩家1")
        name1_entry.pack()

        tk.Label(win, text="玩家1 卡组:").pack(pady=(5, 0))
        combo1 = ttk.Combobox(win, values=list_saved_decks(), state="readonly", width=30)
        combo1.pack()
        if combo1["values"]:
            combo1.current(0)

        # 玩家2
        tk.Label(win, text="玩家2 名字:").pack(pady=(10, 0))
        name2_entry = tk.Entry(win, width=30)
        name2_entry.insert(0, "玩家2")
        name2_entry.pack()

        tk.Label(win, text="玩家2 卡组:").pack(pady=(5, 0))
        combo2 = ttk.Combobox(win, values=list_saved_decks(), state="readonly", width=30)
        combo2.pack()
        if combo2["values"]:
            combo2.current(0)

        same_deck_var = tk.BooleanVar(value=False)
        def toggle_same():
            if same_deck_var.get():
                combo2.config(state="disabled")
            else:
                combo2.config(state="readonly")
        tk.Checkbutton(win, text="双方使用同一卡组", variable=same_deck_var, command=toggle_same).pack(pady=5)

        def start():
            name1 = name1_entry.get().strip() or "玩家1"
            name2 = name2_entry.get().strip() or "玩家2"
            deck_name1 = combo1.get()
            if not deck_name1:
                messagebox.showwarning("提示", "请先为玩家1选择卡组")
                return
            deck1 = load_deck(deck_name1, DEFAULT_REGISTRY)
            if not deck1:
                messagebox.showwarning("提示", f"无法读取卡组 {deck_name1}")
                return

            if same_deck_var.get():
                deck2 = deck1
            else:
                deck_name2 = combo2.get()
                if not deck_name2:
                    messagebox.showwarning("提示", "请先为玩家2选择卡组")
                    return
                deck2 = load_deck(deck_name2, DEFAULT_REGISTRY)
                if not deck2:
                    messagebox.showwarning("提示", f"无法读取卡组 {deck_name2}")
                    return

            player1 = Player(side=0, name=name1, diver="Local", card_deck=deck1.to_game_deck(None), original_deck_defs=_deck_defs_list(deck1))
            player1.sacrifice_chooser = lambda req: None
            player1.immersion_points = dict(deck1.immersion_points)

            player2 = Player(side=1, name=name2, diver="Local", card_deck=deck2.to_game_deck(None), original_deck_defs=_deck_defs_list(deck2))
            player2.sacrifice_chooser = lambda req: None
            player2.immersion_points = dict(deck2.immersion_points)

            duel = LocalDuel(player1, list(deck1.card_entries.keys()))
            win.destroy()
            self.app.start_local_battle(duel, player1, player2)

        tk.Button(win, text="开始测试", font=("Microsoft YaHei", 12), command=start).pack(pady=10)


# ========== 卡组构筑 ==========
class DeckBuilderFrame(tk.Frame):
    def __init__(self, parent, app: TardsApp, deck_name: Optional[str] = None):
        super().__init__(parent)
        self.app = app
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
        top = tk.Frame(self)
        top.pack(fill=tk.X, padx=10, pady=5)
        tk.Button(top, text="← 返回主菜单", command=self.app.show_menu).pack(side=tk.LEFT)
        tk.Label(top, text="卡组名:").pack(side=tk.LEFT, padx=5)
        self.name_entry = tk.Entry(top, width=20)
        self.name_entry.insert(0, self.deck.name)
        self.name_entry.pack(side=tk.LEFT, padx=5)
        tk.Button(top, text="保存卡组", command=self._save_deck).pack(side=tk.LEFT, padx=10)
        self.is_test_var = tk.BooleanVar(value=self.deck.is_test_deck)
        self.test_check = tk.Checkbutton(top, text="测试卡组", variable=self.is_test_var, fg="orange", font=("Microsoft YaHei", 10, "bold"), command=self._on_test_mode_change)
        self.test_check.pack(side=tk.LEFT, padx=10)

        immersion_frame = tk.LabelFrame(self, text="沉浸点分配 (每卡包 0-3)")
        immersion_frame.pack(fill=tk.X, padx=10, pady=5)
        self.imm_sliders = {}
        for pack in Pack:
            f = tk.Frame(immersion_frame)
            f.pack(side=tk.LEFT, padx=10)
            tk.Label(f, text=pack.value).pack()
            var = tk.IntVar(value=0)
            sc = tk.Scale(f, from_=0, to=3, orient=tk.HORIZONTAL, variable=var, command=lambda _, p=pack: self._on_imm_change(p))
            sc.pack()
            self.imm_sliders[pack] = var

        self.validation_label = tk.Label(self, text="", fg="red")
        self.validation_label.pack(fill=tk.X, padx=10)

        filter_frame = tk.Frame(self)
        filter_frame.pack(fill=tk.X, padx=10, pady=2)
        tk.Label(filter_frame, text="筛选:").pack(side=tk.LEFT)
        self.show_minion = tk.BooleanVar(value=True)
        self.show_strategy = tk.BooleanVar(value=True)
        self.show_conspiracy = tk.BooleanVar(value=True)
        self.hide_unimplemented = tk.BooleanVar(value=False)
        tk.Checkbutton(filter_frame, text="异象", variable=self.show_minion, command=self._refresh_available).pack(side=tk.LEFT, padx=2)
        tk.Checkbutton(filter_frame, text="策略", variable=self.show_strategy, command=self._refresh_available).pack(side=tk.LEFT, padx=2)
        tk.Checkbutton(filter_frame, text="阴谋", variable=self.show_conspiracy, command=self._refresh_available).pack(side=tk.LEFT, padx=2)
        tk.Checkbutton(filter_frame, text="隐藏未实现", variable=self.hide_unimplemented, command=self._refresh_available).pack(side=tk.LEFT, padx=(10, 0))
        tk.Label(filter_frame, text="排序:").pack(side=tk.LEFT, padx=(10, 0))
        self.sort_by = tk.StringVar(value="immersion")
        tk.Radiobutton(filter_frame, text="沉浸度", variable=self.sort_by, value="immersion", command=self._refresh_available).pack(side=tk.LEFT, padx=2)
        tk.Radiobutton(filter_frame, text="费用", variable=self.sort_by, value="cost", command=self._refresh_available).pack(side=tk.LEFT, padx=2)

        cards_frame = tk.LabelFrame(self, text="可用卡牌 (点击添加)")
        cards_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        self.notebook = ttk.Notebook(cards_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        self.pack_tabs = {}
        for pack in Pack:
            tab = tk.Frame(self.notebook)
            self.notebook.add(tab, text=pack.value)
            canvas = tk.Canvas(tab)
            scrollbar = tk.Scrollbar(tab, orient=tk.VERTICAL, command=canvas.yview)
            inner = tk.Frame(canvas)
            inner.bind("<Configure>", lambda e, c=canvas: c.configure(scrollregion=c.bbox("all")))
            canvas.create_window((0, 0), window=inner, anchor="nw")
            canvas.configure(yscrollcommand=scrollbar.set)
            canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            self.pack_tabs[pack] = inner

        # 卡牌详情
        self.detail_label = tk.Label(self, text="将鼠标悬停在卡牌上查看详情", anchor="w", justify=tk.LEFT,
                                     wraplength=1100, fg="#555", font=("Microsoft YaHei", 10))
        self.detail_label.pack(fill=tk.X, padx=10, pady=2)

        deck_frame = tk.LabelFrame(self, text="当前卡组")
        deck_frame.pack(fill=tk.X, padx=10, pady=5)
        self.deck_listbox = tk.Listbox(deck_frame, height=8)
        self.deck_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        deck_btn_frame = tk.Frame(deck_frame)
        deck_btn_frame.pack(side=tk.RIGHT, fill=tk.Y)
        tk.Button(deck_btn_frame, text="移除所选", command=self._remove_selected).pack(pady=2)
        tk.Button(deck_btn_frame, text="清空卡组", command=self._clear_deck).pack(pady=2)
        self.deck_count_label = tk.Label(deck_frame, text="0 张")
        self.deck_count_label.pack(side=tk.BOTTOM, fill=tk.X)

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

    def _show_card_detail(self, card):
        lines = [f"{card.name}  [{card.pack.value} {card.immersion_display} {card.rarity.name}]"]
        lines.append(f"费用: {card.cost}  类型: {card.card_type.value}")
        if card.attack is not None:
            lines.append(f"攻击/生命: {card.attack}/{card.health}")
        if card.keywords:
            kw = " ".join(f"{k}{v if v is not True else ''}" for k, v in card.keywords.items())
            lines.append(f"关键词: {kw}")
        if card.evolve_to:
            lines.append(f"成长为: {card.evolve_to}")
        desc = getattr(card, "description", "")
        if desc:
            lines.append(f"效果: {desc}")
        self.detail_label.config(text="  |  ".join(lines), fg="#000")

    def _clear_card_detail(self):
        self.detail_label.config(text="将鼠标悬停在卡牌上查看详情", fg="#555")

    # ===== BattleFrame 卡牌详情大图 =====
    def _update_detail_canvas(self, card):
        if not hasattr(self, "detail_canvas"):
            return
        cvs = self.detail_canvas
        cvs.delete("all")
        am = get_asset_manager()
        cw, ch = 160, 220
        img = None
        if getattr(card, "asset_id", None):
            img = am.get_card_face(card.asset_id, cw - 4, ch - 4)
        if img:
            cvs.create_image(cw // 2, ch // 2, image=img)
            cvs.image = img
        else:
            # 回退：显示文字信息
            lines = [card.name, str(card.cost), card.card_type.value]
            if isinstance(card, MinionCard):
                lines.append(f"{card.attack}/{card.health}")
            y = 40
            for line in lines:
                cvs.create_text(cw // 2, y, text=line, fill="#212121", font=("Microsoft YaHei", 10, "bold"))
                y += 24
            desc = getattr(card, "description", "")
            if desc:
                cvs.create_text(cw // 2, y + 10, text=desc, fill="#616161", font=("Microsoft YaHei", 9), width=cw - 10)

    def _clear_detail_canvas(self):
        if not hasattr(self, "detail_canvas"):
            return
        cvs = self.detail_canvas
        cvs.delete("all")
        cvs.create_text(80, 110, text="悬停卡牌查看详情", fill="#9e9e9e", font=("Microsoft YaHei", 10))

    def _on_imm_change(self, pack: Pack):
        pts = self.imm_sliders[pack].get()
        self.deck.set_immersion(pack, pts)
        self._refresh_available()
        self._refresh_deck_list()

    def _cost_sort_key(self, c):
        cost = c.cost
        return cost.t + cost.b + cost.s + cost.c + cost.ct + sum(cost.minerals.values())

    def _refresh_available(self):
        for tab in self.pack_tabs.values():
            for w in tab.winfo_children():
                w.destroy()
        type_filter = set()
        if self.show_minion.get():
            type_filter.add(CardType.MINION)
        if self.show_strategy.get():
            type_filter.add(CardType.STRATEGY)
        if self.show_conspiracy.get():
            type_filter.add(CardType.CONSPIRACY)
        sort_by = self.sort_by.get()
        is_test = self.deck.is_test_deck
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
            tab = self.pack_tabs[pack]
            if not cards:
                tk.Label(tab, text="无可用卡牌（请分配沉浸点）").pack(anchor="w", padx=5, pady=2)
                continue
            if sort_by == "cost":
                cards.sort(key=lambda c: (self._cost_sort_key(c), c.immersion_level, c.name))
            else:
                cards.sort(key=lambda c: (c.immersion_level, self._cost_sort_key(c), c.name))
            for card in cards:
                info = f"[{card.immersion_display} {card.cost}] {card.name}"
                if card.attack is not None:
                    info += f" {card.attack}/{card.health}"
                btn = tk.Button(tab, text=info, anchor="w", command=lambda c=card: self._add_card(c.name))
                btn.pack(fill=tk.X, padx=2, pady=1)
                btn.bind("<Enter>", lambda e, c=card: self._show_card_detail(c))
                btn.bind("<Leave>", lambda e: self._clear_card_detail())

    def _add_card(self, name: str):
        card_def = DEFAULT_REGISTRY.get(name)
        if not card_def:
            return
        current = self.deck.get_card_count(name)
        # 测试卡组取消稀有度上限和40张限制
        if not self.deck.is_test_deck:
            if current >= card_def.rarity.value:
                messagebox.showwarning("提示", f"{card_def.rarity.name} 卡最多携带 {card_def.rarity.value} 张")
                return
            if self.deck.total_cards() >= 40:
                messagebox.showwarning("提示", "卡组已满 40 张")
                return
        self.deck.add_card(name)
        self._refresh_deck_list()

    def _remove_selected(self):
        sel = self.deck_listbox.curselection()
        if not sel:
            return
        text = self.deck_listbox.get(sel[0])
        name = text.split(" x")[0]
        self.deck.remove_card(name, 1)
        self._refresh_deck_list()

    def _clear_deck(self):
        self.deck.card_entries.clear()
        self._refresh_deck_list()

    def _refresh_deck_list(self):
        self.deck_listbox.delete(0, tk.END)
        for name, count in sorted(self.deck.card_entries.items()):
            self.deck_listbox.insert(tk.END, f"{name} x{count}")
        prefix = "[测试] " if self.deck.is_test_deck else ""
        self.deck_count_label.config(text=f"{prefix}{self.deck.total_cards()} 张")
        errors = self.deck.validate()
        if errors:
            self.validation_label.config(text=" | ".join(errors), fg="red")
        else:
            if self.deck.is_test_deck:
                self.validation_label.config(text="测试卡组（无构筑限制）", fg="orange")
            else:
                self.validation_label.config(text="卡组合法", fg="green")

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
        # 检查是否覆盖已有文件
        from tards.deck_io import DECKS_DIR
        existing = [f[:-5] for f in os.listdir(DECKS_DIR) if f.endswith(".json")]
        if name in existing:
            if not messagebox.askyesno("覆盖确认", f"卡组 [{name}] 已存在，是否覆盖？"):
                return
        path = save_deck(self.deck)
        msg = f"已保存到 {path}"
        if self.deck.is_test_deck:
            msg += "\n（测试卡组，仅可用于本地测试）"
        messagebox.showinfo("保存成功", msg)


# ========== 联机大厅 ==========
class LobbyFrame(tk.Frame):
    def __init__(self, parent, app: TardsApp, is_host: bool):
        super().__init__(parent)
        self.app = app
        self.is_host = is_host
        self.duel: Optional[NetworkDuel] = None
        self._build()

    def _build(self):
        tk.Button(self, text="← 返回主菜单", command=self.app.show_menu).pack(anchor="nw", padx=10, pady=5)

        tk.Label(self, text="选择卡组:").pack(anchor="w", padx=10, pady=5)
        self.deck_combo = ttk.Combobox(self, values=list_saved_decks(), state="readonly", width=30)
        self.deck_combo.pack(anchor="w", padx=10)
        if self.deck_combo["values"]:
            self.deck_combo.current(0)

        tk.Label(self, text="玩家名:").pack(anchor="w", padx=10, pady=5)
        self.name_entry = tk.Entry(self, width=20)
        self.name_entry.insert(0, "玩家A" if self.is_host else "玩家B")
        self.name_entry.pack(anchor="w", padx=10)

        if self.is_host:
            tk.Label(self, text="端口:").pack(anchor="w", padx=10, pady=5)
            self.port_entry = tk.Entry(self, width=10)
            self.port_entry.insert(0, "9876")
            self.port_entry.pack(anchor="w", padx=10)
            tk.Button(self, text="创建房间并等待", font=("Microsoft YaHei", 14), command=self._start_host).pack(pady=20)
        else:
            tk.Label(self, text="Host IP:").pack(anchor="w", padx=10, pady=5)
            self.ip_entry = tk.Entry(self, width=20)
            self.ip_entry.insert(0, "127.0.0.1")
            self.ip_entry.pack(anchor="w", padx=10)
            tk.Label(self, text="端口:").pack(anchor="w", padx=10, pady=5)
            self.port_entry = tk.Entry(self, width=10)
            self.port_entry.insert(0, "9876")
            self.port_entry.pack(anchor="w", padx=10)
            tk.Button(self, text="加入房间", font=("Microsoft YaHei", 14), command=self._start_client).pack(pady=20)

        self.status_label = tk.Label(self, text="", fg="blue")
        self.status_label.pack(pady=10)

    def _get_selected_deck(self) -> Optional[Deck]:
        name = self.deck_combo.get()
        if not name:
            messagebox.showwarning("提示", "请先选择或构筑一个卡组")
            return None
        deck = load_deck(name, DEFAULT_REGISTRY)
        if not deck:
            messagebox.showwarning("提示", f"无法读取卡组 {name}")
            return None
        if deck.is_test_deck:
            messagebox.showwarning("提示", f"卡组 [{name}] 为测试卡组，不能用于联机对战")
            return None
        return deck

    def _start_host(self):
        deck = self._get_selected_deck()
        if not deck:
            return
        pname = self.name_entry.get().strip() or "玩家A"
        port = int(self.port_entry.get() or 9876)

        local_player = Player(side=0, name=pname, diver="Net", card_deck=deck.to_game_deck(None), original_deck_defs=_deck_defs_list(deck))
        local_player.sacrifice_chooser = lambda req: None
        local_player.immersion_points = dict(deck.immersion_points)
        opponent = Player(side=1, name="等待中...", diver="Net", card_deck=[])
        opponent.sacrifice_chooser = lambda req: None

        deck_names = []
        for name in sorted(deck.card_entries.keys()):
            deck_names.extend([name] * deck.card_entries[name])
        self.duel = NetworkDuel(local_player, deck_names, is_host=True, port=port)
        self.status_label.config(text=f"等待连接于端口 {port} ...")

        def connect_thread():
            ok = self.duel.connect()
            if ok:
                self.after(0, lambda: self._on_connected(deck, local_player, opponent))
            else:
                self.after(0, lambda: self.status_label.config(text="连接失败", fg="red"))

        threading.Thread(target=connect_thread, daemon=True).start()

    def _start_client(self):
        deck = self._get_selected_deck()
        if not deck:
            return
        pname = self.name_entry.get().strip() or "玩家B"
        ip = self.ip_entry.get().strip() or "127.0.0.1"
        port = int(self.port_entry.get() or 9876)

        local_player = Player(side=1, name=pname, diver="Net", card_deck=deck.to_game_deck(None), original_deck_defs=_deck_defs_list(deck))
        local_player.sacrifice_chooser = lambda req: None
        local_player.immersion_points = dict(deck.immersion_points)
        opponent = Player(side=0, name="等待中...", diver="Net", card_deck=[])
        opponent.sacrifice_chooser = lambda req: None

        deck_names = []
        for name in sorted(deck.card_entries.keys()):
            deck_names.extend([name] * deck.card_entries[name])
        self.duel = NetworkDuel(local_player, deck_names, is_host=False, host_ip=ip, port=port)
        self.status_label.config(text=f"正在连接 {ip}:{port} ...")

        def connect_thread():
            ok = self.duel.connect()
            if ok:
                self.after(0, lambda: self._on_connected(deck, local_player, opponent))
            else:
                self.after(0, lambda: self.status_label.config(text="连接失败", fg="red"))

        threading.Thread(target=connect_thread, daemon=True).start()

    def _on_connected(self, local_deck: Deck, local_player: Player, opponent: Player):
        opponent.name = self.duel.remote_name or "对手"
        # 重建对手的 original_deck_defs
        opponent.original_deck_defs = []
        for name in self.duel.remote_deck_list:
            cd = DEFAULT_REGISTRY.get(name)
            if cd:
                opponent.original_deck_defs.append(cd)
        # 转换远程沉浸度字符串键为 Pack 枚举
        from tards.card_db import Pack
        opp_imm = {}
        for k, v in self.duel.remote_immersion_points.items():
            try:
                pack = Pack(k)
                opp_imm[pack] = v
            except ValueError:
                pass
        opponent.immersion_points = opp_imm
        self.status_label.config(text=f"已连接！对手: {opponent.name}", fg="green")
        self.after(500, lambda: self.app.start_battle(self.duel, local_player, opponent))


class BluffDialog(tk.Toplevel):
    def __init__(self, parent, card_name: str, on_choice: Callable[[bool], None]):
        super().__init__(parent)
        self.title("阴谋激活")
        self.geometry("300x150")
        self.on_choice = on_choice
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", lambda: self._choose(False))
        tk.Label(self, text=f"[{card_name}]\n选择激活方式", font=("Microsoft YaHei", 12)).pack(pady=10)
        btn_frame = tk.Frame(self)
        btn_frame.pack(pady=10)
        tk.Button(btn_frame, text="真正激活", width=10, font=("Microsoft YaHei", 10, "bold"),
                  bg="#e3f2fd", activebackground="#bbdefb",
                  command=lambda: self._choose(True)).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="虚张声势", width=10, font=("Microsoft YaHei", 10),
                  bg="#ffebee", activebackground="#ffcdd2",
                  command=lambda: self._choose(False)).pack(side=tk.LEFT, padx=5)

    def _choose(self, is_true: bool):
        self.on_choice(is_true)
        self.grab_release()
        self.destroy()


class SacrificeDialog(tk.Toplevel):
    def __init__(self, parent, minions: List[Minion], required_blood: int, on_confirm: Callable[[List[Minion]], None]):
        super().__init__(parent)
        self.title("献祭")
        self.geometry("300x300")
        self.on_confirm = on_confirm
        self.transient(parent)
        self.grab_set()
        self.minions = minions
        self.required_blood = required_blood
        self.vars = []
        tk.Label(self, text=f"需要献祭 {required_blood} 点鲜血", font=("Microsoft YaHei", 12, "bold"), fg="#c62828").pack(pady=5)
        self.status_label = tk.Label(self, text="已选: 0 / 0", fg="red")
        self.status_label.pack(pady=5)
        list_frame = tk.Frame(self)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10)
        for m in minions:
            var = tk.BooleanVar(value=False)
            pos_str = f"{m.position}" if getattr(m, "position", None) else ""
            text = f"{m.name} ({m.attack}/{m.health}) [丰饶{m.keywords.get('丰饶',1)}] {pos_str}"
            cb = tk.Checkbutton(list_frame, text=text, variable=var, command=self._update)
            cb.pack(anchor="w")
            self.vars.append(var)
        self.confirm_btn = tk.Button(self, text="确认献祭", font=("Microsoft YaHei", 10, "bold"),
                                      bg="#ffcdd2", activebackground="#ef9a9a",
                                      command=self._confirm, state=tk.DISABLED)
        self.confirm_btn.pack(pady=5)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _update(self):
        total = sum(m.keywords.get("丰饶", 1) for var, m in zip(self.vars, self.minions) if var.get())
        enough = total >= self.required_blood
        self.status_label.config(text=f"已选: {total} / {self.required_blood}", fg="green" if enough else "red")
        self.confirm_btn.config(state=tk.NORMAL if enough else tk.DISABLED)

    def _confirm(self):
        selected = [m for var, m in zip(self.vars, self.minions) if var.get()]
        # 危险操作二次确认：献祭具有亡语的异象
        deathrattle_minions = [m for m in selected if m.keywords.get("亡语")]
        if deathrattle_minions:
            names = ", ".join(m.name for m in deathrattle_minions)
            if not messagebox.askyesno("确认献祭", f"以下异象具有亡语，献祭后将触发亡语效果：\n{names}\n\n确定要继续献祭吗？"):
                return
        self.grab_release()
        self.destroy()
        self.on_confirm(selected)

    def _on_close(self):
        self.grab_release()
        self.destroy()
        self.on_confirm([])


class DiscoverDialog(tk.Toplevel):
    def __init__(self, parent, names: List[str], on_choose: Callable[[str], None]):
        super().__init__(parent)
        self.title("开发")
        self.geometry("400x220")
        self.names = names
        self.on_choose = on_choose
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        tk.Label(self, text="选择一张卡牌加入手牌:", font=("Microsoft YaHei", 12)).pack(pady=10)
        btn_frame = tk.Frame(self)
        btn_frame.pack(pady=10)
        for name in names:
            btn = tk.Button(btn_frame, text=name, width=12, height=2, font=("Microsoft YaHei", 10),
                            bg="#e8f5e9", activebackground="#c8e6c9",
                            command=lambda n=name: self._choose(n))
            btn.pack(side=tk.LEFT, padx=5)

    def _choose(self, name: str):
        self.on_choose(name)
        self.grab_release()
        self.destroy()

    def _on_close(self):
        if self.names:
            self.on_choose(self.names[0])
        self.grab_release()
        self.destroy()


class ChoiceDialog(tk.Toplevel):
    """通用抉择弹窗，支持自定义标题和选项文案。"""

    def __init__(self, parent, title: str, options: List[str], on_choose: Callable[[str], None]):
        super().__init__(parent)
        self.title(title)
        self.options = options
        self.on_choose = on_choose
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        tk.Label(self, text="请选择一项：", font=("Microsoft YaHei", 12)).pack(pady=10)
        btn_frame = tk.Frame(self)
        btn_frame.pack(pady=10)
        for opt in options:
            btn = tk.Button(btn_frame, text=opt, width=14, height=2, font=("Microsoft YaHei", 10),
                            bg="#fff3e0", activebackground="#ffe0b2",
                            command=lambda o=opt: self._choose(o))
            btn.pack(side=tk.LEFT, padx=5)

    def _choose(self, option: str):
        self.on_choose(option)
        self.grab_release()
        self.destroy()

    def _on_close(self):
        if self.options:
            self.on_choose(self.options[0])
        self.grab_release()
        self.destroy()


# ========== 对战界面 ==========
class BattleFrame(tk.Frame):
    CELL_SIZE = 80
    COL_NAMES = ["高地", "山脊", "中路", "河岸", "水路"]
    HAND_CARD_WIDTH = 90
    HAND_CARD_HEIGHT = 120

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
        self.targeting_picker: Optional[TargetPicker] = None
        self._pending_play_data: Optional[Dict[str, Any]] = None
        self._game_thread: Optional[threading.Thread] = None
        self._targeting_source_minion: Optional[Minion] = None
        self._dragging_card = None
        self._dragging_serial = None
        self._drag_start_x = 0
        self._drag_start_y = 0
        self._drag_label = None

        self._build_ui()
        self._draw_board_grid()
        self._start_game_thread()
        self._schedule_refresh()
        self._bind_shortcuts()

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
        # space: 拍铃
        if key == "space":
            self._on_bell()
            return
        # Return: 确认指向选择（如果数量已满足）
        if key == "Return":
            if self.targeting_picker and self.targeting_picker.request.count > 0:
                if len(self.targeting_picker.selected) >= self.targeting_picker.request.count:
                    self.targeting_picker.confirm()
            return
        # a: 自动填充所有攻击目标
        if key.lower() == "a":
            self._auto_fill_attack_targets()
            return
        # 1~9: 选择对应手牌
        if key in ("1", "2", "3", "4", "5", "6", "7", "8", "9"):
            idx = int(key) - 1
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
            multi = m.keywords.get("高频", 0) or m.keywords.get("连击", 0) or m.keywords.get("多重打击", 0)
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
            self._drag_label = tk.Label(self, image=img, bg="white", relief=tk.RIDGE, bd=1)
            self._drag_label.image = img
        else:
            name = getattr(self._dragging_card, "name", "未知")
            self._drag_label = tk.Label(
                self, text=name, bg="#fff9c4", font=("Microsoft YaHei", 10, "bold"),
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
        # 拖拽距离过短视为点击，不拦截
        dist = ((event.x_root - self._drag_start_x) ** 2 +
                (event.y_root - self._drag_start_y) ** 2) ** 0.5
        if dist < 20:
            self._dragging_card = None
            self._dragging_serial = None
            return
        # 判断释放位置是否在棋盘内
        canvas_x = event.x_root - self.canvas.winfo_rootx()
        canvas_y = event.y_root - self.canvas.winfo_rooty()
        board_w = self.BOARD_COLS * self.CELL_SIZE
        board_h = self.BOARD_ROWS * self.CELL_SIZE
        if 0 <= canvas_x < board_w and 0 <= canvas_y < board_h:
            c = int(canvas_x // self.CELL_SIZE)
            r = int(canvas_y // self.CELL_SIZE)
            self._try_play_at_position(self._dragging_serial, (r, c))
        self._dragging_card = None
        self._dragging_serial = None

    def _try_play_at_position(self, serial, target):
        """尝试在指定格子直接部署卡牌（仅支持无需献祭/指向的随从卡）。"""
        if not self.duel.game:
            return
        active = self.duel.game.current_player
        if not active or serial < 1 or serial > len(active.card_hand):
            return
        card = active.card_hand[serial - 1]
        from tards.cards import MinionCard
        if not isinstance(card, MinionCard):
            self.hint_label.config(text="只能拖拽部署随从卡")
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
        if self.duel.game.board.get_minion_at(target):
            self._flash_invalid_at(target)
            return
        self._submit_play(serial, target)

    def _build_ui(self):
        # 左侧棋盘
        self.canvas = tk.Canvas(self, width=500, height=500, bg="white")
        self.canvas.pack(side=tk.LEFT, padx=10, pady=10)
        self.canvas.bind("<Button-1>", self._on_canvas_click)

        # 右侧
        right = tk.Frame(self)
        right.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=10, pady=10)

        # 阶段显示
        self.phase_label = tk.Label(right, text="等待游戏开始...", font=("Microsoft YaHei", 14, "bold"), fg="#d32f2f")
        self.phase_label.pack(fill=tk.X, pady=(0, 5))

        # 玩家信息
        info_frame = tk.LabelFrame(right, text="玩家信息", padx=5, pady=5)
        info_frame.pack(fill=tk.X, pady=5)
        self.info_labels = {}
        for pname in [self.local_player.name, self.opponent.name]:
            lbl = tk.Label(info_frame, text=f"{pname}: 等待中...", anchor="w")
            lbl.pack(fill=tk.X)
            self.info_labels[pname] = lbl

        # 牌堆 / 弃牌堆 视觉区
        deck_frame = tk.LabelFrame(right, text="牌库")
        deck_frame.pack(fill=tk.X, pady=5)
        self.deck_canvases = {}
        for pname in [self.local_player.name, self.opponent.name]:
            row = tk.Frame(deck_frame)
            row.pack(fill=tk.X, pady=2)
            tk.Label(row, text=pname, width=8, anchor="w").pack(side=tk.LEFT)
            # 牌堆
            deck_cvs = tk.Canvas(row, width=50, height=70, bg="#f5f5f5", highlightthickness=1, highlightbackground="#bdbdbd")
            deck_cvs.pack(side=tk.LEFT, padx=5)
            # 弃牌堆
            dis_cvs = tk.Canvas(row, width=50, height=70, bg="#f5f5f5", highlightthickness=1, highlightbackground="#bdbdbd")
            dis_cvs.pack(side=tk.LEFT, padx=5)
            self.deck_canvases[pname] = {"deck": deck_cvs, "discard": dis_cvs}

        # 手牌
        hand_frame = tk.LabelFrame(right, text="手牌")
        hand_frame.pack(fill=tk.X, pady=5)
        hand_canvas = tk.Canvas(hand_frame, height=self.HAND_CARD_HEIGHT + 10)
        hbar = tk.Scrollbar(hand_frame, orient=tk.HORIZONTAL, command=hand_canvas.xview)
        hand_canvas.configure(xscrollcommand=hbar.set)
        hbar.pack(side=tk.BOTTOM, fill=tk.X)
        hand_canvas.pack(side=tk.TOP, fill=tk.X, expand=True)
        self.hand_inner = tk.Frame(hand_canvas)
        hand_canvas.create_window((0, 0), window=self.hand_inner, anchor="nw")
        self.hand_inner.bind("<Configure>", lambda e, c=hand_canvas: c.configure(scrollregion=c.bbox("all")))

        # 按钮
        btn_frame = tk.Frame(right)
        btn_frame.pack(fill=tk.X, pady=5)
        self.bell_btn = tk.Button(btn_frame, text="拍铃 (双击)")
        self.bell_btn.pack(side=tk.LEFT, padx=5)
        self.bell_btn.bind("<Double-Button-1>", lambda e: self._on_bell())
        self.brake_btn = tk.Button(btn_frame, text="拉闸 (双击)")
        self.brake_btn.pack(side=tk.LEFT, padx=5)
        self.brake_btn.bind("<Double-Button-1>", lambda e: self._on_brake())
        self.exchange_btn = tk.Button(btn_frame, text="兑换矿物", command=self._on_exchange)
        self.exchange_btn.pack(side=tk.LEFT, padx=5)
        self.exchange_squirrel_btn = tk.Button(btn_frame, text="兑换松鼠", command=self._on_exchange_squirrel)
        self.exchange_squirrel_btn.pack(side=tk.LEFT, padx=5)
        self.cancel_btn = tk.Button(btn_frame, text="取消选择", command=self._on_cancel)
        self.cancel_btn.pack(side=tk.LEFT, padx=5)
        self.terminate_btn = tk.Button(btn_frame, text="终止游戏", command=self._on_terminate_game, fg="red")
        self.terminate_btn.pack(side=tk.LEFT, padx=5)

        self.hint_label = tk.Label(right, text="等待游戏开始...", fg="blue", wraplength=500)
        self.hint_label.pack(fill=tk.X, pady=5)

        # 活跃阴谋
        self.conspiracy_frame = tk.LabelFrame(right, text="活跃阴谋")
        self.conspiracy_frame.pack(fill=tk.X, pady=5)
        self.conspiracy_label = tk.Label(self.conspiracy_frame, text="无", anchor="w")
        self.conspiracy_label.pack(fill=tk.X, padx=5)

        # 操作历史
        history_frame = tk.LabelFrame(right, text="操作历史")
        history_frame.pack(fill=tk.X, pady=5)
        self.history_list = tk.Listbox(history_frame, height=5, font=("Microsoft YaHei", 9))
        self.history_list.pack(fill=tk.X, padx=5, pady=2)

        # 卡牌详情大图（悬停时显示）
        detail_frame = tk.LabelFrame(right, text="卡牌详情")
        detail_frame.pack(fill=tk.X, pady=5)
        self.detail_canvas = tk.Canvas(detail_frame, width=160, height=220, bg="#fafafa", highlightthickness=1, highlightbackground="#e0e0e0")
        self.detail_canvas.pack(padx=5, pady=5)
        self.detail_canvas.create_text(80, 110, text="悬停卡牌查看详情", fill="#9e9e9e", font=("Microsoft YaHei", 10))

        # 日志
        log_frame = tk.LabelFrame(right, text="日志")
        log_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        self.log_text = scrolledtext.ScrolledText(log_frame, state=tk.DISABLED, wrap=tk.WORD)
        self.log_text.pack(fill=tk.BOTH, expand=True)
        self.log_text.tag_config("death", foreground="#d32f2f", font=("Microsoft YaHei", 9, "bold"))
        self.log_text.tag_config("damage", foreground="#ff5722")
        self.log_text.tag_config("victory", foreground="#4caf50", font=("Microsoft YaHei", 10, "bold"))

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

    def _add_history(self, text: str):
        """添加一条操作历史记录。"""
        if not self.duel.game:
            return
        turn = self.duel.game.current_turn
        phase = self.duel.game.current_phase
        phase_map = {"draw": "抽牌", "action": "出牌", "resolve": "结算", "start": "开始", "end": "结束"}
        phase_text = phase_map.get(phase, phase)
        entry = f"回合{turn} [{phase_text}] {text}"
        self.history_list.insert(tk.END, entry)
        if self.history_list.size() > 50:
            self.history_list.delete(0)
        self.history_list.see(tk.END)

    def _preview_deploy_positions(self, serial: int):
        """悬停手牌时预览合法部署位置（绿色虚线方框）。"""
        if not self.duel.game:
            return
        active = self.duel.game.current_player
        if not active or serial < 1 or serial > len(active.card_hand):
            return
        card = active.card_hand[serial - 1]
        if not isinstance(card, MinionCard):
            return
        valid = [t for t in active.get_valid_targets(card)
                 if isinstance(t, tuple) and self.duel.game.board.is_valid_deploy(t, active, card)
                 and self.duel.game.board.get_minion_at(t) is None]
        for (r, c) in valid:
            cx = c * self.CELL_SIZE + self.CELL_SIZE // 2
            cy = r * self.CELL_SIZE + self.CELL_SIZE // 2
            self.canvas.create_rectangle(cx - 38, cy - 38, cx + 38, cy + 38,
                                         outline="#4caf50", width=2, dash=(4, 4),
                                         tags="preview_hint")

    def _clear_preview(self):
        """清除部署位置预览。"""
        self.canvas.delete("preview_hint")

    def _draw_board_grid(self):
        am = get_asset_manager()
        self._tile_image_refs = {}
        for r in range(5):
            for c in range(5):
                x1 = c * self.CELL_SIZE
                y1 = r * self.CELL_SIZE
                x2 = x1 + self.CELL_SIZE
                y2 = y1 + self.CELL_SIZE
                color = "#e0f7fa"
                terrain_id = None
                if r in (0, 1):
                    color = "#ffebee"
                    terrain_id = "terrain_enemy"
                elif r == 2:
                    color = "#f5f5f5"
                    terrain_id = "terrain_neutral"
                elif r in (3, 4):
                    color = "#e8f5e9"
                    terrain_id = "terrain_friendly"
                self.canvas.create_rectangle(x1, y1, x2, y2, fill=color, outline="black", tags=f"cell_{r}_{c}")
                # 尝试加载地形纹理
                if terrain_id:
                    tile = am.get_board_tile(terrain_id, self.CELL_SIZE)
                    if tile:
                        self._tile_image_refs[(r, c)] = tile
                        self.canvas.create_image(x1 + self.CELL_SIZE // 2, y1 + self.CELL_SIZE // 2,
                                                 image=tile, tags=f"cell_{r}_{c}")
        for c, name in enumerate(self.COL_NAMES):
            x1 = c * self.CELL_SIZE
            x2 = x1 + self.CELL_SIZE
            self.canvas.create_rectangle(x1, 0, x2, 20, fill="#cfd8dc", outline="black", tags="board_grid")
            self.canvas.create_text(c * self.CELL_SIZE + self.CELL_SIZE // 2, 5, text=name, anchor=tk.N, font=("Microsoft YaHei", 10, "bold"), tags="board_grid")

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
        multi_attack = minion.keywords.get("高频", 0) or minion.keywords.get("连击", 0) or minion.keywords.get("多重打击", 0)
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

    def _draw_keyword_icons(self, cx, cy, minion, tag):
        """在异象左下角绘制关键词缩写图标，最多3个。"""
        keyword_styles = {
            "恐惧": ("#9c27b0", "white"),
            "冰冻": ("#00bcd4", "white"),
            "眩晕": ("#ff9800", "white"),
            "休眠": ("#795548", "white"),
            "亡语": ("#607d8b", "white"),
            "迅捷": ("#2196f3", "white"),
            "潜水": ("#03a9f4", "white"),
            "潜行": ("#9e9e9e", "white"),
            "成长": ("#4caf50", "white"),
            "视野": ("#ffeb3b", "black"),
            "高频": ("#f44336", "white"),
            "连击": ("#e91e63", "white"),
            "多重打击": ("#e91e63", "white"),
            "防空": ("#009688", "white"),
            "尖刺": ("#8bc34a", "black"),
            "穿刺": ("#ff5722", "white"),
            "串击": ("#ff5722", "white"),
            "穿透": ("#ff5722", "white"),
            "横扫": ("#ff9800", "white"),
            "丰饶": ("#ff9800", "white"),
            "献祭": ("#795548", "white"),
            "协同": ("#2196f3", "white"),
            "独行": ("#ff9800", "white"),
        }

        active_keywords = []
        for k, v in minion.keywords.items():
            if v is False or v is None:
                continue
            if isinstance(v, int) and v == 0:
                continue
            if k in ("丰饶", "献祭") and v == 1:
                continue
            active_keywords.append((k, v))

        if not active_keywords:
            return

        priority = {
            "恐惧": 0, "冰冻": 0, "眩晕": 0, "休眠": 0,
            "亡语": 1, "迅捷": 1, "潜水": 1, "潜行": 1,
            "成长": 2, "视野": 3, "高频": 3, "连击": 3, "多重打击": 3,
        }
        active_keywords.sort(key=lambda x: priority.get(x[0], 99))

        am = get_asset_manager()
        for i, (k, v) in enumerate(active_keywords[:3]):
            bx = cx - 20 + i * 18
            by = cy + 18
            icon = am.get_icon(f"kw_{k}", 16)
            if icon:
                ref_key = f"{tag}_kw_{i}"
                self._minion_image_refs[ref_key] = icon
                self.canvas.create_image(bx, by, image=icon, tags=(tag, "minion", "kw_icon"))
                continue
            # 无图标时回退到色块+文字
            bg, fg = keyword_styles.get(k, ("#607d8b", "white"))
            text = k[0]
            if isinstance(v, int) and v > 1:
                text += str(v)
            elif isinstance(v, int) and v == 1 and k in ("视野", "高频", "连击", "多重打击", "横扫", "尖刺"):
                text += "1"
            self.canvas.create_rectangle(bx - 8, by - 6, bx + 8, by + 6,
                                         fill=bg, outline="white", width=1,
                                         tags=(tag, "minion", "kw_icon"))
            self.canvas.create_text(bx, by, text=text, fill=fg,
                                    font=("Microsoft YaHei", 7, "bold"),
                                    tags=(tag, "minion", "kw_icon"))

    def _render_board(self):
        self.canvas.delete("minion")
        self.canvas.delete("target_hint")
        if not self.duel.game:
            return
        am = get_asset_manager()
        self._minion_image_refs = {}
        for (r, c), m in self.duel.game.board.minion_place.items():
            cx = c * self.CELL_SIZE + self.CELL_SIZE // 2
            cy = r * self.CELL_SIZE + self.CELL_SIZE // 2
            color = "#42a5f5" if m.owner.side == self.local_player.side else "#ef5350"
            tag = f"minion_{r}_{c}"
            # 根据关键词决定边框颜色
            outline = "black"
            width = 2
            if m.keywords.get("恐惧"):
                outline = "#9c27b0"  # 紫色
                width = 3
            elif m.keywords.get("冰冻"):
                outline = "#00bcd4"  # 青色
                width = 3
            elif m.keywords.get("眩晕"):
                outline = "#ff9800"  # 橙色
                width = 3
            elif m.keywords.get("成长") is not None and m.keywords.get("成长") is not False:
                outline = "#4caf50"  # 绿色
                width = 3
            # 阴影
            self.canvas.create_rectangle(cx - 28, cy - 23, cx + 32, cy + 27, fill="#757575", outline="", tags=(tag, "minion"))
            # 尝试加载肖像缩略图
            portrait = None
            if getattr(m, "asset_id", None):
                portrait = am.get_thumbnail(m.asset_id, 56, 56)
            if portrait:
                self._minion_image_refs[(r, c)] = portrait
                self.canvas.create_image(cx, cy, image=portrait, tags=(tag, "minion", "portrait"))
                # 保留边框
                self.canvas.create_rectangle(cx - 28, cy - 25, cx + 28, cy + 25, fill="", outline=outline, width=width, tags=(tag, "minion"))
            else:
                self.canvas.create_rectangle(cx - 30, cy - 25, cx + 30, cy + 25, fill=color, outline=outline, width=width, tags=(tag, "minion"))
            self.canvas.create_text(cx, cy - 8, text=m.name, fill="white", font=("Microsoft YaHei", 9, "bold"), tags=(tag, "minion"))
            # 攻击/生命数值颜色：增强=绿，减弱=红，受伤=橙
            atk_color = "white"
            if m.current_attack > m.base_attack:
                atk_color = "#76ff03"
            elif m.current_attack < m.base_attack:
                atk_color = "#ff5252"
            hp_color = "white"
            if m.current_health < m.current_max_health:
                hp_color = "#ffab40"
            elif m.current_health > m.base_health:
                hp_color = "#76ff03"
            self.canvas.create_text(cx - 10, cy + 10, text=str(m.attack), fill=atk_color, font=("Microsoft YaHei", 10), tags=(tag, "minion"))
            self.canvas.create_text(cx, cy + 10, text="/", fill="white", font=("Microsoft YaHei", 10), tags=(tag, "minion"))
            self.canvas.create_text(cx + 10, cy + 10, text=str(m.health), fill=hp_color, font=("Microsoft YaHei", 10), tags=(tag, "minion"))
            self.canvas.tag_bind(tag, "<Enter>", lambda e, mm=m: self._show_minion_tooltip(e, mm))
            self.canvas.tag_bind(tag, "<Leave>", lambda e: self._hide_tooltip())
            self.canvas.tag_bind(tag, "<Motion>", lambda e: self._move_tooltip(e.x_root, e.y_root))
            self.canvas.tag_bind(tag, "<Button-1>", lambda e, mm=m: self._on_minion_click(mm))
            # 如果当前在指向模式中且该异象是合法目标，高亮边框
            if self.targeting_picker and m in self.targeting_picker.valid_targets:
                self.canvas.create_rectangle(cx - 32, cy - 27, cx + 32, cy + 27, outline="yellow", width=4, tags="target_hint")
            # 黄色星号：行动阶段中仍需选择攻击目标的异象
            stars = self._get_minion_pending_stars(m)
            if stars > 0:
                star_text = "★" * stars
                self.canvas.create_text(cx + 22, cy - 18, text=star_text, fill="yellow",
                                        font=("Microsoft YaHei", 10, "bold"), tags=(tag, "minion", "pending_star"))
            # 关键词图标
            self._draw_keyword_icons(cx, cy, m, tag)
            # 清除攻击预设按钮（右下角小红叉）
            pending = getattr(m, "_pending_attack_targets", None)
            if pending and isinstance(pending, list) and len(pending) > 0:
                clear_x = cx + 22
                clear_y = cy + 18
                clear_tag = f"clear_pending_{r}_{c}"
                self.canvas.create_rectangle(clear_x - 6, clear_y - 6, clear_x + 6, clear_y + 6,
                                             fill="#ff5252", outline="white", width=1,
                                             tags=(clear_tag, "minion"))
                self.canvas.create_text(clear_x, clear_y, text="×", fill="white",
                                        font=("Microsoft YaHei", 8, "bold"),
                                        tags=(clear_tag, "minion"))
                self.canvas.tag_bind(clear_tag, "<Button-1>",
                                     lambda e, pos=m.position: self._clear_attack_targets(pos))
            # 可交互指示器（行动阶段中可设置攻击目标的异象）
            if (self.duel.game and self.duel.game.current_phase == "action"
                    and m.owner == self.duel.game.current_player
                    and m.can_attack_this_turn(self.duel.game.current_turn)):
                vision = m.keywords.get("视野", 0)
                multi = m.keywords.get("高频", 0) or m.keywords.get("连击", 0) or m.keywords.get("多重打击", 0)
                if vision > 0 or (isinstance(multi, int) and multi > 0):
                    self.canvas.create_oval(cx + 18, cy - 22, cx + 26, cy - 14,
                                            fill="#76ff03", outline="white", width=1,
                                            tags=(tag, "minion", "interactive_dot"))
        # 绘制攻击预设连线
        for (r, c), m in self.duel.game.board.minion_place.items():
            pending = getattr(m, "_pending_attack_targets", None)
            if not pending or not isinstance(pending, list):
                continue
            x1 = c * self.CELL_SIZE + self.CELL_SIZE // 2
            y1 = r * self.CELL_SIZE + self.CELL_SIZE // 2
            for target in pending:
                if hasattr(target, "position") and target.position:
                    tr, tc = target.position
                    x2 = tc * self.CELL_SIZE + self.CELL_SIZE // 2
                    y2 = tr * self.CELL_SIZE + self.CELL_SIZE // 2
                    self.canvas.create_line(x1, y1, x2, y2,
                                            fill="#ffeb3b", dash=(4, 4), width=2,
                                            arrow=tk.LAST, tags=("target_arrow", "minion"))
        # 高亮指向来源异象（金色发光边框）
        if self._targeting_source_minion and self._targeting_source_minion.position:
            sr, sc = self._targeting_source_minion.position
            scx = sc * self.CELL_SIZE + self.CELL_SIZE // 2
            scy = sr * self.CELL_SIZE + self.CELL_SIZE // 2
            self.canvas.create_rectangle(scx - 34, scy - 29, scx + 34, scy + 29,
                                         outline="gold", width=4, tags="target_hint")
        # 高亮合法目标（位置）——黄色方框
        if self.valid_targets:
            for t in self.valid_targets:
                if isinstance(t, tuple) and len(t) == 2:
                    vr, vc = t
                    vcx = vc * self.CELL_SIZE + self.CELL_SIZE // 2
                    vcy = vr * self.CELL_SIZE + self.CELL_SIZE // 2
                    self.canvas.create_rectangle(vcx - 38, vcy - 38, vcx + 38, vcy + 38,
                                                 outline="#ffd600", width=4,
                                                 fill="#fff59d", stipple="gray50",
                                                 tags="target_hint")

    def _render_hand(self):
        for w in list(self.hand_inner.winfo_children()):
            w.destroy()
        active = self.duel.game and self.duel.game.current_player
        if not active:
            return
        # 网络对战中，只显示本地玩家的手牌；本地测试中，显示当前回合玩家的手牌
        if isinstance(self.duel, NetworkDuel) and active != self.local_player:
            return
        card_type_colors = {
            MinionCard: "#e3f2fd",
            Strategy: "#e8f5e9",
            Conspiracy: "#f3e5f5",
            MineralCard: "#fffde7",
        }
        am = get_asset_manager()
        cw = self.HAND_CARD_WIDTH
        ch = self.HAND_CARD_HEIGHT
        for i, card in enumerate(active.card_hand):
            base_bg = card_type_colors.get(type(card), "white")
            bg = "#fff9c4" if self.selected_card_idx == i else base_bg
            # 若当前处于指向模式且该手牌是合法目标，高亮为亮黄色
            if self.targeting_picker and card in self.targeting_picker.valid_targets:
                bg = "#ffeb3b"
            # 可操作指示：费用可负担且处于行动阶段且未在指向模式中
            cost_ok, _ = card.cost.can_afford_detail(active)
            can_play_now = (cost_ok and not self.targeting_picker
                            and self.duel.game
                            and self.duel.game.current_phase == "action")
            frame_bg = "#4caf50" if can_play_now else "white"
            frame_bd = 2 if can_play_now else 0
            serial = i + 1
            frame = tk.Frame(self.hand_inner, bg=frame_bg, bd=frame_bd)
            frame.pack(side=tk.LEFT, padx=2)
            cvs = tk.Canvas(frame, width=cw, height=ch, bg=bg, highlightthickness=0)
            cvs.pack(padx=2, pady=2)
            # 尝试加载卡面图像
            img = None
            if getattr(card, "asset_id", None):
                img = am.get_card_face(card.asset_id, cw - 4, ch - 4)
            if img:
                cvs.create_image(cw // 2, ch // 2, image=img, tags="card_img")
                cvs.image = img  # 防止被 GC
            else:
                # 纯色回退
                cvs.create_rectangle(2, 2, cw - 2, ch - 2, fill=bg, outline="#90a4ae", width=1, tags="card_bg")
            # 卡牌文字覆盖
            name = card.name
            cost_str = str(card.cost)
            stats = ""
            if isinstance(card, MinionCard):
                stats = f"{card.attack}/{card.health}"
            # 名称（顶部居中）
            cvs.create_text(cw // 2, 14, text=name, fill="#212121",
                            font=("Microsoft YaHei", 9, "bold"), tags="card_text")
            # 费用（左上角）
            cvs.create_text(10, 10, text=cost_str, fill="#d32f2f",
                            font=("Microsoft YaHei", 8, "bold"), tags="card_text")
            # 类型与攻防（底部）
            bottom_text = stats
            if isinstance(card, Strategy):
                bottom_text = "【策】"
            elif isinstance(card, Conspiracy):
                bottom_text = "【谋】"
            elif isinstance(card, MineralCard):
                bottom_text = "【矿】"
            elif isinstance(card, MinionCard):
                bottom_text = f"【随】{stats}"
            cvs.create_text(cw // 2, ch - 12, text=bottom_text, fill="#455a64",
                            font=("Microsoft YaHei", 8), tags="card_text")
            # 绑定事件
            cvs.bind("<Button-1>", lambda e, idx=i: self._on_hand_card_click(idx))
            cvs.bind("<ButtonPress-1>", lambda e, c=card, s=serial: self._on_drag_start(e, c, s))
            cvs.bind("<Enter>", lambda e, c=card, s=serial: (self._show_card_tooltip(e, c), self._preview_deploy_positions(s), self._update_detail_canvas(c)))
            cvs.bind("<Leave>", lambda e: (self._hide_tooltip(), self._clear_preview(), self._clear_detail_canvas()))
            cvs.bind("<Motion>", lambda e, c=card: self._move_tooltip(e.x_root, e.y_root))

    def _card_display_text(self, card) -> str:
        name = card.name
        cost = str(card.cost)
        type_icon = ""
        if isinstance(card, MinionCard):
            type_icon = "【随】"
        elif isinstance(card, Strategy):
            type_icon = "【策】"
        elif isinstance(card, Conspiracy):
            type_icon = "【谋】"
        elif isinstance(card, MineralCard):
            type_icon = "【矿】"
        if isinstance(card, MinionCard):
            return f"{type_icon}{name}\n{cost}费 {card.attack}/{card.health}"
        return f"{type_icon}{name}\n{cost}费"

    def _render_info(self):
        if not self.duel.game:
            return
        am = get_asset_manager()
        back_img = am.get_card_back("default", 46, 66)
        for pname, lbl in self.info_labels.items():
            player = None
            if self.duel.game.p1.name == pname:
                player = self.duel.game.p1
            elif self.duel.game.p2.name == pname:
                player = self.duel.game.p2
            if player:
                active_mark = " ●" if self.duel.game.current_player == player else ""
                lbl.config(text=(
                    f"{pname}{active_mark} | HP:{player.health}/{player.health_max} "
                    f"T:{player.t_point}/{player.t_point_max} "
                    f"C:{player.c_point}/{player.c_point_max} B:{player.b_point} S:{player.s_point} "
                    f"手牌:{len(player.card_hand)} | "
                    f"卡组:{len(player.card_deck)} 弃牌:{len(player.card_dis)} 阴谋:{len(player.active_conspiracies)}"
                ))
                # 更新牌堆/弃牌堆 Canvas
                cvs_map = self.deck_canvases.get(pname)
                if cvs_map:
                    for key, count in [("deck", len(player.card_deck)), ("discard", len(player.card_dis))]:
                        cvs = cvs_map[key]
                        cvs.delete("all")
                        if back_img:
                            cvs.create_image(25, 35, image=back_img)
                            cvs.image = back_img
                        else:
                            cvs.create_rectangle(2, 2, 48, 68, fill="#8d6e63", outline="#5d4037", width=2)
                        cvs.create_text(25, 60, text=str(count), fill="white",
                                        font=("Microsoft YaHei", 10, "bold"))
            # 绑定点击事件以支持将玩家作为指向目标
            lbl.bind("<Button-1>", lambda e, p=player: self._on_player_label_click(p))
            # 高亮提示：如果当前处于指向模式且该玩家是合法目标，改变背景色
            if self.targeting_picker and player and player in self.targeting_picker.valid_targets:
                lbl.config(bg="#fff59d", cursor="hand2")
            elif self.duel.game.current_player and self.duel.game.current_player.name == pname:
                lbl.config(bg="#e8f5e9", cursor="arrow")
            else:
                lbl.config(bg="SystemButtonFace", cursor="arrow")

    def _on_minion_click(self, minion: Minion):
        if not self.targeting_picker:
            # 没有指向模式时，尝试触发视野/高频设置
            self._handle_board_unit_click(minion.position)
            return
        if minion in self.targeting_picker.valid_targets:
            self.targeting_picker.select(minion)
            if self.targeting_picker:
                self.hint_label.config(text=self.targeting_picker.get_prompt())
                self._render_board()
                self._render_info()

    def _on_player_label_click(self, player: Optional[Player]):
        if not self.targeting_picker or not player:
            return
        if player in self.targeting_picker.valid_targets:
            self.targeting_picker.select(player)
            if self.targeting_picker:
                self.hint_label.config(text=self.targeting_picker.get_prompt())
                self._render_board()
                self._render_info()

    def process_targeting_request(self, request: TargetingRequest):
        """通用指向入口。任何需要玩家选择目标的行为都调用此方法。"""
        self.targeting_picker = TargetPicker(request)
        self.valid_targets = request.valid_targets
        self.hint_label.config(text=self.targeting_picker.get_prompt(), font=("Microsoft YaHei", 12, "bold"), fg="#d32f2f")
        self._render_board()
        self._render_info()

    def _enter_targeting_mode(self, picker: TargetPicker, clear_card_selection: bool = True):
        """兼容旧入口，内部转发到 process_targeting_request。"""
        req = TargetingRequest(
            valid_targets=picker.valid_targets,
            count=picker.request.count if hasattr(picker, 'request') else 1,
            allow_repeat=picker.request.allow_repeat if hasattr(picker, 'request') else False,
            prompt=picker.get_prompt().split(" (")[0] if hasattr(picker, 'get_prompt') else "请选择目标",
            on_confirm=picker.on_confirm,
            on_cancel=picker.on_cancel,
        )
        self.process_targeting_request(req)
        if clear_card_selection:
            self.selected_card = None
            self.selected_card_idx = None

    def _exit_targeting_mode(self):
        self.targeting_picker = None
        self.valid_targets = []
        self._pending_play_data = None
        self.selected_card = None
        self.selected_card_idx = None
        self._targeting_source_minion = None
        self.hint_label.config(text="", font=("Microsoft YaHei", 10), fg="blue")
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

    def _handle_board_unit_click(self, target):
        """处理玩家点击场上自己的异象。"""
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
        vision = m.keywords.get("视野", 0)
        can_attack = m.can_attack_this_turn(self.duel.game.current_turn)
        if vision <= 0 and not can_attack:
            return
        multi_attack = m.keywords.get("高频", 0) or m.keywords.get("连击", 0) or m.keywords.get("多重打击", 0)
        atk_candidates = get_attack_target_candidates(m, self.duel.game)
        if not atk_candidates:
            return

        count = multi_attack if isinstance(multi_attack, int) else 1
        req = TargetingRequest(
            valid_targets=atk_candidates,
            count=count,
            allow_repeat=True,
            prompt=f"请选择 {m.name} 的 {count} 个攻击目标",
            on_confirm=lambda selected_atks: (
                self.duel.submit_local_action({
                    "type": "set_attack_targets",
                    "pos": m.position,
                    "targets": selected_atks,
                }),
                self._exit_targeting_mode(),
            ),
            on_cancel=self._exit_targeting_mode,
        )
        self._targeting_source_minion = m
        self.process_targeting_request(req)

    def _on_hand_card_click(self, idx: int):
        active = self.duel.game and self.duel.game.current_player
        if not active or idx >= len(active.card_hand):
            return
        # 网络对战中，只能操作本地玩家；本地测试中，当前回合玩家均可操作
        if isinstance(self.duel, NetworkDuel) and active != self.local_player:
            return
        card = active.card_hand[idx]

        # 若当前处于指向模式且该手牌是合法目标，选择它作为指向目标
        if self.targeting_picker and card in self.targeting_picker.valid_targets:
            self.targeting_picker.select(card)
            if self.targeting_picker:
                self.hint_label.config(text=self.targeting_picker.get_prompt())
                self._render_board()
                self._render_info()
                self._render_hand()
            return

        serial = idx + 1

        # Conspiracy：先选虚张声势，再进入通用指向管道
        if isinstance(card, Conspiracy):
            def on_bluff_choice(is_true: bool):
                if is_true:
                    valid = [t for t in active.get_valid_targets(card) if active.card_can_play(serial, t)[0]]
                    if valid:
                        req = TargetingRequest(
                            valid_targets=valid,
                            count=getattr(card, "targets_count", 1),
                            allow_repeat=getattr(card, "targets_repeat", False),
                            prompt=f"请选择 [{card.name}] 的目标",
                            on_confirm=lambda selected: (
                                self._submit_play(serial, selected[0], bluff=False,
                                                  extra_targets=selected[1:] or None),
                                self._exit_targeting_mode(),
                            ),
                            on_cancel=self._exit_targeting_mode,
                        )
                        self.process_targeting_request(req)
                    else:
                        self._submit_play(serial, None, bluff=False)
                else:
                    self._submit_play(serial, None, bluff=True)
                    self.hint_label.config(text=f"[{card.name}] 虚张声势")
            BluffDialog(self, card.name, on_bluff_choice)
            return

        # 随从卡：先处理献祭，再进入通用多阶段指向管道
        if isinstance(card, MinionCard):
            if card.cost.b > 0:
                minions = list(self.duel.game.board.get_minions_of_player(active)) if self.duel.game else []
                if not minions:
                    self.hint_label.config(text="场上没有可献祭的友方异象")
                    return
                def on_sacrifice_confirm(selected: List[Minion]):
                    total = sum(m.keywords.get("丰饶", 1) for m in selected)
                    if total < card.cost.b:
                        self.hint_label.config(text="献祭不足，无法部署")
                        return
                    self._pending_sacrifices = selected
                    self._run_targeting_pipeline(serial, card, idx, is_minion=True)
                SacrificeDialog(self, minions, card.cost.b, on_sacrifice_confirm)
                return
            self._run_targeting_pipeline(serial, card, idx, is_minion=True)
            return

        # 策略/矿物/阴谋卡等：进入通用多阶段指向管道
        self._run_targeting_pipeline(serial, card, idx, is_minion=False)

    def _run_targeting_pipeline(self, serial: int, card, idx: int, is_minion: bool):
        """通用多阶段指向管道。随从卡和策略卡共用。
        第一阶段：随从卡选部署位置，策略卡选效果主目标。
        后续阶段：extra_targeting_stages 定义的额外目标。"""
        active = self.duel.game.current_player
        stages = list(getattr(card, "extra_targeting_stages", []))
        selected_targets: List[Any] = []
        total_stages = len(stages) + 1

        def run_stage(stage_idx: int):
            if stage_idx == 0:
                # 第一阶段：主目标
                if is_minion:
                    valid = [t for t in active.get_valid_targets(card)
                             if isinstance(t, tuple) and self.duel.game
                             and self.duel.game.board.is_valid_deploy(t, active, card)
                             and self.duel.game.board.get_minion_at(t) is None]
                    prompt = f"[{card.name}] 阶段 1/{total_stages}：请选择部署位置"
                    count = 1
                    repeat = False
                else:
                    valid = [t for t in active.get_valid_targets(card) if active.card_can_play(serial, t)[0]]
                    prompt = f"[{card.name}] 阶段 1/{total_stages}：请选择效果目标"
                    count = getattr(card, "targets_count", 1)
                    repeat = getattr(card, "targets_repeat", False)
            else:
                stage_def = stages[stage_idx - 1]
                if isinstance(stage_def, (list, tuple)):
                    fn, count, repeat = stage_def[0], stage_def[1], stage_def[2]
                else:
                    fn = stage_def.get("fn")
                    count = stage_def.get("count", 1)
                    repeat = stage_def.get("repeat", False)
                valid = list(fn(active, self.duel.game.board))
                prompt = f"[{card.name}] 阶段 {stage_idx + 1}/{total_stages}：请选择额外目标"

            if not valid:
                if stage_idx < len(stages):
                    run_stage(stage_idx + 1)
                else:
                    self._submit_play(serial, selected_targets[0] if selected_targets else None,
                                      extra_targets=selected_targets[1:] or None)
                    self._exit_targeting_mode()
                return

            # 快捷路径：唯一合法目标是 None（非指向性）
            if len(valid) == 1 and valid[0] is None:
                if stage_idx < len(stages):
                    run_stage(stage_idx + 1)
                else:
                    self._submit_play(serial, None)
                    self._exit_targeting_mode()
                return

            # 单目标自动确认：只有一个合法目标时直接选中
            if count == 1 and len(valid) == 1:
                selected_targets.extend([valid[0]])
                if stage_idx < len(stages):
                    run_stage(stage_idx + 1)
                else:
                    self._submit_play(serial, selected_targets[0] if selected_targets else None,
                                      extra_targets=selected_targets[1:] or None)
                    self._exit_targeting_mode()
                return

            req = TargetingRequest(
                valid_targets=valid,
                count=count,
                allow_repeat=repeat,
                prompt=prompt,
                on_confirm=lambda sel: (
                    selected_targets.extend(sel),
                    run_stage(stage_idx + 1) if stage_idx < len(stages) else (
                        self._submit_play(serial, selected_targets[0],
                                          extra_targets=selected_targets[1:] or None),
                        self._exit_targeting_mode(),
                    ),
                ),
                on_cancel=self._exit_targeting_mode,
            )
            self.process_targeting_request(req)

        run_stage(0)
        self.selected_card_idx = idx
        self.selected_card = card

    def _on_deploy_pos_selected(self, serial: int, card, pos):
        """[兼容 shim] 部署位置选定后直接提交。额外目标已由 _run_targeting_pipeline 处理。"""
        self._submit_play(serial, pos)
        self._exit_targeting_mode()

    def _flash_invalid_at(self, target):
        """在指定位置闪烁红色边框，提示非法操作。"""
        if not self.duel.game:
            return
        if isinstance(target, tuple) and len(target) == 2:
            r, c = target
        elif hasattr(target, "position") and target.position:
            r, c = target.position
        else:
            return
        cx = c * self.CELL_SIZE + self.CELL_SIZE // 2
        cy = r * self.CELL_SIZE + self.CELL_SIZE // 2
        flash = self.canvas.create_rectangle(cx - 40, cy - 40, cx + 40, cy + 40,
                                             outline="#ff1744", width=4,
                                             tags="flash_hint")
        self.after(200, lambda: self.canvas.delete("flash_hint"))

    def _on_canvas_click(self, event):
        active = self.duel.game and self.duel.game.current_player
        if not active:
            return
        # 网络对战中，只能操作本地玩家；本地测试中，当前回合玩家均可操作
        if isinstance(self.duel, NetworkDuel) and active != self.local_player:
            return
        c = event.x // self.CELL_SIZE
        r = event.y // self.CELL_SIZE
        target = (r, c)

        # 1. 如果有目标选择器进行中，优先处理目标选择
        if self.targeting_picker:
            clicked_target = None
            if target in self.valid_targets:
                clicked_target = target
            else:
                if self.duel.game:
                    m = self.duel.game.board.get_minion_at(target)
                    if m and m in self.valid_targets:
                        clicked_target = m
            if clicked_target is not None:
                self.targeting_picker.select(clicked_target)
                if self.targeting_picker:
                    self.hint_label.config(text=self.targeting_picker.get_prompt())
                    self._render_board()
                    self._render_info()
            else:
                self._flash_invalid_at(target)
                self.hint_label.config(text="点击的不是合法目标", fg="red")
                self.after(500, lambda: self.hint_label.config(fg="blue") if self.hint_label else None)
            return

        # 2. 如果没有选中的手牌，检查是否点击了场上的可交互异象（视野/高频）
        if not self.selected_card or not self.valid_targets:
            self._handle_board_unit_click(target)
            return

        # 3. 手牌选择中的原有逻辑
        if isinstance(self.selected_card, MinionCard):
            if target in self.valid_targets:
                self._submit_play(self.selected_card_idx + 1, target)
            else:
                self._flash_invalid_at(target)
                self.hint_label.config(text="点击的不是合法目标", fg="red")
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
        self.hint_label.config(text="点击的不是合法目标", fg="red")
        self.after(1000, self._reset_guide_hint)

    def _submit_play(self, serial: int, target: Any, bluff: bool = False, extra_targets: Optional[List[Any]] = None):
        active = self.duel.game.current_player if self.duel.game else None
        if active and 1 <= serial <= len(active.card_hand):
            card = active.card_hand[serial - 1]
            if card.cost.b >= 3:
                if not messagebox.askyesno("确认出牌", f"确定要打出 [{card.name}] 吗？\n费用: {card.cost}"):
                    self._exit_targeting_mode()
                    return
        self._exit_targeting_mode()
        action = {"type": "play", "serial": serial, "target": target, "bluff": bluff}
        if extra_targets:
            action["extra_targets"] = extra_targets
        sacrifices = getattr(self, "_pending_sacrifices", None)
        if sacrifices:
            action["sacrifices"] = sacrifices
            self._pending_sacrifices = []
        self._clear_selection()
        self.duel.submit_local_action(action)
        card_name = active.card_hand[serial - 1].name if active and 1 <= serial <= len(active.card_hand) else "未知卡牌"
        self._add_history(f"打出 [{card_name}]")
        self.hint_label.config(text="已出牌，等待结果...")
        self.after(2000, self._reset_guide_hint)

    def _reset_guide_hint(self):
        """根据当前阶段恢复引导文字。"""
        if not self.duel.game or not self.hint_label:
            return
        phase = self.duel.game.current_phase
        if phase == "action":
            if self.targeting_picker:
                self.hint_label.config(text="指向模式：点击目标确认 | Enter确认 | ESC取消", fg="#d32f2f", font=("Microsoft YaHei", 12, "bold"))
            else:
                self.hint_label.config(text="出牌阶段：点击手牌出牌 | 点击异象设攻击目标 | 双击拍铃/拉闸 | B拉闸 Space拍铃 | 1~9快捷选牌 | ESC取消", fg="blue", font=("Microsoft YaHei", 10))
        elif phase == "resolve":
            self.hint_label.config(text="结算阶段进行中，请稍候...", fg="#b71c1c", font=("Microsoft YaHei", 10))
        elif phase == "draw":
            self.hint_label.config(text="抽牌阶段...", fg="#1565c0", font=("Microsoft YaHei", 10))

    def _on_bell(self):
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
        if self.targeting_picker:
            self.targeting_picker.cancel()
            self._exit_targeting_mode()
        else:
            self._clear_selection()

    def _on_exchange(self):
        active = self.duel.game and self.duel.game.current_player
        if not active:
            return
        if isinstance(self.duel, NetworkDuel) and active != self.local_player:
            return
        from tards.card_db import Pack
        if active.immersion_points.get(Pack.DISCRETE, 0) < 1:
            messagebox.showinfo("兑换矿物", "你没有离散沉浸度，无法兑换矿物")
            return

        minerals = []
        for name, card_def in DEFAULT_REGISTRY._cards.items():
            if card_def.card_type == CardType.MINERAL:
                tmp_card = card_def.to_game_card(active)
                if tmp_card.exchange_cost.can_afford(active):
                    minerals.append((name, card_def.cost, card_def.mineral_type))

        if not minerals:
            messagebox.showinfo("兑换矿物", "当前没有可兑换的矿物")
            return

        win = tk.Toplevel(self)
        win.title("兑换矿物")
        win.geometry("300x200")
        tk.Label(win, text="选择要兑换的矿物:").pack(pady=5)

        var = tk.StringVar(win)
        options = [f"{name} ({cost}) [{mtype}]" for name, cost, mtype in minerals]
        var.set(options[0])
        menu = tk.OptionMenu(win, var, *options)
        menu.pack(pady=5)

        def do_exchange():
            selected = var.get()
            name = selected.split(" ")[0]
            self.duel.submit_local_action({"type": "exchange", "card_name": name})
            win.destroy()
            self._add_history(f"兑换矿物 [{name}]")
            self.hint_label.config(text=f"已兑换 {name}")
            self.after(1500, self._reset_guide_hint)

        tk.Button(win, text="确认兑换", command=do_exchange).pack(pady=5)
        tk.Button(win, text="取消", command=win.destroy).pack(pady=5)

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
        self._add_history("兑换松鼠")
        self.hint_label.config(text="已兑换松鼠")

    def _clear_selection(self):
        self.selected_card_idx = None
        self.selected_card = None
        self.valid_targets = []
        self._pending_sacrifices = []
        self._render_hand()
        self._render_board()

    def _schedule_refresh(self):
        self._try_refresh()
        self.after(200, self._schedule_refresh)

    def _try_refresh(self):
        if gui_refresh_event.is_set():
            gui_refresh_event.clear()
            self._render_info()
            self._render_board()
            self._render_hand()
            if self.duel.game:
                active = self.duel.game.current_player
                if isinstance(self.duel, NetworkDuel):
                    if active == self.local_player:
                        self.hint_label.config(text=f"轮到你的行动")
                    else:
                        self.hint_label.config(text=f"等待 {active.name} 行动...")
                else:
                    self.hint_label.config(text=f"轮到 {active.name} 行动")
        # 活跃阴谋显示（网络对战只显示自己的，本地测试显示当前回合玩家的）
        conspiracies_player = self.local_player
        if not isinstance(self.duel, NetworkDuel) and self.duel.game and self.duel.game.current_player:
            conspiracies_player = self.duel.game.current_player
        if conspiracies_player.active_conspiracies:
            names = ", ".join(c.name for c in conspiracies_player.active_conspiracies)
            self.conspiracy_label.config(text=names)
        else:
            self.conspiracy_label.config(text="无")
        if self.duel.game:
            phase_map = {
                "draw": "抽牌阶段",
                "action": "出牌阶段",
                "resolve": "结算阶段",
                "start": "回合开始",
                "end": "回合结束",
            }
            phase_text = phase_map.get(self.duel.game.current_phase, self.duel.game.current_phase or "")
            turn = self.duel.game.current_turn
            phase = self.duel.game.current_phase
            if phase == "resolve":
                self.phase_label.config(text=f"回合 {turn} | {phase_text}", bg="#ffcdd2", fg="#b71c1c", font=("Microsoft YaHei", 16, "bold"))
            elif phase == "action":
                self.phase_label.config(text=f"回合 {turn} | {phase_text}", bg="#c8e6c9", fg="#1b5e20", font=("Microsoft YaHei", 14, "bold"))
            else:
                self.phase_label.config(text=f"回合 {turn} | {phase_text}", bg="SystemButtonFace", fg="#d32f2f", font=("Microsoft YaHei", 14, "bold"))
            self.app.root.title(f"Tards 对战 - 回合{turn} {phase_text}")
        else:
            self.phase_label.config(text="等待游戏开始...")
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
            if has_underworld:
                self.exchange_squirrel_btn.pack(side=tk.LEFT, padx=5)
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
            else:
                self.exchange_squirrel_btn.pack_forget()

    def _start_game_thread(self):
        self.duel.local_turn_callback = lambda: gui_refresh_event.set()
        self.duel.game_over_callback = lambda winner: self.after(0, lambda: self._on_gameover(winner))
        self.duel.discover_request_callback = lambda names: self.after(0, lambda: self._show_discover(names))
        self.duel.choice_request_callback = lambda options, title: self.after(0, lambda: self._show_choice(options, title))
        self.local_player.sacrifice_chooser = self._make_sacrifice_chooser()
        self.opponent.sacrifice_chooser = self._make_sacrifice_chooser()

        def run():
            import time
            # 创建对局日志写入器（同时写文件和控制台）
            log_writer = BattleLogWriter.create_for_battle()
            self._log_path = getattr(log_writer, "log_path", None)
            old_stdout = sys.stdout
            sys.stdout = self._GuiLogWriter(self, log_writer)
            try:
                self.duel.resolve_step_callback = lambda: (
                    gui_refresh_event.set(),
                    time.sleep(0.4),
                )
                self.duel.run_game(self.opponent)
            except Exception as e:
                import traceback
                error_msg = f"游戏线程异常: {e}\n{traceback.format_exc()}"
                print(error_msg)
                self.after(0, lambda: messagebox.showerror("游戏错误", error_msg))
            finally:
                self.duel.resolve_step_callback = None
                sys.stdout = old_stdout
                log_writer.close()

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

    def _fmt_keywords(self, keywords: dict) -> str:
        parts = []
        for k, v in keywords.items():
            if v is True:
                parts.append(k)
            else:
                parts.append(f"{k}{v}")
        return " ".join(parts)

    def _show_card_tooltip(self, event, card):
        lines = [card.name, f"费用: {card.cost}"]
        if isinstance(card, MinionCard):
            lines.append(f"攻击/生命: {card.attack}/{card.health}")
        if getattr(card, "keywords", None):
            lines.append(f"关键词: {self._fmt_keywords(card.keywords)}")
        text = "\n".join(lines)
        self._tooltip = Tooltip(self.hand_inner, text, event.x_root, event.y_root)

    def _show_minion_tooltip(self, event, minion):
        lines = [minion.name]
        atk_text = str(minion.attack)
        if minion.current_attack != minion.base_attack:
            atk_text += f" (基础{minion.base_attack})"
        hp_text = str(minion.health)
        if minion.current_health != minion.base_health or minion.current_max_health != minion.base_max_health:
            hp_text += f" (基础{minion.base_health}/{minion.base_max_health})"
        lines.append(f"攻击/生命: {atk_text}/{hp_text}")
        if minion.keywords:
            lines.append(f"关键词: {self._fmt_keywords(minion.keywords)}")
        # 指向关系
        pending = getattr(minion, "_pending_attack_targets", None)
        if pending and isinstance(pending, list) and len(pending) > 0:
            target_names = []
            for t in pending:
                if hasattr(t, "name"):
                    target_names.append(t.name)
                else:
                    target_names.append(str(t))
            lines.append(f"攻击目标: {' → '.join(target_names)}")
        # 被哪些异象指向（攻击目标 + 特殊效果目标）
        pointed_by = []
        if self.duel.game and self.duel.game.board:
            for m in self.duel.game.board.minion_place.values():
                if m is minion:
                    continue
                m_pending = getattr(m, "_pending_attack_targets", None)
                if m_pending and isinstance(m_pending, list) and minion in m_pending:
                    pointed_by.append(m.name)
                    continue
                # 通用反向查找：检查其他异象的实例属性是否引用本异象
                for val in vars(m).values():
                    if val is minion:
                        pointed_by.append(m.name)
                        break
                    if isinstance(val, (list, tuple, set)) and minion in val:
                        pointed_by.append(m.name)
                        break
        if pointed_by:
            lines.append(f"被指向: {', '.join(pointed_by)}")
        text = "\n".join(lines)
        self._tooltip = Tooltip(self.canvas, text, event.x_root, event.y_root)

    def _move_tooltip(self, x, y):
        if self._tooltip:
            self._tooltip.move(x, y)

    def _hide_tooltip(self):
        if self._tooltip:
            self._tooltip.destroy()
            self._tooltip = None

    def _on_terminate_game(self):
        """终止当前对局并返回主菜单。日志已由 BattleLogWriter 自动保存。"""
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

    def _on_gameover(self, winner_name: Optional[str]):
        msg = f"游戏结束！胜者: {winner_name}" if winner_name else "游戏结束：平局"
        messagebox.showinfo("对战结束", msg)
        if hasattr(self.duel, "close"):
            self.duel.close()
        self.app.show_menu()

    class _GuiLogWriter:
        """把 print 输出同步到 GUI 日志框，实际文件写入委托给 BattleLogWriter。"""
        def __init__(self, gui: "BattleFrame", log_writer):
            self.gui = gui
            self.log_writer = log_writer
        def write(self, s: str):
            if s.strip():
                msg = s.strip()
                self.gui.after(0, lambda msg=msg: self.gui._log(msg))
                self.log_writer.write(msg + "\n")
        def flush(self):
            self.log_writer.flush()


def main():
    root = tk.Tk()
    app = TardsApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
