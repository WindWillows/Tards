# Tards 卡牌游戏开发 —— 新对话启动上下文

## 一、项目概览

- **项目名称**：Tards TCG（集换式卡牌游戏）
- **技术栈**：Python 3.14 + Tkinter（严禁 Pygame）+ TCP JSON 网络协议
- **根目录**：`C:\Users\34773\Desktop\tards开发库`
- **虚拟环境**：`.venv\Scripts/python.exe`
- **已知环境坑**：Windows PowerShell GBK 编码导致 CLI 乱码；建议写临时 `.py` 文件再执行

## 二、当前工作状态（截至 2026-05-13）

### 2.1 本轮已完成（本次对话）

**Bug 修复**
- **21张 target_none 卡牌修复**：离散4张 + 血契4张 + 冥刻13张，改为内部 `TargetingRequest`
- **书架侦测器 bug**：修复 `deploy_hooks` 与 `special` 执行顺序（先 special 后 deploy_hooks）
- **火矢 property 报错**：`t.attack += 4` → `t.gain_attack(4, permanent=True)`
- **松鼠消失 bug**：移除 5 张卡错误绑定的 `_youniao_special`（松鼠/松鼠罐/黑山羊/多足座首/多足底座）
- **阴谋非指向 bug**：`_on_hand_card_click` 中 Conspiracy 分支漏了 `valid == [None]` 判断，冥刻11张阴谋全部修复
- **阴谋触发修复**：
  - 怪石：监听 `EVENT_BELL` → 新增常量 `EVENT_BRAKE`
  - 入河：`effect_fn` 未设置 `frame.cancelled=True` 且未保存 `_ruhe_pending` 信息
  - 墨水：`effect_fn` 为空，补充取消策略+洗入对方卡组
- **献祭回滚 B 点泄漏**（关键修复）：
  - 根因：`game.py` 在 `try...finally` 中设置 `sacrifice_chooser`，但 `play_card()` 将 `deploy_fn` 推入 EffectQueue 即返回，`finally` 在异步 effect 执行前已恢复 `sacrifice_chooser` 为 `None`
  - 结果：`effect()` 中 `request_sacrifice` 返回 `None` → 部署回滚；`game.py` 预加的 `temp_b` 未同步扣除 → B 点永久泄漏
  - 修复：`game.py` 不再设置 `sacrifice_chooser`，改为暂存 `card._preselected_sacrifices`；`cards.py` `_default_minion_effect` 优先读取该属性；失败时 `game.py` 回滚 `temp_b`

**功能实现**
- **离散1级沉浸度重构**：`card_hand_max+1` → `extra_hand_max=2`（附加手牌槽体系）
- **冥刻1级松鼠牌堆 toggle**：抽牌阶段替代抽牌，UI复选框控制，抽后自动关闭
- **附加手牌槽 UI/消耗双修复**：
  - Tkinter pack 顺序修复
  - `can_afford_detail` / `pay` 识别 `extra_hand`
  - 消耗后自动 `_compact_extra_hand()`
- **快捷键扩展**：`1`~`0` 覆盖 10 张手牌；动态 `hand_zones` 设计，未来扩展只需追加条目
- **卡组编辑器 UI 重构**：减小卡牌列表宽度，右侧新增统计面板（类型分布/卡包分布/平均费用）
- **UI布局迁移**：费用信息从玩家信息栏移至右侧（附加手牌槽旁），玩家信息区增大预留沉浸度/光环位置

### 2.2 各卡包状态

| 卡包 | 总数 | 异象卡 | 策略卡 | 状态 |
|------|------|--------|--------|------|
| **离散** | 183 | 92/92 | 87/87 | **全部完成** |
| **冥刻** | 163 | 93/101 | 51/51 | 异象卡剩余8张（保卫者、巫毒娃娃、天籁人偶、Bishop、溴化银、亡灵、硫氰化钾、竹心） |
| **血契** | 70 | 30/30 | 40/40 | **全部完成** |
| **合计** | **416** | **215** | **178** | — |

### 2.3 近期架构变更（必须知晓）

**献祭流程（2026-05-13 修复）**
- `game.py` 预加血到 `active.b_point`，通过 `card._preselected_sacrifices` 传递献祭目标
- `cards.py` `_default_minion_effect` 优先读取 `_preselected_sacrifices`，无则回退到 `request_sacrifice()`
- 部署失败（`card_can_play` 失败 / `play_card` 失败）时，`game.py` 回滚 `temp_b`

**双区手牌 serial 映射**
- `1..len(card_hand)` 为普通手牌，后续为附加手牌
- `_get_hand_card(serial)` 统一解析；所有硬编码 `card_hand[serial-1]` 已替换

**阴谋执行模型**
- 通配符监听所有事件 → `condition_fn` 判断 → 满足条件后移出活跃区并注销监听
- 根据是否在堆栈解析中选择 `push_stack`（反制型）或 `queue`（普通型）
- 反制型阴谋（入河、墨水）必须在 `effect_fn` 中设置 `event_data["frame"].cancelled = True`

**指向系统**
- 旧模式 `extra_targeting_stages` 与新模式 `TargetingRequest` 并存
- 新模式：`targets_fn=target_none` + `effect_fn`/`special_fn` 内部通过 `game.targeting_system.request_target()` 发起指向
- 回滚保证：`effect_fn`/`special_fn` 返回 `False` 时自动退还费用、卡牌回手

**费用系统**
- `card_can_play()` 返回 `tuple[bool, str]`，调用时务必取 `[0]` 或解包
- `Cost.pay()` 已适配 `extra_hand` 矿物消耗；消耗后自动 `_compact_extra_hand()`

**EventBus 性能（已知问题）**
- `*` 通配符监听器（如三氟化氯）每次事件都执行，高频事件下性能开销显著
- 待优化：事件分类缓存、条件过滤提前化、或按需订阅模式

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
| `card_pools/discrete.py` | 离散卡包 183 张定义 |
| `card_pools/discrete_effects.py` | 离散卡包效果实现 |
| `card_pools/underworld.py` | 冥刻卡包 163 张定义 |
| `card_pools/underworld_effects.py` | 冥刻卡包效果实现 |
| `card_pools/blood.py` | 血契卡包 70 张定义 |
| `card_pools/blood_effects.py` | 血契卡包效果实现 |
| `card_pools/effect_utils.py` | 标准效果工具库（**优先使用**） |
| `tards/player.py` | `Player` 类；双区手牌 + 松鼠牌堆 + 献祭选择器 |
| `tards/game.py` | `Game` 主引擎；献祭预加/回滚；阴谋触发；action_phase |
| `tards/cards.py` | 卡牌基类 + `_default_minion_effect`；**献祭预选目标优先读取** |
| `tards/cost.py` | 费用系统；已适配 extra_hand 矿物消耗 |
| `tards/targeting.py` | `TargetingSystem`（同步阻塞指向请求） |
| `tards/constants.py` | 事件常量；新增 `EVENT_BRAKE` |
| `gui_client.py` | GUI；动态 hand_zones + 右侧费用面板 + 卡组编辑器统计 |
| `AGENTS.md` | Agent 工作规则 |
| `TARDS_GAME_REFERENCE.md` | 完整项目参考文档 |

---

## 五、常见陷阱

1. **`from .xxx_effects import *`** 只会导入 `__all__` 中的名字。新函数必须加入 `__all__` 和对应 `MAP`。
2. **PowerShell 编码**：CLI 脚本输出中文会乱码，建议写临时 `.py` 文件再执行。
3. **`StrReplaceFile` 慎用 `replace_all`**：确认不会误改其他同名变量。
4. **新事件常量**：若新增事件类型，务必同步添加到使用处的 `import` 列表。
5. **内部指向取消 = 返回 False**：`effect_fn`/`special_fn` 内部指向被取消时，必须 `return False` 以触发自动回滚。
6. **`Cost` 对象必须 copy**：`to_game_card()` 或任何创建卡牌副本时，若原卡持有 `Cost` 实例，务必调用 `.copy()`。
7. **献祭目标传递**：`game.py` 不再设置 `sacrifice_chooser`，改用 `card._preselected_sacrifices` 传递预选目标。
8. **Deploy 顺序**：异象自身 `special`（注册监听/初始化）必须在 `deploy_hooks`（其他卡反应）之前执行。

---

## 六、启动任务建议

**当前最优先任务**：
1. 冥刻剩余 8 张异象卡（保卫者、巫毒娃娃、天籁人偶、Bishop、溴化银、亡灵、硫氰化钾、竹心）—— 已有 `special_fn` 函数定义，但未在 `underworld.py` 的 `register_card` 中链接
2. EventBus `*` 通配符性能优化
3. 监听器生命周期管理（弹回/移除时自动清理）

**注意**：下一段对话的具体任务需与用户确认。

---

*生成时间：2026-05-13*
