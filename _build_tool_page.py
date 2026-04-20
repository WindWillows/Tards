#!/usr/bin/env python3
"""构建 effect_utils 可视化查询页面（含关键词查询）。"""

import re
import ast
from pathlib import Path
import json

ROOT = Path("c:/Users/34773/Desktop/tards开发库")

# Semantic categories for functions
SEMANTIC_CATEGORIES = [
    ("伤害与治疗", [r"damage|heal|hurt|destroy_minion|kill"], 100),
    ("召唤与回响", [r"summon|echo|token|copy_card|copy_minion|summon_copy"], 95),
    ("手牌与牌库", [r"draw|discard|mill|deck|hand|shuffle|search_deck|reveal|put_on_top|put_on_bottom|peek|place_at|discover|draw_cards_of"], 90),
    ("异象查询与选择", [r"get_minions|all_enemy|all_friendly|random_minion|random_enemy|random_friendly|frontmost|by_tag|has_tag|get_enemy|get_friendly|get_all|get_frontmost|get_adjacent|get_card_defs"], 85),
    ("移动与位置", [r"move|shift|swap|empty_positions|get_adjacent"], 80),
    ("状态与增益", [r"buff|debuff|keyword|add_keyword|remove_keyword|silence|override_keywords|set_stat|modify_stat|augment|replace_combat"], 75),
    ("资源管理", [r"gain_resource|t_point|c_point|b_point|s_point"], 70),
    ("事件监听", [r"on_before|on_after|on_turn|on_damage|on_attack|on_deploy|on_destroy|on_discard|on_mill|on_sacrifice|on_draw|on_card_played|on_event|event|listener|add_event_listener|remove_event_listener|clear_event"], 65),
    ("延迟与条件", [r"delay|if_possible|track_stat|get_stat|increment_stat|track_per_turn|get_per_turn"], 60),
    ("群体效果", [r"aoe|all_enemies|all_friendly|damage_all|heal_all|buff_all|destroy_all"], 55),
    ("目标选择", [r"target|get_attack_target|get_front_minion|get_frontmost|can_minion_attack|is_untargetable"], 50),
    ("战场实用", [r"board|place_minion|remove_minion|get_terrain|clear_attack|can_attack|is_valid|target_check"], 45),
    ("战斗伤害", [r"combat|swing|attack_target|replace_combat|augment_combat"], 40),
    ("计数与追踪", [r"track|stat|count|deployed|damage_dealt|remember_target|get_remembered|clear_remembered|get_last_damage"], 35),
    ("地形与特殊机制", [r"terrain|override_terrain|clear_terrain"], 30),
]


def parse_effect_utils():
    path = ROOT / "card_pools" / "effect_utils.py"
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    tree = ast.parse(content)
    functions = []
    for node in tree.body:
        if isinstance(node, ast.FunctionDef):
            docstring = ast.get_docstring(node) or ""
            brief = docstring.split("\n")[0] if docstring else ""
            args = [arg.arg for arg in node.args.args if arg.arg not in ("self", "cls")]
            returns = ""
            if node.returns and isinstance(node.returns, ast.Constant):
                returns = str(node.returns.value)
            functions.append({
                "name": node.name,
                "line": node.lineno,
                "brief": brief,
                "docstring": docstring,
                "args": args,
                "returns": returns,
                "is_compat": "【兼容】" in docstring,
                "source": content.split("\n")[node.lineno-1:node.end_lineno],
            })
    functions.sort(key=lambda x: x["line"])
    return functions


def classify_function(func_name: str) -> str:
    name_lower = func_name.lower()
    for cat_name, patterns, priority in SEMANTIC_CATEGORIES:
        for pat in patterns:
            if re.search(pat, name_lower):
                return cat_name
    return "其他"


def extract_keyword_definitions():
    """从 rules_text.txt 提取关键词定义。"""
    path = ROOT / "rules_text.txt"
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    
    keywords = {}
    in_keyword_section = False
    for line in content.split("\n"):
        line = line.strip()
        if line == "词条":
            in_keyword_section = True
            continue
        if in_keyword_section and line:
            if "：" in line or ":" in line:
                sep = "：" if "：" in line else ":"
                name, desc = line.split(sep, 1)
                name = name.strip()
                # Filter out non-keyword lines (explanatory text, section headers)
                # Valid keyword names: 2-8 Chinese chars, optionally ending with X
                if not re.match(r'^[\u4e00-\u9fa5]{2,8}[Xx]?$', name):
                    continue
                # Strip X suffix for base name
                base_name = re.sub(r'[Xx]\s*$', '', name).strip()
                keywords[base_name] = desc.strip()
            elif line.startswith("卡组组建"):
                break
    return keywords


def scan_keyword_references(functions):
    """扫描哪些函数引用了哪些关键词。"""
    # Also scan core engine files
    core_files = {
        "game.py": ROOT / "tards" / "game.py",
        "board.py": ROOT / "tards" / "board.py",
        "cards.py": ROOT / "tards" / "cards.py",
        "player.py": ROOT / "tards" / "player.py",
        "targeting.py": ROOT / "tards" / "targeting.py",
    }
    
    # Build function source map
    func_sources = {}
    for func in functions:
        func_sources[func["name"]] = "\n".join(func["source"])
    
    # Add core engine functions
    for fname, fpath in core_files.items():
        if not fpath.exists():
            continue
        with open(fpath, "r", encoding="utf-8") as f:
            content = f.read()
        tree = ast.parse(content)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                src = "\n".join(content.split("\n")[node.lineno-1:node.end_lineno])
                full_name = f"{fname}::{node.name}"
                func_sources[full_name] = src
    
    # Get all keyword base names
    kw_defs = extract_keyword_definitions()
    kw_names = set(kw_defs.keys())
    # Also add keywords from constants that might not be in rules_text
    from tards.constants import GENERAL_KEYWORDS
    for kw in GENERAL_KEYWORDS:
        base = re.sub(r'[Xx]\s*$', '', kw)
        kw_names.add(base)
    
    # Scan references
    keyword_funcs = {kw: [] for kw in kw_names}
    
    for func_name, source in func_sources.items():
        for kw in kw_names:
            if kw in source:
                keyword_funcs[kw].append(func_name)
    
    # Remove self-references and deduplicate
    for kw in keyword_funcs:
        keyword_funcs[kw] = sorted(set(keyword_funcs[kw]))
    
    return keyword_funcs


def scan_calls_in_file(filepath, target_functions):
    if not filepath.exists():
        return []
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
    called = set()
    for func in target_functions:
        pattern = r'\b' + re.escape(func["name"]) + r'\s*\('
        if re.search(pattern, content):
            called.add(func["name"])
    return sorted(called)


def get_card_name_from_line(line):
    m = re.search(r'register_card\(\s*name\s*=\s*"([^"]+)"', line)
    if m:
        return m.group(1)
    return None


def scan_pack_file(filepath, target_functions):
    if not filepath.exists():
        return {}
    with open(filepath, "r", encoding="utf-8") as f:
        lines = f.readlines()
    result = {}
    current_card = None
    for i, line in enumerate(lines):
        card_name = get_card_name_from_line(line)
        if card_name:
            current_card = card_name
            result[current_card] = set()
        if current_card:
            for func in target_functions:
                pattern = r'\b' + re.escape(func["name"]) + r'\s*\('
                if re.search(pattern, line):
                    result[current_card].add(func["name"])
    return {k: sorted(v) for k, v in result.items() if v}


def scan_effects_file(filepath, target_functions):
    if not filepath.exists():
        return {}
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
    tree = ast.parse(content)
    result = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            func_name = node.name
            start = node.lineno - 1
            end = node.end_lineno
            func_source = "\n".join(content.split("\n")[start:end])
            called = set()
            for func in target_functions:
                pattern = r'\b' + re.escape(func["name"]) + r'\s*\('
                if re.search(pattern, func_source):
                    called.add(func["name"])
            if called:
                result[func_name] = sorted(called)
    return result


def build_data():
    functions = parse_effect_utils()
    func_names = [f["name"] for f in functions]
    
    packs = {
        "离散卡包": ROOT / "card_pools" / "discrete.py",
        "冥刻卡包": ROOT / "card_pools" / "underworld.py",
        "血契卡包": ROOT / "card_pools" / "blood.py",
    }
    effects = {
        "离散效果": ROOT / "card_pools" / "discrete_effects.py",
        "冥刻效果": ROOT / "card_pools" / "underworld_effects.py",
        "血契效果": ROOT / "card_pools" / "blood_effects.py",
    }
    
    pack_usage = {}
    for pack_name, filepath in packs.items():
        pack_usage[pack_name] = scan_pack_file(filepath, functions)
    
    effects_usage = {}
    for effect_name, filepath in effects.items():
        effects_usage[effect_name] = scan_effects_file(filepath, functions)
    
    auto_usage = scan_calls_in_file(ROOT / "tards" / "auto_effects.py", functions)
    translate_usage = scan_calls_in_file(ROOT / "translate_packs.py", functions)
    
    func_callers = {f["name"]: [] for f in functions}
    
    for pack_name, cards in pack_usage.items():
        for card_name, called_funcs in cards.items():
            for func_name in called_funcs:
                if func_name in func_callers:
                    func_callers[func_name].append({"type": "card", "pack": pack_name, "name": card_name})
    
    for effect_name, funcs in effects_usage.items():
        for func_name, called_funcs in funcs.items():
            for cf in called_funcs:
                if cf in func_callers:
                    func_callers[cf].append({"type": "effect", "pack": effect_name, "name": func_name})
    
    for func_name in auto_usage:
        if func_name in func_callers:
            func_callers[func_name].append({"type": "auto_effects", "pack": "auto_effects.py", "name": "auto_effects.py"})
    
    for func_name in translate_usage:
        if func_name in func_callers:
            func_callers[func_name].append({"type": "translate", "pack": "translate_packs.py", "name": "translate_packs.py"})
    
    for func in functions:
        func["category"] = classify_function(func["name"])
    
    keyword_defs = extract_keyword_definitions()
    keyword_funcs = scan_keyword_references(functions)
    
    return {
        "functions": functions,
        "pack_usage": pack_usage,
        "effects_usage": effects_usage,
        "func_callers": func_callers,
        "keyword_defs": keyword_defs,
        "keyword_funcs": keyword_funcs,
    }


def generate_html(data):
    functions = data["functions"]
    func_callers = data["func_callers"]
    keyword_defs = data["keyword_defs"]
    keyword_funcs = data["keyword_funcs"]
    
    categories = {}
    for func in functions:
        cat = func["category"]
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(func)
    
    category_order = [
        "伤害与治疗", "召唤与回响", "手牌与牌库", "异象查询与选择",
        "移动与位置", "状态与增益", "战斗伤害", "群体效果",
        "目标选择", "资源管理", "事件监听", "延迟与条件",
        "计数与追踪", "战场实用", "地形与特殊机制", "其他",
    ]
    
    ordered_categories = []
    for cat_name in category_order:
        if cat_name in categories and categories[cat_name]:
            ordered_categories.append((cat_name, categories[cat_name]))
    for cat_name, funcs in categories.items():
        if cat_name not in category_order and funcs:
            ordered_categories.append((cat_name, funcs))
    
    total_funcs = len(functions)
    total_compat = sum(1 for f in functions if f["is_compat"])
    total_keywords = len(keyword_defs)
    
    html = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Tards 效果工具库 - 函数与关键词查询</title>
<style>
  * { box-sizing: border-box; }
  body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    margin: 0; padding: 0;
    background: #f5f6fa;
    color: #2d3436;
  }
  .header {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    padding: 24px 32px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.15);
  }
  .header h1 { margin: 0; font-size: 24px; }
  .header p { margin: 8px 0 0; opacity: 0.9; font-size: 14px; }
  .tabs {
    display: flex;
    gap: 0;
    padding: 0 32px;
    background: white;
    border-bottom: 1px solid #e1e4e8;
  }
  .tab {
    padding: 12px 24px;
    cursor: pointer;
    font-size: 14px;
    font-weight: 500;
    color: #6b7280;
    border-bottom: 2px solid transparent;
    transition: all 0.2s;
  }
  .tab:hover { color: #4a5568; }
  .tab.active {
    color: #667eea;
    border-bottom-color: #667eea;
  }
  .toolbar {
    display: flex;
    gap: 12px;
    padding: 16px 32px;
    background: white;
    border-bottom: 1px solid #e1e4e8;
    flex-wrap: wrap;
    align-items: center;
  }
  .toolbar input, .toolbar select {
    padding: 8px 12px;
    border: 1px solid #d1d5db;
    border-radius: 6px;
    font-size: 14px;
    outline: none;
  }
  .toolbar input:focus, .toolbar select:focus {
    border-color: #667eea;
    box-shadow: 0 0 0 3px rgba(102,126,234,0.15);
  }
  .toolbar input[type="text"] { width: 280px; }
  .toolbar label { font-size: 13px; color: #6b7280; }
  .stats {
    margin-left: auto;
    font-size: 13px;
    color: #6b7280;
  }
  .container {
    padding: 24px 32px;
    max-width: 1400px;
    margin: 0 auto;
  }
  .tab-panel { display: none; }
  .tab-panel.active { display: block; }
  .category {
    margin-bottom: 24px;
  }
  .category-title {
    font-size: 16px;
    font-weight: 600;
    color: #4a5568;
    margin-bottom: 12px;
    padding-bottom: 6px;
    border-bottom: 2px solid #e2e8f0;
  }
  .func-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(360px, 1fr));
    gap: 12px;
  }
  .func-card {
    background: white;
    border-radius: 10px;
    padding: 16px;
    border: 1px solid #e2e8f0;
    transition: all 0.2s;
    cursor: pointer;
  }
  .func-card:hover {
    box-shadow: 0 4px 12px rgba(0,0,0,0.08);
    border-color: #cbd5e0;
    transform: translateY(-1px);
  }
  .func-card.hidden { display: none; }
  .func-card.unused { border-left: 4px solid #f56565; }
  .func-card.used { border-left: 4px solid #48bb78; }
  .func-card.many { border-left: 4px solid #4299e1; }
  .func-card.compat { background: #fffaf0; border-left: 4px solid #ed8936; }
  .func-header {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    margin-bottom: 6px;
  }
  .func-name {
    font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace;
    font-size: 14px;
    font-weight: 600;
    color: #2b6cb0;
  }
  .func-line {
    font-size: 11px;
    color: #a0aec0;
  }
  .func-brief {
    font-size: 13px;
    color: #4a5568;
    margin-bottom: 10px;
    line-height: 1.4;
  }
  .func-meta {
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
    align-items: center;
  }
  .badge {
    font-size: 11px;
    padding: 2px 8px;
    border-radius: 12px;
    font-weight: 500;
  }
  .badge-unused { background: #fed7d7; color: #c53030; }
  .badge-used { background: #c6f6d5; color: #276749; }
  .badge-many { background: #bee3f8; color: #2c5282; }
  .badge-compat { background: #feebc8; color: #c05621; }
  .caller-list {
    margin-top: 10px;
    padding-top: 10px;
    border-top: 1px solid #edf2f7;
    font-size: 12px;
  }
  .caller-list summary {
    color: #667eea;
    cursor: pointer;
    font-weight: 500;
    user-select: none;
  }
  .caller-item {
    padding: 2px 0;
    color: #4a5568;
  }
  .caller-type {
    display: inline-block;
    width: 14px;
    text-align: center;
    margin-right: 4px;
  }
  .caller-pack { color: #a0aec0; margin-left: 4px; }
  .detail-panel {
    display: none;
    margin-top: 10px;
    padding: 12px;
    background: #f7fafc;
    border-radius: 6px;
    font-size: 12px;
    line-height: 1.6;
  }
  .detail-panel.show { display: block; }
  .detail-panel pre {
    margin: 4px 0;
    white-space: pre-wrap;
    word-break: break-word;
    color: #4a5568;
  }
  .code-block {
    background: #1a202c;
    color: #e2e8f0;
    padding: 12px;
    border-radius: 6px;
    overflow-x: auto;
    font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace;
    font-size: 12px;
    line-height: 1.5;
    margin-top: 8px;
  }
  .code-block .line-num {
    color: #718096;
    display: inline-block;
    width: 32px;
    text-align: right;
    margin-right: 8px;
    user-select: none;
  }
  .legend {
    display: flex;
    gap: 16px;
    font-size: 12px;
    margin-top: 8px;
  }
  .legend-item { display: flex; align-items: center; gap: 6px; }
  .legend-box { width: 12px; height: 12px; border-radius: 2px; }
  /* Keyword cards */
  .kw-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(420px, 1fr));
    gap: 14px;
  }
  .kw-card {
    background: white;
    border-radius: 10px;
    padding: 18px;
    border: 1px solid #e2e8f0;
    border-left: 4px solid #667eea;
    transition: all 0.2s;
    cursor: pointer;
  }
  .kw-card:hover {
    box-shadow: 0 4px 12px rgba(0,0,0,0.08);
    transform: translateY(-1px);
  }
  .kw-card.hidden { display: none; }
  .kw-name {
    font-size: 15px;
    font-weight: 600;
    color: #2d3748;
    margin-bottom: 8px;
  }
  .kw-desc {
    font-size: 13px;
    color: #4a5568;
    line-height: 1.5;
    margin-bottom: 12px;
  }
  .kw-funcs {
    font-size: 12px;
    color: #667eea;
  }
  .kw-func-tag {
    display: inline-block;
    background: #edf2f7;
    color: #4a5568;
    padding: 2px 8px;
    border-radius: 4px;
    margin: 2px 4px 2px 0;
    font-size: 11px;
  }
</style>
</head>
<body>
"""

    html += f"""
<div class="header">
  <h1>🔧 Tards 效果工具库 - 函数与关键词查询</h1>
  <p>共 {total_funcs} 个通用函数（含 {total_compat} 个兼容层） | {total_keywords} 个关键词</p>
</div>

<div class="tabs">
  <div class="tab active" onclick="switchTab('functions')">📦 函数查询</div>
  <div class="tab" onclick="switchTab('keywords')">🏷️ 关键词查询</div>
</div>
"""

    # Functions tab
    html += """
<div id="tab-functions" class="tab-panel active">
  <div class="toolbar">
    <input type="text" id="searchFunc" placeholder="搜索函数名或描述..." oninput="filterFunc()">
    <select id="usageFilter" onchange="filterFunc()">
      <option value="all">全部</option>
      <option value="used">已使用</option>
      <option value="unused">未使用</option>
    </select>
    <select id="packFilter" onchange="filterFunc()">
      <option value="all">全部卡包</option>
      <option value="离散卡包">离散卡包</option>
      <option value="冥刻卡包">冥刻卡包</option>
      <option value="血契卡包">血契卡包</option>
    </select>
    <label style="display:flex;align-items:center;gap:6px;cursor:pointer;font-size:13px;color:#4a5568;">
      <input type="checkbox" id="hideCompat" onchange="filterFunc()"> 隐藏兼容层
    </label>
    <div class="legend">
      <div class="legend-item"><div class="legend-box" style="background:#f56565;"></div>未使用</div>
      <div class="legend-item"><div class="legend-box" style="background:#48bb78;"></div>已使用（≤3处）</div>
      <div class="legend-item"><div class="legend-box" style="background:#4299e1;"></div>广泛使用（&gt;3处）</div>
    </div>
    <div class="stats" id="funcStats"></div>
  </div>

  <div class="container">
"""

    for cat_name, funcs in ordered_categories:
        if not funcs:
            continue
        html += f'<div class="category" data-category="{cat_name}">\n'
        html += f'<div class="category-title">{cat_name} ({len(funcs)})</div>\n'
        html += '<div class="func-grid">\n'
        
        for func in funcs:
            callers = func_callers.get(func["name"], [])
            caller_count = len(callers)
            if caller_count == 0:
                usage_class = "unused"
                badge_class = "badge-unused"
                badge_text = "未使用"
            elif caller_count <= 3:
                usage_class = "used"
                badge_class = "badge-used"
                badge_text = f"{caller_count} 处调用"
            else:
                usage_class = "many"
                badge_class = "badge-many"
                badge_text = f"{caller_count} 处调用"
            
            caller_html = ""
            if callers:
                caller_items = ""
                for c in callers:
                    icon = {"card": "🃏", "effect": "⚡", "auto_effects": "🔧", "translate": "📜"}.get(c["type"], "•")
                    caller_items += f'<div class="caller-item"><span class="caller-type">{icon}</span>{c["name"]}<span class="caller-pack">({c["pack"]})</span></div>'
                caller_html = f'<details class="caller-list"><summary>调用详情 ({caller_count})</summary>{caller_items}</details>'
            
            args_str = ", ".join(func["args"]) if func["args"] else ""
            
            html += f"""
  <div class="func-card {usage_class}{' compat' if func['is_compat'] else ''}" data-name="{func['name']}" data-usage="{'used' if caller_count > 0 else 'unused'}" data-compat="{'true' if func['is_compat'] else 'false'}" data-callers='{json.dumps(callers)}'>
    <div class="func-header">
      <span class="func-name">{func['name']}({args_str})</span>
      <span class="func-line">行 {func['line']}</span>
    </div>
    <div class="func-brief">{func['brief'] or '无描述'}</div>
    <div class="func-meta">
      <span class="badge {badge_class}">{badge_text}</span>
      {'<span class="badge badge-compat">兼容层</span>' if func['is_compat'] else ''}
    </div>
    {caller_html}
    <div class="detail-panel" id="detail-{func['name']}">
      <strong>完整文档：</strong>
      <pre>{func['docstring'] or '无'}</pre>
      <strong style="display:block;margin-top:10px;">源代码：</strong>
      <div class="code-block">{"".join(f'<span class="line-num">{func["line"]+i}</span>{line.replace("<","&lt;").replace(">","&gt;")}<br>' for i,line in enumerate(func['source']))}</div>
    </div>
  </div>
"""
        html += "</div></div>\n"
    
    html += "</div></div>\n"

    # Keywords tab
    html += """
<div id="tab-keywords" class="tab-panel">
  <div class="toolbar">
    <input type="text" id="searchKw" placeholder="搜索关键词..." oninput="filterKw()">
    <div class="stats" id="kwStats"></div>
  </div>
  <div class="container">
    <div class="kw-grid" id="kwGrid">
"""

    for kw_name, kw_desc in sorted(keyword_defs.items()):
        related_funcs = keyword_funcs.get(kw_name, [])
        func_tags = ""
        for fn in related_funcs[:8]:
            func_tags += f'<span class="kw-func-tag">{fn}</span>'
        if len(related_funcs) > 8:
            func_tags += f'<span class="kw-func-tag">+{len(related_funcs)-8} more</span>'
        
        html += f"""
      <div class="kw-card" data-kw="{kw_name}">
        <div class="kw-name">{kw_name}</div>
        <div class="kw-desc">{kw_desc}</div>
        <div class="kw-funcs">
          <strong>相关函数：</strong>
          {func_tags if func_tags else '<span style="color:#a0aec0;">无</span>'}
        </div>
      </div>
"""
    
    html += "    </div>\n  </div>\n</div>\n"

    # JavaScript
    html += """
<script>
function switchTab(tabName) {
  document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
  document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
  event.target.classList.add('active');
  document.getElementById('tab-' + tabName).classList.add('active');
}

function filterFunc() {
  const search = document.getElementById('searchFunc').value.toLowerCase();
  const usage = document.getElementById('usageFilter').value;
  const pack = document.getElementById('packFilter').value;
  const hideCompat = document.getElementById('hideCompat').checked;
  const cards = document.querySelectorAll('.func-card');
  let visible = 0;

  cards.forEach(card => {
    const name = card.dataset.name.toLowerCase();
    const brief = card.querySelector('.func-brief').textContent.toLowerCase();
    const cardUsage = card.dataset.usage;
    const callers = JSON.parse(card.dataset.callers || '[]');
    const isCompat = card.dataset.compat === 'true';

    let show = true;
    if (search && !name.includes(search) && !brief.includes(search)) show = false;
    if (usage !== 'all' && cardUsage !== usage) show = false;
    if (pack !== 'all') {
      const inPack = callers.some(c => c.pack === pack);
      if (!inPack) show = false;
    }
    if (hideCompat && isCompat) show = false;

    card.classList.toggle('hidden', !show);
    if (show) visible++;
  });

  document.getElementById('funcStats').textContent = '显示 ' + visible + ' / ' + cards.length;
}

function filterKw() {
  const search = document.getElementById('searchKw').value.toLowerCase();
  const cards = document.querySelectorAll('.kw-card');
  let visible = 0;

  cards.forEach(card => {
    const name = card.dataset.kw.toLowerCase();
    const desc = card.querySelector('.kw-desc').textContent.toLowerCase();
    const funcs = card.querySelector('.kw-funcs').textContent.toLowerCase();

    let show = true;
    if (search && !name.includes(search) && !desc.includes(search) && !funcs.includes(search)) show = false;

    card.classList.toggle('hidden', !show);
    if (show) visible++;
  });

  document.getElementById('kwStats').textContent = '显示 ' + visible + ' / ' + cards.length;
}

document.querySelectorAll('.func-card').forEach(card => {
  card.addEventListener('click', function(e) {
    if (e.target.closest('details')) return;
    const detail = this.querySelector('.detail-panel');
    if (detail) detail.classList.toggle('show');
  });
});

filterFunc();
filterKw();
</script>
</body>
</html>
"""

    return html


if __name__ == "__main__":
    print("Building tool library page...")
    data = build_data()
    html = generate_html(data)

    output_path = ROOT / "effect_utils_browser.html"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"Generated: {output_path}")
    print(f"  Functions: {len(data['functions'])}")
    print(f"  Keywords: {len(data['keyword_defs'])}")
    print(f"  Used: {sum(1 for f in data['functions'] if data['func_callers'][f['name']])}, Unused: {sum(1 for f in data['functions'] if not data['func_callers'][f['name']])}")
