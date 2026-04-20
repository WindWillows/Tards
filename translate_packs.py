#!/usr/bin/env python3
"""
卡组翻译器：将自然语言卡包文本翻译为 register_card 调用。
效果函数暂时留空（TODO），元数据（名称、费用、类型、面板、关键词、沉浸等级）自动提取。
"""

import os
import re
from typing import Any, Dict, List, Optional

# 导入关键词列表用于匹配
from tards.constants import GENERAL_KEYWORDS, TAG_TOKENS
from tards.card_db import Rarity

# 导入标签覆盖表（为描述中才有标签的卡牌补充标签）
try:
    from card_pools.tag_overrides import TAG_OVERRIDES
except ImportError:
    TAG_OVERRIDES = {}

OUTPUT_DIR = "card_pools"

COST_RE = re.compile(r"^\d+CT$|^\d+[A-Z](?:\d+[A-Z])*$")
PANEL_RE = re.compile(r"^(\d+)/(\d+)$")
STACK_LIMIT_RE = re.compile(r"堆叠上限为(\d+)")
IMMERSION_RE = re.compile(r"^(.*?)\((I{1,3})\)$")
MINERAL_TYPE_RE = re.compile(r"^(.*?)（([IGDM])）$")
RARITY_RE = re.compile(r"^(.*?)\((铁|铜|银|金)\)$")
LEADING_NUM_RE = re.compile(r"^\d+\.\s*")

# 常见描述动词/词，用于防御性过滤误解析的描述行
DESCRIPTION_VERBS = {
    "获得", "造成", "使", "对", "给", "抽", "回复", "恢复", "增加",
    "减少", "降低", "提升", "将", "随机", "选择", "消灭", "移除",
    "弃置", "摧毁", "生成", "召唤", "部署", "开发", "打出", "使用",
    "激活", "触发", "令", "若", "当", "每当", "回合", "战斗",
}

REGION_MAP = {
    "单位：": "minion",
    "矿物：": "mineral",
    "策略：": "strategy",
    "阴谋：": "conspiracy",
    "时刻：": "moment",
}

PACK_FILE_MAP = {
    "离散卡包.txt": ("discrete", "DISCRETE"),
    "冥刻卡包.txt": ("underworld", "UNDERWORLD"),
    "血契卡包.txt": ("blood", "BLOOD"),
}


def find_cost_index(tokens: List[str]) -> int:
    for i, tok in enumerate(tokens):
        if COST_RE.match(tok):
            return i
    return -1


def infer_card_type(region: str, attack: Optional[int], health: Optional[int], description: str) -> str:
    if region == "mineral":
        return "mineral"
    if region == "conspiracy":
        return "conspiracy"
    if region == "moment":
        return "strategy"
    # 只有矿物区内的卡才用"堆叠上限"推断
    if region == "mineral" and "堆叠上限" in description:
        return "mineral"
    if attack is not None and health is not None:
        return "minion"
    return "strategy"


def extract_stack_limit(description: str) -> int:
    m = STACK_LIMIT_RE.search(description)
    return int(m.group(1)) if m else 1


def normalize_keywords(keywords: List[str]) -> Dict[str, Any]:
    result: Dict[str, Any] = {}
    for kw in keywords:
        m = re.match(r"^([\u4e00-\u9fa5]+)(-?\d+)$", kw)
        if m:
            result[m.group(1)] = int(m.group(2))
        else:
            result[kw] = True
    return result


def parse_main_line(line: str, region: str, is_indented: bool = False) -> Optional[Dict[str, Any]]:
    line = line.strip()
    if not line:
        return None

    # 去掉 // 注释
    if "//" in line:
        line = line.split("//")[0].strip()
    if not line:
        return None

    # 去掉前导序号如 "82. "
    line = LEADING_NUM_RE.sub("", line)

    # 中文逗号、顿号替换为空格，避免被当成一个 token
    line = line.replace('，', ' ').replace('、', ' ')
    tokens = line.split()
    cost_idx = find_cost_index(tokens)
    if cost_idx == -1:
        return None  # 没有费用，不是卡牌主行

    name_tokens = tokens[:cost_idx]
    if not name_tokens:
        return None

    immersion_level = 1
    mineral_type = None
    rarity = Rarity.IRON

    last = name_tokens[-1]
    # 先尝试匹配沉浸度（冥刻卡包格式如：松鼠球(铁)(I)）
    m_imm = IMMERSION_RE.match(last)
    if m_imm:
        last = m_imm.group(1)
        immersion_level = len(m_imm.group(2))
        name_tokens = name_tokens[:-1] + [last] if len(name_tokens) > 1 else [last]

    # 再尝试匹配稀有度（所有卡牌类型都可能有稀有度后缀）
    m_rarity = RARITY_RE.match(last)
    if m_rarity:
        raw_name = " ".join(name_tokens[:-1] + [m_rarity.group(1)]) if len(name_tokens) > 1 else m_rarity.group(1)
        rarity_map = {"铁": Rarity.IRON, "铜": Rarity.BRONZE, "银": Rarity.SILVER, "金": Rarity.GOLD}
        rarity = rarity_map.get(m_rarity.group(2), Rarity.IRON)
        last = raw_name
        name_tokens = name_tokens[:-1] + [raw_name] if len(name_tokens) > 1 else [raw_name]

    if region == "mineral":
        m = MINERAL_TYPE_RE.match(last)
        if m:
            name = " ".join(name_tokens[:-1] + [m.group(1)]) if len(name_tokens) > 1 else m.group(1)
            mineral_type = m.group(2)
        else:
            name = " ".join(name_tokens)
    else:
        name = " ".join(name_tokens)

    # 防御性过滤：如果名称 token 只有 1 个且是常见描述动词，大概率是描述行被误解析
    if len(name_tokens) == 1 and name_tokens[0] in DESCRIPTION_VERBS:
        return None

    cost_str = tokens[cost_idx]
    rest = tokens[cost_idx + 1 :]

    # 特殊稀有度规则：名称中包含“座首”或“底座”默认为金卡
    if "座首" in name or "底座" in name:
        rarity = Rarity.GOLD

    attack = None
    health = None
    keywords = []
    desc_parts = []

    panel_idx = -1
    for i, tok in enumerate(rest):
        pm = PANEL_RE.match(tok)
        if pm:
            attack = int(pm.group(1))
            health = int(pm.group(2))
            panel_idx = i
            break

    def _extract_keyword_suffix(suffix: str) -> str:
        """提取关键词后的数值后缀，支持阿拉伯数字、罗马数字Ⅰ/Ⅱ/Ⅲ/I/II/III、以及负数。"""
        roman_map = {"Ⅰ": "1", "Ⅱ": "2", "Ⅲ": "3", "I": "1", "II": "2", "III": "3"}
        if not suffix:
            return ""
        # 纯阿拉伯数字
        if suffix.isdigit():
            return suffix
        # 罗马数字
        if suffix in roman_map:
            return roman_map[suffix]
        # 负数
        if suffix.startswith("-") and suffix[1:].isdigit():
            return suffix
        return ""

    candidates = rest[panel_idx + 1 :] if panel_idx != -1 else rest
    tags = []
    for token in candidates:
        is_kw = False
        is_tag = False
        # 先匹配通用关键词
        for kw in GENERAL_KEYWORDS:
            if token == kw:
                is_kw = True
                keywords.append(kw)
                break
            if token.startswith(kw):
                suffix = token[len(kw):]
                normalized = _extract_keyword_suffix(suffix)
                if normalized:
                    is_kw = True
                    keywords.append(kw + normalized)
                    break
        # 再匹配标签（即使已是 keyword，某些词也作为 tag）
        for tag in TAG_TOKENS:
            if token == tag:
                is_tag = True
                if tag not in tags:
                    tags.append(tag)
                break
            if token.startswith(tag):
                suffix = token[len(tag):]
                normalized = _extract_keyword_suffix(suffix)
                if normalized:
                    is_tag = True
                    tag_val = tag + normalized
                    if tag_val not in tags:
                        tags.append(tag_val)
                    break
        if not is_kw and not is_tag:
            desc_parts.append(token)

    description = " ".join(desc_parts)
    card_type = infer_card_type(region, attack, health, description)
    stack_limit = extract_stack_limit(description) if card_type == "mineral" else 1

    return {
        "name": name.strip(),
        "cost_str": cost_str,
        "card_type": card_type,
        "attack": attack,
        "health": health,
        "keywords": keywords,
        "tags": tags,
        "description": description,
        "immersion_level": immersion_level,
        "mineral_type": mineral_type,
        "stack_limit": stack_limit,
        "rarity": rarity,
        "is_moment": region == "moment",
        "is_token": is_indented,
    }


def _indent_level(raw_line: str) -> int:
    lvl = 0
    for ch in raw_line:
        if ch == '\t':
            lvl += 4
        elif ch == ' ':
            lvl += 1
        else:
            break
    return lvl


def process_file(filepath: str) -> List[Dict[str, Any]]:
    cards: List[Dict[str, Any]] = []
    current_region: Optional[str] = None
    current_card: Optional[Dict[str, Any]] = None
    minion_stack: List[Tuple[int, Dict[str, Any]]] = []

    with open(filepath, "r", encoding="utf-8") as f:
        lines = f.readlines()

    # 找到第一个区域切换行开始解析
    start_idx = 0
    for i, line in enumerate(lines):
        if line.strip() in REGION_MAP:
            start_idx = i
            break

    for raw_line in lines[start_idx:]:
        line = raw_line.strip()

        matched_region = None
        for region_key in REGION_MAP:
            if line.startswith(region_key):
                matched_region = REGION_MAP[region_key]
                break
        if matched_region:
            if current_card:
                cards.append(current_card)
                current_card = None
            current_region = matched_region
            minion_stack.clear()
            continue

        if not line:
            if current_card:
                cards.append(current_card)
                current_card = None
            continue

        indent = _indent_level(raw_line)
        is_indented = indent > 0
        parsed = parse_main_line(line, current_region or "minion", is_indented)
        if parsed:
            parsed["indent_level"] = indent
            if current_card:
                cards.append(current_card)
            current_card = parsed
            # 建立退格（成长）关系（仅对单位卡在同区域内）
            if parsed.get("card_type") == "minion":
                while minion_stack and minion_stack[-1][0] >= indent:
                    minion_stack.pop()
                if minion_stack:
                    parent = minion_stack[-1][1]
                    parent["evolve_to"] = parsed["name"]
                minion_stack.append((indent, parsed))
        else:
            if current_card:
                # 描述续行
                current_card["description"] += " " + line
            # 否则是孤立的描述，忽略

    if current_card:
        cards.append(current_card)

    # 二次提取：从描述中检测亡语等机制关键词（仅对单位卡）
    for card in cards:
        if card.get("card_type") != "minion":
            continue
        desc = card.get("description", "")
        kw_set = set(card.get("keywords", []))
        if "亡语" in desc and not any(k.startswith("亡语") for k in kw_set):
            card["keywords"].append("亡语")

    return cards


def escape_string(s: str) -> str:
    return s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ")


_CN_NUM = {'一':1, '二':2, '两':2, '三':3, '四':4, '五':5, '六':6, '七':7, '八':8, '九':9, '十':10}

def _parse_count(s: str) -> int:
    if s.isdigit():
        return int(s)
    total = 0
    for ch in s:
        total += _CN_NUM.get(ch, 0)
    return total if total > 0 else 1


def try_generate_develop_effect(description: str) -> Optional[str]:
    """尝试从描述中生成简单的开发效果函数代码字符串。"""
    import re
    # 排除持续/触发式效果（如“使你获得：...开发...”、“每当...开发...”）
    if re.search(r'(?:使你获得|每当|受到.*?时|死亡时|.*?时，.*?开发)', description):
        return None
    # 若描述中有多个开发子句，过于复杂，不自动生成
    if description.count("开发") > 1:
        return None
    simple_patterns = [
        (r'开发([一二两三四五六七八九十\d]+)张卡组中的牌', 'deck'),
        (r'开发[1一]张[“"]([^”"]+)[”"]\s*。?\s*$', 'named'),
        (r'开发[1一]张(离散|冥刻|血契|通用)?(金卡|银卡|铜卡|铁卡)?(单位|策略|阴谋|矿物)?\s*。?\s*$', 'filtered'),
    ]
    for pat, kind in simple_patterns:
        m = re.search(pat, description)
        if m:
            # 保守策略：若描述中还有复杂后续效果，则不自动生成
            tail = description[m.end():]
            if tail and re.search(r'(?:然后|将其|使|给|对|造成|回复|抽|获得\d|失去|消灭|弃置|摧毁|召唤|复制|加入战场|取消)', tail):
                return None
            if kind == 'deck':
                count = _parse_count(m.group(1))
                if count == 1:
                    return 'lambda p, t, g, extras=None: g.develop_card(p, p.original_deck_defs)'
                else:
                    return f'lambda p, t, g, extras=None: ([g.develop_card(p, p.original_deck_defs) for _ in range({count})] or True)'
            elif kind == 'named':
                name = m.group(1)
                return f'lambda p, t, g, extras=None: g.develop_card(p, [c for c in DEFAULT_REGISTRY.all_cards() if c.name == "{name}"])'
            elif kind == 'filtered':
                pack_name, rarity_name, type_name = m.groups()
                conds = []
                if pack_name:
                    pmap = {"离散":"Pack.DISCRETE","冥刻":"Pack.UNDERWORLD","血契":"Pack.BLOOD","通用":"Pack.GENERAL"}
                    conds.append(f"c.pack == {pmap[pack_name]}")
                if rarity_name:
                    rmap = {"金卡":"Rarity.GOLD","银卡":"Rarity.SILVER","铜卡":"Rarity.BRONZE","铁卡":"Rarity.IRON"}
                    conds.append(f"c.rarity == {rmap[rarity_name]}")
                if type_name:
                    tmap = {"单位":"CardType.MINION","策略":"CardType.STRATEGY","阴谋":"CardType.CONSPIRACY","矿物":"CardType.MINERAL"}
                    conds.append(f"c.card_type == {tmap[type_name]}")
                pool = f"[c for c in DEFAULT_REGISTRY.all_cards() if {' and '.join(conds)}]" if conds else "DEFAULT_REGISTRY.all_cards()"
                return f'lambda p, t, g, extras=None: g.develop_card(p, {pool})'
    return None


def try_generate_draw_effect(description: str) -> Optional[str]:
    """尝试生成抽牌效果。"""
    import re
    # 保守：不处理带条件或限定的复杂抽牌
    if re.search(r'(?:若|每当|受到|死亡|消灭|弃置|摧毁|加入战场|回合开始|回合结束)', description):
        return None
    m = re.search(r'抽([一二两三四五六七八九十\d]+)张牌', description)
    if m:
        count = _parse_count(m.group(1))
        return f'lambda p, t, g, extras=None: (p.draw_card({count}, game=g) or True)'
    m = re.search(r'双方各抽([一二两三四五六七八九十\d]+)张牌', description)
    if m:
        count = _parse_count(m.group(1))
        return f'lambda p, t, g, extras=None: ([pl.draw_card({count}, game=g) for pl in g.players] or True)'
    return None


def try_generate_heal_effect(description: str) -> Optional[str]:
    """尝试生成回血/恢复效果。"""
    import re
    if re.search(r'(?:若|每当|受到|死亡|消灭)', description):
        return None
    m = re.search(r'(?:回复|恢复|获得)([一二两三四五六七八九十\d]+)点?(?:生命|HP|hp)', description)
    if m:
        count = _parse_count(m.group(1))
        return f'lambda p, t, g, extras=None: (p.health_change({count}) or True)'
    return None


def try_generate_lose_hp_effect(description: str) -> Optional[str]:
    """尝试生成流失生命值效果（描述中的'失去X点HP/生命值'）。

    与'造成伤害'不同：流失生命值不受坚韧/伤害替换影响，不触发'受到伤害时'效果。
    含条件词（若、每当、受到、改为等）的效果会被过滤，需人工实现。
    """
    import re
    if re.search(r'(?:若|每当|受到|改为|死亡|消灭|回合开始|回合结束)', description):
        return None
    # 使/令 [目标] 失去 [数字] 点 HP/生命值
    m = re.search(r'(?:使|令)(?:对手|敌方主角|1个单位|一个单位|目标)失去([一二两三四五六七八九十\d]+)点?(?:HP|hp|生命)', description)
    if m:
        dmg = _parse_count(m.group(1))
        return f'lambda p, t, g, extras=None: (t.lose_hp({dmg}) or True) if hasattr(t, "lose_hp") else False'
    # 你失去X点HP
    m = re.search(r'你失去([一二两三四五六七八九十\d]+)点?(?:HP|hp|生命)', description)
    if m:
        dmg = _parse_count(m.group(1))
        return f'lambda p, t, g, extras=None: (p.lose_hp({dmg}) or True)'
    return None


def try_generate_damage_effect(description: str) -> Optional[str]:
    """尝试生成【造成伤害】效果（受到坚韧/伤害替换影响，触发'受到伤害时'效果）。"""
    import re
    if re.search(r'(?:若|每当|受到|死亡|消灭|回合开始|回合结束)', description):
        return None
    # 对1个单位/对手/敌方主角/全体敌方目标/所有单位 造成伤害
    m = re.search(r'对(?:([一二两三四五六七八九十\d]?)个?单位|对手|敌方主角|全体敌方目标|所有单位)造成([一二两三四五六七八九十\d]+)点伤害', description)
    if m:
        dmg = _parse_count(m.group(2))
        target = m.group(1)
        if target and target in ('', '1', '一'):
            # 对1个单位造成伤害 -> 默认 t 是目标
            return f'lambda p, t, g, extras=None: (t.health_change(-{dmg}) if hasattr(t, "health_change") else (t.take_damage({dmg}) if hasattr(t, "take_damage") else False) or True)'
        if target in ('对手', '敌方主角'):
            return f'lambda p, t, g, extras=None: ((g.p2 if p == g.p1 else g.p1).health_change(-{dmg}) or True)'
        if target in ('全体敌方目标', '所有单位'):
            return f'lambda p, t, g, extras=None: ([(m.health_change(-{dmg}) if hasattr(m, "health_change") else m.take_damage({dmg})) for m in g.board.minion_place.values() if m.is_alive() and not g.is_immune(m, p)] or True)'
    return None


def try_generate_keyword_effect(description: str) -> Optional[str]:
    """尝试生成赋予关键词的效果。"""
    import re
    if re.search(r'(?:若|每当|受到|死亡|消灭|回合开始|回合结束)', description):
        return None
    # 匹配：使一个单位获得恐惧/冰冻/眩晕/先攻1/迅捷/坚韧1 等
    m = re.search(r'使(?:[1一]个?单位|目标)获得([\u4e00-\u9fa5]+)([一二两三四五六七八九十\d]*)', description)
    if m:
        kw = m.group(1)
        val_str = m.group(2)
        val = _parse_count(val_str) if val_str else True
        bool_kws = {"恐惧", "冰冻", "眩晕", "迅捷", "协同", "独行", "藤蔓", "水生", "两栖", "串击", "穿刺", "空袭", "防空", "潜水", "潜行", "绝缘", "尖刺", "回响", "坚韧", "视野", "横扫", "高地", "漂浮物", "脆弱", "三重打击", "穿透", "亡语"}
        if kw in bool_kws and val is True:
            return 'lambda p, t, g, extras=None: (setattr(t, "base_keywords", dict(getattr(t, "base_keywords", {}))) or t.base_keywords.update({"' + kw + '": True}) or t.recalculate() or True) if hasattr(t, "recalculate") else False'
        if kw in {"先攻", "冰冻", "眩晕", "休眠", "坚韧", "尖刺", "视野", "高频", "横扫"}:
            return 'lambda p, t, g, extras=None: (setattr(t, "base_keywords", dict(getattr(t, "base_keywords", {}))) or t.base_keywords.update({"' + kw + '": ' + str(val) + '}) or t.recalculate() or True) if hasattr(t, "recalculate") else False'
    return None


def try_generate_targets_fn(description: str, card_type: str) -> Optional[tuple]:
    """根据效果描述自动推断策略/阴谋/矿物的 targets_fn。

    返回 (fn_name, count, repeat)。count 为需要选择的目标数量，
    repeat 表示是否允许重复选择同一目标。
    """
    if card_type not in ("strategy", "conspiracy", "mineral"):
        return None
    import re
    desc = description.strip()

    # AOE / 全体效果：不需要指向
    if any(x in desc for x in ["全体敌方目标", "所有单位", "所有敌方单位", "所有友方单位", "对手所有单位"]):
        return ("target_none", 1, False)

    # 指向敌方玩家（对手/敌方主角）
    if re.search(r'对(?:对手|敌方主角)', desc):
        return ("target_enemy_player", 1, False)

    # 回复HP类，且未提及"单位"时：通常指向自己
    if re.search(r'回复\d+点HP|恢复\d+点生命', desc) and "单位" not in desc:
        return ("target_self", 1, False)

    # 识别数量词
    count_match = re.search(r'([一二两三四五六七八九十\d]+)个(?:友方)?单位', desc)
    count = _parse_count(count_match.group(1)) if count_match else 1

    # 指向友方单位
    if re.search(r'(?:对|使|消灭|将)友方(?:生物)?单位|友方一个单位|[1一]个友方(?:生物)?单位', desc):
        return ("target_friendly_minions", count, False)

    # 指向一个单位（包含"使一个单位获得XXX"、"对1个单位造成伤害"、"消灭一个单位"、"交换一个单位"、"将一个单位移动"）
    if re.search(r'(?:对|使|消灭|交换|将)(?:[1一]个?单位|一个单位|目标单位)', desc):
        return ("target_any_minion", count, False)

    # 明确指向敌方单位（包含"将一个敌方单位移动"）
    if re.search(r'(?:对|交换|将)(?:敌方单位|敌方一个单位|1个敌方单位|[1一]个敌方单位|敌人)', desc):
        return ("target_enemy_minions", count, False)

    return None


def try_generate_minion_extra_stages(deploy_desc: str) -> Optional[str]:
    """根据部署效果描述自动推断 extra_targeting_stages。

    返回 Python 列表字面量字符串，如 \"[(target_any_minion, 1, False)]\"
    只处理需要指向的部署效果；如果不需要额外指向，返回 None。
    """
    if not deploy_desc:
        return None
    import re
    desc = deploy_desc.strip()

    # AOE / 全体效果：不需要额外指向
    if any(x in desc for x in ["全体敌方目标", "所有单位", "所有敌方单位", "所有友方单位", "对手所有单位"]):
        return None

    # 指向敌方玩家（对手/敌方主角）
    if re.search(r'对(?:对手|敌方主角)', desc):
        return "[(target_enemy_player, 1, False)]"

    # 识别数量词
    count_match = re.search(r'([一二两三四五六七八九十\d]+)个(?:友方)?单位', desc)
    count = _parse_count(count_match.group(1)) if count_match else 1

    # 指向友方单位
    if re.search(r'(?:对|使|消灭|将)友方单位|友方一个单位|[1一]个友方单位', desc):
        return f"[(target_friendly_minions, {count}, False)]"

    # 指向一个单位（包含"使一个单位获得XXX"、"对1个单位造成伤害"、"消灭一个单位"、"交换一个单位"、"将一个单位移动"）
    if re.search(r'(?:对|使|消灭|交换|将)(?:[1一]个?单位|一个单位|目标单位)', desc):
        return f"[(target_any_minion, {count}, False)]"

    # 明确指向敌方单位（包含"将一个敌方单位移动"）
    if re.search(r'(?:对|交换|将)(?:敌方单位|敌方一个单位|1个敌方单位|[1一]个敌方单位|敌人)', desc):
        return f"[(target_enemy_minions, {count}, False)]"

    # 对战效果：与敌方单位对战
    if re.search(r'与(?:敌方单位|敌人|[1一]个敌方单位)对战', desc):
        return f"[(target_enemy_minions, {count}, False)]"

    return None


def try_generate_extra_targeting_stages(desc: str) -> Optional[str]:
    """根据策略卡效果描述自动推断 extra_targeting_stages。

    返回 Python 列表字面量字符串，如 \"[(target_enemy_minions, 1, False)]\"
    """
    import re
    if not desc:
        return None
    # 使友方...然后与敌方单位对战
    if re.search(r'然后与.*敌方单位对战', desc):
        return "[(target_enemy_minions, 1, False)]"
    return None


def try_generate_sacrifice_transform_effect(description: str) -> Optional[str]:
    """专门匹配 13号孩子：献祭后，变为 XXX。"""
    import re
    m = re.search(r'献祭后，变为[“"]([^”"]+)[”"]', description)
    if m:
        target_name = m.group(1)
        return f'lambda p, t, g, extras=None: (setattr(t, "_transform_on_sacrifice", "{target_name}") or True) if hasattr(t, "_transform_on_sacrifice") else True'
    return None


def try_generate_move_effect(description: str) -> Optional[str]:
    """尝试生成移动/交换/遣返类效果。"""
    desc = description.strip()
    # 将一个敌方单位移动到友方区域
    if re.search(r'将.*?敌方.*?移动.*?友方区域', desc):
        return 'lambda p, t, g, extras=None: move_enemy_to_friendly(p, t, g)'
    # 将两个友方单位交换位置
    if re.search(r'交换两个友方单位', desc):
        return 'lambda p, t, g, extras=None: swap_units(t, extras, g)'
    # 将两个敌方单位交换位置
    if re.search(r'交换两个敌方单位', desc):
        return 'lambda p, t, g, extras=None: swap_units(t, extras, g)'
    # 将一个单位返回手牌
    if re.search(r'返回手牌', desc):
        return 'lambda p, t, g, extras=None: return_to_hand(t, g, p)'
    return None


def generate_card_code(card: Dict[str, Any], pack_enum: str, special_map: Optional[Dict[str, str]] = None, strategy_map: Optional[Dict[str, str]] = None) -> str:
    lines = []
    name = card["name"]
    cost_str = card["cost_str"]
    card_type = card["card_type"]
    immersion = card["immersion_level"]
    desc = card["description"].strip()

    type_map = {
        "minion": "CardType.MINION",
        "strategy": "CardType.STRATEGY",
        "conspiracy": "CardType.CONSPIRACY",
        "mineral": "CardType.MINERAL",
    }
    ct = type_map.get(card_type, "CardType.STRATEGY")

    lines.append(f'register_card(')
    lines.append(f'    name="{escape_string(name)}",')
    lines.append(f'    cost_str="{cost_str}",')
    lines.append(f'    card_type={ct},')
    lines.append(f'    pack=Pack.{pack_enum},')
    lines.append(f'    rarity={card["rarity"]},')
    if immersion > 1 or card_type in ("minion", "strategy", "conspiracy"):
        lines.append(f'    immersion_level={immersion},')

    if card["attack"] is not None:
        lines.append(f'    attack={card["attack"]},')
    if card["health"] is not None:
        lines.append(f'    health={card["health"]},')

    kw = normalize_keywords(card["keywords"])
    if kw:
        # 把 dict 写成一行
        kw_parts = [f'"{k}": {repr(v)}' for k, v in kw.items()]
        lines.append(f'    keywords={{{", ".join(kw_parts)}}},')

    # 雕像卡的标签（冥刻卡包）
    _STATUE_TAGS = {
        "节肢座首": ["昆虫"],
        "多足底座": ["昆虫"],
        "水肺座首": ["水生", "两栖"],
        "鳍尾底座": ["水生", "两栖"],
        "尖牙座首": ["陆生", "肉食动物"],
        "利爪底座": ["陆生", "肉食动物"],
        "丰饶座首": [],
        "牢牲底座": [],
        "长翅座首": ["飞禽"],
        "破风底座": ["飞禽"],
    }

    # 标签：主行解析的 tags + 覆盖表补充 + 雕像卡标签
    tags = list(card.get("tags", []))
    override_tags = TAG_OVERRIDES.get(name)
    if override_tags:
        for t in override_tags:
            if t not in tags:
                tags.append(t)
    for t in _STATUE_TAGS.get(name, []):
        if t not in tags:
            tags.append(t)
    if tags:
        lines.append(f'    tags={tags},')

    # 隐藏词条：离散卡包默认空 dict，用户可后续手动编辑
    if pack_enum == "DISCRETE":
        lines.append(f'    hidden_keywords={{}},')

    if card_type == "mineral" and card.get("mineral_type"):
        lines.append(f'    mineral_type="{card["mineral_type"]}",')
        lines.append(f'    stack_limit={card["stack_limit"]},')

    if card.get("is_moment"):
        lines.append(f'    is_moment=True,')

    if card.get("is_token"):
        lines.append(f'    is_token=True,')

    if card.get("evolve_to"):
        lines.append(f'    evolve_to="{escape_string(card["evolve_to"])}",')

    # 雕像卡自动注入字段（冥刻卡包）
    _STATUE_MAP = {
        "节肢座首": ("arthropod", True, False, "_arthropod_top_effect", None),
        "多足底座": ("arthropod", False, True, None, "_arthropod_bottom_effect"),
        "水肺座首": ("aquatic", True, False, "_aquatic_top_effect", None),
        "鳍尾底座": ("aquatic", False, True, None, "_aquatic_bottom_effect"),
        "尖牙座首": ("predator", True, False, "_predator_top_effect", None),
        "利爪底座": ("predator", False, True, None, "_predator_bottom_effect"),
        "丰饶座首": ("sacrifice", True, False, "_sacrifice_top_effect", None),
        "牢牲底座": ("sacrifice", False, True, None, "_sacrifice_bottom_effect"),
        "长翅座首": ("avian", True, False, "_avian_top_effect", None),
        "破风底座": ("avian", False, True, None, "_avian_bottom_effect"),
    }
    if name in _STATUE_MAP:
        pair, is_top, is_bottom, act_fn, fuse_fn = _STATUE_MAP[name]
        lines.append(f'    statue_top={is_top},')
        lines.append(f'    statue_bottom={is_bottom},')
        lines.append(f'    statue_pair="{pair}",')
        if act_fn:
            lines.append(f'    on_statue_activate={act_fn},')
        if fuse_fn:
            lines.append(f'    on_statue_fuse={fuse_fn},')

    # 效果描述注释
    if desc:
        lines.append(f'    # 效果描述：{escape_string(desc)}')

    # 尝试自动生成简单效果
    chosen_effect = None
    is_deploy = "部署：" in desc or "部署时：" in desc
    deploy_part = desc.split("部署：", 1)[1].split("。", 1)[0] + "。" if "部署：" in desc else desc

    if "开发" in desc:
        chosen_effect = try_generate_develop_effect(deploy_part if is_deploy else desc)

    if not chosen_effect and "获得恐惧" in desc and desc.count("获得恐惧") == 1:
        import re
        m = re.match(r'^(?:部署：)?使(?:1个|一个)单位获得恐惧。?$', desc)
        if m:
            chosen_effect = 'lambda p, t, g, extras=None: (t.apply_fear() or True) if hasattr(t, "apply_fear") else False'

    if not chosen_effect and ("抽" in desc and "牌" in desc):
        chosen_effect = try_generate_draw_effect(desc)

    if not chosen_effect and ("回复" in desc or "恢复" in desc or "获得" in desc and ("HP" in desc or "生命" in desc)):
        chosen_effect = try_generate_heal_effect(desc)

    if not chosen_effect and ("失去" in desc or "流失" in desc) and ("HP" in desc or "生命" in desc or "hp" in desc):
        chosen_effect = try_generate_lose_hp_effect(desc)

    if not chosen_effect and "伤害" in desc:
        chosen_effect = try_generate_damage_effect(desc)

    if not chosen_effect and "获得" in desc:
        chosen_effect = try_generate_keyword_effect(desc)

    if not chosen_effect and "献祭后，变为" in desc:
        chosen_effect = try_generate_sacrifice_transform_effect(desc)

    if not chosen_effect and ("移动" in desc or "交换" in desc or "返回手牌" in desc):
        chosen_effect = try_generate_move_effect(desc)

    # 自动推断 targets_fn
    chosen_targets_fn = try_generate_targets_fn(desc, card_type)
    if not chosen_targets_fn:
        if card_type == "minion":
            chosen_targets_fn = ("target_friendly_positions", 1, False)
        else:
            chosen_targets_fn = ("target_none", 1, False)
    fn_name, target_count, target_repeat = chosen_targets_fn
    lines.append(f'    targets_fn={fn_name},')
    if target_count != 1:
        lines.append(f'    targets_count={target_count},')
    if target_repeat:
        lines.append(f'    targets_repeat=True,')

    # 部署效果的额外指向目标推导（已统一为 extra_targeting_stages）
    if card_type == "minion" and is_deploy:
        extra_stages = try_generate_minion_extra_stages(deploy_part)
        if extra_stages:
            lines.append(f'    extra_targeting_stages={extra_stages},')

    # 策略卡多阶段指向推导
    if card_type in ("strategy", "conspiracy", "mineral"):
        extra_stages = try_generate_extra_targeting_stages(desc)
        if extra_stages:
            lines.append(f'    extra_targeting_stages={extra_stages},')

    if card_type in ("strategy",):
        # 人工实现的策略效果优先于自动生成
        if strategy_map and name in strategy_map:
            lines.append(f'    effect_fn={strategy_map[name]},')
        elif chosen_effect:
            lines.append(f'    effect_fn={chosen_effect},')
        else:
            lines.append(f'    effect_fn=None,  # TODO: 实现效果')
    elif card_type == "minion":
        if chosen_effect and is_deploy:
            lines.append(f'    special_fn={chosen_effect},')
        elif special_map and name in special_map:
            lines.append(f'    special_fn={special_map[name]},')
        else:
            lines.append(f'    special_fn=None,  # TODO: 实现部署/回合效果')
    elif card_type == "conspiracy":
        lines.append(f'    condition_fn=None,  # TODO: 实现触发条件')
        if chosen_effect:
            lines.append(f'    effect_fn={chosen_effect},')
        else:
            lines.append(f'    effect_fn=None,  # TODO: 实现效果')
    elif card_type == "mineral":
        if chosen_effect:
            lines.append(f'    effect_fn={chosen_effect},')
        else:
            lines.append(f'    effect_fn=None,  # TODO: 实现打出效果')

    lines.append(f')')
    return "\n".join(lines)


def generate_file(cards: List[Dict[str, Any]], filename: str, pack_enum: str) -> str:
    lines = [
        '# 自动生成的卡包定义文件',
        '# 由 translate_packs.py 翻译生成',
        '',
        'from tards import register_card, CardType, Pack, Rarity, DEFAULT_REGISTRY',
        'from tards.targets import target_friendly_positions, target_none, target_any_minion, target_enemy_minions, target_enemy_player, target_self, target_friendly_minions',
        'from tards.auto_effects import move_enemy_to_friendly, swap_units, return_to_hand',
    ]
    # 使用 importlib 直接加载 effects 文件，避免触发 card_pools/__init__.py
    special_map: Dict[str, str] = {}
    strategy_map: Dict[str, str] = {}
    effects_path = os.path.join(OUTPUT_DIR, f"{filename}_effects.py")
    if os.path.exists(effects_path):
        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location(
                f"{filename}_effects", effects_path
            )
            if spec and spec.loader:
                effects_mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(effects_mod)
                special_map = getattr(effects_mod, "SPECIAL_MAP", {})
                strategy_map = getattr(effects_mod, "STRATEGY_MAP", {})
        except Exception:
            pass
    if special_map or strategy_map:
        lines.append(f'from .{filename}_effects import *')
    lines.extend([
        '',
        f'# Pack: {pack_enum}',
        '',
    ])
    for card in cards:
        lines.append(generate_card_code(card, pack_enum, special_map, strategy_map))
        lines.append("")
    return "\n".join(lines)


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    for txt_name, (py_name, pack_enum) in PACK_FILE_MAP.items():
        if not os.path.exists(txt_name):
            print(f"跳过不存在的文件: {txt_name}")
            continue

        print(f"正在解析 {txt_name} ...")
        cards = process_file(txt_name)
        print(f"  解析出 {len(cards)} 张卡牌")

        content = generate_file(cards, py_name, pack_enum)
        out_path = os.path.join(OUTPUT_DIR, f"{py_name}.py")
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"  已写入 {out_path}")

    # 生成 __init__.py
    init_path = os.path.join(OUTPUT_DIR, "__init__.py")
    with open(init_path, "w", encoding="utf-8") as f:
        f.write("# 自动生成的卡包池\n")
        for _, (py_name, _) in PACK_FILE_MAP.items():
            f.write(f"from . import {py_name}\n")
    print(f"  已写入 {init_path}")


if __name__ == "__main__":
    main()
