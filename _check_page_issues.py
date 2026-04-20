#!/usr/bin/env python3
import ast
import re
from collections import Counter

# Check effect_utils.py for duplicates and missing docstrings
with open('card_pools/effect_utils.py', 'r', encoding='utf-8') as f:
    content = f.read()
    tree = ast.parse(content)

# Use direct tree traversal to find top-level functions only
top_level_funcs = []
for node in tree.body:
    if isinstance(node, ast.FunctionDef):
        top_level_funcs.append(node)

print("=== Top-level functions ===")
print(f"Total: {len(top_level_funcs)}")

no_doc = [(n.name, n.lineno) for n in top_level_funcs if not ast.get_docstring(n)]
print(f"\nWithout docstring: {len(no_doc)}")
for name, line in no_doc:
    print(f"  line {line}: {name}")

# Check HTML for duplicates and no-desc
with open('effect_utils_browser.html', 'r', encoding='utf-8') as f:
    html = f.read()

cards = re.findall(r'data-name="([^"]+)"', html)
dup_cards = {k: v for k, v in Counter(cards).items() if v > 1}
print(f"\n=== HTML issues ===")
print(f"Duplicate cards in HTML: {len(dup_cards)}")
for name, count in sorted(dup_cards.items(), key=lambda x: -x[1]):
    print(f"  {name}: {count} times")

no_desc = html.count('无描述')
print(f"Total '无描述' occurrences: {no_desc}")

# Compare: top-level funcs vs HTML cards
html_names = set(cards)
top_names = {n.name for n in top_level_funcs}
print(f"\nTop-level funcs: {len(top_names)}")
print(f"HTML cards: {len(html_names)}")
print(f"Missing from HTML: {sorted(top_names - html_names)}")
print(f"Extra in HTML: {sorted(html_names - top_names)}")
