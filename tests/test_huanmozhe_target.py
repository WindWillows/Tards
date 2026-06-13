"""唤魔者效果预设位置测试。"""

import sys
sys.path.insert(0, "TARDS(demo)")

from tests.harness import GameHarness


def test_huanmozhe_preset_position():
    h = GameHarness("p1", "p2")
    p1, p2 = h.p1, h.p2

    # 清空战场并在 p1 友好区部署唤魔者
    h.clear_board()
    evoker = h.deploy("唤魔者", p1, (3, 0))
    assert evoker is not None, "部署唤魔者失败"
    assert evoker.name == "唤魔者"

    # 预设召唤位置为 (3, 1)
    target_pos = (3, 1)
    evoker._pending_effect_target = target_pos

    # 触发结算阶段开始
    h.resolve_phase(p1, p2)

    summoned = h.at(target_pos)
    assert summoned is not None, f"预设位置 {target_pos} 没有召唤出精灵"
    assert "精灵" in summoned.tags, f"召唤出的 {summoned.name} 不是精灵"
    assert summoned.keywords.get("迅捷") is True, f"召唤出的 {summoned.name} 没有迅捷"
    print(f"测试通过：在 {target_pos} 召唤出 {summoned.name}，具有迅捷")


def test_huanmozhe_no_preset_no_summon():
    h = GameHarness("p1", "p2")
    p1, p2 = h.p1, h.p2

    h.clear_board()
    evoker = h.deploy("唤魔者", p1, (3, 0))
    assert evoker is not None

    # 不预设目标
    evoker._pending_effect_target = None

    before = set(h.game.board.minion_place.keys())
    h.resolve_phase(p1, p2)
    after = set(h.game.board.minion_place.keys())

    assert after == before, "未预设目标时不应召唤精灵"
    print("测试通过：未预设目标时未召唤精灵")


if __name__ == "__main__":
    test_huanmozhe_preset_position()
    test_huanmozhe_no_preset_no_summon()
    print("全部通过")
