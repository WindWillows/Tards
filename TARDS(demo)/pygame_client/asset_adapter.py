"""Tkinter AssetManager → pygame Surface 适配层。

不修改 tards/assets.py 的现有缓存与 Tkinter 路径，
仅在其上封装一层 PIL.Image → pygame.Surface 转换与缓存。
"""

from __future__ import annotations

import sys
from typing import Dict, Optional, Tuple

import pygame

from tards.assets import get_asset_manager

# PIL 导入仅用于类型注解（运行时已在 assets.py 中检查过）
from PIL.Image import Image as PILImage


class PygameAssetAdapter:
    """为 pygame 渲染层提供图像加载适配。"""

    def __init__(self, base_path: str = "assets"):
        self._am = get_asset_manager(base_path)
        self._surface_cache: Dict[
            Tuple[str, Tuple[int, int]], Optional[pygame.Surface]
        ] = {}

    @staticmethod
    def _pil_to_surface(pil_img: PILImage) -> pygame.Surface:
        """将 PIL Image 转为 pygame Surface（RGBA 或 RGB）。"""
        mode = pil_img.mode
        data = pil_img.tobytes()
        size = pil_img.size
        if mode == "RGBA":
            return pygame.image.fromstring(data, size, mode)
        # RGB 或其他模式统一按 RGB 处理
        return pygame.image.fromstring(data, size, "RGB")

    def _get_surface(self, cache_key: str, width: int, height: int,
                     loader) -> Optional[pygame.Surface]:
        """通用缓存加载：先查 Surface 缓存，再调用 PIL loader 转换。"""
        key = (cache_key, (width, height))
        cached = self._surface_cache.get(key)
        if cached is not None or key in self._surface_cache:
            return cached

        pil_img = loader()
        if pil_img is None:
            self._surface_cache[key] = None
            return None

        surf = self._pil_to_surface(pil_img)
        self._surface_cache[key] = surf
        return surf

    # ------------------------------------------------------------------
    # 公共 API（与 AssetManager 命名一致，但返回 pygame.Surface）
    # ------------------------------------------------------------------

    def get_card_face(self, asset_id: str, width: int, height: int) -> Optional[pygame.Surface]:
        return self._get_surface(
            f"card_face:{asset_id}", width, height,
            lambda: self._am.get_card_face_raw(asset_id, width, height)
        )

    def get_card_back(self, asset_id: Optional[str], width: int, height: int) -> Optional[pygame.Surface]:
        aid = asset_id or "default"
        return self._get_surface(
            f"card_back:{aid}", width, height,
            lambda: self._am.get_card_back_raw(aid, width, height)
        )

    def get_thumbnail(self, asset_id: str, width: int, height: int) -> Optional[pygame.Surface]:
        surf = self._get_surface(
            f"thumb:{asset_id}", width, height,
            lambda: self._am.get_thumbnail_raw(asset_id, width, height)
        )
        if surf is not None:
            return surf
        # 回退到卡面
        return self.get_card_face(asset_id, width, height)

    def get_icon(self, icon_id: str, size: int) -> Optional[pygame.Surface]:
        return self._get_surface(
            f"icon:{icon_id}", size, size,
            lambda: self._am.get_icon_raw(icon_id, size)
        )

    def get_type_icon(self, icon_id: str, size: int) -> Optional[pygame.Surface]:
        return self._get_surface(
            f"type_icon:{icon_id}", size, size,
            lambda: self._am.get_type_icon_raw(icon_id, size)
        )

    def get_board_tile(self, terrain_id: str, size: int) -> Optional[pygame.Surface]:
        return self._get_surface(
            f"tile:{terrain_id}", size, size,
            lambda: self._am.get_board_tile_raw(terrain_id, size)
        )

    def get_ui_element(self, element_id: str, width: int, height: int) -> Optional[pygame.Surface]:
        return self._get_surface(
            f"ui:{element_id}", width, height,
            lambda: self._am.get_ui_element_raw(element_id, width, height)
        )

    def clear_cache(self) -> None:
        """清空 pygame Surface 缓存。"""
        self._surface_cache.clear()


# 全局默认实例（惰性初始化）
_default_adapter: Optional[PygameAssetAdapter] = None


def get_pygame_asset_adapter(base_path: str = "assets") -> PygameAssetAdapter:
    """获取全局默认 PygameAssetAdapter 实例。"""
    global _default_adapter
    if _default_adapter is None:
        _default_adapter = PygameAssetAdapter(base_path)
    return _default_adapter
