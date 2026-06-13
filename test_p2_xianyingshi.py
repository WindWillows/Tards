import sys
sys.path.insert(0, "TARDS(demo)")

from tests.harness import GameHarness
from tests.assertions import assert_minion_exists

h = GameHarness()
p1, p2 = h.players

# 玩家2在第1行（后排）部署显影室
h.deploy("显影室", p2, (1, 2))
assert_minion_exists(h.game, (1, 2), "显影室")

h.resolve_phase(p1, p2)

# 检查是否召唤了溴化银
m = h.game.board.minion_place.get((0, 2))
if m:
    print(f"溴化银已召唤: {m.name} at (0, 2)")
else:
    print("ERROR: 溴化银未召唤！")
    print("棋盘状态:")
    for r in range(5):
        row = []
        for c in range(5):
            m = h.game.board.minion_place.get((r, c))
            if m:
                row.append(f"{m.owner.name[0]}{m.name}")
            else:
                row.append(".")
        print(f"  [{r}] {' | '.join(row)}")
