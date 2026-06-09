# Tards GUI 迁移计划：Tkinter → Pygame

## 项目现状

- **Gamestart.py**: 3400 行，14 类，167 方法。`BattleFrame` 独占 ~2200 行。
- **assets/**: 10 个子目录全部为空。416 张注册卡牌，0 个 `asset_id`。
- **tards/**: 引擎零 Tkinter 耦合，通过 `threading.Event` + callback provider 与 GUI 通信。
- **pygame**: 未安装。
- **当前架构**: Tkinter 主线程 + 游戏守护线程。全局 `gui_refresh_event` 每 200ms 轮询，destructive redraw。

---

## 核心策略

**渐进式迁移，双引擎并行，Battle 优先。**

1. 保留 `Gamestart.py`（Tkinter）完整可用，作为 fallback 和卡组构筑工具。
2. 新建 `pygame_client/` 目录，独立开发 pygame 客户端。
3. 先用 **程序生成视觉**（pygame 自绘卡牌模板、费用球、类型图标）解决 `assets/` 为空的问题，不阻塞框架开发。
4. 美术资源后续可逐步替换，无需改代码。
5. 卡组构筑（`DeckBuilderFrame`）因控件复杂（滚动列表、筛选器、拖拽排序），放到最后；前期可用 Tkinter 版建卡组，pygame 版只负责打牌。

---

## 版本回退点（Git Tag 规划）

| Tag | 阶段 | 验收标准 |
|-----|------|---------|
| `pygame-v0.1-infra` | 基础设施 | `AssetManager` 输出 pygame Surface；`SceneManager` 能切场景；MenuScene 可显示 |
| `pygame-v0.2-render` | Battle 纯渲染 | 能启动本地对战并在 pygame 窗口中实时渲染棋盘、手牌、信息面板（仅观战，无交互） |
| `pygame-v0.3-playable` | Battle 可玩 | 能用鼠标完成完整对局：出牌、指向、攻击预设、拍铃、拉闸、兑换 |
| `pygame-v0.4-modal` | 弹窗系统 | 抉择、献祭、发现等模态弹窗在 pygame 内完成，不再调用 Tkinter |
| `pygame-v0.5-client` | 完整客户端 | Menu + Lobby + 本地/联机对战全部在 pygame 内运行 |
| `pygame-v0.6-full` | 全量替换（可选） | DeckBuilderScene 完成，可彻底移除 Tkinter 依赖 |

每个 tag 打完后，若后续开发遇到无法解决的阻塞，可立即回退到该 tag 重新分支。

---

## Phase 0：基础设施与美术资源准备

> **目标**：让 pygame 能跑起来，能加载和渲染所有现有资源（即使资源为空也要有 fallback）。
> **预计工期**：4-5 天

### P0.1 安装 pygame 并验证环境
- **前置**：无
- **施工区域**：`.venv/`（虚拟环境）
- **内容**：
  - `pip install pygame>=2.5`
  - 写最小验证脚本 `pygame_client/_test_env.py`：创建窗口、绘制矩形、加载字体、退出
  - 验证 Windows 高 DPI 支持（`ctypes.windll.user32.SetProcessDPIAware()` 或 pygame 2.5 原生支持）
- **难度**：★☆☆☆☆
- **验收**：运行脚本后弹出 1280×720 窗口，显示"pygame OK"中文，无乱码，按 ESC 退出

### P0.2 AssetManager Pygame 适配层
- **前置**：P0.1
- **施工区域**：`tards/assets.py`（改造）+ 新建 `pygame_client/asset_adapter.py`
- **内容**：
  - `assets.py` 中把 `ImageTk.PhotoImage` 输出改为可配置：保留 Tkinter 路径，新增 `to_pygame_surface()` 方法
  - 缓存字典改为 `Dict[Tuple[str, Tuple[int, int]], pygame.Surface]`（或同时存 Tk 和 pygame 两种格式）
  - `AssetManager.get_card_face()` 等 API 增加 `backend="tk"|"pygame"` 参数，默认保持 `"tk"` 兼容旧代码
  - 新建 `pygame_client/asset_adapter.py`：封装 `load_image(path) -> pygame.Surface`、带异常回退（文件缺失时返回纯色占位 Surface）
- **难度**：★★☆☆☆
- **验收**：Tkinter 版 `Gamestart.py` 仍能正常启动；pygame 侧能调用 `am.get_card_face(id, w, h, backend="pygame")` 返回 Surface

### P0.3 程序生成卡牌视觉系统（Procedural Card Renderer）
- **前置**：P0.2
- **施工区域**：`pygame_client/procedural_cards.py`（新建）
- **内容**：
  - 由于 `assets/cards/faces/` 为空，所有卡牌面必须程序生成
  - 设计卡牌模板：
    - 背景色按卡包区分（离散=蓝、冥刻=紫、血契=红、通用=灰）
    - 顶部左侧：费用球（T=黄色圆、B=红色圆、C=蓝色圆、S=紫色圆，多费用时横向排列）
    - 中央：卡名（大号粗体）+ 类型图标（异象/策略/阴谋/矿物）
    - 底部：异象显示 攻击/生命 盾牌框；策略/阴谋显示类型文字标签
    - 边框：金色细线（稀有度影响亮度，普通=银、稀有=金）
  - 生成函数 `render_card_surface(card_def, width, height) -> pygame.Surface`
  - 缩略图 `render_thumbnail(card_def, size) -> pygame.Surface`
  - 缓存机制：按 `(card_name, width, height)` 缓存 Surface，避免每帧重绘
- **难度**：★★★☆☆
- **验收**：生成一张 200×280 的卡牌 Surface，保存为 PNG 能肉眼看出是"卡牌"（有边框、费用球、文字）

### P0.4 字体与国际化基础
- **前置**：P0.1
- **施工区域**：`pygame_client/fonts.py`（新建）+ `assets/fonts/`（新建目录，放字体文件）
- **内容**：
  - 下载并放置 `NotoSansSC-Regular.otf` 和 `NotoSansSC-Bold.otf`（或思源黑体）到 `assets/fonts/`
  - 建立 `FontManager`：按字号缓存 `pygame.font.Font` 实例
  - 提供 `render_text(text, size, color, bold=False) -> pygame.Surface`
  - 处理缺失字体回退：若找不到 Noto Sans，回退到系统 `simhei.ttf` 或 `msgothic.ttc`
- **难度**：★★☆☆☆
- **验收**：pygame 窗口中能正确渲染"献祭 僵尸猪人 获得2B"等中英文混合文本，无乱码

### P0.5 棋盘格子与 UI 装饰程序生成
- **前置**：P0.2, P0.4
- **施工区域**：`pygame_client/procedural_board.py`（新建）
- **内容**：
  - `assets/board/tiles/` 为空，需程序生成 5 列地形底图：
    - 高地（土黄岩石质感）、山脊（灰色峭壁）、中路（草地）、河岸（沙地）、水路（深蓝水面）
    - 用 pygame 绘制基础色块 + 噪点纹理（随机小圆点模拟质感）+ 地形名称水印
  - 生成 5×5 棋盘底图 `render_board_background(cell_size) -> pygame.Surface`
  - 生成关键词图标：`render_keyword_icon(keyword, size) -> pygame.Surface`（冰冻=雪花、亡语=骷髅、恐惧=鬼脸等）
- **难度**：★★★☆☆
- **验收**：棋盘底图看起来有 5 种不同地形，不是纯色块；关键词图标 16×16 可辨识

---

## Phase 1：SceneManager + MenuScene + 游戏线程桥接

> **目标**：建立 pygame 主循环和场景栈，能把游戏线程跑起来并在后台推进，pygame 前台实时显示状态。
> **预计工期**：3-4 天
> **版本回退点**：`pygame-v0.1-infra`

### P1.1 SceneManager 与主循环架构
- **前置**：P0.1
- **施工区域**：`pygame_client/core.py`（新建）
- **内容**：
  - `Scene` 基类：`handle_event(event)`, `update(dt)`, `draw(screen)`
  - `SceneManager`：`push(scene)`, `pop()`, `switch(name)`, `current`
  - `GameApp` 类：封装 `pygame.display.set_mode`、主循环、`clock.tick(60)`、delta time 计算
  - 主循环伪代码结构：
    ```
    while running:
        dt = clock.tick(60) / 1000.0
        for event in pygame.event.get(): scene.handle_event(event)
        scene.update(dt)
        screen.fill(bg)
        scene.draw(screen)
        pygame.display.flip()
    ```
- **难度**：★★☆☆☆
- **验收**：能切换 MenuScene ↔ 空白 TestScene，按 ESC 返回，帧率稳定 60fps

### P1.2 MenuScene（主菜单）
- **前置**：P1.1
- **施工区域**：`pygame_client/scenes/menu.py`（新建）
- **内容**：
  - 暗色背景（#0f172a）+ 标题 "Tards"（大字号居中）
  - 4 个按钮：本地对战、联机对战（Host）、联机对战（Client）、卡组构筑（跳转 Tkinter）
  - 按钮 hover 效果：亮度提升 + 轻微放大
  - 点击"本地对战" → 进入 `BattleScene`
- **难度**：★★☆☆☆
- **验收**：鼠标悬停和点击有视觉反馈；点击本地对战能进入 BattleScene（即使 BattleScene 此时只是黑屏）

### P1.3 游戏线程桥接（非阻塞式）
- **前置**：P1.1
- **施工区域**：`pygame_client/duel_bridge.py`（新建）
- **内容**：
  - 封装 `LocalDuel` 的启动和通信：
    - `DuelBridge` 类持有 `LocalDuel` 实例和游戏线程
    - 维护 `action_queue: queue.Queue`（GUI → 游戏线程）
    - 维护 `state_queue: queue.Queue`（游戏线程 → GUI）
  - 替换 `gui_refresh_event`：游戏线程不再设置全局 Event，而是把精简状态快照推入 `state_queue`
  - 关键：保持 `choice_provider` / `targeting_provider` / `discover_provider` 等注入逻辑不变，只是把阻塞方式从 `threading.Event` 改为从 `action_queue` 取数据
  - `BattleScene.update(dt)` 每帧检查 `state_queue`，有新状态就更新内部镜像
- **难度**：★★★☆☆
- **验收**：能在 pygame 主循环中启动一局本地对战，游戏线程正常推进（打印日志到控制台），pygame 侧每帧收到状态更新

### P1.4 状态镜像与序列化
- **前置**：P1.3
- **施工区域**：`pygame_client/state_mirror.py`（新建）
- **内容**：
  - 定义 `BattleState` dataclass：包含双方玩家资源、棋盘异象列表、手牌列表、阶段、回合数等
  - 编写 `snapshot_from_game(game: Game) -> BattleState`，从 `tards/` 引擎对象中提取只读数据
  - 避免在 pygame 线程中直接访问引擎可变对象（防止竞态）
  - 状态更新频率：游戏线程在关键节点（阶段切换、出牌后、结算后）推送快照，非每帧推送
- **难度**：★★★☆☆
- **验收**：pygame 侧 `BattleState` 能准确反映当前回合、T点、手牌数量、棋盘异象位置

---

## Phase 2：BattleScene 纯渲染（观战模式）

> **目标**：能在 pygame 窗口中完整渲染一局对战的所有视觉元素，但不处理用户输入（仅观战）。
> **预计工期**：6-8 天
> **版本回退点**：`pygame-v0.2-render`

### P2.1 棋盘渲染系统
- **前置**：P0.5, P1.4
- **施工区域**：`pygame_client/scenes/battle.py` + `pygame_client/renderers/board_renderer.py`
- **内容**：
  - 棋盘位置计算：根据窗口大小动态计算 `cell_size` 和 `board_offset`
  - 绘制 5×5 格子底图（使用 P0.5 的程序生成地形）
  - 绘制行列标签（高地/山脊/中路/河岸/水路 + 0-4 行号）
  - 绘制部署预览高亮（合法格子黄色半透明 overlay）
  - 绘制指向模式高亮（合法目标脉冲边框）
- **难度**：★★★☆☆
- **验收**：窗口 resize 时棋盘自适应居中；5 列地形肉眼可区分

### P2.2 异象渲染系统
- **前置**：P2.1
- **施工区域**：`pygame_client/renderers/minion_renderer.py`
- **内容**：
  - 每个异象是一个 `MinionSprite` 类（非 pygame Sprite，只是命名），包含 `rect` 和渲染方法
  - 分层绘制：
    1. 阴影层（半透明黑椭圆）
    2. 底图（蓝/红圆角矩形，按 owner 区分）
    3. 立绘/缩略图（P0.3 生成的缩略图，或纯色块+首字）
    4. 边框（状态色：冰冻=青、眩晕=橙、恐惧=紫、成长=绿）
    5. 名称（顶部居中，小字号）
    6. 攻击/生命（左下/右下，颜色按 buff/debuff 变化）
    7. 关键词图标（左下角，最多 3 个，P0.5 生成）
    8. 行动指示器（绿色圆点：可攻击但未设目标）
    9. 攻击预设星号（黄色 ★）
    10. 清除预设按钮（小红叉，固定位置）
  - 漂浮物/藤蔓宿主：金色/紫色粗边框
- **难度**：★★★★☆
- **验收**：棋盘上异象看起来像游戏单位而非色块；鼠标悬停有反应（后续 P2.6 做 tooltip）

### P2.3 攻击连线与特效渲染
- **前置**：P2.2
- **施工区域**：`pygame_client/renderers/effects_renderer.py`
- **内容**：
  - 攻击预设连线：贝塞尔曲线或直线，黄色半透明，带箭头指向目标
  - 指向来源高亮：金色发光边框（多层矩形模拟 glow）
  - 合法目标高亮：黄色脉冲边框（正弦波控制 alpha）
  - 所有特效需在 `update(dt)` 中更新动画参数（如脉冲相位）
- **难度**：★★★☆☆
- **验收**：两个异象之间的攻击连线有箭头；指向模式下来源和目标都有动态高亮

### P2.4 手牌区渲染
- **前置**：P0.3, P1.4
- **施工区域**：`pygame_client/renderers/hand_renderer.py`
- **内容**：
  - 底部横向手牌区：高度固定 160px，宽度自适应
  - 每张手牌是一个 `CardSprite`：使用 P0.3 程序生成卡牌 Surface
  - 选中态：卡牌 y 坐标上移 20px，阴影放大，其他手牌暗化 60%
  - 可打出态：绿色外发光（程序生成 glow 效果）
  - 堆叠数：红色圆角矩形 + 白字（右上角）
  - 阴谋激活标记：绿色圆 + "激" 字
  - 手牌过多时横向压缩（卡牌间距减小）或启用横向拖拽滚动
- **难度**：★★★☆☆
- **验收**：10 张手牌能完整显示；选中、可打出、不可打出三种状态视觉区分明显

### P2.5 信息面板与资源渲染
- **前置**：P0.4, P1.4
- **施工区域**：`pygame_client/renderers/hud_renderer.py`
- **内容**：
  - 双方玩家信息面板（顶部或左右两侧）：
    - 名字 + 回合指示（绿色圆点"●"）
    - HP 条（ProgressBar 自绘：底框 + 填充色 + 数字）
    - 资源图标行：T/C/B/S 用彩色圆球 + 数字（变化时缩放弹跳）
    - 牌组信息：手牌数、牌库数、弃牌数、阴谋数（小图标+数字）
  - 当前玩家资源面板（屏幕右下或左下，大而醒目）
  - 阶段标签："抽牌阶段"/"出牌阶段"/"结算阶段"（中央横幅或顶部条）
  - 回合数显示
- **难度**：★★★☆☆
- **验收**：所有数字与引擎状态一致；资源变化时能看到缩放动画

### P2.6 Tooltip 与详情浮窗
- **前置**：P2.2, P2.4
- **施工区域**：`pygame_client/ui/tooltip.py`
- **内容**：
  - 悬停异象/手牌时，鼠标附近弹出浮窗
  - 浮窗内容：卡名、费用、类型、攻击/生命、关键词、效果描述
  - 浮窗尺寸：固定宽度 240px，高度自适应文本
  - 边界检测：若靠近屏幕边缘，向反方向偏移
  - 背景：深色半透明（#1e293b，alpha=230）+ 细边框
- **难度**：★★☆☆☆
- **验收**：悬停任意异象和手牌，1 秒内弹出 tooltip；移开鼠标 tooltip 消失

### P2.7 对局历史流
- **前置**：P2.5
- **施工区域**：`pygame_client/ui/history_log.py`
- **内容**：
  - 右侧窄条（宽度 200px）显示对局历史
  - 每项用图标+简短文字：【出牌】僵尸猪人 → (2,中路)、【攻击】僵尸猪人 → 林鼠、【兑换】铁锭
  - 自动滚动到最新项
  - 历史数据从 `BattleLogWriter` 或 `state_queue` 中获取
- **难度**：★★☆☆☆
- **验收**：打出一张牌后，历史流在 0.5 秒内出现新条目

---

## Phase 3：BattleScene 完整交互

> **目标**：玩家能用鼠标完成完整对局，不再依赖 Tkinter 的输入系统。
> **预计工期**：5-7 天
> **版本回退点**：`pygame-v0.3-playable`

### P3.1 输入状态机与点击检测
- **前置**：P2.1-P2.4
- **施工区域**：`pygame_client/scenes/battle.py` + `pygame_client/input/`
- **内容**：
  - 为所有可点击元素维护 `pygame.Rect`：棋盘格子、异象、手牌、按钮
  - 状态机：`IDLE` → `CARD_SELECTED` → `DEPLOY_TARGETING` → `EFFECT_TARGETING` → `ATTACK_TARGETING`
  - 每帧检测 `mouse_pos`，hover 时元素高亮
  - 点击手牌 → 进入 `CARD_SELECTED`，计算合法目标范围
  - 点击棋盘格子/异象 → 根据当前状态决定是出牌、设攻击目标还是取消
- **难度**：★★★★☆
- **验收**：状态转换无误；错误点击（如点击非法目标）有视觉反馈（屏幕边缘闪红）

### P3.2 卡牌拖拽出牌
- **前置**：P3.1
- **施工区域**：`pygame_client/scenes/battle.py`
- **内容**：
  - 鼠标按下（在手牌上）→ 开始拖拽：卡牌跟随鼠标，半透明
  - 拖拽到棋盘合法格子上方时，格子高亮
  - 鼠标释放：
    - 在合法格子上 → 提交出牌动作
    - 在非法区域 → 卡牌弹回手牌（缓动动画）
  - 点击（非拖拽）手牌 → 选中态（上移），再点击目标 → 出牌
- **难度**：★★★☆☆
- **验收**：拖拽和点击两种出牌方式都可用；释放到非法区域有弹回动画

### P3.3 攻击目标预设交互
- **前置**：P3.1
- **施工区域**：`pygame_client/scenes/battle.py`
- **内容**：
  - 点击场上己方异象（有视野/高频）→ 进入 `ATTACK_TARGETING`
  - 合法目标高亮（红色边框脉冲）
  - 点击目标 → 添加攻击预设；高频需选多个目标（循环选择直到够数）
  - 已设目标显示连线；点击小红叉清除该异象的全部预设
  - 一键自动填充（A 键）：为所有可攻击异象填充默认目标
- **难度**：★★★☆☆
- **验收**：完整完成一次"林鼠（高频2）选择两个敌方目标"的流程

### P3.4 动作提交与游戏线程通信
- **前置**：P3.1, P1.3
- **施工区域**：`pygame_client/duel_bridge.py`
- **内容**：
  - 把所有 GUI 动作转换为 action dict，通过 `action_queue` 发送给游戏线程：
    - 出牌：`{"type": "play", "serial": N, "target": (r,c), "bluff": False}`
    - 攻击预设：`{"type": "set_attack_targets", "pos": (r,c), "targets": [...]}`
    - 拍铃：`{"type": "bell"}`
    - 拉闸：`{"type": "brake"}`
    - 兑换：`{"type": "exchange", "mineral_type": "I"}`
    - 抽松鼠开关：`{"type": "toggle_squirrel"}`
  - 动作提交后立即本地预测（optional）：先在镜像状态中模拟效果，0.1s 后再等游戏线程确认
- **难度**：★★★☆☆
- **验收**：能用 pygame 完成一整局本地对战（从回合1到游戏结束），无崩溃

### P3.5 按钮与快捷键系统
- **前置**：P3.4
- **施工区域**：`pygame_client/ui/button_bar.py`
- **内容**：
  - 底部/侧边按钮栏：拍铃、拉闸、兑换（弹出 mineral 选择）、兑换松鼠、取消选择、终止游戏
  - 按钮自绘：圆角矩形 + 图标文字 + hover 态
  - 快捷键映射（复刻 Tkinter 版）：
    - `B` = 拉闸, `Space` = 拍铃, `ESC` = 取消, `A` = 自动攻击, `1-0` = 选牌
    - `S/I/G/D/M` = 兑换对应矿物
  - `pygame.KEYDOWN` 事件处理
- **难度**：★★☆☆☆
- **验收**：所有快捷键与 Tkinter 版行为一致；按钮点击有按下/释放视觉反馈

---

## Phase 4：模态弹窗系统

> **目标**：替换全部 6 个 Tkinter Toplevel 对话框，让 pygame 内能处理抉择、献祭、发现、诈唬、数字选择、反馈。
> **预计工期**：4-5 天
> **版本回退点**：`pygame-v0.4-modal`

### P4.1 弹窗管理器框架
- **前置**：P1.1
- **施工区域**：`pygame_client/ui/modal_manager.py`
- **内容**：
  - `ModalManager`：维护栈式弹窗队列，背景遮罩（半透明黑 #000000 alpha=150）
  - 弹窗出现时，底层 Scene 停止接收输入（或只接收 ESC）
  - 弹窗动画：从中心缩放出现（0.8 → 1.0），200ms
  - 关闭动画：反向缩放 + 淡出
- **难度**：★★★☆☆
- **验收**：弹窗出现时背景变暗；按 ESC 可关闭（若允许取消）

### P4.2 抉择弹窗（ChoiceDialog）
- **前置**：P4.1
- **施工区域**：`pygame_client/ui/modals/choice_modal.py`
- **内容**：
  - 标题 + 选项按钮列表（竖排）
  - 每个选项按钮：程序生成的小卡牌预览或纯文字按钮
  - 返回选择的字符串索引
- **难度**：★★☆☆☆
- **验收**：触发"火药：选择 TNT 或 复制技术"时，弹窗正确显示；选择后游戏线程继续

### P4.3 献祭弹窗（SacrificeDialog）
- **前置**：P4.1
- **施工区域**：`pygame_client/ui/modals/sacrifice_modal.py`
- **内容**：
  - 显示场上所有友方异象（缩略图 + 名称 + 丰饶值）
  - 玩家点击选择要献祭的异象（可多选）
  - 实时显示已选献祭总和 B 点 vs 需求 B 点
  - 确认/取消按钮
- **难度**：★★★☆☆
- **验收**：打出需要 2B 的卡时，弹窗正确显示可选异象；选够后确认按钮可用

### P4.4 发现/诈唬/数字选择弹窗
- **前置**：P4.1
- **施工区域**：`pygame_client/ui/modals/`（DiscoverModal, BluffModal, NumericModal）
- **内容**：
  - DiscoverModal：类似 ChoiceModal，但选项是卡牌（横向排列）
  - BluffModal："是否虚张声势？" 二选一
  - NumericModal：输入数字（如"选择 1-3"），用按钮 +/- 或键盘输入
- **难度**：★★☆☆☆
- **验收**：三种弹窗各至少测试一次成功通过

### P4.5 反馈弹窗（FeedbackDialog）
- **前置**：P4.1
- **施工区域**：`pygame_client/ui/modals/feedback_modal.py`
- **内容**：
  - 多行文本输入框（pygame 无原生输入框，需自研或引入 `pygame_gui`）
  - 评分星级（1-5 星，点击选择）
  - 提交/取消按钮
  - **决策点**：自研文本输入框工作量高，可考虑引入 `pygame_gui` 的 `UITextEntryLine` / `UITextBox`
- **难度**：★★★☆☆（若自研）或 ★★☆☆☆（若用 pygame_gui）
- **验收**：能输入中文反馈并提交到本地文件

### P4.6 Provider 桥接改造
- **前置**：P4.2-P4.5
- **施工区域**：`pygame_client/duel_bridge.py`
- **内容**：
  - 把 `LocalDuel` 注入的 `choice_provider`、`targeting_provider`、`discover_provider`、`sacrifice_chooser` 全部桥接到 pygame ModalManager
  - provider 函数不再阻塞 Tkinter，而是：
    1. 向 pygame 主循环发送自定义事件（如 `pygame.event.Event(SHOW_CHOICE_MODAL, ...)`）
    2. 在 ModalManager 中显示弹窗
    3. 玩家选择后，把结果写回 `action_queue`，解除游戏线程阻塞
- **难度**：★★★★☆
- **验收**：完整对局中所有弹窗都在 pygame 内处理，不再弹出 Tkinter 窗口

---

## Phase 5：MenuScene + LobbyScene + 联机对战

> **目标**：完整的客户端，不再依赖 Tkinter 启动器。
> **预计工期**：4-5 天
> **版本回退点**：`pygame-v0.5-client`

### P5.1 MenuScene 完善
- **前置**：P1.2
- **施工区域**：`pygame_client/scenes/menu.py`
- **内容**：
  - 添加背景图（或程序生成星空/魔法背景动画）
  - 增加"退出游戏"、"设置"（分辨率、音量）按钮
  - 设置面板：分辨率下拉（800×600 / 1280×720 / 1920×1080）、全屏开关、音量滑块
  - 版本号显示
- **难度**：★★☆☆☆
- **验收**：能调整分辨率并即时生效；全屏/窗口切换正常

### P5.2 LobbyScene（联机大厅）
- **前置**：P5.1
- **施工区域**：`pygame_client/scenes/lobby.py`
- **内容**：
  - 玩家名字输入框（自研或 pygame_gui）
  - 卡组选择：下拉列表（读取 `decks/*.json`）
  - Host：端口输入 + "创建房间"按钮
  - Client：IP 输入 + 端口输入 + "加入房间"按钮
  - 连接状态显示（连接中/已连接/失败）
  - 双方准备后，进入 BattleScene
- **难度**：★★★☆☆
- **验收**：Host 和 Client 能成功配对并进入对战；NetworkDuel 的回调正确桥接到 pygame

### P5.3 联机对战桥接
- **前置**：P5.2, P4.6
- **施工区域**：`pygame_client/duel_bridge.py`
- **内容**：
  - `NetworkDuel` 的回调接口（`local_turn_callback`、`game_over_callback` 等）桥接到 pygame 事件系统
  - 远端玩家行动时，本机 BattleScene 正确显示动画和状态变化
  - 断线处理：弹窗提示 + 返回 LobbyScene
- **难度**：★★★☆☆
- **验收**：两台电脑（或同一电脑两个进程）能完成一整局联机对战

### P5.4 启动器整合
- **前置**：P5.3
- **施工区域**：根目录 `tards_pygame.py`（新建）+ `启动Tards.bat`
- **内容**：
  - 新建入口文件 `tards_pygame.py`，启动 pygame 客户端
  - 修改 `启动Tards.bat`，提供两个选项：
    - [1] Pygame 客户端（新）
    - [2] Tkinter 客户端（旧，保留 DeckBuilder）
  - 或者保持两个独立入口：`Gamestart.py`（Tkinter）和 `tards_pygame.py`（pygame）
- **难度**：★☆☆☆☆
- **验收**：双击 `tards_pygame.py` 直接启动 pygame 客户端

---

## Phase 6：DeckBuilderScene（可选/最后）

> **目标**：把卡组构筑也迁到 pygame，最终彻底移除 Tkinter 依赖。
> **预计工期**：7-10 天（高不确定性）
> **版本回退点**：`pygame-v0.6-full`

### P6.0 技术选型决策
- **选项 A（推荐）**：引入 `pygame_gui` 库，用它提供的 `UISelectionList`、`UIScrollBar`、`UITextEntryLine`、`UIDropDownMenu` 等控件加速开发
- **选项 B（自研）**：自己实现滚动列表、文本输入、下拉菜单，工作量极大
- **决策建议**：选 A。`pip install pygame-gui`，在 DeckBuilderScene 中混用 pygame_gui 控件和自绘卡牌。

### P6.1 卡牌筛选与列表
- **前置**：P6.0 决策
- **施工区域**：`pygame_client/scenes/deck_builder.py`
- **内容**：
  - 左侧：可滚动卡牌网格（所有已注册卡牌，按卡包分页）
  - 顶部筛选栏：类型筛选（异象/策略/阴谋/矿物）、费用区间、关键词搜索
  - 点击卡牌 → 右侧显示详情 + "加入卡组"按钮
- **难度**：★★★★☆
- **验收**：能浏览全部 416 张卡牌；筛选器能正确过滤

### P6.2 卡组编辑与保存
- **前置**：P6.1
- **施工区域**：`pygame_client/scenes/deck_builder.py`
- **内容**：
  - 右侧：当前卡组列表（可滚动），显示卡牌名×数量、总张数、沉浸度统计
  - 拖拽/点击从卡组移除卡牌
  - 沉浸度滑块（按卡包）
  - 测试卡组 checkbox
  - 保存按钮（调用 `deck_io.save_deck`）
  - 合法性校验（40张、沉浸度上限、卡包限制）实时显示错误提示
- **难度**：★★★★☆
- **验收**：能新建、编辑、保存一套合法卡组；非法时保存按钮禁用并显示原因

### P6.3 移除 Tkinter 依赖（可选）
- **前置**：P6.2
- **施工区域**：全仓库
- **内容**：
  - 确认 `tards/` 无 Tkinter 引用
  - 删除 `Gamestart.py`（或移入 `archive/`）
  - 更新 `AGENTS.md` 和文档中的启动说明
- **难度**：★☆☆☆☆
- **验收**：仓库中无 `tkinter` 导入（除可能的工具脚本外）

---

## 关键风险与应对

| 风险 | 影响 | 应对策略 |
|------|------|---------|
| **pygame 中文输入框自研困难** | P4.5、P5.2、P6 受阻 | 早期引入 `pygame_gui` 作为输入控件后备；或保留 Tkinter 的 DeckBuilder |
| **游戏线程与 pygame 主循环竞态** | 崩溃或画面撕裂 | 严格通过 `state_queue` 单向传递快照；pygame 线程绝不直接修改引擎对象 |
| **416 张卡牌无美术** | 即使框架升级，视觉效果仍像"高级控制台" | P0.3 程序生成卡牌视觉必须做到位；后续可批量替换为真实立绘 |
| **NetworkDuel 回调假设 Tkinter** | 联机功能在 pygame 下异常 | P4.6、P5.3 中把 Tkinter 的 `widget.after(0, lambda)` 替换为 `pygame.event.post` |
| **性能：每帧重建手牌 Surface** | 帧率下降 | P2.4 中必须实现卡牌 Surface 缓存；手牌数量变化时才重建 |

---

## 人员分工建议（若多人协作）

| 角色 | 负责模块 | 技能要求 |
|------|---------|---------|
| **引擎/架构** | P0.2, P1.3, P1.4, P3.4, P4.6, P5.3 | 熟悉 `tards/` 引擎、多线程、队列通信 |
| **渲染/美术** | P0.3, P0.5, P2.1-P2.7, P3.1-P3.3 | pygame 绘图、动画、坐标计算 |
| **UI/交互** | P1.1, P1.2, P3.5, P4.1-P4.5, P5.1, P5.2 | 状态机、事件处理、弹窗管理 |
| **DeckBuilder** | P6.0-P6.2 | pygame_gui（若选A）或复杂自研控件 |

---

## 总工期估算

| 阶段 | 工期 | 累计 |
|------|------|------|
| Phase 0 | 4-5 天 | 5 天 |
| Phase 1 | 3-4 天 | 9 天 |
| Phase 2 | 6-8 天 | 17 天 |
| Phase 3 | 5-7 天 | 24 天 |
| Phase 4 | 4-5 天 | 29 天 |
| Phase 5 | 4-5 天 | 34 天 |
| Phase 6（可选）| 7-10 天 | 44 天 |

**最小可用版本（v0.3-playable）**：约 **3-4 周**（1 人全职）。
**完整客户端（v0.5-client）**：约 **5 周**。
**全量替换（v0.6-full）**：约 **6-7 周**。
