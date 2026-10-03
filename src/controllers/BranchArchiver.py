from dataclasses import dataclass

from src.controllers.ArchiveManager import ArchiveManager
from src.dto.OperationResult import OperationResult
from src.models.Key import Key


@dataclass
class ArchivePreview:
    """What 'Archive old branch' would do. Shown to the user BEFORE executing (section 10)."""
    root_id: int
    ids: list
    justification: str

    @property
    def count(self) -> int:
        return len(self.ids)


class BranchArchiver:
    """Executes the archive of an old branch as ONE undoable action.
    Choosing the branch is delegated to a selector (ArchiveManager by default), so this
    class only moves events out of the active catalogue and the AVL into the history."""

    def __init__(self, scenery, selector=None):
        self.scenery = scenery
        self.selector = selector or ArchiveManager()

    def preview(self):
        """Read-only. Returns an ArchivePreview, or None if no branch is eligible."""
        s = self.scenery
        args = (s.tree.getRoot(), s.active_events, s.simulation_clock, s.parameters.t)
        winner, ids = self.selector.select_eligible_branch(*args)
        if winner is None:
            return None
        candidates = self.selector.eligible_branches(*args)
        chosen = next(c for c in candidates if c[0] is winner)
        return ArchivePreview(winner.getEventId(), ids, self._justify(candidates, chosen, s.parameters.t))

    def archive(self) -> OperationResult:
        preview = self.preview()  # the set is FIXED here, before the tree is modified
        if preview is None:
            return OperationResult(False, "No hay ninguna rama elegible para archivar; el estado se conserva.")
        s = self.scenery
        with s.history.single_action():
            # Descendants first (the list has every node after its ancestors): each removal is
            # then a cheap leaf / one-child delete. In normal mode every delete rebalances;
            # in stress mode only the BST order is kept. Rotations never change the fixed set.
            for event_id in reversed(preview.ids):
                event = s.active_events.pop(event_id)
                s.tree.delete(Key(event.getPriority(), event.getMagnitude(), event_id))
                s.archived_events[event_id] = event  # data, stations and associations are kept
            s.metrics.increment("mass_archives")
            s.metrics.increment("events_archived", preview.count)
        return OperationResult(True, f"Rama con raíz {preview.root_id} archivada: "
                               f"{preview.count} evento(s) pasaron al histórico.")

    @staticmethod
    def _justify(candidates, chosen, t_hours):
        node, size, depth = chosen
        text = [f"{len(candidates)} rama(s) elegible(s): todos sus eventos tienen prioridad baja "
                f"y antigüedad mayor que {t_hours} h.",
                f"Se elige la raíz {node.getEventId()}: es la de mayor cantidad de nodos ({size})."]
        same_size = [c for c in candidates if c[1] == size]
        if len(same_size) > 1:
            text.append(f"Hay empate de tamaño entre {len(same_size)} ramas; "
                        f"gana la raíz más profunda (profundidad {depth}).")
            same_depth = [c for c in same_size if c[2] == depth]
            if len(same_depth) > 1:
                text.append(f"Persiste el empate entre {len(same_depth)} raíces; "
                            f"gana el mayor identificador ({node.getEventId()}).")
        return " ".join(text)