from dataclasses import dataclass
from typing import Any, Callable, List, Optional


@dataclass
class StackFrame:
    """堆栈帧：代表堆栈上的一个待结算效果。"""

    name: str
    fn: Callable[[], None]
    source: Any = None
    cancelled: bool = False


class EffectQueue:
    """效果队列与堆栈：支持 FIFO 连锁队列 + LIFO 响应堆栈。

    核心设计：
    - 堆栈（Stack）用于"主动打出/执行"的效果（如打出卡牌、战斗结算）。
      每个堆栈帧结算前触发响应窗口，允许其他效果推入堆栈顶部（LIFO），
      实现 Counterspell 式"取消原效果"。
    - 队列（Queue）用于"自动触发"的连锁效果（如亡语、回合开始/结束、雕像融合）。
      按 FIFO 顺序处理，在堆栈清空后执行，不触发响应窗口。

    向后兼容：
    - `resolve(name, fn)` 语义不变：若已在结算中则直接执行；否则推入堆栈并结算。
    - `queue(name, fn)` 语义不变：追加到队列，若不在结算中则立即处理。
    """

    def __init__(self, game):
        self.game = game
        self._stack: List[StackFrame] = []
        self._queue: List[StackFrame] = []
        self._resolving = False
        self._resolving_stack = False  # 堆栈结算中（含响应窗口）
        self._max_stack_depth = 500  # 防止无限响应链

    def is_resolving(self) -> bool:
        return self._resolving

    def push_stack(self, name: str, fn: Callable[[], None], source: Any = None) -> StackFrame:
        """将效果推入堆栈顶部。返回 StackFrame，可被其他效果取消。"""
        frame = StackFrame(name=name, fn=fn, source=source)
        self._stack.append(frame)
        return frame

    def resolve_stack(self):
        """按 LIFO 顺序结算堆栈中的所有效果。

        在结算每个效果前触发响应窗口（before_stack_resolve 事件），
        允许监听器推入新的响应效果到堆栈顶部，或设置当前帧 cancelled。
        """
        self._resolving_stack = True
        try:
            depth = 0
            while self._stack and not self.game.game_over:
                depth += 1
                if depth > self._max_stack_depth:
                    print(f"  [警告] 堆栈深度超过 {self._max_stack_depth}，强制中断")
                    break

                # 查看堆栈顶（不弹出），触发响应窗口
                top = self._stack[-1]
                if not top.cancelled:
                    event = self._trigger_response_window(top)
                    if event and getattr(event, "cancelled", False):
                        top.cancelled = True

                # 响应窗口可能推入了新效果，也可能清空了堆栈
                if not self._stack:
                    break

                frame = self._stack.pop()
                if frame.cancelled:
                    print(f"  [取消] {frame.name}")
                    continue

                print(f"  [结算] {frame.name}")
                self._resolving = True
                try:
                    frame.fn()
                finally:
                    self._resolving = False
                    self.game.check_game_over()
                    self.game.refresh_all_auras()
        finally:
            self._resolving_stack = False

    def _trigger_response_window(self, frame: StackFrame):
        """触发响应窗口，允许其他效果在当前堆栈帧结算前做出响应。

        通过事件总线发射 before_stack_resolve 事件。监听器可检查
        event.data["frame"] 并决定是否推入新的堆栈效果。
        """
        if hasattr(self.game, "emit_event"):
            try:
                return self.game.emit_event("before_stack_resolve", frame=frame)
            except Exception as e:
                print(f"  [响应窗口错误] {e}")
        return None

    def queue(self, name: str, fn: Callable[[], None]):
        """将效果加入连锁队列。若当前不在结算中，立即开始处理队列。

        注意：在堆栈响应窗口期间，队列不会自动处理，而是等堆栈清空后再统一处理。
        这确保了自动触发的连锁效果（如亡语）不会在可响应的堆栈帧之前执行。
        """
        self._queue.append(StackFrame(name=name, fn=fn))
        if not self._resolving and not self._resolving_stack:
            self._process_queue()

    def resolve(self, name: str, fn: Callable[[], None], source: Any = None):
        """执行一个主效果，并在其结束后处理所有连锁。

        若当前已经在结算中，说明这是某个主效果内部的子调用，
        直接执行而不再套一层堆栈处理（堆栈/队列已在外层控制）。
        """
        if self._resolving:
            fn()
            return

        self.push_stack(name, fn, source=source)
        self.resolve_stack()
        self._process_queue()

    def _process_queue(self):
        """按 FIFO 顺序处理队列中的连锁效果。"""
        while self._queue and not self.game.game_over:
            frame = self._queue.pop(0)
            print(f"  [连锁] {frame.name}")
            self._resolving = True
            try:
                frame.fn()
            finally:
                self._resolving = False
                self.game.check_game_over()
                self.game.refresh_all_auras()
