"""程序生成美术验收测试。

运行后弹出窗口展示：
    - 顶部：4 张程序生成卡牌（200×280）
    - 中部：对应缩略图（64×64）
    - 左下：5×5 棋盘底图
    - 右下：关键词图标

按 ESC 或等待 3 秒自动退出，截图保存到 _test_procedural_screenshot.png。
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pygame

# 先导入所有卡包池，触发卡牌注册到 DEFAULT_REGISTRY
import card_pools

from tards.data.card_db import DEFAULT_REGISTRY
from pygame_client.procedural_cards import render_card_surface, render_thumbnail
from pygame_client.procedural_board import render_board_background, render_keyword_icon
from pygame_client.fonts import get_font_manager


def main():
    pygame.init()
    screen = pygame.display.set_mode((1280, 720))
    pygame.display.set_caption("Procedural Art Test")
    clock = pygame.time.Clock()
    fm = get_font_manager()

    # 获取测试卡牌
    test_names = ["僵尸猪人", "林鼠", "火药", "铁锭"]
    test_cards = []
    for name in test_names:
        cd = DEFAULT_REGISTRY.get(name)
        if cd:
            test_cards.append(cd)
        else:
            print(f"[警告] 注册表中未找到卡牌: {name}")

    # 预生成 Surface
    card_surfs = [render_card_surface(c, 200, 280) for c in test_cards]
    thumb_surfs = [render_thumbnail(c, 64) for c in test_cards]
    board_surf = render_board_background(80, 5, 5)
    kw_icons = [render_keyword_icon(k, 24) for k in
                ["冰冻", "亡语", "恐惧", "迅捷", "成长", "视野", "高频", "丰饶"]]

    # 3 秒后自动退出
    pygame.time.set_timer(pygame.USEREVENT, 3000)

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                running = False
            if event.type == pygame.USEREVENT:
                running = False

        screen.fill((15, 23, 42))

        # 卡牌（顶部）
        x = 20
        for s in card_surfs:
            screen.blit(s, (x, 20))
            x += 210

        # 缩略图（中部）
        x = 20
        for s in thumb_surfs:
            screen.blit(s, (x, 320))
            x += 74

        # 棋盘（左下）
        screen.blit(board_surf, (20, 420))

        # 关键词图标（右下）
        x = 460
        y = 420
        for icon in kw_icons:
            screen.blit(icon, (x, y))
            x += 30
            if x > 1200:
                x = 460
                y += 30

        # 标签
        lbl = fm.render_text("卡牌(上) / 缩略图(中) / 棋盘(下左) / 关键词(下右)", 16, (200, 200, 200))
        screen.blit(lbl, (20, 690))

        pygame.display.flip()
        clock.tick(60)

    pygame.image.save(screen, "pygame_client/_test_procedural_screenshot.png")
    pygame.quit()
    print("验证通过：截图已保存 pygame_client/_test_procedural_screenshot.png")
    sys.exit()


if __name__ == "__main__":
    main()
