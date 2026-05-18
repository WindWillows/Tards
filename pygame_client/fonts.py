"""Pygame 字体管理器。

支持项目目录字体 + 系统字体回退，按字号缓存 Font 实例。
"""

from __future__ import annotations

import os
import sys
from typing import Dict, List, Optional, Tuple

import pygame


class FontManager:
    """统一字体管理器。

    搜索顺序：
        1. 项目目录 assets/fonts/NotoSansSC-VF.ttf
        2. Windows 系统字体目录（Noto Sans SC / 微软雅黑 / 黑体等）
        3. pygame 默认字体（最后回退，不支持中文）
    """

    _instance: Optional["FontManager"] = None

    def __new__(cls) -> "FontManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._fonts: Dict[Tuple[int, bool], pygame.font.Font] = {}
            cls._instance._search_paths = cls._instance._build_search_paths()
        return cls._instance

    def _build_search_paths(self) -> List[str]:
        """构建字体搜索路径列表（按优先级）。"""
        paths: List[str] = []

        # 1. 项目目录
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        paths.append(os.path.join(project_root, "assets", "fonts", "NotoSansSC-VF.ttf"))

        # 2. 系统字体
        if sys.platform == "win32":
            win_root = os.environ.get("SYSTEMROOT", "C:\\Windows")
            win_fonts = os.path.join(win_root, "Fonts")
            candidates = [
                "NotoSansSC-VF.ttf",
                "msyh.ttc",
                "msyhbd.ttc",
                "simhei.ttf",
                "STXIHEI.TTF",
            ]
            for name in candidates:
                paths.append(os.path.join(win_fonts, name))

        return paths

    def _find_font_path(self) -> Optional[str]:
        """查找第一个存在的字体文件路径。"""
        for p in self._search_paths:
            if os.path.isfile(p):
                return p
        return None

    def get_font(self, size: int, bold: bool = False) -> pygame.font.Font:
        """获取指定字号（和粗细）的 Font 实例，带缓存。"""
        key = (size, bold)
        if key not in self._fonts:
            path = self._find_font_path()
            if path is not None:
                self._fonts[key] = pygame.font.Font(path, size)
            else:
                # 回退到 pygame 默认字体（不支持中文，但至少不崩溃）
                self._fonts[key] = pygame.font.SysFont("simhei", size, bold=bold)
        return self._fonts[key]

    def render_text(
        self,
        text: str,
        size: int,
        color,
        bold: bool = False,
        antialias: bool = True,
    ) -> pygame.Surface:
        """渲染文本为 Surface。"""
        font = self.get_font(size, bold)
        return font.render(str(text), antialias, color)

    def get_text_size(self, text: str, size: int, bold: bool = False) -> Tuple[int, int]:
        """获取文本渲染后的尺寸（不实际渲染）。"""
        font = self.get_font(size, bold)
        return font.size(str(text))

    def clear_cache(self) -> None:
        """清空字体缓存（用于热更新或内存回收）。"""
        self._fonts.clear()


def get_font_manager() -> FontManager:
    """获取全局默认 FontManager 实例。"""
    return FontManager()
