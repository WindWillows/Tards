"""美术资源管理器。

提供统一的图像加载、缩放和缓存接口。所有方法在资源缺失或 Pillow 未安装时
均返回 None，渲染层应据此回退到纯文本/几何绘制。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Dict, Optional, Tuple

try:
    from PIL import Image, ImageTk

    _PIL_AVAILABLE = True
except Exception:
    _PIL_AVAILABLE = False


class AssetManager:
    """统一资源管理器。

    目录结构约定（相对于 base_path）：
        cards/faces/        卡面肖像
        cards/backs/        卡背
        cards/thumbnails/   缩略图（棋盘/阴谋区）
        icons/keywords/     关键词图标
        icons/types/        类型图标
        board/tiles/        棋盘格子纹理
        board/ui/           UI 装饰元素
        config.json         可选：asset_id → 相对路径 映射表
    """

    # 图像搜索的后缀名顺序
    _EXTS = (".png", ".jpg", ".jpeg", ".gif", ".webp")

    def __init__(self, base_path: str = "assets"):
        self.base_path = Path(base_path)
        self._cache: Dict[Tuple[str, Tuple[int, int]], Optional[ImageTk.PhotoImage]] = {}
        self._config: Dict[str, str] = {}
        self._load_config()

    # ------------------------------------------------------------------
    # 配置
    # ------------------------------------------------------------------

    def _load_config(self) -> None:
        config_file = self.base_path / "config.json"
        if config_file.exists():
            try:
                with config_file.open("r", encoding="utf-8") as f:
                    self._config = json.load(f)
            except Exception:
                self._config = {}

    # ------------------------------------------------------------------
    # 公共 API
    # ------------------------------------------------------------------

    def available(self) -> bool:
        """Pillow 是否可用且资源目录存在。"""
        return _PIL_AVAILABLE and self.base_path.exists()

    def get_card_face(self, asset_id: str, width: int, height: int) -> Optional[ImageTk.PhotoImage]:
        """加载卡面图像。"""
        return self._get(f"card_face:{asset_id}", width, height, "cards/faces", asset_id)

    def get_card_back(self, asset_id: Optional[str], width: int, height: int) -> Optional[ImageTk.PhotoImage]:
        """加载卡背图像。若 asset_id 为 None，使用 default。"""
        aid = asset_id or "default"
        return self._get(f"card_back:{aid}", width, height, "cards/backs", aid)

    def get_thumbnail(self, asset_id: str, width: int, height: int) -> Optional[ImageTk.PhotoImage]:
        """加载缩略图（棋盘/阴谋区用）。若不存在，回退到卡面。"""
        thumb = self._get(f"thumb:{asset_id}", width, height, "cards/thumbnails", asset_id)
        if thumb is not None:
            return thumb
        return self.get_card_face(asset_id, width, height)

    def get_icon(self, icon_id: str, size: int) -> Optional[ImageTk.PhotoImage]:
        """加载关键词/类型图标。"""
        return self._get(f"icon:{icon_id}", size, size, "icons/keywords", icon_id)

    def get_type_icon(self, icon_id: str, size: int) -> Optional[ImageTk.PhotoImage]:
        """加载类型图标。"""
        return self._get(f"type_icon:{icon_id}", size, size, "icons/types", icon_id)

    def get_board_tile(self, terrain_id: str, size: int) -> Optional[ImageTk.PhotoImage]:
        """加载棋盘格子纹理。"""
        return self._get(f"tile:{terrain_id}", size, size, "board/tiles", terrain_id)

    def get_ui_element(self, element_id: str, width: int, height: int) -> Optional[ImageTk.PhotoImage]:
        """加载 UI 装饰元素。"""
        return self._get(f"ui:{element_id}", width, height, "board/ui", element_id)

    def clear_cache(self) -> None:
        """清空图像缓存。用于资源热更新。"""
        self._cache.clear()

    # ------------------------------------------------------------------
    # 内部实现
    # ------------------------------------------------------------------

    def _get(self, cache_key: str, width: int, height: int,
             default_dir: str, asset_id: str) -> Optional[ImageTk.PhotoImage]:
        if not _PIL_AVAILABLE:
            return None
        cache = self._cache.get((cache_key, (width, height)))
        if cache is not None or (cache_key, (width, height)) in self._cache:
            return cache
        img = self._load_and_scale(asset_id, default_dir, width, height)
        self._cache[(cache_key, (width, height))] = img
        return img

    def _load_and_scale(self, asset_id: str, default_dir: str,
                        width: int, height: int) -> Optional[ImageTk.PhotoImage]:
        path = self._resolve_path(asset_id, default_dir)
        if path is None or not path.exists():
            return None
        try:
            img = Image.open(path)
            if img.mode not in ("RGB", "RGBA"):
                img = img.convert("RGBA")
            if img.size != (width, height):
                img = img.resize((width, height), Image.LANCZOS)
            return ImageTk.PhotoImage(img)
        except Exception:
            return None

    def _resolve_path(self, asset_id: str, default_dir: str) -> Optional[Path]:
        # 1. 优先使用 config.json 映射
        mapped = self._config.get(asset_id)
        if mapped:
            p = self.base_path / mapped
            if p.exists():
                return p
        # 2. 约定目录查找
        base = self.base_path / default_dir
        for ext in self._EXTS:
            p = base / f"{asset_id}{ext}"
            if p.exists():
                return p
        return None


# 全局默认实例（惰性初始化）
_default_manager: Optional[AssetManager] = None


def get_asset_manager(base_path: str = "assets") -> AssetManager:
    """获取全局默认 AssetManager 实例。"""
    global _default_manager
    if _default_manager is None:
        _default_manager = AssetManager(base_path)
    return _default_manager
