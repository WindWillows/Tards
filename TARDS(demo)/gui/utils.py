"""GUI 通用工具函数。

原位于 Gamestart.py，现独立出来供各 GUI 模块共享。
"""

from typing import Any, List

import tkinter as tk

from tards.data.card_db import DEFAULT_REGISTRY
from tards.data.deck import Deck

from gui.theme import _RULE_TERM_PATTERN, _DETAIL_TERM_PATTERN


def _insert_rule_text(text_widget: tk.Text, content: str, clear: bool = True) -> None:
    """向文本控件插入游戏规则内容，自动加粗游戏术语。"""
    if clear:
        text_widget.delete("1.0", tk.END)
    if not content:
        return
    text_widget.tag_config("rule_term", font=("Microsoft YaHei", 11, "bold"))
    for part in _RULE_TERM_PATTERN.split(content):
        if not part:
            continue
        if _RULE_TERM_PATTERN.fullmatch(part):
            text_widget.insert(tk.END, part, ("rule_term",))
        else:
            text_widget.insert(tk.END, part)


def _insert_rich_detail(text_widget: tk.Text, content: str) -> None:
    """向详情文本控件插入内容，自动加粗关键词与数字。"""
    text_widget.delete("1.0", tk.END)
    if not content:
        return
    text_widget.tag_config("detail_term", font=("Microsoft YaHei", 10, "bold"))
    for part in _DETAIL_TERM_PATTERN.split(content):
        if not part:
            continue
        if _DETAIL_TERM_PATTERN.fullmatch(part):
            text_widget.insert(tk.END, part, ("detail_term",))
        else:
            text_widget.insert(tk.END, part)


def _deck_defs_list(deck: Deck) -> List[Any]:
    """将 Deck 转换为 CardDefinition 列表，保留卡组顺序。"""
    defs = []
    for name, count in deck.card_entries.items():
        cd = DEFAULT_REGISTRY.get(name)
        if cd:
            for _ in range(count):
                defs.append(cd)
    return defs
