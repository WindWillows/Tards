from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional

from .cost import Cost


class Pack(Enum):
    """卡包枚举。"""
    GENERAL = "通用"
    PLANT = "植物"
    MIRACLE = "奇迹"
    DISCRETE = "离散"
    UNDERWORLD = "冥刻"
    BLOOD = "血祭"


class Rarity(Enum):
    """稀有度枚举，value 为最大携带数量。"""
    GOLD = 1
    SILVER = 2
    BRONZE = 3
    IRON = 4


class CardType(Enum):
    MINION = "异象"
    STRATEGY = "策略"
    CONSPIRACY = "阴谋"
    MINERAL = "矿物"


@dataclass
class CardDefinition:
    """卡牌元数据定义，用于构筑和对战生成。"""
    name: str
    cost_str: str
    card_type: CardType
    pack: Pack
    rarity: Rarity
    immersion_level: int = 0  # 沉浸等级 I=1, II=2, III=3
    attack: Optional[int] = None
    health: Optional[int] = None
    keywords: Dict[str, Any] = field(default_factory=dict)
    # 以下字段用于生成实际的对战卡牌对象
    targets_fn: Optional[Callable] = None
    effect_fn: Optional[Callable] = None
    special_fn: Optional[Callable] = None
    condition_fn: Optional[Callable] = None
    mineral_type: Optional[str] = None
    stack_limit: int = 1
    is_moment: bool = False
    is_token: bool = False
    evolve_to: Optional[str] = None
    # 指向目标数量与重复性
    targets_count: int = 1
    targets_repeat: bool = False
    # 多阶段指向（如"先选友方，再选敌方"）
    # 随从卡和策略卡通用：第一阶段为 targets_fn，后续阶段为 extra_targeting_stages
    extra_targeting_stages: List[Any] = field(default_factory=list)
    # 自动化事件回调（时间节点触发）
    on_turn_start: Optional[Callable] = None
    on_turn_end: Optional[Callable] = None
    on_phase_start: Optional[Callable] = None
    on_phase_end: Optional[Callable] = None
    # 雕像拼装字段
    statue_top: bool = False
    statue_bottom: bool = False
    statue_pair: Optional[str] = None
    on_statue_activate: Optional[Callable] = None
    on_statue_fuse: Optional[Callable] = None
    # 通用变化回调
    on_evolve_fn: Optional[Callable] = None
    # 分类标签（如昆虫、飞禽等）
    tags: List[str] = field(default_factory=list)
    # 隐藏词条（如"友好""非生命"等，不由关键词行直接显示）
    hidden_keywords: Dict[str, Any] = field(default_factory=dict)
    # 美术资源标识
    asset_id: Optional[str] = None        # 卡牌主资源ID（卡面/肖像）
    asset_back_id: Optional[str] = None   # 卡背资源ID（牌堆/手牌背面）

    def __post_init__(self):
        self.cost = Cost.from_string(self.cost_str)

    @property
    def immersion_display(self) -> str:
        if self.immersion_level <= 0:
            return ""
        levels = {1: "I", 2: "II", 3: "III"}
        return levels.get(self.immersion_level, str(self.immersion_level))

    def to_game_card(self, owner):
        """根据定义生成实际的对战用 Card 对象。
        
        注意：这是一个占位实现，后续会根据 card_type 导入对应的类并生成实例。
        """
        from .cards import Conspiracy, MineralCard, MinionCard, Strategy
        from .targets import target_none

        targets = self.targets_fn or target_none

        if self.card_type == CardType.MINION:
            card = MinionCard(
                name=self.name,
                owner=owner,
                cost=self.cost,
                targets=targets,
                attack=self.attack or 0,
                health=self.health or 1,
                special=self.special_fn,
                keywords=self.keywords.copy(),
                on_turn_start=self.on_turn_start,
                on_turn_end=self.on_turn_end,
                on_phase_start=self.on_phase_start,
                on_phase_end=self.on_phase_end,
                hidden_keywords=self.hidden_keywords.copy() if self.hidden_keywords else None,
            )
            card.evolve_to = self.evolve_to
            card.statue_top = self.statue_top
            card.statue_bottom = self.statue_bottom
            card.statue_pair = self.statue_pair
            card.on_statue_activate = self.on_statue_activate
            card.on_statue_fuse = self.on_statue_fuse
            card.on_evolve_fn = self.on_evolve_fn
            card.tags = list(self.tags)
            card.targets_count = self.targets_count
            card.targets_repeat = self.targets_repeat
            card.extra_targeting_stages = list(self.extra_targeting_stages)
            card.asset_id = self.asset_id
            card.asset_back_id = self.asset_back_id
            return card
        elif self.card_type == CardType.STRATEGY:
            card = Strategy(
                name=self.name,
                cost=self.cost,
                effect_fn=self.effect_fn,
                targets=targets,
                on_turn_start=self.on_turn_start,
                on_turn_end=self.on_turn_end,
                on_phase_start=self.on_phase_start,
                on_phase_end=self.on_phase_end,
                hidden_keywords=self.hidden_keywords.copy() if self.hidden_keywords else None,
            )
            card.owner = owner
            card.targets_count = self.targets_count
            card.targets_repeat = self.targets_repeat
            card.extra_targeting_stages = list(self.extra_targeting_stages)
            card.asset_id = self.asset_id
            card.asset_back_id = self.asset_back_id
            return card
        elif self.card_type == CardType.CONSPIRACY:
            card = Conspiracy(
                name=self.name,
                cost=self.cost,
                condition_fn=self.condition_fn or (lambda g, e, p: False),
                effect_fn=self.effect_fn or (lambda g, e, p: None),
                targets=targets,
                on_turn_start=self.on_turn_start,
                on_turn_end=self.on_turn_end,
                on_phase_start=self.on_phase_start,
                on_phase_end=self.on_phase_end,
            )
            card.owner = owner
            card.targets_count = self.targets_count
            card.targets_repeat = self.targets_repeat
            card.extra_targeting_stages = list(self.extra_targeting_stages)
            card.asset_id = self.asset_id
            card.asset_back_id = self.asset_back_id
            return card
        elif self.card_type == CardType.MINERAL:
            card = MineralCard(
                name=self.name,
                mineral_type=self.mineral_type or "",
                exchange_cost=self.cost,
                play_effect=self.effect_fn,
                stack_limit=self.stack_limit,
                on_turn_start=self.on_turn_start,
                on_turn_end=self.on_turn_end,
                on_phase_start=self.on_phase_start,
                on_phase_end=self.on_phase_end,
            )
            card.targets_count = self.targets_count
            card.targets_repeat = self.targets_repeat
            card.asset_id = self.asset_id
            card.asset_back_id = self.asset_back_id
            return card
        else:
            raise ValueError(f"未知的卡牌类型: {self.card_type}")


class CardRegistry:
    """全局卡牌注册表。"""

    def __init__(self):
        self._cards: Dict[str, CardDefinition] = {}

    def register(self, card: CardDefinition) -> CardDefinition:
        if card.name in self._cards:
            raise ValueError(f"卡牌 [{card.name}] 已存在")
        self._cards[card.name] = card
        return card

    def get(self, name: str) -> Optional[CardDefinition]:
        return self._cards.get(name)

    def all_cards(self) -> List[CardDefinition]:
        return list(self._cards.values())

    def by_pack(self, pack: Pack) -> List[CardDefinition]:
        return [c for c in self._cards.values() if c.pack == pack]

    def by_immersion(self, pack: Pack, level: int) -> List[CardDefinition]:
        return [c for c in self._cards.values() if c.pack == pack and c.immersion_level <= level]


# 全局默认注册表
DEFAULT_REGISTRY = CardRegistry()


def register_card(
    name: str,
    cost_str: str,
    card_type: CardType,
    pack: Pack,
    rarity: Rarity,
    immersion_level: int = 0,
    attack: Optional[int] = None,
    health: Optional[int] = None,
    keywords: Optional[Dict[str, Any]] = None,
    targets_fn=None,
    effect_fn=None,
    special_fn=None,
    condition_fn=None,
    mineral_type: Optional[str] = None,
    stack_limit: int = 1,
    is_moment: bool = False,
    is_token: bool = False,
    evolve_to: Optional[str] = None,
    on_turn_start=None,
    on_turn_end=None,
    on_phase_start=None,
    on_phase_end=None,
    statue_top: bool = False,
    statue_bottom: bool = False,
    statue_pair: Optional[str] = None,
    on_statue_activate=None,
    on_statue_fuse=None,
    on_evolve_fn=None,
    tags: Optional[List[str]] = None,
    hidden_keywords: Optional[Dict[str, Any]] = None,
    extra_targeting_stages=None,
    asset_id: Optional[str] = None,
    asset_back_id: Optional[str] = None,
    registry: CardRegistry = DEFAULT_REGISTRY,
) -> CardDefinition:
    """便捷注册函数。"""
    # 冥刻卡包异象默认具有献祭1和丰饶1
    kw = dict(keywords) if keywords else {}
    if pack == Pack.UNDERWORLD and card_type == CardType.MINION:
        if "献祭" not in kw:
            kw["献祭"] = 1
        if "丰饶" not in kw:
            kw["丰饶"] = 1

    card = CardDefinition(
        name=name,
        cost_str=cost_str,
        card_type=card_type,
        pack=pack,
        rarity=rarity,
        immersion_level=immersion_level,
        attack=attack,
        health=health,
        keywords=kw,
        targets_fn=targets_fn,
        effect_fn=effect_fn,
        special_fn=special_fn,
        condition_fn=condition_fn,
        mineral_type=mineral_type,
        stack_limit=stack_limit,
        is_moment=is_moment,
        extra_targeting_stages=extra_targeting_stages or [],
        is_token=is_token,
        evolve_to=evolve_to,
        hidden_keywords=hidden_keywords or {},
        on_turn_start=on_turn_start,
        on_turn_end=on_turn_end,
        on_phase_start=on_phase_start,
        on_phase_end=on_phase_end,
        statue_top=statue_top,
        statue_bottom=statue_bottom,
        statue_pair=statue_pair,
        on_statue_activate=on_statue_activate,
        on_statue_fuse=on_statue_fuse,
        on_evolve_fn=on_evolve_fn,
        tags=tags or [],
        asset_id=asset_id,
        asset_back_id=asset_back_id,
    )
    registry.register(card)
    return card
