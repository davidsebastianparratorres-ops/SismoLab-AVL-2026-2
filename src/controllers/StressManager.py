from dataclasses import dataclass, field

from src.dto.OperationResult import OperationResult
from src.controllers.TreeAuditor import TreeAuditor

_COST_PREFIXES = ("case_", "rotations_")


@dataclass
class RecoveryResult:
    """Outcome of the global recovery: what it found, what it cost, what the audit said."""
    success: bool
    message: str
    imbalanced_before: int = 0
    rotations: dict = field(default_factory=dict)  # counters that changed = cost of the recovery
    audit: object = None


class StressManager:
    """Execution-mode transitions: enter stress mode and recover back to normal mode.
    Each transition is ONE undoable action. The tree algorithm lives in AVL.restore_balance;
    this class only orchestrates it (audit, mode switch, history, cost)."""

    def __init__(self, scenery):
        self.scenery = scenery

    def enter_stress(self) -> OperationResult:
        s = self.scenery
        if s.stress_mode:
            return OperationResult(False, "El sistema ya está en modo estrés.")
        s.history.record()
        s.stress_mode = True
        return OperationResult(True, "Modo estrés activado: las rotaciones quedan aplazadas.")

    def recover(self) -> RecoveryResult:
        """Global recovery. Leaves stress mode ONLY if the audit confirms a valid AVL."""
        s = self.scenery
        if not s.stress_mode:
            return RecoveryResult(False, "El árbol ya está en modo normal; no hay nada que recuperar.")
        before = self._audit(stress_mode=True)
        if before.has_errors():  # order / metadata errors cannot be fixed by rotating
            return RecoveryResult(False, "No se puede recuperar: hay errores de orden o de metadatos.",
                                  before.imbalanced_count, audit=before)
        costs_before = s.metrics.to_dict()
        with s.history.single_action():
            s.tree.restore_balance()
            after = self._audit(stress_mode=False)
            if after.is_valid_avl:
                s.stress_mode = False
        rotations = {name: value - costs_before[name] for name, value in s.metrics.to_dict().items()
                     if name.startswith(_COST_PREFIXES) and value != costs_before[name]}
        if not after.is_valid_avl:
            return RecoveryResult(False, "La auditoría no confirmó el equilibrio; se mantiene el modo estrés.",
                                  before.imbalanced_count, rotations, after)
        return RecoveryResult(True, f"Recuperación completa: {before.imbalanced_count} nodos desbalanceados "
                              "corregidos. Auditoría confirmada; modo normal.",
                              before.imbalanced_count, rotations, after)

    def _audit(self, stress_mode):
        s = self.scenery
        return TreeAuditor().audit(s.tree.getRoot(), s.active_events, stress_mode=stress_mode,
                                   archived_ids=set(s.archived_events), eliminated_ids=s.eliminated_ids)