# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for TARDS (demo).

Usage:
    cd TARDS(demo)
    pyinstaller Tards.spec

Output:
    dist/Tards/            (one-directory bundle)
    dist/Tards/Tards.exe   (launcher)
"""

import os

block_cipher = None

# 项目根目录（spec 文件所在目录）
ROOT = os.path.abspath(SPECPATH)

# 需要打包为“数据文件”的目录/文件。
# 格式: (源路径, 目标路径)
# 目标路径是相对于 PyInstaller 输出的应用根目录。
datas = [
    ("assets", "assets"),
    ("card_pools", "card_pools"),
    ("decks", "decks"),
    ("gui", "gui"),
    ("tards", "tards"),
    ("local_duel.py", "."),
]

# 显式声明隐藏导入，避免 PyInstaller 漏掉动态/反射加载的模块。
hiddenimports = [
    # tards 子包（显式声明，确保重构后仍被打包）
    "tards",
    "tards.cards",
    "tards.game",
    "tards.core",
    "tards.data",
    "tards.net",
    # Pillow / Tkinter
    "PIL",
    "PIL.Image",
    "PIL.ImageDraw",
    "PIL.ImageTk",
    "PIL._tkinter_finder",
    # 卡包池（确保所有效果模块被打包）
    "card_pools",
    "card_pools.discrete",
    "card_pools.underworld",
    "card_pools.blood",
    "card_pools.general",
    "card_pools.general_effects",
    "card_pools.miracle",
    "card_pools.miracle_effects",
    "card_pools.discrete_effects",
    "card_pools.underworld_effects",
    "card_pools.blood_effects",
    "card_pools.effect_utils",
    "card_pools.effect_decorator",
]

a = Analysis(
    ["Gamestart.py"],
    pathex=[ROOT],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Tards",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=os.path.join(ROOT, "assets", "icons", "app.ico"),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="Tards",
)
