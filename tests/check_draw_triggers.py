"""一次性检查所有带“抽取”效果的卡牌在抽到时是否触发正常。

直接运行：
    cd TARDS(demo)
    python -m tests.check_draw_triggers
"""

from __future__ import annotations

import io
import sys
import traceback

# 确保所有卡包已注册
import card_pools.blood
import card_pools.discrete
import card_pools.general
import card_pools.miracle
import card_pools.underworld

from card_pools.effect_utils import create_card_by_name
from tests.harness import GameHarness


DRAW_CARDS = [
    ("汞雾", {"check": lambda h: h.p1.health == 28 and h.p2.health == 28}),
    ("高炉", {"check": lambda h: len(h.p1.card_hand) >= 1}),
    ("奇怪的蛹", {"check": lambda h: h.p1.card_hand and h.p1.card_hand[-1].name == "奇怪的蛹"}),
    ("食蚁兽", {"check": lambda h: h.p1.card_hand and h.p1.card_hand[-1].name == "食蚁兽"}),
    (
        "水漫缮写室",
        {
            "setup": lambda h: (h.give_hand(h.p1, "书架"), h.give_hand(h.p1, "火灵")),
            "patch_choice": True,
            "check": lambda h: True,  # 只要选择并执行不崩溃即可
        },
    ),
    (
        "纠缠血流",
        {
            "setup": lambda h: setattr(h.p1, "s_point", 5),
            "check": lambda h: h.p1.card_hand and h.p1.card_hand[-1].name == "纠缠血流",
        },
    ),
    ("血痂", {"check": lambda h: h.p1.health == 27}),
    (
        "雪降",
        {
            "setup": lambda h: (
                setattr(h.p1, "s_point", 5),
                h.deploy("书架", h.p1, (4, 0)),
                h.deploy("火灵", h.p2, (0, 0)),
            ),
            "check": lambda h: any(
                m.keywords.get("冰冻", 0) > 0
                for m in h.game.board.minion_place.values()
            ),
        },
    ),
]


def _make_choice_stub(h: GameHarness):
    """让需要选择的抽取效果自动选第一个选项。"""
    orig = h.game.request_choice

    def stub(player, options, title="", **kwargs):
        if options:
            return options[0]
        return None

    h.game.request_choice = stub
    return orig


def main():
    results = []
    for name, cfg in DRAW_CARDS:
        h = GameHarness()
        h.game.current_turn = 1  # 避免水漫缮写室等跳过开局阶段
        original_choice = None
        try:
            if "setup" in cfg:
                cfg["setup"](h)
            if cfg.get("patch_choice"):
                original_choice = _make_choice_stub(h)

            # 将目标卡放到牌库顶并抽取
            card = create_card_by_name(name, h.p1)
            h.p1.card_deck.append(card)
            drawn = h.p1.draw_card(1, game=h.game)

            ok = bool(drawn) and cfg["check"](h)
            results.append((name, ok, None))
        except Exception as e:
            results.append((name, False, traceback.format_exc()))
        finally:
            if original_choice is not None:
                h.game.request_choice = original_choice

    print("\n===== 抽取效果检查结果 =====")
    all_ok = True
    for name, ok, err in results:
        status = "[OK]" if ok else "[FAIL]"
        print(f"{status} {name}")
        if err:
            print(err)
        if not ok:
            all_ok = False
    print("============================")
    print("全部正常" if all_ok else "存在异常，请查看详情")


if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    main()
