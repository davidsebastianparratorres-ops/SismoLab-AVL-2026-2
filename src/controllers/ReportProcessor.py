from dataclasses import dataclass, field

from src.models.SimulationClock import ensure_datetime
from src.rules.EventValidator import validate_event_input


class Decision:
    CREATED = "CREATED"          # unknown id -> new event
    UPDATED = "UPDATED"          # higher revision on an active event
    REACTIVATED = "REACTIVATED"  # higher revision on an archived event
    CONFIRMED = "CONFIRMED"      # same revision, same data
    CONFLICT = "CONFLICT"        # same revision, different data
    OUTDATED = "OUTDATED"        # lower revision
    REJECTED = "REJECTED"        # eliminated id, unknown station or invalid data


@dataclass
class StepResult:
    """What one queue step did (section 8): shown by the GUI after each step."""
    report: object
    decision: str
    message: str
    rotations: dict = field(default_factory=dict)  # only counters that changed in this step


class ReportProcessor:
    """Applies queued reports to the scenery following the resolution table of
    section 6. It decides; creating / correcting events is delegated to Scenery."""

    def __init__(self, scenery):
        self.scenery = scenery

    def enqueue(self, reports) -> None:
        # Preparing a burst is ONE undoable action: undoing it removes the whole burst.
        with self.scenery.history.single_action():
            self.scenery.queue.extend(reports)

    def process_next(self):
        """Resolves the report at the head of the queue completely (one undoable
        action, even if the report ends up discarded). Returns None if the queue is empty."""
        s = self.scenery
        if len(s.queue) == 0:
            return None
        before = s.metrics.to_dict()
        with s.history.single_action():
            report = s.queue.dequeue()
            decision, message = self._resolve(report)
        rotations = {name: value - before[name] for name, value in s.metrics.to_dict().items()
                     if name.startswith(("case_", "rotations_")) and value != before[name]}
        return StepResult(report, decision, message, rotations)

    # ------------------------------------------------------------------
    # Resolution table (section 6)
    # ------------------------------------------------------------------
    def _resolve(self, report):
        s = self.scenery
        if not (isinstance(report.revision, int) and report.revision >= 1):
            return self._discard(Decision.REJECTED, "La revisión debe ser un entero positivo.")
        if report.station_id not in s.stations:
            return self._discard(Decision.REJECTED, f"Estación desconocida: {report.station_id}.")
        if report.event_id in s.eliminated_ids:
            return self._discard(Decision.REJECTED, f"El evento {report.event_id} fue eliminado; "
                                 "sus reportes se rechazan hasta deshacer la eliminación.")

        event = s.active_events.get(report.event_id)
        if event is None:
            event = s.archived_events.get(report.event_id)
        if event is None:
            return self._create(report)

        if report.revision < event.getReview():
            return self._discard(Decision.OUTDATED, f"Reporte antiguo: revisión {report.revision} "
                                 f"< vigente {event.getReview()}.")
        if report.revision > event.getReview():
            return self._update(report)
        if self._same_data(report, event):
            return self._confirm(report, event)
        s.metrics.increment("conflicts")
        return Decision.CONFLICT, (f"Conflicto: misma revisión {report.revision} con datos distintos; "
                                   "el reporte se rechaza sin modificar el evento.")

    def _create(self, report):
        s = self.scenery
        result = s.create_event(report.event_id, report.magnitude, report.depth_km, report.epicenter_x,
                                report.epicenter_y, report.occurred_at, report.station_id)
        if not result.success:
            return self._discard(Decision.REJECTED, result.message)
        result.event.setReview(report.revision)  # the first revision received may be > 1
        return Decision.CREATED, f"Evento {report.event_id} registrado con revisión {report.revision}."

    def _update(self, report):
        s = self.scenery
        errors = validate_event_input(report.event_id, report.magnitude, report.depth_km,
                                      report.epicenter_x, report.epicenter_y, report.occurred_at,
                                      report.station_id, s.stations, s.simulation_clock)
        if errors:
            return self._discard(Decision.REJECTED, " ".join(errors))
        archived = report.event_id in s.archived_events
        if archived:  # back to the active catalogue; correct_event then places it in the tree
            s.active_events[report.event_id] = s.archived_events.pop(report.event_id)
        s.correct_event(report.event_id, report.magnitude, report.depth_km, report.epicenter_x,
                        report.epicenter_y, report.station_id, report.occurred_at, report.revision)
        if archived:
            return Decision.REACTIVATED, f"Evento {report.event_id} reactivado (revisión {report.revision})."
        return Decision.UPDATED, f"Evento {report.event_id} actualizado a la revisión {report.revision}."

    def _confirm(self, report, event):
        if report.station_id not in event.getStations():  # never duplicates a station
            event.getStations().append(report.station_id)
        return Decision.CONFIRMED, f"Evento {report.event_id} confirmado por {report.station_id}."

    def _discard(self, decision, message):
        self.scenery.metrics.increment("reports_discarded")
        return decision, message

    @staticmethod
    def _signature(magnitude, depth, x, y, occurred_at):
        # Tenths as integers and an aware datetime: comparisons never depend on float noise
        # or on text format. The sender is deliberately NOT part of it (section 6).
        return (round(magnitude * 10), round(depth * 10), round(x * 10), round(y * 10),
                ensure_datetime(occurred_at))

    def _same_data(self, report, event):
        epicenter = event.getEpicenter()
        return (self._signature(report.magnitude, report.depth_km, report.epicenter_x,
                                report.epicenter_y, report.occurred_at)
                == self._signature(event.getMagnitude(), event.getDepth_km(), epicenter.getX(),
                                   epicenter.getY(), event.getOcurredAt()))