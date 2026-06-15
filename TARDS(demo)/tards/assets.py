"""美术资源管理器。

提供统一的图像加载、缩放和缓存接口。所有方法在资源缺失或 Pillow 未安装时
均返回 None，渲染层应据此回退到纯文本/几何绘制。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from time import time
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

    # 默认资源目录：与 tards/ 同级（即 TARDS(demo)/assets），避免受 cwd 影响
    _DEFAULT_BASE_PATH = str(Path(__file__).parent.parent / "assets")

    def __init__(self, base_path: str = _DEFAULT_BASE_PATH):
        self.base_path = Path(base_path)
        self._cache: Dict[Tuple[str, Tuple[int, int]], ImageTk.PhotoImage] = {}
        self._raw_cache: Dict[Tuple[str, Tuple[int, int]], Optional[Image.Image]] = {}
        # 记录资源加载失败的时间戳，避免对缺失资源每帧都重试，同时允许热新增资源在短时间后自动生效
        self._miss_times: Dict[Tuple[str, Tuple[int, int]], float] = {}
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
        self._raw_cache.clear()
        self._miss_times.clear()

    # ------------------------------------------------------------------
    # 内部实现
    # ------------------------------------------------------------------

    def _get(self, cache_key: str, width: int, height: int,
             default_dir: str, asset_id: str) -> Optional[ImageTk.PhotoImage]:
        if not _PIL_AVAILABLE:
            return None
        cache_key_tuple = (cache_key, (width, height))
        cache = self._cache.get(cache_key_tuple)
        if cache is not None:
            return cache
        # 旧版本可能曾把 None 写入缓存；遇到时清除并重新尝试加载
        if cache_key_tuple in self._cache:
            del self._cache[cache_key_tuple]
        now = time()
        last_miss = self._miss_times.get(cache_key_tuple)
        if last_miss is not None and now - last_miss < 2.0:
            return None
        img = self._load_and_scale(asset_id, default_dir, width, height)
        if img is not None:
            self._cache[cache_key_tuple] = img
            self._miss_times.pop(cache_key_tuple, None)
        else:
            self._miss_times[cache_key_tuple] = now
        return img

    def _load_raw_image(self, asset_id: str, default_dir: str,
                         width: int, height: int) -> Optional[Image.Image]:
        """加载并缩放原始 PIL Image，供 pygame 等外部渲染器使用。"""
        path = self._resolve_path(asset_id, default_dir)
        if path is None or not path.exists():
            return None
        try:
            img = Image.open(path)
            if img.mode not in ("RGB", "RGBA"):
                img = img.convert("RGBA")
            if img.size != (width, height):
                # 小尺寸图标（如 15×15 像素画）使用最近邻，避免抗锯齿模糊
                resample = Image.NEAREST if max(width, height) <= 32 else Image.LANCZOS
                img = img.resize((width, height), resample)
            return img
        except Exception:
            return None

    def _load_and_scale(self, asset_id: str, default_dir: str,
                        width: int, height: int) -> Optional[ImageTk.PhotoImage]:
        img = self._load_raw_image(asset_id, default_dir, width, height)
        if img is None:
            return None
        return ImageTk.PhotoImage(img)

    def get_raw_image(self, cache_key: str, width: int, height: int,
                      default_dir: str, asset_id: str) -> Optional[Image.Image]:
        """加载原始 PIL Image 并缓存。供外部渲染器（如 pygame）使用。"""
        if not _PIL_AVAILABLE:
            return None
        key = (cache_key, (width, height))
        cached = self._raw_cache.get(key)
        if cached is not None:
            return cached
        # 旧版本可能曾把 None 写入缓存；遇到时清除并重新尝试加载
        if key in self._raw_cache:
            del self._raw_cache[key]
        now = time()
        last_miss = self._miss_times.get(key)
        if last_miss is not None and now - last_miss < 2.0:
            return None
        img = self._load_raw_image(asset_id, default_dir, width, height)
        if img is not None:
            self._raw_cache[key] = img
            self._miss_times.pop(key, None)
        else:
            self._miss_times[key] = now
        return img

    # ------------------------------------------------------------------
    # 原始图像公共 API（供 pygame 等外部渲染器使用）
    # ------------------------------------------------------------------

    def get_card_face_raw(self, asset_id: str, width: int, height: int) -> Optional[Image.Image]:
        """加载卡面原始图像。"""
        return self.get_raw_image(f"card_face:{asset_id}", width, height, "cards/faces", asset_id)

    def get_card_back_raw(self, asset_id: Optional[str], width: int, height: int) -> Optional[Image.Image]:
        """加载卡背原始图像。"""
        aid = asset_id or "default"
        return self.get_raw_image(f"card_back:{aid}", width, height, "cards/backs", aid)

    def get_thumbnail_raw(self, asset_id: str, width: int, height: int) -> Optional[Image.Image]:
        """加载缩略图原始图像。若不存在，回退到卡面。"""
        thumb = self.get_raw_image(f"thumb:{asset_id}", width, height, "cards/thumbnails", asset_id)
        if thumb is not None:
            return thumb
        return self.get_card_face_raw(asset_id, width, height)

    def get_icon_raw(self, icon_id: str, size: int) -> Optional[Image.Image]:
        """加载关键词图标原始图像。"""
        return self.get_raw_image(f"icon:{icon_id}", size, size, "icons/keywords", icon_id)

    def get_type_icon_raw(self, icon_id: str, size: int) -> Optional[Image.Image]:
        """加载类型图标原始图像。"""
        return self.get_raw_image(f"type_icon:{icon_id}", size, size, "icons/types", icon_id)

    def get_board_tile_raw(self, terrain_id: str, size: int) -> Optional[Image.Image]:
        """加载棋盘格子纹理原始图像。"""
        return self.get_raw_image(f"tile:{terrain_id}", size, size, "board/tiles", terrain_id)

    def get_ui_element_raw(self, element_id: str, width: int, height: int) -> Optional[Image.Image]:
        """加载 UI 装饰元素原始图像。"""
        return self.get_raw_image(f"ui:{element_id}", width, height, "board/ui", element_id)

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


def get_asset_manager(base_path: str = AssetManager._DEFAULT_BASE_PATH) -> AssetManager:
    """获取全局默认 AssetManager 实例。"""
    global _default_manager
    if _default_manager is None:
        _default_manager = AssetManager(base_path)
    return _default_manager
