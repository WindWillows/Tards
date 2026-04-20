#!/usr/bin/env python3
"""构建 effect_utils 可视化查询页面。"""

import re
import ast
import os
from pathlib import Path

ROOT = Path("c:/Users/34773/Desktop/tards开发库")

def parse_effect_utils():
    """解析 effect_utils.py 中的所有函数定义。"""
    path = ROOT / "card_pools" / "effect_utils.py"
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    tree = ast.parse(content)
    functions = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            docstring = ast.get_docstring(node) or ""
            brief = docstring.split("\n")[0] if docstring else ""
            # Get argument names
            args = []
            for arg in node.args.args:
                if arg.arg not in ("self", "cls"):
                    args.append(arg.arg)
            # Get return annotation hint if available
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
            })
    functions.sort(key=lambda x: x["line"])
    return functions


def scan_calls_in_file(filepath, target_functions):
    """扫描单个文件中调用了哪些 target_functions。"""
    if not filepath.exists():
        return []
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    called = set()
    # Simple regex to find function calls: func_name(
    for func in target_functions:
        # Match word boundary to avoid partial matches
        pattern = r'\b' + re.escape(func["name"]) + r'\s*\('
        if re.search(pattern, content):
            called.add(func["name"])
    return sorted(called)


def get_card_name_from_line(line):
    """从卡包文件的行中提取卡牌名称。"""
    # Look for register_card(name="...")
    m = re.search(r'register_card\(\s*name\s*=\s*"([^"]+)"', line)
    if m:
        return m.group(1)
    return None


def scan_pack_file(filepath, target_functions):
    """扫描卡包文件，返回 {卡牌名: [调用的函数列表]}。"""
    if not filepath.exists():
        return {}
    with open(filepath, "r", encoding="utf-8") as f:
        lines = f.readlines()

    result = {}
    current_card = None

    for i, line in enumerate(lines):
        # Detect card registration
        card_name = get_card_name_from_line(line)
        if card_name:
            current_card = card_name
            result[current_card] = set()

        if current_card:
            for func in target_functions:
                pattern = r'\b' + re.escape(func["name"]) + r'\s*\('
                if re.search(pattern, line):
                    result[current_card].add(func["name"])

    # Convert sets to sorted lists, filter empty
    return {k: sorted(v) for k, v in result.items() if v}


def scan_effects_file(filepath, target_functions):
    """扫描 effects 文件，返回 {效果函数名: [调用的函数列表]}。"""
    if not filepath.exists():
        return {}
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    tree = ast.parse(content)
    result = {}

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            func_name = node.name
            # Get source range
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

    # Scan pack files (generated card definitions)
    packs = {
        "离散卡包": ROOT / "card_pools" / "discrete.py",
        "冥刻卡包": ROOT / "card_pools" / "underworld.py",
        "血契卡包": ROOT / "card_pools" / "blood.py",
    }

    # Scan effects files
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

    # Also scan auto_effects.py and translate_packs.py
    auto_usage = scan_calls_in_file(ROOT / "tards" / "auto_effects.py", functions)
    translate_usage = scan_calls_in_file(ROOT / "translate_packs.py", functions)

    # Build reverse mapping: function -> callers
    func_callers = {f["name"]: [] for f in functions}

    for pack_name, cards in pack_usage.items():
        for card_name, called_funcs in cards.items():
            for func_name in called_funcs:
                if func_name in func_callers:
                    func_callers[func_name].append({
                        "type": "card",
                        "pack": pack_name,
                        "name": card_name,
                    })

    for effect_name, funcs in effects_usage.items():
        for func_name, called_funcs in funcs.items():
            for cf in called_funcs:
                if cf in func_callers:
                    func_callers[cf].append({
                        "type": "effect",
                        "pack": effect_name,
                        "name": func_name,
                    })

    for func_name in auto_usage:
        if func_name in func_callers:
            func_callers[func_name].append({
                "type": "auto_effects",
                "pack": "auto_effects.py",
                "name": "auto_effects.py",
            })

    for func_name in translate_usage:
        if func_name in func_callers:
            func_callers[func_name].append({
                "type": "translate",
                "pack": "translate_packs.py",
                "name": "translate_packs.py",
            })

    return {
        "functions": functions,
        "pack_usage": pack_usage,
        "effects_usage": effects_usage,
        "func_callers": func_callers,
    }


def generate_html(data):
    functions = data["functions"]
    func_callers = data["func_callers"]
    pack_usage = data["pack_usage"]
    effects_usage = data["effects_usage"]

    # Group functions by category based on line ranges
    categories = []
    cat_ranges = [
        (1, 200, "基础伤害与治疗"),
        (200, 400, "召唤与召唤物"),
        (400, 600, "手牌与牌库操作"),
        (600, 800, "状态与增益"),
        (800, 1000, "资源与费用"),
        (1000, 1200, "事件与监听"),
        (1200, 1400, "查询与选择"),
        (1400, 1600, "移动与位置"),
        (1600, 1800, "控制流与条件"),
        (1800, 2000, "地形与特殊机制"),
        (2000, 9999, "其他"),
    ]

    for f in functions:
        assigned = False
        for start, end, cat_name in cat_ranges:
            if start <= f["line"] < end:
                categories.append((cat_name, f))
                assigned = True
                break
        if not assigned:
            categories.append(("其他", f))

    # Build HTML
    html = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Tards 效果工具库 - 函数查询</title>
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
  .legend {
    display: flex;
    gap: 16px;
    font-size: 12px;
    margin-top: 8px;
  }
  .legend-item { display: flex; align-items: center; gap: 6px; }
  .legend-box { width: 12px; height: 12px; border-radius: 2px; }
</style>
</head>
<body>
"""

    html += f"""
<div class="header">
  <h1>🔧 Tards 效果工具库 - 函数查询</h1>
  <p>共 {len(functions)} 个通用函数 | 点击卡片查看调用详情</p>
</div>

<div class="toolbar">
  <input type="text" id="search" placeholder="搜索函数名或描述..." oninput="filter()">
  <select id="usageFilter" onchange="filter()">
    <option value="all">全部</option>
    <option value="used">已使用</option>
    <option value="unused">未使用</option>
  </select>
  <select id="packFilter" onchange="filter()">
    <option value="all">全部卡包</option>
    <option value="离散卡包">离散卡包</option>
    <option value="冥刻卡包">冥刻卡包</option>
    <option value="血契卡包">血契卡包</option>
  </select>
  <div class="legend">
    <div class="legend-item"><div class="legend-box" style="background:#f56565;"></div>未使用</div>
    <div class="legend-item"><div class="legend-box" style="background:#48bb78;"></div>已使用（≤3处）</div>
    <div class="legend-item"><div class="legend-box" style="background:#4299e1;"></div>广泛使用（&gt;3处）</div>
  </div>
  <div class="stats" id="stats"></div>
</div>

<div class="container">
"""

    current_cat = None
    for cat_name, func in categories:
        if cat_name != current_cat:
            if current_cat is not None:
                html += "</div></div>\n"
            html += f'<div class="category" data-category="{cat_name}">\n'
            html += f'<div class="category-title">{cat_name}</div>\n'
            html += '<div class="func-grid">\n'
            current_cat = cat_name

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

        # Build caller HTML
        caller_html = ""
        if callers:
            caller_items = ""
            for c in callers:
                icon = {"card": "🃏", "effect": "⚡", "auto_effects": "🔧", "translate": "📜"}.get(c["type"], "•")
                caller_items += f'<div class="caller-item"><span class="caller-type">{icon}</span>{c["name"]}<span class="caller-pack">({c["pack"]})</span></div>'
            caller_html = f'<details class="caller-list"><summary>调用详情 ({caller_count})</summary>{caller_items}</details>'

        # Args display
        args_str = ", ".join(func["args"]) if func["args"] else ""

        html += f"""
  <div class="func-card {usage_class}" data-name="{func['name']}" data-usage="{'used' if caller_count > 0 else 'unused'}" data-callers='{json.dumps(callers)}'>
    <div class="func-header">
      <span class="func-name">{func['name']}({args_str})</span>
      <span class="func-line">行 {func['line']}</span>
    </div>
    <div class="func-brief">{func['brief'] or '无描述'}</div>
    <div class="func-meta">
      <span class="badge {badge_class}">{badge_text}</span>
    </div>
    {caller_html}
    <div class="detail-panel" id="detail-{func['name']}">
      <strong>完整文档：</strong>
      <pre>{func['docstring'] or '无'}</pre>
    </div>
  </div>
"""

    if current_cat is not None:
        html += "</div></div>\n"

    # Add JavaScript
    html += """
</div>

<script>
function filter() {
  const search = document.getElementById('search').value.toLowerCase();
  const usage = document.getElementById('usageFilter').value;
  const pack = document.getElementById('packFilter').value;
  const cards = document.querySelectorAll('.func-card');
  let visible = 0;

  cards.forEach(card => {
    const name = card.dataset.name.toLowerCase();
    const brief = card.querySelector('.func-brief').textContent.toLowerCase();
    const cardUsage = card.dataset.usage;
    const callers = JSON.parse(card.dataset.callers || '[]');

    let show = true;
    if (search && !name.includes(search) && !brief.includes(search)) show = false;
    if (usage !== 'all' && cardUsage !== usage) show = false;
    if (pack !== 'all') {
      const inPack = callers.some(c => c.pack === pack);
      if (!inPack) show = false;
    }

    card.classList.toggle('hidden', !show);
    if (show) visible++;
  });

  document.getElementById('stats').textContent = '显示 ' + visible + ' / ' + cards.length;
}

document.querySelectorAll('.func-card').forEach(card => {
  card.addEventListener('click', function(e) {
    if (e.target.closest('details')) return;
    const detail = this.querySelector('.detail-panel');
    if (detail) detail.classList.toggle('show');
  });
});

filter();
</script>
</body>
</html>
"""

    return html


import json

if __name__ == "__main__":
    print("Building tool library page...")
    data = build_data()
    html = generate_html(data)

    output_path = ROOT / "effect_utils_browser.html"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"Generated: {output_path}")
    print(f"  Functions: {len(data['functions'])}")

    # Print usage stats
    used = sum(1 for f in data["functions"] if data["func_callers"][f["name"]])
    unused = len(data["functions"]) - used
    print(f"  Used: {used}, Unused: {unused}")

    # Print top used functions
    top = sorted(data["func_callers"].items(), key=lambda x: len(x[1]), reverse=True)[:10]
    print("  Top used functions:")
    for name, callers in top:
        if callers:
            print(f"    {name}: {len(callers)} callers")
