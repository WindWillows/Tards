# Tards 卡牌对战游戏（Demo）

一个基于 Python + tkinter 的本地/联机卡牌对战游戏 Demo。

> 本项目使用 AI 辅助编码完成。核心机制、卡牌设计、规则定义由开发者主导，AI 作为实现工具。

---

## 目录说明

```
.
├── TARDS(demo)/          # 游戏主程序（入口、引擎、GUI、卡包池）
│   ├── Gamestart.py      # 启动入口
│   ├── tards/            # 游戏引擎
│   │   ├── cards/        # 卡牌类型
│   │   ├── core/         # 核心运行时（棋盘、玩家、费用、指向等）
│   │   ├── data/         # 卡牌数据、卡组构筑与 IO
│   │   ├── game/         # Game 控制器 mixins
│   │   └── net/          # 网络对战协议与控制器
│   ├── card_pools/       # 卡包池与卡牌效果
│   ├── gui/              # tkinter 界面
│   ├── assets/           # 字体、图标等美术资源
│   └── decks/            # 预置卡组 JSON
├── tests/                # 回归测试
├── docs/                 # 规则书、架构文档、Agent 说明
├── tools/                # 生成 PDF、翻译卡包等工具脚本
├── pygame_client/        # 实验性 Pygame 客户端（未接入主程序）
├── agent_team/           # AI 开发辅助工具（非游戏本体）
├── config/               # AI 开发配置（非游戏本体）
└── releases/             # 发行 zip（本地备份，正式 Release 见 GitHub Releases）
```

---

## 环境准备

要求 Python 3.10+（推荐 3.14）。

```bash
# 安装依赖
pip install -r TARDS(demo)/requirements.txt

# 或使用 pyproject.toml
pip install -e .
```

---

## 运行游戏

```bash
cd TARDS(demo)
python Gamestart.py
```

---

## 运行测试

```bash
python tests/run.py              # 全部 92 个测试
python tests/run.py xuejian      # 按名称过滤
```

---

## 打包成 exe

```bash
cd TARDS(demo)
pyinstaller --noconfirm Tards.spec
```

打包结果在 `TARDS(demo)/dist/Tards/`。清理后的发行 zip 放在仓库根目录 `releases/`。

---

## 字体授权

项目使用 [Noto Sans SC](https://fonts.google.com/noto/fonts?noto.query=Noto+Sans+SC)（SIL Open Font License 1.1）作为界面字体。

---

## 主要文档

- `docs/ARCHITECTURE.md` — 架构说明
- `docs/TARDS_GAME_REFERENCE.md` — 游戏规则与机制参考
- `docs/AGENTS.md` — 给 AI 维护者的开发约定
