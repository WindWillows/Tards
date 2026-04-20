from typing import Callable, List, Tuple


class EffectQueue:
    """效果队列：确保"效果一旦开始结算，不会被由此效果引发的其他效果打断"。

    主效果通过 resolve() 执行，执行期间新产生的连锁效果被收集到队列中。
    主效果结束后，按 FIFO 顺序依次处理队列中的连锁效果。
    处理连锁效果期间产生的新连锁继续追加到队列末尾。
    """

    def __init__(self, game):
        self.game = game
        self._queue: List[Tuple[str, Callable[[], None]]] = []
        self._resolving = False

    def is_resolving(self) -> bool:
        return self._resolving

    def queue(self, name: str, fn: Callable[[], None]):
        """将效果加入队列。若当前不在结算中，立即开始处理队列。"""
        self._queue.append((name, fn))
        if not self._resolving:
            self._process()

    def resolve(self, name: str, fn: Callable[[], None]):
        """执行一个主效果，并在其结束后处理所有连锁。

        若当前已经在结算中，说明这是某个主效果内部的子调用，
        直接执行而不再套一层队列处理（队列已在外层控制）。
        """
        if self._resolving:
            fn()
            return

        self._resolving = True
        try:
            fn()
        finally:
            self._resolving = False
            self.game.refresh_all_auras()
            self._process()

    def _process(self):
        """按 FIFO 顺序处理队列中的连锁效果。"""
        while self._queue and not self.game.game_over:
            name, fn = self._queue.pop(0)
            print(f"  [连锁] {name}")
            self._resolving = True
            try:
                fn()
            finally:
                self._resolving = False
                self.game.check_game_over()
                self.game.refresh_all_auras()
