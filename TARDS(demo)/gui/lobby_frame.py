"""联机对战大厅界面。

原位于 Gamestart.py，现独立为单独的 Frame 模块。
"""

from __future__ import annotations

import threading
import tkinter as tk
from tkinter import messagebox, ttk
from typing import TYPE_CHECKING, Optional

from tards import Player
from tards.card_db import DEFAULT_REGISTRY, Pack
from tards.deck import Deck
from tards.deck_io import list_saved_decks, load_deck
from tards.net_game import NetworkDuel

from gui.theme import UI_THEME
from gui.utils import _deck_defs_list

if TYPE_CHECKING:
    from Gamestart import TardsApp


class LobbyFrame(tk.Frame):
    def __init__(self, parent, app: "TardsApp", is_host: bool):
        super().__init__(parent)
        self.app = app
        self.is_host = is_host
        self.duel: Optional[NetworkDuel] = None
        self._build()

    def _build(self):
        self.config(bg=UI_THEME["bg_main"])
        tk.Button(self, text="← 返回主菜单", bg=UI_THEME["btn_secondary_bg"], fg=UI_THEME["btn_secondary_fg"],
                  activebackground=UI_THEME["btn_secondary_active"], relief=tk.RAISED, bd=1,
                  command=self.app.show_menu).pack(anchor="nw", padx=10, pady=5)

        tk.Label(self, text="选择卡组:", bg=UI_THEME["bg_main"], fg=UI_THEME["text_primary"]).pack(anchor="w", padx=10, pady=5)
        self.deck_combo = ttk.Combobox(self, values=list_saved_decks(), state="readonly", width=30)
        self.deck_combo.pack(anchor="w", padx=10)
        if self.deck_combo["values"]:
            self.deck_combo.current(0)

        tk.Label(self, text="玩家名:", bg=UI_THEME["bg_main"], fg=UI_THEME["text_primary"]).pack(anchor="w", padx=10, pady=5)
        self.name_entry = tk.Entry(self, width=20, bg=UI_THEME["bg_panel"], fg=UI_THEME["text_primary"],
                                   insertbackground=UI_THEME["text_primary"])
        self.name_entry.insert(0, "玩家A" if self.is_host else "玩家B")
        self.name_entry.pack(anchor="w", padx=10)

        if self.is_host:
            tk.Label(self, text="端口:", bg=UI_THEME["bg_main"], fg=UI_THEME["text_primary"]).pack(anchor="w", padx=10, pady=5)
            self.port_entry = tk.Entry(self, width=10, bg=UI_THEME["bg_panel"], fg=UI_THEME["text_primary"],
                                       insertbackground=UI_THEME["text_primary"])
            self.port_entry.insert(0, "9876")
            self.port_entry.pack(anchor="w", padx=10)

            self.ngrok_var = tk.BooleanVar(value=False)
            tk.Checkbutton(self, text="使用内网穿透（跨网络联机）", variable=self.ngrok_var,
                           bg=UI_THEME["bg_main"], fg=UI_THEME["text_primary"], selectcolor=UI_THEME["bg_panel"],
                           command=self._toggle_ngrok).pack(anchor="w", padx=10, pady=5)

            self.ngrok_frame = tk.Frame(self, bg=UI_THEME["bg_main"])
            self.ngrok_frame.pack(anchor="w", padx=10, fill="x")
            tk.Label(self.ngrok_frame, text="ngrok Authtoken（可选，首次使用需填写）:",
                     bg=UI_THEME["bg_main"], fg=UI_THEME["text_secondary"]).pack(anchor="w")
            self.ngrok_token_entry = tk.Entry(self.ngrok_frame, width=40, show="*",
                                              bg=UI_THEME["bg_panel"], fg=UI_THEME["text_primary"],
                                              insertbackground=UI_THEME["text_primary"])
            self.ngrok_token_entry.pack(anchor="w")
            self.ngrok_url_label = tk.Label(self.ngrok_frame, text="", fg=UI_THEME["success"], wraplength=400,
                                            bg=UI_THEME["bg_main"])
            self.ngrok_url_label.pack(anchor="w", pady=5)
            self.ngrok_frame.pack_forget()  # 默认隐藏

            tk.Button(self, text="创建房间并等待", font=("Microsoft YaHei", 14),
                      bg=UI_THEME["btn_primary_bg"], fg=UI_THEME["btn_primary_fg"],
                      activebackground=UI_THEME["btn_primary_active"], relief=tk.RAISED, bd=1,
                      command=self._start_host).pack(pady=20)
        else:
            tk.Label(self, text="Host 地址（IP 或 ngrok 地址）:", bg=UI_THEME["bg_main"], fg=UI_THEME["text_primary"]).pack(anchor="w", padx=10, pady=5)
            self.ip_entry = tk.Entry(self, width=30, bg=UI_THEME["bg_panel"], fg=UI_THEME["text_primary"],
                                     insertbackground=UI_THEME["text_primary"])
            self.ip_entry.insert(0, "127.0.0.1")
            self.ip_entry.pack(anchor="w", padx=10)
            tk.Label(self, text="端口:", bg=UI_THEME["bg_main"], fg=UI_THEME["text_primary"]).pack(anchor="w", padx=10, pady=5)
            self.port_entry = tk.Entry(self, width=10, bg=UI_THEME["bg_panel"], fg=UI_THEME["text_primary"],
                                       insertbackground=UI_THEME["text_primary"])
            self.port_entry.insert(0, "9876")
            self.port_entry.pack(anchor="w", padx=10)
            tk.Button(self, text="加入房间", font=("Microsoft YaHei", 14),
                      bg=UI_THEME["btn_primary_bg"], fg=UI_THEME["btn_primary_fg"],
                      activebackground=UI_THEME["btn_primary_active"], relief=tk.RAISED, bd=1,
                      command=self._start_client).pack(pady=20)

        self.status_label = tk.Label(self, text="", fg=UI_THEME["accent"], bg=UI_THEME["bg_main"])
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

    def _toggle_ngrok(self):
        if self.ngrok_var.get():
            self.ngrok_frame.pack(anchor="w", padx=10, fill="x", before=self.status_label)
        else:
            self.ngrok_frame.pack_forget()

    def _start_host(self):
        deck = self._get_selected_deck()
        if not deck:
            return
        pname = self.name_entry.get().strip() or "玩家A"
        port = int(self.port_entry.get() or 9876)
        use_ngrok = getattr(self, 'ngrok_var', None) and self.ngrok_var.get()
        ngrok_token = self.ngrok_token_entry.get().strip() if use_ngrok else None

        local_player = Player(side=0, name=pname, diver="Net", card_deck=deck.to_game_deck(None), original_deck_defs=_deck_defs_list(deck))
        local_player.sacrifice_chooser = lambda req: None
        local_player.immersion_points = dict(deck.immersion_points)
        opponent = Player(side=1, name="等待中...", diver="Net", card_deck=[])
        opponent.sacrifice_chooser = lambda req: None

        deck_names = []
        for name in sorted(deck.card_entries.keys()):
            deck_names.extend([name] * deck.card_entries[name])
        self.duel = NetworkDuel(local_player, deck_names, is_host=True, port=port,
                                use_ngrok=use_ngrok, ngrok_token=ngrok_token)

        if use_ngrok:
            self.status_label.config(text=f"正在启动内网穿透隧道...")
        else:
            self.status_label.config(text=f"等待连接于端口 {port} ...")

        def connect_thread():
            ok = self.duel.connect()
            if ok:
                if use_ngrok:
                    url = self.duel.get_ngrok_url()
                    self.after(0, lambda: self.ngrok_url_label.config(text=f"公网地址: {url}", fg=UI_THEME["success"]))
                self.after(0, lambda: self._on_connected(deck, local_player, opponent))
            else:
                self.after(0, lambda: self.status_label.config(text="连接失败", fg=UI_THEME["danger"]))

        threading.Thread(target=connect_thread, daemon=True).start()

    def _parse_host_address(self, raw: str) -> tuple[str, int]:
        """解析 Host 地址，支持普通 IP:端口 和 ngrok tcp://host:port 格式。"""
        raw = raw.strip()
        # 去掉 tcp:// 前缀
        if raw.startswith("tcp://"):
            raw = raw[6:]
        # 尝试解析 host:port 格式
        if ":" in raw:
            host, port_str = raw.rsplit(":", 1)
            try:
                return host, int(port_str)
            except ValueError:
                pass
        # 回退到单独 IP，使用默认端口
        return raw, 9876

    def _start_client(self):
        deck = self._get_selected_deck()
        if not deck:
            return
        pname = self.name_entry.get().strip() or "玩家B"
        raw_addr = self.ip_entry.get().strip() or "127.0.0.1"
        ip, port = self._parse_host_address(raw_addr)

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
                self.after(0, lambda: self.status_label.config(text="连接失败", fg=UI_THEME["danger"]))

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
        opp_imm = {}
        for k, v in self.duel.remote_immersion_points.items():
            try:
                pack = Pack(k)
                opp_imm[pack] = v
            except ValueError:
                pass
        opponent.immersion_points = opp_imm
        self.status_label.config(text=f"已连接！对手: {opponent.name}", fg=UI_THEME["success"])
        self.after(500, lambda: self.app.start_battle(self.duel, local_player, opponent))
