# Tards 开发交接文档

> 生成时间：2026-06-19  
> 交接对象：接手 bug 排查与体验优化的下一位 agent  
> 当前工作中心：**bug 排查与体验优化**

---

## 1. 项目基本信息

- **项目路径**：`C:\Users\34773\Desktop\tards开发库\TARDS(demo)`
- **Python**：3.14.3（虚拟环境 `.venv`）
- **GUI**：Tkinter
- **打包**：PyInstaller 6.21.0，`TARDS(demo)\Tards.spec` → `dist\Tards\Tards.exe`
- **测试入口**：`tests/run.py`
- **当前测试状态**：91/91 通过（截至上次运行）

---

## 2. 用户协作偏好（必须遵守）

项目已添加 skill `.agents/skills/early-report-ask-often/`，优先级高于默认 AGENTS.md：

1. **先汇报，再测试**：完成任务后不要立刻跑完整测试，尽早向用户汇报状态，等指示后再决定是否测试。
2. **鼓励频繁提问**：对任何不确定、模糊的地方主动使用 `AskUserQuestion` 提问，禁止猜测。
3. **严禁猜测意图**：只能基于用户明确文字行动，不脑补需求。

---

## 3. 近期已完成工作

### 3.1 通用卡包拆分

- 拆分 `card_pools/general.py` 为：
  - `card_pools/general.py`：仅保留 `register_card` 注册表。
  - `card_pools/general_effects.py`：所有效果函数库。
- 同步更新 `card_pools/__init__.py`、`Tards.spec` 的 `hiddenimports`。

### 3.2 奇迹卡包与汞雾

- 新增 `card_pools/miracle.py` 与 `card_pools/miracle_effects.py`。
- 新增银卡 **汞雾**：4T 2/2 协同，沉浸度 1。
  - 抽取：双方各失去 2 HP。
  - 部署：将距离本异象最近的异象的回响加入手牌。
- 复用已有的 `Pack.MIRACLE` 枚举。

### 3.3 卡组构筑器 UI 尝试（已回退）

- 尝试为卡池按钮按稀有度添加右侧斜边条带，因渲染异常已回退。
- 当前按钮保持原样式。

### 3.4 结算阶段节奏优化

- 在 `tards/game.py` 新增 `resolve_column_delay` 属性（默认 0，不影响测试）。
- 在 `gui/battle/battle_frame.py` 设置 `self.duel.resolve_column_delay = 1.0`。
- 效果：本地对战结算阶段每列（水路→河岸→中路→山脊→高地）结算完后停顿约 1 秒。

### 3.5 联机安全与体验修复

- 修复 `tards/net_protocol.py` 中 `deserialize_action` 与 `_deserialize_target` 的字段类型校验，防止缺字段/错类型导致连接线程崩溃。
- 修复 `tards/net_game.py` 中 HELLO / START / Discover / Choice / Mulligan 等远端消息的字段校验。
- 修复联机游戏结束时误报“连接断开”：
  - 游戏结束后先发送 `GAMEOVER` 再触发 UI。
  - 正常结束关闭连接时不再发送 `DISCONNECT`。
  - `battle_frame` 在游戏结束时同时标记 `_disconnect_handled`，避免覆盖“对战结束”提示。

### 3.6 卡牌信息 PDF

- 新增 `tools/generate_card_pdfs.py`，可按卡包生成 PDF 文档。
- 已生成：`通用卡包.pdf`、`奇迹卡包.pdf`、`离散卡包.pdf`、`冥刻卡包.pdf`、`血祭卡包.pdf`（在项目根目录）。

### 3.7 抽取效果检查

- 新增 `tests/check_draw_triggers.py`，验证所有带“抽取”关键词的卡牌（汞雾、高炉、奇怪的蛹、食蚁兽、水漫缮写室、纠缠血流、血痂、雪降）。
- 当前全部正常。

---

## 4. 关键文件状态

| 文件 | 说明 |
|------|------|
| `card_pools/general.py` | 通用卡注册表 |
| `card_pools/general_effects.py` | 通用卡效果函数库 |
| `card_pools/miracle.py` | 奇迹卡注册表（仅汞雾） |
| `card_pools/miracle_effects.py` | 奇迹卡效果函数库 |
| `tards/game.py` | 结算阶段、自然 T 槽上限、resolve_column_delay |
| `tards/player.py` | `_natural_t_max_cap_modifier`、鲜血费用逻辑 |
| `tards/cards.py` | 鲜血费用处理（`_blood_paid_from_b_point`） |
| `tards/net_game.py` | 联机握手、消息校验、游戏结束通知 |
| `tards/net_protocol.py` | Action / Target 序列化与反序列化、字段校验 |
| `gui/battle/battle_frame.py` | 主战斗界面、联机回调、游戏结束/断开处理 |
| `gui/battle/input_controller.py` | 手牌点击、献祭/部署流程 |
| `gui/dialogs.py` | 弹窗（已居中） |
| `Tards.spec` | PyInstaller 配置，已加入 general_effects / miracle 等 hiddenimports |

---

## 5. 已知问题与下一步重点

当前工作中心已明确为 **bug 排查与体验优化**。建议优先方向：

1. **联机稳定性**：继续在实际双机对战中观察是否还有断连、卡顿、状态不同步。
2. **结算阶段体验**：`resolve_column_delay = 1.0` 是否符合预期，是否需要按列/按攻击细分。
3. **UI 体验**：卡组构筑器、战斗界面交互、弹窗体验。
4. **卡牌效果回归**：新增卡（汞雾）与抽取卡在实际对局中的边界情况。
5. **代码健康度**：继续减少硬编码、完善测试覆盖。

---

## 6. 常用命令

```bash
# 运行测试
cd "C:\Users\34773\Desktop\tards开发库"
set PYTHONPATH=TARDS(demo)
python -m tests.run

# 检查抽取效果
cd TARDS(demo)
python -m tests.check_draw_triggers

# 打包 exe（先结束 Tards.exe 进程）
cd TARDS(demo)
..\.venv\Scripts\pyinstaller.exe Tards.spec -y
```

---

## 7. 临时/可清理文件

以下文件是运行脚本时生成的临时输出，可视情况删除：

- `TARDS(demo)/draw_cards.txt`
- `tests/draw_trigger_check.txt`
- `tests/full_regression.txt`

---

## 8. 延伸阅读

- `docs/AGENTS.md`
- `docs/ARCHITECTURE.md`
- `docs/TARDS_GAME_REFERENCE.md`
- `docs/COMPLEX_CARDS_INDEX.md`
- `.agents/skills/tards-dev/SKILL.md`（Tards 开发专用 skill）
