"""主菜单界面。

原位于 Gamestart.py，现独立为单独的 Frame 模块。
"""

from __future__ import annotations

import re
import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk
from typing import TYPE_CHECKING, Optional

from tards import Player
from tards.card_db import DEFAULT_REGISTRY
from tards.deck_io import list_saved_decks, load_deck

from gui.theme import UI_THEME, _RULES_TEXT
from gui.utils import _insert_rule_text, _deck_defs_list
from local_duel import LocalDuel

if TYPE_CHECKING:
    from Gamestart import TardsApp


class MenuFrame(tk.Frame):
    def __init__(self, parent, app: "TardsApp"):
        super().__init__(parent)
        self.app = app
        self._build()

    def _build(self):
        self.config(bg=UI_THEME["bg_main"])
        tk.Label(self, text="Tards", font=("Microsoft YaHei", 36, "bold"),
                 bg=UI_THEME["bg_main"], fg=UI_THEME["accent"]).pack(pady=(60, 30))
        tk.Label(self, text="战术式卡牌对战", font=("Microsoft YaHei", 12),
                 bg=UI_THEME["bg_main"], fg=UI_THEME["text_secondary"]).pack(pady=(0, 50))

        btn_specs = [
            ("开始对战", self._show_battle_dialog, "primary"),
            ("你的卡组", self._show_deck_dialog, "secondary"),
            ("关于游戏", self._show_about_dialog, "secondary"),
            ("退出游戏", self._on_exit, "danger"),
        ]
        for text, cmd, style in btn_specs:
            if style == "primary":
                btn = tk.Button(self, text=text, font=("Microsoft YaHei", 14), width=18,
                                bg=UI_THEME["btn_primary_bg"], fg=UI_THEME["btn_primary_fg"],
                                activebackground=UI_THEME["btn_primary_active"],
                                activeforeground=UI_THEME["btn_primary_fg"],
                                relief=tk.RAISED, bd=2, command=cmd)
            elif style == "danger":
                btn = tk.Button(self, text=text, font=("Microsoft YaHei", 14), width=18,
                                bg=UI_THEME["btn_danger_bg"], fg=UI_THEME["btn_danger_fg"],
                                activebackground=UI_THEME["btn_danger_active"],
                                activeforeground=UI_THEME["btn_danger_fg"],
                                relief=tk.RAISED, bd=2, command=cmd)
            else:
                btn = tk.Button(self, text=text, font=("Microsoft YaHei", 14), width=18,
                                bg=UI_THEME["bg_panel"], fg=UI_THEME["text_primary"],
                                activebackground=UI_THEME["btn_secondary_active"],
                                relief=tk.RAISED, bd=1, command=cmd)
            btn.pack(pady=10)

    def _center_window(self, window, width, height):
        window.update_idletasks()
        x = (window.winfo_screenwidth() // 2) - (width // 2)
        y = (window.winfo_screenheight() // 2) - (height // 2)
        window.geometry(f"{width}x{height}+{x}+{y}")

    def _show_menu_dialog(self, title, options):
        win = tk.Toplevel(self)
        win.title(title)
        win.transient(self)
        win.grab_set()
        win.resizable(False, False)
        win.config(bg=UI_THEME["bg_main"])
        self._center_window(win, 300, 140 + len(options) * 50)
        tk.Label(win, text=title, font=("Microsoft YaHei", 14, "bold"),
                 bg=UI_THEME["bg_main"], fg=UI_THEME["text_primary"]).pack(pady=(15, 10))
        for text, cmd, style in options:
            if style == "primary":
                bg, fg, active = UI_THEME["btn_primary_bg"], UI_THEME["btn_primary_fg"], UI_THEME["btn_primary_active"]
            elif style == "danger":
                bg, fg, active = UI_THEME["btn_danger_bg"], UI_THEME["btn_danger_fg"], UI_THEME["btn_danger_active"]
            else:
                bg, fg, active = UI_THEME["btn_secondary_bg"], UI_THEME["btn_secondary_fg"], UI_THEME["btn_secondary_active"]

            def make_command(c=cmd, w=win):
                w.destroy()
                c()

            tk.Button(win, text=text, font=("Microsoft YaHei", 12), width=16,
                      bg=bg, fg=fg, activebackground=active,
                      activeforeground=fg,
                      relief=tk.RAISED, bd=1,
                      command=make_command).pack(pady=5)
        return win

    def _show_battle_dialog(self):
        self._show_menu_dialog("开始对战", [
            ("创建房间", lambda: self.app.show_lobby(is_host=True), "primary"),
            ("加入游戏", lambda: self.app.show_lobby(is_host=False), "primary"),
            ("本地测试", self._start_local_test, "secondary"),
        ])

    def _show_deck_dialog(self):
        self._show_menu_dialog("你的卡组", [
            ("创建卡组", self.app.show_deck_builder, "primary"),
            ("修改卡组", self._edit_existing_deck, "secondary"),
        ])

    def _show_about_dialog(self):
        """打开关于游戏弹窗：左侧目录 + 右侧内容。"""
        win = tk.Toplevel(self)
        win.title("关于游戏")
        win.transient(self)
        win.grab_set()
        win.resizable(False, False)
        win.config(bg=UI_THEME["bg_main"])
        self._center_window(win, 920, 620)

        tk.Label(win, text="关于 Tards", font=("Microsoft YaHei", 16, "bold"),
                 bg=UI_THEME["bg_main"], fg=UI_THEME["text_primary"]).pack(pady=(15, 10))

        main = tk.PanedWindow(win, orient=tk.HORIZONTAL, bg=UI_THEME["bg_main"])
        main.pack(fill=tk.BOTH, expand=True, padx=15, pady=5)

        # ===== 左侧目录 =====
        toc_outer = tk.Frame(main, bg=UI_THEME["bg_main"], width=210)
        main.add(toc_outer, minsize=180)
        toc_outer.pack_propagate(False)
        toc_canvas = tk.Canvas(toc_outer, bg=UI_THEME["bg_main"], highlightthickness=0, bd=0)
        toc_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        toc_scroll = tk.Scrollbar(toc_outer, orient=tk.VERTICAL, command=toc_canvas.yview)
        toc_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        toc_canvas.config(yscrollcommand=toc_scroll.set)
        toc_inner = tk.Frame(toc_canvas, bg=UI_THEME["bg_main"])
        toc_inner_id = toc_canvas.create_window((0, 0), window=toc_inner, anchor="nw", width=190)
        toc_inner.bind("<Configure>", lambda e: toc_canvas.configure(scrollregion=toc_canvas.bbox("all")))
        toc_canvas.bind("<Configure>", lambda e, iid=toc_inner_id: toc_canvas.itemconfig(iid, width=e.width))
        toc_canvas.bind("<MouseWheel>", lambda e: toc_canvas.yview_scroll(int(-e.delta / 120), "units"))

        # ===== 右侧内容 =====
        content_frame = tk.Frame(main, bg=UI_THEME["bg_main"])
        main.add(content_frame, minsize=560)

        # 规则文本
        rules_text = scrolledtext.ScrolledText(
            content_frame, wrap=tk.WORD, state=tk.DISABLED,
            bg=UI_THEME["bg_panel"], fg=UI_THEME["text_primary"],
            font=("Microsoft YaHei", 11), relief=tk.FLAT, bd=0,
        )
        rules_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # 开发团队页
        team_frame = tk.Frame(content_frame, bg=UI_THEME["bg_main"])
        tk.Label(team_frame, text="开发人员名单", font=("Microsoft YaHei", 16, "bold"),
                 bg=UI_THEME["bg_main"], fg=UI_THEME["text_primary"]).pack(pady=(40, 15))
        tk.Label(team_frame, text="（等待完善中……）", font=("Microsoft YaHei", 12),
                 bg=UI_THEME["bg_main"], fg=UI_THEME["text_muted"]).pack()

        # 解析并插入规则内容
        rules_text.config(state=tk.NORMAL)
        sections = []
        line_no = 1
        for para in _RULES_TEXT.split("\n"):
            stripped = para.strip()
            if not stripped:
                rules_text.insert(tk.END, "\n")
                line_no += 1
                continue
            if re.match(r"^[一二三四五六七八九十]+、", stripped):
                sections.append((stripped, line_no, 1))
                rules_text.insert(tk.END, stripped + "\n", ("h1",))
            elif re.match(r"^\d+\\.", stripped):
                sections.append((stripped, line_no, 2))
                rules_text.insert(tk.END, stripped + "\n", ("h2",))
            else:
                _insert_rule_text(rules_text, stripped + "\n", clear=False)
            line_no += 1
        rules_text.config(state=tk.DISABLED)

        rules_text.tag_config("h1", font=("Microsoft YaHei", 14, "bold"),
                              foreground=UI_THEME["accent"], spacing1=12, spacing3=6)
        rules_text.tag_config("h2", font=("Microsoft YaHei", 12, "bold"),
                              foreground=UI_THEME["text_primary"], spacing1=8, spacing3=4)

        # 生成目录按钮
        current_btn = [None]

        def goto_section(idx, line):
            team_frame.pack_forget()
            rules_text.pack(fill=tk.BOTH, expand=True)
            rules_text.update_idletasks()
            rules_text.config(state=tk.NORMAL)
            # 按行号比例滚动，避免 see 在布局未完成时失效
            total = int(rules_text.index("end-1c").split(".")[0])
            if total > 0:
                fraction = max(0.0, (line - 1) / total)
                rules_text.yview_moveto(fraction)
            rules_text.config(state=tk.DISABLED)
            _highlight_toc(idx)

        def show_team(idx):
            rules_text.pack_forget()
            team_frame.pack(fill=tk.BOTH, expand=True)
            team_frame.update_idletasks()
            _highlight_toc(idx)

        def _highlight_toc(idx):
            for i, b in enumerate(toc_buttons):
                if i == idx:
                    b.config(bg=UI_THEME["accent"], fg=UI_THEME["btn_primary_fg"])
                else:
                    b.config(bg=UI_THEME["bg_panel"], fg=UI_THEME["text_primary"])
            current_btn[0] = toc_buttons[idx]

        toc_buttons = []
        for idx, (title, line, level) in enumerate(sections):
            btn = tk.Button(toc_inner, text=title, anchor="w",
                            bg=UI_THEME["bg_panel"], fg=UI_THEME["text_primary"],
                            activebackground=UI_THEME["btn_secondary_active"],
                            relief=tk.FLAT, bd=0, cursor="hand2",
                            command=lambda i=idx, l=line: goto_section(i, l))
            btn.pack(fill=tk.X, pady=1, padx=(0 if level == 1 else 14, 0))
            btn.config(font=("Microsoft YaHei", 11, "bold") if level == 1 else ("Microsoft YaHei", 10))
            toc_buttons.append(btn)

        # 开发团队目录按钮
        team_idx = len(toc_buttons)
        team_btn = tk.Button(toc_inner, text="开发团队", anchor="w",
                             bg=UI_THEME["bg_panel"], fg=UI_THEME["text_primary"],
                             activebackground=UI_THEME["btn_secondary_active"],
                             relief=tk.FLAT, bd=0, cursor="hand2",
                             command=lambda i=team_idx: show_team(i))
        team_btn.pack(fill=tk.X, pady=(8, 1), padx=(0, 0))
        team_btn.config(font=("Microsoft YaHei", 11, "bold"))
        toc_buttons.append(team_btn)

        # 默认定位到第一个章节
        win.update_idletasks()
        win.update()
        if sections:
            goto_section(0, sections[0][1])

        tk.Button(win, text="关闭", font=("Microsoft YaHei", 11), width=12,
                  bg=UI_THEME["btn_secondary_bg"], fg=UI_THEME["btn_secondary_fg"],
                  activebackground=UI_THEME["btn_secondary_active"], relief=tk.RAISED, bd=1,
                  command=win.destroy).pack(pady=(0, 15))

    def _on_exit(self):
        self.app.root.quit()

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
