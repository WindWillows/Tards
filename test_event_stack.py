"""
事件堆栈单元测试

覆盖场景：
1. EventBus 基础行为（注册、优先级、取消、通配符、批量注销）
2. 伤害事件链（before_damage 取消/修改、damaged、after_damage）
3. 攻击事件链（before_attack 取消/修改目标、attacked、after_attack）
4. 部署事件（before_deploy 取消）
5. 消灭事件（before_destroy 阻止消灭）
6. 移除事件（before_remove 阻止移除）
7. 资源变化事件（before_c_change 修改）
"""

import unittest
from typing import Any, Dict, List

from tards.events import EventBus, GameEvent
from tards.constants import (
    EVENT_BEFORE_DAMAGE,
    EVENT_DAMAGED,
    EVENT_AFTER_DAMAGE,
    EVENT_BEFORE_ATTACK,
    EVENT_ATTACKED,
    EVENT_AFTER_ATTACK,
    EVENT_BEFORE_DEPLOY,
    EVENT_DEPLOYED,
    EVENT_AFTER_DEPLOY,
    EVENT_BEFORE_DESTROY,
    EVENT_DESTROYED,
    EVENT_AFTER_DESTROY,
    EVENT_BEFORE_REMOVE,
    EVENT_REMOVED,
    EVENT_BEFORE_C_CHANGE,
    EVENT_C_CHANGED,
)
from tards import Game, Player, MinionCard, Strategy, Cost, target_friendly_positions, target_any_minion


# ---------------------------------------------------------------------------
# EventBus 纯单元测试
# ---------------------------------------------------------------------------

class TestEventBus(unittest.TestCase):
    def test_register_and_emit(self):
        """基本注册与发射。"""
        bus = EventBus()
        calls = []
        bus.register("test", lambda e: calls.append(e.data["val"]))
        event = bus.emit("test", val=42)
        self.assertEqual(calls, [42])
        self.assertEqual(event.type, "test")
        self.assertEqual(event.get("val"), 42)

    def test_priority_order(self):
        """priority 越小越先执行。"""
        bus = EventBus()
        order = []
        bus.register("test", lambda e: order.append("b"), priority=10)
        bus.register("test", lambda e: order.append("a"), priority=0)
        bus.register("test", lambda e: order.append("c"), priority=20)
        bus.emit("test")
        self.assertEqual(order, ["a", "b", "c"])

    def test_cancel_before_event(self):
        """before_* 事件设置 cancelled 后，后续监听器不执行。"""
        bus = EventBus()
        order = []
        bus.register("before_test", lambda e: (order.append("first"), setattr(e, "cancelled", True)), priority=0)
        bus.register("before_test", lambda e: order.append("second"), priority=10)
        event = bus.emit("before_test")
        self.assertEqual(order, ["first"])
        self.assertTrue(event.cancelled)

    def test_wildcard_listener(self):
        """'*' 通配符监听器收到所有事件。"""
        bus = EventBus()
        events = []
        bus.register("*", lambda e: events.append(e.type))
        bus.emit("damage", val=1)
        bus.emit("heal", val=2)
        bus.emit("draw", val=3)
        self.assertEqual(events, ["damage", "heal", "draw"])

    def test_wildcard_priority_interleave(self):
        """通配符与专用监听器按 priority 混合排序。"""
        bus = EventBus()
        order = []
        bus.register("test", lambda e: order.append("specific_5"), priority=5)
        bus.register("*", lambda e: order.append("wildcard_3"), priority=3)
        bus.register("test", lambda e: order.append("specific_10"), priority=10)
        bus.emit("test")
        self.assertEqual(order, ["wildcard_3", "specific_5", "specific_10"])

    def test_unregister_by_owner(self):
        """通过 owner_id 批量注销。"""
        bus = EventBus()
        calls = []
        owner = bus.register("test", lambda e: calls.append(1))
        bus.register("test", lambda e: calls.append(2))
        bus.emit("test")
        self.assertEqual(calls, [1, 2])
        bus.unregister_by_owner(owner)
        bus.emit("test")
        self.assertEqual(calls, [1, 2, 2])

    def test_unregister_single(self):
        """注销单个监听器。"""
        bus = EventBus()
        calls = []
        fn = lambda e: calls.append(1)
        bus.register("test", fn)
        bus.emit("test")
        self.assertEqual(calls, [1])
        bus.unregister("test", fn)
        bus.emit("test")
        self.assertEqual(calls, [1])


# ---------------------------------------------------------------------------
# 伤害事件链测试
# ---------------------------------------------------------------------------

class TestDamageEvents(unittest.TestCase):
    def setUp(self):
        """构建一个极简双人对局，用于事件测试。"""
        self.p1 = Player(side=0, name="P1", diver="测试", card_deck=[])
        self.p2 = Player(side=1, name="P2", diver="测试", card_deck=[])
        self.game = Game(self.p1, self.p2)
        self.p1.sacrifice_chooser = lambda req: None
        self.p2.sacrifice_chooser = lambda req: None

    def _make_minion(self, name="测试兵", attack=1, health=3, owner=None, pos=(3, 0)):
        """创建一个 Minion 并部署到指定位置。"""
        if owner is None:
            owner = self.p1
        card = MinionCard(
            name=name,
            owner=owner,
            cost=Cost(t=1),
            targets=target_friendly_positions,
            attack=attack,
            health=health,
        )
        minion = card.effect(owner, pos, self.game)
        # card.effect 返回 bool，需要重新获取 minion
        return self.game.board.get_minion_at(pos)

    def test_cancel_before_damage(self):
        """before_damage 取消后，目标不受伤。"""
        m = self._make_minion("盾兵", health=5, pos=(3, 0))
        self.assertEqual(m.current_health, 5)

        def shield(event):
            if event.get("target") == m:
                event.cancelled = True

        self.game.register_listener(EVENT_BEFORE_DAMAGE, shield)
        m.take_damage(3)
        self.assertEqual(m.current_health, 5, "伤害应被完全阻止")

    def test_modify_before_damage(self):
        """before_damage 中修改 damage，实际伤害应被改变。"""
        m = self._make_minion("脆兵", health=5, pos=(3, 1))

        def weaken(event):
            if event.get("target") == m:
                event.data["damage"] = 1

        self.game.register_listener(EVENT_BEFORE_DAMAGE, weaken)
        m.take_damage(3)
        self.assertEqual(m.current_health, 4, "伤害应从 3 被修改为 1")

    def test_damage_event_chain(self):
        """验证 before_damage → damaged → after_damage 完整链。"""
        m = self._make_minion("链兵", health=5, pos=(3, 2))
        chain = []

        def before(event):
            chain.append(("before", event.get("damage")))

        def damaged(event):
            chain.append(("damaged", event.get("actual")))

        def after(event):
            chain.append(("after", event.get("actual")))

        self.game.register_listener(EVENT_BEFORE_DAMAGE, before)
        self.game.register_listener(EVENT_DAMAGED, damaged)
        self.game.register_listener(EVENT_AFTER_DAMAGE, after)
        m.take_damage(2)
        self.assertEqual(chain, [("before", 2), ("damaged", 2), ("after", 2)])
        self.assertEqual(m.current_health, 3)

    def test_after_damage_cannot_undo(self):
        """after_damage 中修改 damage 不影响已发生的伤害。"""
        m = self._make_minion("实兵", health=5, pos=(3, 3))

        def evil_modify(event):
            event.data["damage"] = 99

        self.game.register_listener(EVENT_AFTER_DAMAGE, evil_modify)
        m.take_damage(2)
        self.assertEqual(m.current_health, 3, "after_damage 不应改变已生效的伤害")


# ---------------------------------------------------------------------------
# 攻击事件链测试
# ---------------------------------------------------------------------------

class TestAttackEvents(unittest.TestCase):
    def setUp(self):
        self.p1 = Player(side=0, name="P1", diver="测试", card_deck=[])
        self.p2 = Player(side=1, name="P2", diver="测试", card_deck=[])
        self.game = Game(self.p1, self.p2)
        self.p1.sacrifice_chooser = lambda req: None
        self.p2.sacrifice_chooser = lambda req: None

    def _make_minion(self, name="兵", attack=2, health=3, owner=None, pos=(3, 0)):
        if owner is None:
            owner = self.p1
        card = MinionCard(
            name=name,
            owner=owner,
            cost=Cost(t=1),
            targets=target_friendly_positions,
            attack=attack,
            health=health,
        )
        card.effect(owner, pos, self.game)
        return self.game.board.get_minion_at(pos)

    def test_cancel_before_attack(self):
        """before_attack 取消后，目标不受伤。"""
        attacker = self._make_minion("攻击者", attack=3, health=3, owner=self.p1, pos=(3, 0))
        defender = self._make_minion("防御者", attack=1, health=5, owner=self.p2, pos=(0, 0))

        def pacifist(event):
            event.cancelled = True

        self.game.register_listener(EVENT_BEFORE_ATTACK, pacifist)
        attacker.attack_target(defender)
        self.assertEqual(defender.current_health, 5, "攻击应被完全阻止")

    def test_modify_attack_target(self):
        """before_attack 中修改 defender，攻击应转向新目标。"""
        attacker = self._make_minion("攻击者", attack=3, health=3, owner=self.p1, pos=(3, 0))
        original = self._make_minion("原目标", attack=1, health=5, owner=self.p2, pos=(0, 0))
        redirect = self._make_minion("替罪羊", attack=1, health=5, owner=self.p2, pos=(0, 1))

        def redirector(event):
            event.data["defender"] = redirect
            event.data["target"] = redirect

        self.game.register_listener(EVENT_BEFORE_ATTACK, redirector)
        attacker.attack_target(original)
        self.assertEqual(original.current_health, 5, "原目标不应受伤")
        self.assertEqual(redirect.current_health, 2, "替罪羊应承受 3 点伤害")

    def test_attack_event_chain(self):
        """验证 before_attack → attacked → after_attack 完整链。"""
        attacker = self._make_minion("攻击者", attack=1, health=3, owner=self.p1, pos=(3, 0))
        defender = self._make_minion("防御者", attack=1, health=5, owner=self.p2, pos=(0, 0))
        chain = []

        def before(event):
            chain.append("before_attack")

        def attacked(event):
            chain.append("attacked")

        def after(event):
            chain.append("after_attack")

        self.game.register_listener(EVENT_BEFORE_ATTACK, before)
        self.game.register_listener(EVENT_ATTACKED, attacked)
        self.game.register_listener(EVENT_AFTER_ATTACK, after)
        attacker.attack_target(defender)
        self.assertEqual(chain, ["before_attack", "attacked", "after_attack"])


# ---------------------------------------------------------------------------
# 部署/销毁/移除事件测试
# ---------------------------------------------------------------------------

class TestLifecycleEvents(unittest.TestCase):
    def setUp(self):
        self.p1 = Player(side=0, name="P1", diver="测试", card_deck=[])
        self.p2 = Player(side=1, name="P2", diver="测试", card_deck=[])
        self.game = Game(self.p1, self.p2)
        self.p1.sacrifice_chooser = lambda req: None
        self.p2.sacrifice_chooser = lambda req: None

    def test_cancel_before_deploy(self):
        """before_deploy 取消后，单位不应出现在场上。"""
        card = MinionCard(
            name="禁兵",
            owner=self.p1,
            cost=Cost(t=1),
            targets=target_friendly_positions,
            attack=1,
            health=1,
        )

        def forbidden(event):
            event.cancelled = True

        self.game.register_listener(EVENT_BEFORE_DEPLOY, forbidden)
        result = card.effect(self.p1, (3, 0), self.game)
        self.assertFalse(result)
        self.assertIsNone(self.game.board.get_minion_at((3, 0)))

    def test_deploy_event_chain(self):
        """验证 before_deploy → deployed → after_deploy 完整链。"""
        card = MinionCard(
            name="哨兵",
            owner=self.p1,
            cost=Cost(t=1),
            targets=target_friendly_positions,
            attack=1,
            health=1,
        )
        chain = []

        def before(event):
            chain.append("before_deploy")

        def deployed(event):
            chain.append("deployed")

        def after(event):
            chain.append("after_deploy")

        self.game.register_listener(EVENT_BEFORE_DEPLOY, before)
        self.game.register_listener(EVENT_DEPLOYED, deployed)
        self.game.register_listener(EVENT_AFTER_DEPLOY, after)
        card.effect(self.p1, (3, 1), self.game)
        self.assertEqual(chain, ["before_deploy", "deployed", "after_deploy"])
        self.assertIsNotNone(self.game.board.get_minion_at((3, 1)))

    def test_cancel_before_destroy(self):
        """before_destroy 取消后，单位恢复 1 HP 并留在场上。"""
        card = MinionCard(
            name="不灭兵",
            owner=self.p1,
            cost=Cost(t=1),
            targets=target_friendly_positions,
            attack=1,
            health=2,
        )
        card.effect(self.p1, (3, 2), self.game)
        m = self.game.board.get_minion_at((3, 2))

        def immortal(event):
            event.cancelled = True

        self.game.register_listener(EVENT_BEFORE_DESTROY, immortal)
        m.take_damage(5)
        self.assertTrue(m.is_alive())
        self.assertEqual(m.current_health, 1, "阻止消灭后应恢复至 1 HP")
        self.assertIsNotNone(self.game.board.get_minion_at((3, 2)))

    def test_destroy_event_chain(self):
        """验证 before_destroy → destroyed → after_destroy 完整链。"""
        card = MinionCard(
            name="殉兵",
            owner=self.p1,
            cost=Cost(t=1),
            targets=target_friendly_positions,
            attack=1,
            health=1,
        )
        card.effect(self.p1, (3, 3), self.game)
        m = self.game.board.get_minion_at((3, 3))
        chain = []

        def before(event):
            chain.append("before_destroy")

        def destroyed(event):
            chain.append("destroyed")

        def after(event):
            chain.append("after_destroy")

        self.game.register_listener(EVENT_BEFORE_DESTROY, before)
        self.game.register_listener(EVENT_DESTROYED, destroyed)
        self.game.register_listener(EVENT_AFTER_DESTROY, after)
        m.take_damage(5)
        self.assertEqual(chain, ["before_destroy", "destroyed", "after_destroy"])
        self.assertIsNone(self.game.board.get_minion_at((3, 3)))

    def test_cancel_before_remove(self):
        """before_remove 取消后，单位仍留在场上。"""
        card = MinionCard(
            name="扎根兵",
            owner=self.p1,
            cost=Cost(t=1),
            targets=target_friendly_positions,
            attack=1,
            health=1,
        )
        card.effect(self.p1, (3, 3), self.game)
        m = self.game.board.get_minion_at((3, 3))

        def rooted(event):
            event.cancelled = True

        self.game.register_listener(EVENT_BEFORE_REMOVE, rooted)
        result = self.game.board.remove_minion((3, 3))
        self.assertIsNone(result, "remove_minion 应返回 None（移除被阻止）")
        self.assertIsNotNone(self.game.board.get_minion_at((3, 3)), "单位应仍留在场上")


# ---------------------------------------------------------------------------
# 资源变化事件测试
# ---------------------------------------------------------------------------

class TestResourceEvents(unittest.TestCase):
    def setUp(self):
        self.p1 = Player(side=0, name="P1", diver="测试", card_deck=[])
        self.p2 = Player(side=1, name="P2", diver="测试", card_deck=[])
        self.game = Game(self.p1, self.p2)

    def test_modify_before_c_change(self):
        """before_c_change 中修改 delta，实际变化应被改变。"""
        self.p1.c_point = 0

        def tax(event):
            event.data["delta"] = 1  # 无论想加多少，只给 1

        self.game.register_listener(EVENT_BEFORE_C_CHANGE, tax)
        self.p1.c_point_change(5)
        self.assertEqual(self.p1.c_point, 1, "C 点变化应从 5 被修改为 1")

    def test_cancel_before_c_change(self):
        """before_c_change 取消后，C 点不变。"""
        self.p1.c_point = 3

        def freeze(event):
            event.cancelled = True

        self.game.register_listener(EVENT_BEFORE_C_CHANGE, freeze)
        self.p1.c_point_change(5)
        self.assertEqual(self.p1.c_point, 3, "C 点应不变")

    def test_c_change_event_chain(self):
        """验证 before_c_change → c_changed 完整链。"""
        self.p1.c_point = 0
        chain = []

        def before(event):
            chain.append(("before", event.get("delta")))

        def changed(event):
            chain.append(("changed", event.get("new")))

        self.game.register_listener(EVENT_BEFORE_C_CHANGE, before)
        self.game.register_listener(EVENT_C_CHANGED, changed)
        self.p1.c_point_change(3)
        self.assertEqual(chain, [("before", 3), ("changed", 3)])
        self.assertEqual(self.p1.c_point, 3)


# ---------------------------------------------------------------------------
# 运行入口
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    unittest.main(verbosity=2)
