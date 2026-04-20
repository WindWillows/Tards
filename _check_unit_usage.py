#!/usr/bin/env python3
"""检查"异象"一词在代码中的出现位置，确认替换安全。"""

import re
from pathlib import Path

ROOT = Path("c:/Users/34773/Desktop/tards开发库")

key_files = [
    'tards/cards.py', 'tards/game.py', 'tards/board.py', 'tards/player.py',
    'tards/targeting.py', 'tards/targets.py', 'tards/constants.py',
    'card_pools/effect_utils.py', 'card_pools/effect_decorator.py',
    'card_pools/discrete_effects.py', 'card_pools/underworld_effects.py',
    'card_pools/blood_effects.py',
]

for rel_path in key_files:
    path = ROOT / rel_path
    if not path.exists():
        continue
    with open(path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    for i, line in enumerate(lines, 1):
        if '异象' in line:
            stripped = line.strip()
            print(f'{rel_path}:{i}: {stripped[:120]}')
