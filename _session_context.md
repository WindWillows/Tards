# Tards 卡牌游戏开发 —— 新对话启动上下文

## 一、项目概览

- **项目名称**：Tards TCG（集换式卡牌游戏）
- **技术栈**：Python 3.14 + Tkinter（严禁 Pygame）+ TCP JSON 网络协议
- **根目录**：`C:\Users\34773\Desktop\tards开发库`
- **虚拟环境**：`.venv\Scripts/python.exe`
- **已知环境坑**：Windows PowerShell GBK 编码导致 CLI 乱码；建议写临时 `.py` 文件再执行

## 二、当前工作状态（截至 2026-05-11）

### 2.1 本轮已完成（本次对话）

**Bug 修复**
- **兑换松鼠 0T  bug**：`card_db.py` `to_game_card()` 中 `Cost` 对象未 `copy()`，导致所有从同一 `CardDefinition` 创建的卡牌共享同一个 `Cost` 实例。林鼠效果将某张松鼠的 cost.t 设为 0 时，连带污染了松鼠牌堆中所有待兑换的松鼠。修复：所有卡牌类型的 `cost=` / `exchange_cost=` 传参改为 `self.cost.copy()`。
- **漂浮物部署被拒**：`_default_minion_effect` 中 `board.get_minion_at(target) is not None` 的硬检查没有排除"友方漂浮物上允许叠放"和"藤蔓覆盖友方异象"两种情况。修复：在该检查中增加漂浮物和藤蔓的例外分支。
- **充能铁轨异放不触发**：`to_game_card()` 从未将 `keywords` 中的 `"异放"/"回响"` 值同步到 `card.echo_level`。策略卡打出后 `player.py` 检查 `card.echo_level > 0`，因此异放 2 实际为 0，不会触发。修复：在 `to_game_card()` 四个分支末尾统一初始化 `echo_level`。
- **终局结算卡死**：`resolve_phase` 的 `for col` + `while True` 战斗循环在攻击触发 `game_over = True` 后，因同组其他异象的 `attacker_swings` 未被消耗，导致 `active` 始终非空、`while True` 死循环。修复：在 `for col` 和 `while True` 循环开头各加 `if self.game_over: break`。

**SKILL.md 更新**
- `.agents/skills/tards-dev/SKILL.md` 补充内部指向系统（Internal Targeting）新模式说明与代码模板。

**GitHub 同步**
- 全部修改已推送到 `WindWillows/Tards.git` `master` 分支
- 最新 commit：待本次推送后更新

### 2.2 各卡包状态

| 卡包 | 总数 | 策略卡 | 随从卡 | 状态 |
|------|------|--------|--------|------|
| **离散** | 182 | ~40张已实现 | ~140张已实现 | **指向系统重构完成**，剩余少量复杂卡 |
| **冥刻** | 163 | **51/51 全部完成** | 10张有效果，102张白板/关键词 | 策略卡完成，随从卡大量待实现 |
| **血契** | 70 | 少量 | 少量 | 大量待实现 |

### 2.3 近期架构变更（必须知晓）

**指向系统重构（2026-05-10）**
- **旧模式**：`targets_fn` 预注册合法目标 + `extra_targeting_stages` 多阶段指向
- **新模式**：`targets_fn=target_none` + `effect_fn`/`special_fn` 内部通过 `game.targeting_system.request_target()` 发起指向请求
- **回滚保证**：`effect_fn`/`special_fn` 返回 `False` 时，`play_card()` 自动退还费用、卡牌回手；`special_fn` 返回 `False` 时，`_default_minion_effect` 自动移除已部署异象
- **网络兼容**：内部指向仍走 `game.targeting_provider` → `NetworkDuel._make_targeting_provider()` → TCP `TARGETING` 消息，无需修改网络代码
- **GUI 自动提交**：`targets_fn=target_none` → `valid=[None]` → GUI 自动提交不进入指向模式，实际指向由 `effect_fn` 内部触发

**阴谋触发事件**
- `game.py` 阴谋 effect_fn 执行后 emit `EVENT_CONSPIRACY_TRIGGERED`

**献祭流程（2026-04-19 重构）**
- `game.py` 永久预加血到 `active.b_point`，`cards.py` 只负责消灭牺牲，`Cost.pay()` 统一扣血
- `card_can_play()` 返回 `tuple[bool, str]`，调用时务必取 `[0]` 或解包

**防抖锁模式**
- GUI 输入（出牌/拍铃/拉闸）统一使用 500ms 状态锁防重复提交

---

## 三、核心工作模式（必须严格遵守）

### 3.1 实现新卡牌标准流程
1. 分析效果 → 确定触发时机
2. 检查 `effect_utils.py` 是否已有可用 API
3. 若无可用 API，先扩展工具库，再写卡牌效果
4. 编写 `special_fn`（异象）或 `strategy_fn`（策略）
5. 加上 `@special` 或 `@strategy` 装饰器
6. 在 `card_pools/xxx_effects.py` 中注册到 `SPECIAL_MAP` / `STRATEGY_MAP`
7. 在 `card_pools/xxx.py` 中通过 `register_card()` 注册卡牌

### 3.2 关键规则
- **禁止望文生义**：所有游戏术语有精确定义，不确定时查规则书/代码/问用户
- **禁止自作主张**：不应用其他 TCG 知识推断机制
- **禁止硬编码**：Card effects 必须放在 `effect_fn`/`special_fn` 中，不得在游戏核心循环中检查卡牌名
- **优先更新工具库**：复杂功能先查 `effect_utils.py`，不足时扩展工具库而非写 ad-hoc 代码
- **向后兼容**：原函数注释保留不删除

---

## 四、关键文件速查

| 文件 | 职责 |
|------|------|
| `card_pools/discrete.py` | 离散卡包 182 张定义 |
| `card_pools/discrete_effects.py` | 离散卡包效果实现 + `STRATEGY_MAP` |
| `card_pools/underworld.py` | 冥刻卡包 163 张定义 |
| `card_pools/underworld_effects.py` | 冥刻卡包效果实现 + `SPECIAL_MAP` + `STRATEGY_MAP` |
| `card_pools/effect_utils.py` | 标准效果工具库（**优先使用**） |
| `tards/player.py` | `Player` 类；`exchange_mineral` 已修复上限检查 |
| `tards/game.py` | `Game` 主引擎；阴谋触发事件；**终局结算死循环已修复** |
| `tards/cards.py` | 卡牌基类 + `_default_minion_effect`（已支持 special_fn 回滚；**漂浮物/藤蔓部署已修复**） |
| `tards/card_db.py` | 卡牌定义 + `to_game_card()`（**Cost.copy() + echo_level 初始化已修复**） |
| `tards/targeting.py` | `TargetingSystem`（同步阻塞指向请求） |
| `tards/constants.py` | 事件常量；新增 `EVENT_CONSPIRACY_TRIGGERED` |
| `gui_client.py` | GUI；已添加搜索框 + 出牌/拍铃/拉闸防抖锁 |
| `AGENTS.md` | Agent 工作规则 |
| `TARDS_GAME_REFERENCE.md` | 完整项目参考文档 |

---

## 五、常见陷阱

1. **`from .xxx_effects import *`** 只会导入 `__all__` 中的名字。新函数必须加入 `__all__` 和对应 `MAP`。
2. **Pylance 报错「未定义」**：`import *` 导致静态分析失效，不影响运行时。
3. **PowerShell 编码**：CLI 脚本输出中文会乱码，建议写临时 `.py` 文件再执行。
4. **`StrReplaceFile` 慎用 `replace_all`**：确认不会误改其他同名变量。
5. **新事件常量**：若新增事件类型，务必同步添加到使用处的 `import` 列表。
6. **内部指向取消 = 返回 False**：`effect_fn`/`special_fn` 内部指向被取消时，必须 `return False` 以触发自动回滚。返回 `None` 或其他值不会回滚。
7. **`special_fn` 签名**：检查 `_default_minion_effect` 中的 `inspect.signature` 逻辑，确保参数数量匹配。若定义 `special_fn(minion, player, game, extras)` 但实际调用时 extras 未传入，会静默失败。
8. **`Cost` 对象必须 copy**：`to_game_card()` 或任何创建卡牌副本时，若原卡持有 `Cost` 实例，务必调用 `.copy()`，防止共享可变对象导致副作用（如林鼠 0T 松鼠污染牌堆）。

---

## 六、启动任务建议

**当前最优先任务**：冥刻卡包随从卡（102张白板/仅靠关键词，需判断是否都需要自定义效果）或血契卡包实现。

**注意**：用户在 2026-05-10 表示离散卡包指向系统重构完成，下一段对话的任务需与用户确认。

---

*生成时间：2026-05-11*
