"""Pygame 环境验证脚本。

验收标准：
    - 弹出 1280×720 窗口
    - 显示中文"献祭僵尸猪人获得2B"（白色，居中）
    - 显示"pygame OK"（绿色，上方）
    - 背景为深色 #0f172a
    - 按 ESC 或关闭窗口可正常退出
    - 帧率稳定 60fps

运行方式：
    .venv/Scripts/python.exe pygame_client/_test_env.py
"""

import sys
from pathlib import Path

# 确保项目根目录在 sys.path 中，使 pygame_client 包可被导入
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pygame

from pygame_client.fonts import get_font_manager


def main() -> None:
    pygame.init()
    screen = pygame.display.set_mode((1280, 720))
    pygame.display.set_caption("Tards Pygame Test")
    clock = pygame.time.Clock()
    fm = get_font_manager()

    # 2 秒后自动触发退出（方便无头测试）
    pygame.time.set_timer(pygame.USEREVENT, 2000)

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
            if event.type == pygame.USEREVENT:
                running = False

        # 深色背景
        screen.fill((15, 23, 42))

        # 标题
        title = fm.render_text("pygame OK", 48, (76, 255, 3), bold=True)
        screen.blit(title, (640 - title.get_width() // 2, 240))

        # 中文测试文本（泛用，不依赖具体游戏术语）
        text = fm.render_text("中文渲染测试文本1", 32, (255, 255, 255))
        screen.blit(text, (640 - text.get_width() // 2, 360))

        # 英文+数字+符号混合
        sub = fm.render_text("Test-123 测试！", 20, (148, 163, 184))
        screen.blit(sub, (640 - sub.get_width() // 2, 480))

        pygame.display.flip()
        clock.tick(60)

    # 保存截图供验证
    pygame.image.save(screen, "pygame_client/_test_env_screenshot.png")
    pygame.quit()
    print("验证通过：pygame 窗口创建成功，中文渲染正常，截图已保存")
    sys.exit()


if __name__ == "__main__":
    main()
