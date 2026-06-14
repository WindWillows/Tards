"""浮动提示框组件。

原位于 Gamestart.py，现独立出来供各 GUI 模块共享。
"""

import tkinter as tk

from gui.theme import UI_THEME


class Tooltip:
    """浮动提示框。"""
    def __init__(self, parent, text: str, x: int, y: int):
        self.tw = tk.Toplevel(parent)
        self.tw.wm_overrideredirect(True)
        self.tw.wm_geometry(f"+{x + 15}+{y + 15}")
        label = tk.Label(self.tw, text=text, justify=tk.LEFT,
                         background=UI_THEME["btn_warning_bg"], relief=tk.SOLID, borderwidth=1,
                         font=("Microsoft YaHei", 10), fg=UI_THEME["text_primary"])
        label.pack()
        self.tw.bind("<Leave>", lambda e: self.destroy())

    def move(self, x: int, y: int):
        self.tw.wm_geometry(f"+{x + 15}+{y + 15}")

    def destroy(self):
        try:
            if self.tw and self.tw.winfo_exists():
                self.tw.destroy()
        except tk.TclError:
            pass
