from typing import Dict, List, Optional

from .card_db import CardDefinition, CardRegistry, CardType, Pack, Rarity
from .cards import Card


class Deck:
    """卡组构筑类，负责存储卡组定义并校验构筑规则。"""

    DECK_SIZE = 40
    MAX_IMMERSION_POINTS = 3

    def __init__(
        self,
        name: str,
        registry: CardRegistry,
        immersion_points: Optional[Dict[Pack, int]] = None,
        is_test_deck: bool = False,
    ):
        self.name = name
        self.registry = registry
        # 沉浸点分配：Pack -> int
        self.immersion_points: Dict[Pack, int] = immersion_points or {}
        # 卡牌条目：name -> count
        self.card_entries: Dict[str, int] = {}
        # 测试卡组标记：测试卡组不受构筑规则限制，仅用于本地测试
        self.is_test_deck = is_test_deck

    def set_immersion(self, pack: Pack, points: int):
        """设置某卡包的沉浸点数。"""
        if points < 0:
            raise ValueError("沉浸点数不能为负数")
        if points > 0:
            self.immersion_points[pack] = points
        else:
            self.immersion_points.pop(pack, None)

    def _resolve_name(self, name: str) -> Optional[str]:
        """解析卡牌名称，支持旧卡组文件的后缀兼容（如 '雌鹿(铁)' -> '雌鹿'）。"""
        if self.registry.get(name):
            return name
        # 尝试去掉稀有度后缀
        import re
        m = re.match(r'^(.+?)\((铁|铜|银|金)\)$', name)
        if m:
            stripped = m.group(1)
            if self.registry.get(stripped):
                return stripped
        return None

    def add_card(self, name: str, count: int = 1) -> bool:
        """向卡组中添加指定数量的某张卡牌。"""
        resolved = self._resolve_name(name)
        if not resolved:
            print(f"  错误：卡牌 [{name}] 未在注册表中找到")
            return False
        card_def = self.registry.get(resolved)
        if card_def.card_type == CardType.MINERAL or card_def.is_moment or card_def.is_token:
            print(f"  错误：特殊卡 [{name}] 不能加入卡组")
            return False
        current = self.card_entries.get(resolved, 0)
        self.card_entries[resolved] = current + count
        return True

    def remove_card(self, name: str, count: int = 1) -> bool:
        """从卡组中移除指定数量的某张卡牌。"""
        resolved = self._resolve_name(name)
        if not resolved:
            resolved = name
        current = self.card_entries.get(resolved, 0)
        if current <= 0:
            print(f"  错误：卡组中不存在 [{name}]")
            return False
        new_count = max(0, current - count)
        if new_count == 0:
            self.card_entries.pop(resolved, None)
        else:
            self.card_entries[resolved] = new_count
        return True

    def get_card_count(self, name: str) -> int:
        resolved = self._resolve_name(name)
        if not resolved:
            resolved = name
        return self.card_entries.get(resolved, 0)

    def total_cards(self) -> int:
        return sum(self.card_entries.values())

    def validate(self) -> List[str]:
        """校验卡组合法性，返回错误信息列表。空列表表示合法。
        
        测试卡组 (is_test_deck=True) 仅检查卡牌是否注册、是否为非法特殊卡，
        跳过所有构筑数量限制（40张、沉浸点、卡包数量、沉浸等级、稀有度上限）。
        """
        errors = []

        # 测试卡组：仅做最基本检查
        if self.is_test_deck:
            for name, count in self.card_entries.items():
                card_def = self.registry.get(name)
                if not card_def:
                    errors.append(f"卡组中包含未注册卡牌 [{name}]")
                    continue
                if card_def.card_type == CardType.MINERAL or card_def.is_moment or card_def.is_token:
                    errors.append(f"特殊卡 [{name}] 不能加入卡组")
            return errors

        # 1. 总牌数
        total = self.total_cards()
        if total != self.DECK_SIZE:
            errors.append(f"卡组牌数应为 {self.DECK_SIZE} 张，当前 {total} 张")

        # 2. 沉浸点总和
        total_immersion = sum(self.immersion_points.values())
        if total_immersion > self.MAX_IMMERSION_POINTS:
            errors.append(f"沉浸点总和为 {total_immersion}，超过上限 {self.MAX_IMMERSION_POINTS}")

        # 3. 按卡包统计
        pack_counts: Dict[Pack, int] = {}
        for name, count in self.card_entries.items():
            card_def = self.registry.get(name)
            if not card_def:
                errors.append(f"卡组中包含未注册卡牌 [{name}]")
                continue
            if card_def.card_type == CardType.MINERAL or card_def.is_moment or card_def.is_token:
                errors.append(f"特殊卡 [{name}] 不能加入卡组")
                continue
            pack_counts[card_def.pack] = pack_counts.get(card_def.pack, 0) + count

        # 4. 卡包数量限制
        all_packs = set(list(Pack))
        for pack in all_packs:
            x = self.immersion_points.get(pack, 0)
            count = pack_counts.get(pack, 0)
            if x == 0:
                if count > 0:
                    errors.append(f"[{pack.value}] 卡包未分配沉浸点，但卡组中包含 {count} 张该卡包卡牌")
            else:
                max_allowed = 10 * (x + 1)
                if count > max_allowed:
                    errors.append(f"[{pack.value}] 卡包分配了 {x} 点沉浸点，至多 {max_allowed} 张，当前 {count} 张")
                # 通用卡包没有数量下限；非通用卡包至少 10X 张
                if pack != Pack.GENERAL:
                    min_required = 10 * x
                    if count < min_required:
                        errors.append(f"[{pack.value}] 卡包分配了 {x} 点沉浸点，至少需要 {min_required} 张，当前 {count} 张")

        # 5. 单卡稀有度限制 & 沉浸等级限制
        card_counts: Dict[str, int] = {}
        for name, count in self.card_entries.items():
            card_def = self.registry.get(name)
            if not card_def:
                continue

            # 沉浸等级
            pack_level = self.immersion_points.get(card_def.pack, 0)
            if card_def.immersion_level > pack_level:
                errors.append(
                    f"[{name}] 的沉浸等级为 {card_def.immersion_display}（{card_def.immersion_level}），"
                    f"但 [{card_def.pack.value}] 仅分配了 {pack_level} 点沉浸点"
                )

            # 稀有度上限
            max_copies = card_def.rarity.value
            if count > max_copies:
                errors.append(f"[{name}] 为 {self._rarity_name(card_def.rarity)}，最多携带 {max_copies} 张，当前 {count} 张")

        return errors

    def is_valid(self) -> bool:
        return len(self.validate()) == 0

    def to_game_deck(self, owner) -> List[Card]:
        """将卡组定义转换为实际的对战用 Card 对象列表（已洗牌）。"""
        import random
        deck = []
        for name, count in self.card_entries.items():
            card_def = self.registry.get(name)
            if not card_def or card_def.card_type == CardType.MINERAL or card_def.is_moment or card_def.is_token:
                continue
            for _ in range(count):
                deck.append(card_def.to_game_card(owner))
        random.shuffle(deck)
        return deck

    def to_original_deck_defs(self) -> List[CardDefinition]:
        """返回卡组中所有卡牌的 CardDefinition 列表（按数量展开，未洗牌）。"""
        defs = []
        for name, count in self.card_entries.items():
            card_def = self.registry.get(name)
            if not card_def or card_def.card_type == CardType.MINERAL or card_def.is_moment or card_def.is_token:
                continue
            for _ in range(count):
                defs.append(card_def)
        return defs

    def get_immersion_bonuses(self) -> Dict[Pack, Dict[str, Any]]:
        """获取当前沉浸点分配对应的沉浸增益描述（仅返回文本描述，后续可扩展为实际效果）。"""
        bonuses = {}
        # 这里先放置三个已有卡包的沉浸增益描述，后续可扩展
        discrete_bonus = {
            1: "开放矿物兑换，+1矿物手牌上限",
            2: "费用槽自然上限改为 8T4C",
            3: "开发一张牌时，+1HP",
        }
        underworld_bonus = {
            1: "开局获得6张松鼠牌堆，手牌+1松鼠",
            2: "1T/回合将1张松鼠加入手牌",
            3: "HP≤20给烛烟，HP≤10给大团烛烟",
        }
        blood_bonus = {
            1: "抽牌阶段-1HP，+1S",
            2: "受到单次≥3伤害时，+3S",
            3: "开局将6张'时刻'洗入卡组",
        }

        bonus_map = {
            Pack.DISCRETE: discrete_bonus,
            Pack.UNDERWORLD: underworld_bonus,
            Pack.BLOOD: blood_bonus,
        }

        for pack, points in self.immersion_points.items():
            if points > 0 and pack in bonus_map:
                bonuses[pack] = {
                    "level": points,
                    "bonus": bonus_map[pack].get(points, "未知增益"),
                }
        return bonuses

    def deck_summary(self) -> str:
        """返回卡组统计摘要。"""
        prefix = "[测试卡组] " if self.is_test_deck else ""
        lines = [f"{prefix}卡组 [{self.name}] 摘要:"]
        if self.is_test_deck:
            lines.append(f"  总牌数: {self.total_cards()} 张（测试卡组无40张限制）")
        else:
            lines.append(f"  总牌数: {self.total_cards()}/{self.DECK_SIZE}")
        lines.append(f"  沉浸点分配:")
        for pack in Pack:
            pts = self.immersion_points.get(pack, 0)
            count = sum(
                cnt for name, cnt in self.card_entries.items()
                if self.registry.get(name) and self.registry.get(name).pack == pack
            )
            lines.append(f"    {pack.value}: {pts}点 ({count}张)")
        lines.append(f"  卡牌列表:")
        for name, count in sorted(self.card_entries.items(), key=lambda x: x[0]):
            card_def = self.registry.get(name)
            if card_def:
                info = f"[{card_def.pack.value} {card_def.immersion_display} {self._rarity_name(card_def.rarity)}]"
                lines.append(f"    {name} x{count} {info}")
        return "\n".join(lines)

    @staticmethod
    def _rarity_name(rarity: Rarity) -> str:
        names = {
            Rarity.GOLD: "金",
            Rarity.SILVER: "银",
            Rarity.BRONZE: "铜",
            Rarity.IRON: "铁",
        }
        return names.get(rarity, "未知")
