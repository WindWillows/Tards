"""卡牌/异象详情文本渲染器。

将 BattleFrame 中生成右侧详情面板的逻辑独立出来，便于维护与复用。
"""

from typing import Any

import tkinter as tk

from tards import Minion, MinionCard
from tards.card_db import DEFAULT_REGISTRY, Pack
from gui.theme import UI_THEME
from gui.utils import _insert_rich_detail


class DetailRenderer:
    """负责在 detail_text 中渲染卡牌或场上异象的详情文本。"""

    def __init__(self, frame: Any):
        self.frame = frame

    def render(self, card: Any) -> None:
        """在右侧文本栏中显示卡牌/异象信息（悬停时触发）。"""
        if not hasattr(self.frame, "detail_text"):
            return

        detail_text = self.frame.detail_text
        is_minion = isinstance(card, Minion)

        # 判断是否为冥刻异象（仅冥刻卡包的异象过滤献祭1/丰饶1）
        is_underworld = False
        if is_minion and hasattr(card, "source_card") and card.source_card:
            is_underworld = getattr(card.source_card, "pack", None) == Pack.UNDERWORLD

        # 获取描述：优先从 card 本身，其次从 source_card，最后从注册表
        desc = getattr(card, "description", "")
        if not desc and is_minion and hasattr(card, "source_card") and card.source_card:
            desc = getattr(card.source_card, "description", "")
        if not desc and DEFAULT_REGISTRY:
            lookup_name = card.name
            if is_minion and hasattr(card, "source_card") and card.source_card:
                lookup_name = card.source_card.name
            card_def = DEFAULT_REGISTRY.get(lookup_name)
            if card_def:
                desc = getattr(card_def, "description", "")

        lines = [f"【{card.name}】"]

        if is_minion:
            # 异象：显示当前攻防（含临时变化）和基础值
            base_atk = card.base_attack
            base_hp = card.base_health
            cur_atk = card.current_attack
            cur_hp = card.current_health
            max_hp = card.current_max_health

            atk_str = str(cur_atk)
            if cur_atk != base_atk:
                atk_str += f" (基础{base_atk})"

            hp_str = str(cur_hp)
            if max_hp != card.base_max_health:
                hp_str += f"/{max_hp} (基础{base_hp})"
            elif cur_hp != base_hp:
                hp_str += f" (基础{base_hp})"

            lines.append(f"攻击/生命: {atk_str} / {hp_str}")

            # 费用（从 source_card 获取）
            cost = getattr(card, "cost", None)
            if cost is None and hasattr(card, "source_card") and card.source_card:
                cost = card.source_card.cost
            if cost is not None:
                lines.append(f"费用: {cost}")

            # 关键词
            kw_dict = card.display_keywords
        else:
            # 手牌
            lines.append(f"费用: {getattr(card, 'cost', '?')}")
            if isinstance(card, MinionCard):
                lines.append(f"攻击/生命: {card.attack}/{card.health}")
            kw_dict = getattr(card, "keywords", None) or {}

        if kw_dict:
            kw = self._format_keywords(kw_dict, is_minion and is_underworld)
            if kw:
                lines.append(f"关键词: {kw}")

        # 场上临时赋予的效果（不包括永久攻防增减）
        if is_minion:
            # 临时关键词
            temp_kw = getattr(card, "temp_keywords", None)
            if temp_kw:
                kw_text = self._format_keywords(temp_kw, is_underworld)
                if kw_text:
                    lines.append(f"临时效果: {kw_text}")

            # 注入的回合回调（如被赋予的亡语等）
            injected_start = getattr(card, "_injected_turn_start", []) or []
            injected_end = getattr(card, "_injected_turn_end", []) or []
            for fn in injected_start:
                src = getattr(fn, "_source_name", "未知")
                fn_desc = getattr(fn, "__name__", "结算阶段开始效果")
                lines.append(f"效果【{src}】：{fn_desc}")
            for fn in injected_end:
                src = getattr(fn, "_source_name", "未知")
                fn_desc = getattr(fn, "__name__", "结算阶段结束效果")
                lines.append(f"效果【{src}】：{fn_desc}")

            # 光环效果（来自其他异象的攻击力/生命/关键词修饰）
            aura_providers = [
                (getattr(card, "_aura_attack_provider", None), "攻击力光环"),
                (getattr(card, "_aura_max_health_provider", None), "最大生命光环"),
                (getattr(card, "_aura_keyword_provider", None), "关键词光环"),
            ]
            for prov, label in aura_providers:
                if prov:
                    for entry in prov._entries:
                        src = getattr(entry.source, "name", str(entry.source)) if entry.source else "未知"
                        lines.append(f"效果【{src}】：{label}")

            # EventBus 监听器效果（策略/异象注入的触发效果）
            game = getattr(self.frame.duel, "game", None)
            if game and hasattr(game, "history"):
                for entry in game.history.get_listeners_by_owner(card):
                    src = getattr(
                        entry.callback, "_source_name",
                        getattr(entry.callback, "__name__", "未知")
                    )
                    eff_desc = getattr(entry.callback, "_description", entry.event_type)
                    lines.append(f"效果【{src}】：{eff_desc}")

            # 指向状态
            pending_atks = getattr(card, "_pending_attack_targets", None)
            if pending_atks and isinstance(pending_atks, list) and len(pending_atks) > 0:
                target_names = []
                for t in pending_atks:
                    if hasattr(t, "name"):
                        target_names.append(t.name)
                    elif isinstance(t, tuple) and len(t) == 2:
                        target_names.append(f"({t[0]},{t[1]})")
                    else:
                        target_names.append(str(t))
                lines.append(f"攻击指向: {' → '.join(target_names)}")

            pending_effect = getattr(card, "_pending_effect_target", None)
            if pending_effect is not None:
                eff_name = getattr(pending_effect, "name", str(pending_effect))
                lines.append(f"效果指向: {eff_name}")

            locked_target = getattr(card, "_ankang_locked_target", None)
            if locked_target is not None:
                locked_name = getattr(locked_target, "name", str(locked_target))
                lines.append(f"锁定目标: {locked_name}")

            # 被哪些异象指向（攻击目标 + 效果目标 + 通用实例属性反向查找）
            pointed_by = []
            if game and game.board:
                for m in game.board.minion_place.values():
                    if m is card:
                        continue
                    m_pending = getattr(m, "_pending_attack_targets", None)
                    if m_pending and isinstance(m_pending, list) and card in m_pending:
                        pointed_by.append(m.name)
                        continue
                    m_effect = getattr(m, "_pending_effect_target", None)
                    if m_effect is card:
                        pointed_by.append(m.name)
                        continue
                    # 通用反向查找：检查其他异象的实例属性是否引用本异象
                    for val in vars(m).values():
                        if val is card:
                            pointed_by.append(m.name)
                            break
                        if isinstance(val, (list, tuple, set)) and card in val:
                            pointed_by.append(m.name)
                            break
            if pointed_by:
                lines.append(f"被指向: {', '.join(pointed_by)}")

            # 藤蔓覆盖
            vine = getattr(card, "vine_overlay", None)
            if vine:
                lines.append(
                    f"藤蔓覆盖: {vine.name} ({vine.current_health}/{vine.current_max_health})"
                )

        if desc:
            lines.append(f"\n【效果】\n{desc}")
        else:
            lines.append("\n【效果】\n（暂无描述）")

        text = "\n".join(lines)
        detail_text.config(state=tk.NORMAL)
        _insert_rich_detail(detail_text, text)
        detail_text.config(state=tk.DISABLED)

    @staticmethod
    def _format_keywords(kw_dict: dict, filter_underworld_basic: bool) -> str:
        """将关键词字典格式化为可读的字符串。"""
        if filter_underworld_basic:
            return " ".join(
                f"{k}{v if v is not True else ''}"
                for k, v in kw_dict.items()
                if not (k in ("丰饶", "献祭") and v == 1)
            )
        return " ".join(f"{k}{v if v is not True else ''}" for k, v in kw_dict.items())
