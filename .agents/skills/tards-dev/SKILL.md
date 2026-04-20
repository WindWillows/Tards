---
name: tards-dev
description: |
  Tards 卡牌游戏项目开发专用 skill。用于实现新卡牌、修复卡牌效果、
  理解游戏规则、以及避免硬编码坏习惯。当用户要求：
  (1) 实现/修复某张卡牌的效果，
  (2) 解释某个游戏机制或关键词，
  (3) 修改核心游戏引擎逻辑，
  (4) 调试效果未触发或行为异常，
  (5) 扩展效果工具库时，
  触发本 skill。
---

# Tards 项目开发指南

## 核心原则

1. **不要望文生义**：游戏术语（视野、潜水、移动等）有精确定义，不以日常语义理解。
2. **不要自作主张**：Tards 规则与常规 TCG（炉石/万智/YGO）完全不同，禁止用其他游戏知识推断。
3. **禁止硬编码**：核心引擎（game.py/player.py/board.py/cards.py）中绝不允许出现卡牌名字或特殊分支。
4. **优先扩展工具库**：复杂效果先在 `effect_utils.py` 中实现通用 API，再在卡牌中调用。

## 实现新卡牌的标准流程

```
1. 分析效果 → 确定触发时机（部署/回合开始/回合结束/受伤/亡语/策略打出）
2. 检查 effect_utils.py 是否已有可用 API
3. 若无可用 API，先扩展工具库，再写卡牌效果
4. 编写 special_fn（单位）或 strategy_fn（策略）
5. 加上 @special 或 @strategy 装饰器
6. 在 card_pools/xxx_effects.py 中注册到 SPECIAL_MAP / STRATEGY_MAP
7. 在 card_pools/xxx.py 中通过 register_card() 注册卡牌（或修改现有定义）
8. 运行 python demo.py 测试
```

## 指向系统速查

- 所有指向操作统一走 `TargetingRequest` + `process_targeting_request()`。
- 策略卡主目标由 `targets_fn` 返回合法列表。
- 多阶段指向通过 `extra_targeting_stages=[(stage_fn, count, allow_repeat)]` 实现。
- 手牌目标：使用 `target_hand_minions`，GUI 会自动弹出手牌选择。

## 参考文件导航

| 文件 | 内容 | 何时读取 |
|------|------|----------|
| [rules-core.md](references/rules-core.md) | 胜利条件、棋盘、回合流程、费用、关键词定义 | 需要理解规则或关键词时 |
| [hardcoding-guide.md](references/hardcoding-guide.md) | 硬编码禁令、常见违规案例、正确改造方案 | 实现效果或修改引擎时 |
| [effect-patterns.md](references/effect-patterns.md) | **标准函数签名 + 21个可复制模板 + 完整 API 速查表**（含伤害控制、部署计数、目标记忆、地形覆盖、攻击限制、伤害来源追踪等） | **编写 special_fn / strategy_fn 时（必读）** |
