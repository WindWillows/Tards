#!/usr/bin/env python3
"""将素材图转换为 Tards 应用图标 (assets/icons/app.ico)。

默认源图：assets/icons/keywords/协同.png
"""

import os
from PIL import Image

ROOT = os.path.dirname(os.path.abspath(__file__))
SRC_PATH = os.path.join(ROOT, "assets", "icons", "keywords", "协同.png")
OUT_PATH = os.path.join(ROOT, "assets", "icons", "app.ico")
os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)

img = Image.open(SRC_PATH)
if img.mode != "RGBA":
    img = img.convert("RGBA")

img.save(
    OUT_PATH,
    format="ICO",
    sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
)
print(f"Icon saved to {OUT_PATH}")
