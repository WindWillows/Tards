#!/usr/bin/env python3
"""
Tards 可视化客户端 (Tkinter) + 联机对战
支持：卡组构筑与保存、IP 直连对战、信息不透明。

本文件仅保留程序启动入口；对战界面逻辑已迁移至 gui.battle.battle_frame。
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

import sys

_ensure_dependencies()
import tkinter as tk
from typing import Optional

from tards import Player
from tards.net.net_game import NetworkDuel

# 导入卡包池以注册所有卡牌到 DEFAULT_REGISTRY
import card_pools

from gui.menu_frame import MenuFrame
from gui.deck_builder_frame import DeckBuilderFrame
from gui.lobby_frame import LobbyFrame
from gui.battle.battle_frame import BattleFrame
from local_duel import LocalDuel


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


def main():
    root = tk.Tk()
    app = TardsApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
