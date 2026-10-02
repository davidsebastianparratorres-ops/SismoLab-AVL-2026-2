class Metrics:
    """Accumulated counters (section 14). They are part of the restorable
    state: undo and version restore bring back their previous values.
    Indicators that can be derived from the catalogue (events per priority,
    pending, costly access) are NOT stored here; see Indicators.py."""

    COUNTERS = (
        "corrections_accepted", "reports_discarded", "conflicts",
        "mass_archives", "events_archived",
        "case_LL", "case_RR", "case_LR", "case_RL",
        "rotations_left", "rotations_right",
    )

    def __init__(self, values=None):
        self._values = {name: 0 for name in self.COUNTERS}
        if values:
            self._values.update(values)

    def increment(self, name, amount=1):
        if name not in self._values:
            raise KeyError("Unknown metric: " + str(name))
        self._values[name] += amount

    def get(self, name):
        return self._values[name]

    # A double case (LR/RL) counts ONE case plus two elementary rotations;
    # the rotation counters are fed by each elementary rotation.
    def record_case(self, case):           # "LL" | "RR" | "LR" | "RL"
        self.increment("case_" + case)

    def record_rotation(self, direction):  # "left" | "right"
        self.increment("rotations_" + direction)

    # Undo || snapshot state management (same pattern as SimulationParameters)
    def copy(self):
        return Metrics(dict(self._values))

    def restore(self, snapshot):
        self._values = dict(snapshot._values)

    # Persistence
    def to_dict(self):
        return dict(self._values)

    @staticmethod
    def from_dict(data):
        """Returns (metrics, errors). If errors exist, metrics is None."""
        if not isinstance(data, dict):
            return None, ["La sección de métricas debe ser un objeto."]
        errors = []
        for name in Metrics.COUNTERS:
            value = data.get(name)
            if not (isinstance(value, int) and not isinstance(value, bool) and value >= 0):
                errors.append("Métrica inválida o faltante: " + name + ".")
        return (None, errors) if errors else (Metrics(data), [])