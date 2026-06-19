"""按卡包生成卡牌信息 PDF（A4 表格）。

运行：
    cd TARDS(demo)
    python ..\tools\generate_card_pdfs.py
"""

from __future__ import annotations

import os
from collections import defaultdict
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

# 自动注册所有卡包
import card_pools.blood
import card_pools.discrete
import card_pools.general
import card_pools.miracle
import card_pools.underworld
from tards.data.card_db import DEFAULT_REGISTRY, Pack


FONT_PATH = Path("C:/Windows/Fonts/simhei.ttf")
OUTPUT_DIR = Path("C:/Users/34773/Desktop/tards开发库")


def _fmt_stats(card):
    if card.attack is not None and card.health is not None:
        return f"{card.attack}/{card.health}"
    return "-"


def _fmt_cost(card):
    return str(card.cost) if card.cost else "-"


def build_pack_pdf(pack: Pack, cards, output_path: Path):
    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        rightMargin=15 * mm,
        leftMargin=15 * mm,
        topMargin=15 * mm,
        bottomMargin=15 * mm,
    )
    styles = getSampleStyleSheet()
    normal = styles["Normal"]
    normal.fontName = "Chinese"
    normal.fontSize = 9
    normal.leading = 12

    title_style = styles["Title"]
    title_style.fontName = "Chinese"
    title_style.fontSize = 16

    story = [Paragraph(f"{pack.value}卡包", title_style), Spacer(1, 8 * mm)]

    data = [["名称", "费用", "类型", "攻防", "稀有度", "沉浸度", "描述"]]
    for card in cards:
        desc = (card.description or "").replace("\n", "<br/>")
        data.append([
            Paragraph(str(card.name), normal),
            Paragraph(_fmt_cost(card), normal),
            Paragraph(str(card.card_type.value), normal),
            Paragraph(_fmt_stats(card), normal),
            Paragraph(str(card.rarity.name if card.rarity else "-"), normal),
            Paragraph(str(card.immersion_level), normal),
            Paragraph(desc, normal),
        ])

    col_widths = [28 * mm, 22 * mm, 20 * mm, 18 * mm, 20 * mm, 18 * mm, 67 * mm]
    table = Table(data, colWidths=col_widths, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e2e8f0")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("FONTNAME", (0, 0), (-1, -1), "Chinese"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(table)
    doc.build(story)


def main():
    if not FONT_PATH.exists():
        raise FileNotFoundError(f"找不到中文字体：{FONT_PATH}")
    pdfmetrics.registerFont(TTFont("Chinese", str(FONT_PATH)))

    grouped = defaultdict(list)
    for card in DEFAULT_REGISTRY.all_cards():
        grouped[card.pack].append(card)

    for pack in Pack:
        cards = grouped.get(pack, [])
        if not cards:
            continue
        cards.sort(key=lambda c: (c.immersion_level, str(c.cost), c.name))
        output_path = OUTPUT_DIR / f"{pack.value}卡包.pdf"
        build_pack_pdf(pack, cards, output_path)
        print(f"已生成：{output_path}")


if __name__ == "__main__":
    main()
