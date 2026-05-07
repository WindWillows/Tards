#!/usr/bin/env python3
"""生成 Tards 架构文档 PDF（含关系图）。修复中文字体问题。"""

import os
import sys
import re

# ------------------------------------------------------------------
# 1. 绘制模块关系图（matplotlib）
# ------------------------------------------------------------------
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch

# 设置中文字体
plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei", "Arial Unicode MS"]
plt.rcParams["axes.unicode_minus"] = False

def draw_architecture_diagram(output_path: str):
    fig, ax = plt.subplots(1, 1, figsize=(16, 20))
    ax.set_xlim(0, 16)
    ax.set_ylim(0, 20)
    ax.axis("off")

    colors = {
        "presentation": "#E8F5E9",
        "presentation_border": "#4CAF50",
        "pools": "#FFF3E0",
        "pools_border": "#FF9800",
        "engine": "#E3F2FD",
        "engine_border": "#2196F3",
        "utils": "#F3E5F5",
        "utils_border": "#9C27B0",
        "db": "#ECEFF1",
        "db_border": "#607D8B",
    }

    def box(x, y, w, h, text, color, border_color, fontsize=9, bold=False):
        weight = "bold" if bold else "normal"
        rect = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.15",
                               facecolor=color, edgecolor=border_color, linewidth=2)
        ax.add_patch(rect)
        ax.text(x + w/2, y + h/2, text, ha="center", va="center",
                fontsize=fontsize, weight=weight, wrap=True)

    def arrow(x1, y1, x2, y2, color="#555"):
        ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                    arrowprops=dict(arrowstyle="->", color=color, lw=1.5))

    # 标题
    ax.text(8, 19.5, "Tards TCG 引擎架构图", ha="center", va="center",
            fontsize=24, weight="bold", color="#1a1a1a")
    ax.text(8, 19.0, "模块分层与核心依赖关系", ha="center", va="center",
            fontsize=14, color="#555")

    # 表现层
    ax.text(1.2, 18.2, "表现层", fontsize=13, weight="bold", color=colors["presentation_border"])
    box(1, 17.0, 4.5, 1.0, "gui_client.py\nTkinter GUI / 联机大厅 / 卡组构筑", colors["presentation"], colors["presentation_border"])
    box(5.8, 17.0, 4.5, 1.0, "demo.py / demo_deckbuild.py\n命令行演示 / 卡组验证", colors["presentation"], colors["presentation_border"])

    # 卡包定义层
    ax.text(1.2, 16.2, "卡包定义层", fontsize=13, weight="bold", color=colors["pools_border"])
    box(1, 14.7, 3.0, 1.2, "discrete.py\n离散卡包\n182 张", colors["pools"], colors["pools_border"])
    box(4.2, 14.7, 3.0, 1.2, "underworld.py\n冥刻卡包\n164 张", colors["pools"], colors["pools_border"])
    box(7.4, 14.7, 3.0, 1.2, "blood.py\n血契卡包\n70 张", colors["pools"], colors["pools_border"])
    box(10.6, 14.7, 4.0, 1.2, "*_effects.py\n效果函数", colors["pools"], colors["pools_border"])

    arrow(2.5, 14.7, 2.5, 13.7)
    arrow(5.7, 14.7, 5.7, 13.7)
    arrow(8.9, 14.7, 8.9, 13.7)

    # 卡牌数据库
    ax.text(1.2, 13.7, "卡牌数据库", fontsize=13, weight="bold", color=colors["db_border"])
    box(1, 12.5, 13.6, 1.0, "card_db.py — CardDefinition + CardRegistry + DEFAULT_REGISTRY\nto_game_card() 生成对战实例", colors["db"], colors["db_border"])

    # 游戏引擎层
    ax.text(1.2, 12.0, "游戏引擎层", fontsize=13, weight="bold", color=colors["engine_border"])

    box(1, 10.8, 3.5, 1.0, "game.py\nGame 主控\n主循环 / 阶段推进", colors["engine"], colors["engine_border"], bold=True)
    box(4.8, 10.8, 3.5, 1.0, "effect_queue.py\nEffectQueue\n堆栈 + 队列", colors["engine"], colors["engine_border"])
    box(8.6, 10.8, 3.5, 1.0, "events.py\nEventBus\n事件总线", colors["engine"], colors["engine_border"])
    box(12.4, 10.8, 2.2, 1.0, "game_history.py\nGameHistory\n机器日志", colors["engine"], colors["engine_border"])

    box(1, 9.5, 3.5, 1.0, "player.py\nPlayer\n资源 / 手牌 / 出牌", colors["engine"], colors["engine_border"])
    box(4.8, 9.5, 3.5, 1.0, "board.py\nBoard\n5x5 棋盘 / 覆盖物", colors["engine"], colors["engine_border"])
    box(8.6, 9.5, 3.5, 1.0, "cards.py\nCard / Minion\n四层修饰系统", colors["engine"], colors["engine_border"])
    box(12.4, 9.5, 2.2, 1.0, "deck.py\nDeck\n构筑 / 验证", colors["engine"], colors["engine_border"])

    box(1, 8.2, 3.0, 1.0, "cost.py\nCost\n费用支付", colors["engine"], colors["engine_border"])
    box(4.3, 8.2, 3.0, 1.0, "targeting.py\nTargetingRequest\n指向系统", colors["engine"], colors["engine_border"])
    box(7.6, 8.2, 3.0, 1.0, "targets.py\n22+ 过滤器\n标准指向库", colors["engine"], colors["engine_border"])
    box(10.9, 8.2, 3.7, 1.0, "game_logger.py\nBattleLogWriter\n对战日志", colors["engine"], colors["engine_border"])

    arrow(2.75, 10.8, 2.75, 10.5, color="#2196F3")
    arrow(2.75, 9.5, 2.75, 9.2, color="#2196F3")
    arrow(6.55, 10.8, 6.55, 10.5, color="#2196F3")
    arrow(6.55, 9.5, 6.55, 9.2, color="#2196F3")
    arrow(10.35, 10.8, 10.35, 10.5, color="#2196F3")
    arrow(10.35, 9.5, 10.35, 9.2, color="#2196F3")

    # 工具库层
    ax.text(1.2, 7.6, "工具库层", fontsize=13, weight="bold", color=colors["utils_border"])
    box(1, 6.0, 13.6, 1.4,
        "effect_utils.py — 效果工具库（~2950 行，35 个分区）\n"
        "伤害 / 治疗 / 移动 / Buff / 手牌操作 / 事件监听 / AOE / 延迟效果 / 机器日志查询 / 选择封装",
        colors["utils"], colors["utils_border"], fontsize=10)
    box(1, 5.0, 6.0, 0.8, "effect_decorator.py\n@special / @strategy 装饰器", colors["utils"], colors["utils_border"])
    box(7.2, 5.0, 7.4, 0.8, "auto_effects.py\n自动效果兼容层", colors["utils"], colors["utils_border"])

    arrow(4.5, 8.2, 4.5, 7.4, color="#9C27B0")
    arrow(8.0, 8.2, 8.0, 7.4, color="#9C27B0")

    # 核心数据流
    ax.text(1.2, 4.4, "核心数据流", fontsize=13, weight="bold", color="#333")

    flow_y = 3.8
    flow_items = [
        "1. Player.play_card() -> Cost.pay() -> EffectQueue.resolve()",
        "2. MinionCard.effect() -> Board.place_minion() -> emit_event(DEPLOYED)",
        "3. resolve_phase() -> Minion.attack_target() -> take_damage() -> minion_death()",
        "4. emit_event() -> EventBus.emit() -> 卡牌监听器触发 -> 回调入 EffectQueue",
        "5. GameHistory.on_event() 自动记录所有关键事件到 TurnRecord",
    ]
    for i, item in enumerate(flow_items):
        ax.text(1.2, flow_y - i*0.45, item, fontsize=9.5, color="#333",
                bbox=dict(boxstyle="round,pad=0.3", facecolor="#FAFAFA", edgecolor="#DDD"))

    # 图例
    ax.text(1.2, 0.8, "图例", fontsize=11, weight="bold")
    legend_items = [
        ("表现层", colors["presentation"], colors["presentation_border"]),
        ("卡包定义层", colors["pools"], colors["pools_border"]),
        ("游戏引擎层", colors["engine"], colors["engine_border"]),
        ("工具库层", colors["utils"], colors["utils_border"]),
        ("数据库", colors["db"], colors["db_border"]),
    ]
    for i, (label, fc, ec) in enumerate(legend_items):
        x = 1.2 + i * 2.8
        rect = mpatches.Rectangle((x, 0.3), 0.5, 0.3, facecolor=fc, edgecolor=ec, linewidth=2)
        ax.add_patch(rect)
        ax.text(x + 0.7, 0.45, label, fontsize=9, va="center")

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close()
    print(f"关系图已保存: {output_path}")


# ------------------------------------------------------------------
# 2. 注册中文字体（reportlab）
# ------------------------------------------------------------------
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, PageBreak, Image,
    Table, TableStyle, Preformatted, ListItem, ListFlowable
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

def register_cjk_font():
    """尝试注册系统中可用的中文字体。返回字体名称。"""
    candidates = [
        ("SimHei", "C:/Windows/Fonts/simhei.ttf"),
        ("SimSun", "C:/Windows/Fonts/simsun.ttc"),
        ("MSYaHei", "C:/Windows/Fonts/msyh.ttc"),
    ]
    for name, path in candidates:
        if os.path.exists(path):
            try:
                # .ttc 需要指定 subfontIndex
                if path.endswith(".ttc"):
                    pdfmetrics.registerFont(TTFont(name, path, subfontIndex=0))
                    # 同时注册粗体（如果可用）
                    try:
                        pdfmetrics.registerFont(TTFont(name+"Bold", path, subfontIndex=1))
                    except Exception:
                        pass
                else:
                    pdfmetrics.registerFont(TTFont(name, path))
                print(f"注册字体成功: {name} ({path})")
                return name
            except Exception as e:
                print(f"注册字体失败 {name}: {e}")
                continue
    print("警告: 未找到中文字体，PDF 中文将显示为方块")
    return "Helvetica"


def make_pdf(md_path: str, diagram_path: str, output_path: str):
    cjk_font = register_cjk_font()
    doc = SimpleDocTemplate(output_path, pagesize=A4,
                            rightMargin=2*cm, leftMargin=2*cm,
                            topMargin=2*cm, bottomMargin=2*cm)

    styles = getSampleStyleSheet()

    # 自定义样式，全部使用 CJK 字体
    title_style = ParagraphStyle(
        "CustomTitle", parent=styles["Title"],
        fontName=cjk_font, fontSize=22, spaceAfter=20, leading=28,
        textColor=colors.HexColor("#1a1a1a")
    )
    h1_style = ParagraphStyle(
        "CustomH1", parent=styles["Heading1"],
        fontName=cjk_font, fontSize=16, spaceAfter=12, spaceBefore=16, leading=22,
        textColor=colors.HexColor("#1565C0"), borderColor=colors.HexColor("#1565C0"),
        borderWidth=2, borderPadding=5, leftIndent=0, backColor=colors.HexColor("#E3F2FD")
    )
    h2_style = ParagraphStyle(
        "CustomH2", parent=styles["Heading2"],
        fontName=cjk_font, fontSize=13, spaceAfter=8, spaceBefore=12, leading=18,
        textColor=colors.HexColor("#2196F3")
    )
    h3_style = ParagraphStyle(
        "CustomH3", parent=styles["Heading3"],
        fontName=cjk_font, fontSize=11, spaceAfter=6, spaceBefore=8, leading=15,
        textColor=colors.HexColor("#555")
    )
    body_style = ParagraphStyle(
        "CustomBody", parent=styles["BodyText"],
        fontName=cjk_font, fontSize=9.5, leading=14, spaceAfter=6,
        textColor=colors.HexColor("#333")
    )
    code_style = ParagraphStyle(
        "CustomCode", parent=styles["Code"],
        fontName=cjk_font, fontSize=8, leading=11, spaceAfter=6,
        leftIndent=10, rightIndent=10,
        backColor=colors.HexColor("#F5F5F5"), textColor=colors.HexColor("#333")
    )
    bullet_style = ParagraphStyle(
        "CustomBullet", parent=body_style,
        leftIndent=20, bulletIndent=10, spaceAfter=4
    )
    # 表格单元格样式
    table_header_style = ParagraphStyle(
        "TableHeader", parent=body_style,
        fontName=cjk_font, fontSize=9, textColor=colors.HexColor("#1565C0"),
        alignment=1  # center
    )
    table_cell_style = ParagraphStyle(
        "TableCell", parent=body_style,
        fontName=cjk_font, fontSize=8, leading=12
    )

    story = []

    # 封面
    story.append(Spacer(1, 4*cm))
    story.append(Paragraph("Tards TCG 游戏引擎架构文档", title_style))
    story.append(Spacer(1, 0.5*cm))
    story.append(Paragraph("模块分层、核心类关系与数据流", body_style))
    story.append(Spacer(1, 0.3*cm))
    story.append(Paragraph("生成日期: 2026-05-06", body_style))
    story.append(PageBreak())

    # 关系图页
    story.append(Paragraph("一、模块架构总图", h1_style))
    story.append(Spacer(1, 0.3*cm))
    if os.path.exists(diagram_path):
        img = Image(diagram_path, width=16*cm, height=20*cm)
        story.append(img)
    story.append(PageBreak())

    # 解析 Markdown
    with open(md_path, "r", encoding="utf-8") as f:
        md_text = f.read()

    lines = md_text.splitlines()
    in_code = False
    code_buffer = []
    in_table = False
    table_buffer = []
    in_bullet = False
    bullet_buffer = []

    def flush_code():
        nonlocal code_buffer
        if code_buffer:
            text = "\n".join(code_buffer)
            story.append(Preformatted(text, code_style))
            story.append(Spacer(1, 0.2*cm))
            code_buffer = []

    def flush_table():
        nonlocal table_buffer
        if len(table_buffer) >= 2:
            data = []
            for row in table_buffer:
                cells = [c.strip() for c in row.split("|")]
                cells = [c for c in cells if c]
                data.append(cells)
            if data:
                max_cols = max(len(r) for r in data)
                for r in data:
                    while len(r) < max_cols:
                        r.append("")
                # 用 Paragraph 包裹单元格文本以支持中文
                para_data = []
                for row_idx, row in enumerate(data):
                    para_row = []
                    for col in row:
                        style = table_header_style if row_idx == 0 else table_cell_style
                        para_row.append(Paragraph(escape_html(col), style))
                    para_data.append(para_row)

                col_width = doc.width / max_cols
                t = Table(para_data, colWidths=[col_width] * max_cols)
                t.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E3F2FD")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#1565C0")),
                    ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
                    ("BACKGROUND", (0, 1), (-1, -1), colors.whitesmoke),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 4),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ]))
                story.append(t)
                story.append(Spacer(1, 0.3*cm))
        table_buffer = []

    def flush_bullet():
        nonlocal bullet_buffer
        if bullet_buffer:
            items = [ListItem(Paragraph(b, bullet_style)) for b in bullet_buffer]
            story.append(ListFlowable(items, bulletType="bullet", leftIndent=20))
            story.append(Spacer(1, 0.2*cm))
            bullet_buffer = []

    def escape_html(text: str) -> str:
        text = text.replace("&", "&amp;")
        text = text.replace("<", "&lt;")
        text = text.replace(">", "&gt;")
        text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
        text = re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"<i>\1</i>", text)
        text = re.sub(r"`(.+?)`", r"<font face='{}' size='8'>\1</font>".format(cjk_font), text)
        return text

    for line in lines:
        stripped = line.strip()

        if stripped.startswith("```"):
            if in_code:
                flush_code()
                in_code = False
            else:
                flush_table()
                flush_bullet()
                in_code = True
            continue

        if in_code:
            code_buffer.append(line)
            continue

        if stripped.startswith("|"):
            flush_bullet()
            if not in_table:
                in_table = True
            table_buffer.append(stripped)
            continue
        else:
            if in_table:
                flush_table()
                in_table = False

        if not stripped:
            flush_bullet()
            continue

        if stripped.startswith("# ") and not stripped.startswith("## "):
            flush_bullet()
            story.append(Paragraph(escape_html(stripped[2:]), h1_style))
            continue
        if stripped.startswith("## ") and not stripped.startswith("### "):
            flush_bullet()
            story.append(Paragraph(escape_html(stripped[3:]), h2_style))
            continue
        if stripped.startswith("### "):
            flush_bullet()
            story.append(Paragraph(escape_html(stripped[4:]), h3_style))
            continue

        if stripped.startswith(("- ", "* ")):
            text = escape_html(stripped[2:])
            bullet_buffer.append(text)
            continue

        flush_bullet()
        story.append(Paragraph(escape_html(stripped), body_style))

    flush_code()
    flush_table()
    flush_bullet()

    doc.build(story)
    print(f"PDF 已生成: {output_path}")


if __name__ == "__main__":
    md_file = "ARCHITECTURE.md"
    diagram_file = "architecture_diagram.png"
    pdf_file = "Tards_Architecture.pdf"

    if not os.path.exists(md_file):
        print(f"错误: 找不到 {md_file}")
        sys.exit(1)

    draw_architecture_diagram(diagram_file)
    make_pdf(md_file, diagram_file, pdf_file)
    print("全部完成！")
