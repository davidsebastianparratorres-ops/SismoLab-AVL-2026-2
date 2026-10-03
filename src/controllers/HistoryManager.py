from contextlib import contextmanager

class HistoryManager:
    """Undo/redo stack. Doesn't know what a "snapshot" contains — the
    caller supplies snapshot_factory() (takes a full snapshot) and
    snapshot_restorer(snapshot) (applies one back), so this class works
    the same whether a snapshot means "just the clock" or "the whole
    scenario", without needing to change when more pieces get added."""

    def __init__(self, snapshot_factory, snapshot_restorer):
        self.__snapshot_factory = snapshot_factory
        self.__snapshot_restorer = snapshot_restorer
        self.__undo_stack = []
        self.__redo_stack = []
        self.__grouping = False

    def record(self) -> None:
        # Call BEFORE applying a change — captures the state as it was
        # right before that action, so it can be restored later.
        if self.__grouping:
            return
        self.__undo_stack.append(self.__snapshot_factory())
        self.__redo_stack.clear()  # a new action invalidates the old redo path

    @contextmanager
    def single_action(self):
        self.record()
        outer, self.__grouping = self.__grouping, True
        try:
            yield
        finally:
            self.__grouping = outer

    def undo(self) -> bool:
        if not self.__undo_stack:
            return False
        self.__redo_stack.append(self.__snapshot_factory())
        self.__snapshot_restorer(self.__undo_stack.pop())
        return True

    def redo(self) -> bool:
        if not self.__redo_stack:
            return False
        self.__undo_stack.append(self.__snapshot_factory())
        self.__snapshot_restorer(self.__redo_stack.pop())
        return True

    def can_undo(self) -> bool:
        return len(self.__undo_stack) > 0

    def can_redo(self) -> bool:
        return len(self.__redo_stack) > 0