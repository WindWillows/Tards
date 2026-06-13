import sys
sys.path.insert(0, "TARDS(demo)")

from tests.harness import GameHarness
from tests.assertions import assert_minion_exists
from card_pools.effect_utils import add_card_to_hand_by_name

h = GameHarness()
p1, p2 = h.players

# 给p2一张显影室
add_card_to_hand_by_name("显影室", p2, h.game)

# 部署显影室到第1行（后排）
h.deploy("显影室", p2, (1, 2))
assert_minion_exists(h.game, (1, 2), "显影室")

print("=== 部署后棋盘 ===")
print(h.game.board)

# 模拟一个完整回合
h.game.current_turn = 1
first, second = p1, p2
h.game.history.advance_turn(h.game.current_turn)
h.game.emit_event("turn_start", turn=h.game.current_turn, first=first, second=second)

# 抽牌阶段
h.game.current_phase = h.game.PHASE_DRAW
h.game.emit_event("phase_start", phase=h.game.PHASE_DRAW, first=first, second=second)

# 出牌阶段 - 双方拉闸
h.game.current_phase = h.game.PHASE_ACTION
h.game.emit_event("phase_start", phase=h.game.PHASE_ACTION, first=first, second=second)
# 直接结束action_phase
h.game.emit_event("phase_end", phase=h.game.PHASE_ACTION, first=first, second=second)

# 结算阶段
print("=== 进入结算阶段 ===")
h.game.current_phase = h.game.PHASE_RESOLVE
h.game.emit_event("phase_start", phase=h.game.PHASE_RESOLVE, first=first, second=second)

print("=== 结算阶段后棋盘 ===")
print(h.game.board)

# 检查溴化银
m = h.game.board.minion_place.get((0, 2))
if m:
    print(f"溴化银已召唤: {m.name} at (0, 2)")
else:
    print("ERROR: 溴化银未召唤！")
