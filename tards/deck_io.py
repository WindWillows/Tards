import json
import os
from typing import Dict, Optional

from .card_db import CardRegistry, Pack
from .deck import Deck

# 卡组保存目录固定为项目根目录下的 decks/，避免随运行目录变化
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DECKS_DIR = os.path.join(_PROJECT_ROOT, "decks")


def _ensure_dir():
    os.makedirs(DECKS_DIR, exist_ok=True)


def _pack_to_str(pack: Pack) -> str:
    return pack.name


def _str_to_pack(s: str) -> Pack:
    return Pack[s]


def save_deck(deck: Deck, filename: Optional[str] = None) -> str:
    """保存卡组到 JSON 文件，返回保存路径。"""
    _ensure_dir()
    name = filename or deck.name
    path = os.path.join(DECKS_DIR, f"{name}.json")

    data = {
        "name": deck.name,
        "immersion_points": {
            _pack_to_str(p): pts for p, pts in deck.immersion_points.items()
        },
        "cards": dict(deck.card_entries),
    }

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return path


def load_deck(name: str, registry: CardRegistry) -> Optional[Deck]:
    """从 JSON 文件读取卡组。"""
    path = os.path.join(DECKS_DIR, f"{name}.json")
    if not os.path.exists(path):
        return None

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    deck = Deck(name=data.get("name", name), registry=registry)
    for p_str, pts in data.get("immersion_points", {}).items():
        deck.set_immersion(_str_to_pack(p_str), pts)
    for card_name, count in data.get("cards", {}).items():
        deck.add_card(card_name, count)

    return deck


def list_saved_decks() -> list:
    """列出所有已保存的卡组名称（不含 .json 后缀）。"""
    _ensure_dir()
    files = []
    for f in os.listdir(DECKS_DIR):
        if f.endswith(".json"):
            files.append(f[:-5])
    return files
