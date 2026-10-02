from src.models.Event import Event
from src.models.Key import Key
from src.models.Point import Point
from src.dto.EventLookupResult import EventLookupResult
from src.models.EventStatus import EventStatus
from src.models.AttetionStatus import AttetionStatus
from src.rules.EventValidator import validate_event_input, validate_ranges
from src.dto.OperationResult import OperationResult
from src.rules.EventRules import belongs_to_populated_zone, calculate_priority
from src.controllers.HistoryManager import HistoryManager
from src.controllers.ScenarioSnapshot import take_snapshot, restore_snapshot
from src.controllers.AssociationManager import AssociationManager
from src.models.SimulationParameters import SimulationParameters
from src.models.SimulationClock import SimulationClock
from src.models.Metrics import Metrics
from src.models.Report import ReportQueue

class Scenery:

    def __init__(self, zones, stations, simulation_clock, tree, parameters):
        self.zones = zones
        self.stations = stations
        self.simulation_clock = simulation_clock
        self.tree = tree
        self.active_events = {}
        self.archived_events = {}
        self.eliminated_ids = set()
        self.parameters = parameters
        self.association_manager = AssociationManager(self)
        self.metrics = Metrics()
        self.tree.metrics = self.metrics
        self.queue = ReportQueue()
        # Memento-style undo/redo: record() takes a full snapshot before a
        # change, instead of each action writing its own inverse by hand.
        self.history = HistoryManager(lambda: take_snapshot(self), lambda s: restore_snapshot(self, s))

    @property
    def stress_mode(self):
        return not self.tree.balancing

    @stress_mode.setter
    def stress_mode(self, value):
        self.tree.balancing = not value

    @property
    def access_depth_limit(self):
        return self.parameters.l

    def create_event(
        self,
        event_id: int,
        magnitude: float,
        depth_km: float,
        epicenter_x: float,
        epicenter_y: float,
        occurred_at,
        origin_station_id: str,
    ) -> OperationResult:

        if (event_id in self.active_events
            or event_id in self.archived_events
            or event_id in self.eliminated_ids):
            return OperationResult(False, "Identifier" + str(event_id) + " is already in use.")

        errors = validate_event_input(
            event_id, magnitude, depth_km, epicenter_x, epicenter_y,
            occurred_at, origin_station_id, self.stations, self.simulation_clock
            )

        if errors:
            return OperationResult(False, " ".join(errors))

        epicenter = Point(epicenter_x, epicenter_y)
        is_in_populated_zone = belongs_to_populated_zone(epicenter, self.zones)
        priority = calculate_priority(magnitude, depth_km, is_in_populated_zone)

        event = Event.create_new(
            event_id=event_id,
            magnitude=magnitude,
            depth_km=depth_km,
            epicenter=epicenter,
            ocurredAt=occurred_at,
            origin_station_id=origin_station_id,
            priority=priority,
        )

        # BUG FIX: was Key(event.priority, event.magnitude, event.event_id)
        # none of those exist on Event as plain attributes (private,
        # only exposed via getPriority()/getMagnitude()/getEventId()).
        # This raised AttributeError on every single create_event() call.
        key = Key(event.getPriority(), event.getMagnitude(), event.getEventId())

        self.history.record()
        self.tree.insert(key, event.getEventId())
        self.active_events[event_id] = event
        self.association_manager.recalculate_all()

        # Associations, metrics and visualization updates are wired in
        # once GestorAsociaciones and the metrics module exist left as
        # the next piece to build.

        return OperationResult(True, "Event " + str(event_id) + " created with priority " + str(priority) + ".", event)

    def set_access_depth_limit(self, new_limit):
        self.history.record()
        errors = self.parameters.update(l=new_limit)
        if errors:
            self.history.undo()  # the attempted change never took effect; discard the snapshot we just took
            return OperationResult(False, " ".join(errors))
        return OperationResult(True, "Access depth limit updated to " + str(new_limit) + ".")

    def advance_clock(self, delta):
        errors = SimulationClock.validate_advance(delta)
        if errors:
            return OperationResult(False, " ".join(errors))
        self.history.record()
        self.simulation_clock.advance(delta)
        return OperationResult(True, "Reloj adelantado con éxito.")

    def update_parameters(self, w=None, r=None, l=None, t=None):
        p = self.parameters
        errors = SimulationParameters.validate(
            p.w if w is None else w, p.r if r is None else r,
            p.l if l is None else l, p.t if t is None else t)
        if errors:
            return OperationResult(False, " ".join(errors))
        self.history.record()
        self.parameters.update(w=w, r=r, l=l, t=t)
        if w is not None or r is not None:
            self.association_manager.recalculate_all()
        return OperationResult(True, "Parámetros actualizados.")


    def get_event(self, event_id):
        if event_id in self.active_events:
            return EventLookupResult(EventStatus.ACTIVE, self.active_events[event_id])
        elif event_id in self.archived_events:
            return EventLookupResult(EventStatus.ARCHIVED, self.archived_events[event_id])
        elif event_id in self.eliminated_ids:
            return EventLookupResult(EventStatus.ELIMINATED)
        else:
            return EventLookupResult(EventStatus.UNKNOWN)

    def mark_as_reviewed(self, event_id):
        if event_id not in self.active_events:
            return OperationResult(False, "Event " + str(event_id) + " is not an active event.")

        self.history.record()
        event = self.active_events[event_id]
        # BUG FIX: was `event.status = AttetionStatus.REVIEWED`, which
        # created a brand new public "status" attribute instead of
        # touching the private __status  getStatus() kept returning
        # PENDING forever. Also, the function fell off the end without a
        # return, so callers got None instead of an OperationResult.
        event.setStatus(AttetionStatus.REVIEWED)
        return OperationResult(True, "Event " + str(event_id) + " marked as reviewed.", event)

    def delete_event(self, event_id: int) -> OperationResult:
        """Marks an event as retired: out of the active catalog, out of the
        active AVL, and its id becomes non-reusable (create_event already
        checks eliminated_ids). Only active events can be deleted - an
        archived or already-eliminated id is rejected.

        Note for whoever wires this in: unlike create_event, this does not
        touch AssociationManager. Other events may have had this one as
        their chosen reference, so the caller should run
        association_manager.recalculate_all() right after a successful
        deletion (recalculate_for_event() alone is not enough, since it
        only recomputes the deleted event's own - now gone - association).
        """
        if event_id not in self.active_events:
            return OperationResult(False, "Event " + str(event_id) + " is not an active event.")

        event = self.active_events[event_id]
        key = Key(event.getPriority(), event.getMagnitude(), event.getEventId())

        self.history.record()
        self.tree.delete(key)
        del self.active_events[event_id]
        self.eliminated_ids.add(event_id)
        self.association_manager.recalculate_all()

        return OperationResult(True, "Event " + str(event_id) + " eliminated.", event)

    def correct_event(self, event_id: int, magnitude: float, depth_km: float,
                       epicenter_x: float, epicenter_y: float,
                       reporting_station_id: str,
                       occurred_at=None, review=None) -> OperationResult:
        """Manual correction: magnitude, depth and/or epicenter can change.
        The occurrence time and the event's identity never change - a
        correction is a new report about the same event, not a new event.

        Per spec: review is a positive integer that only ever goes up, and
        the set of stations with accepted reports is conserved (grows),
        it is never replaced by a single "current" station. So
        reporting_station_id is ADDED to the existing set, not swapped in.

        Priority and key can both change (priority depends on magnitude,
        depth and the populated-zone check), so the event's node has to be
        removed and reinserted under its new key - editing it in place
        would leave the AVL's ordering invariant broken.

        The event always returns to PENDING: whoever already reviewed the
        previous data has not reviewed this new report yet.

        Note for whoever wires this in: like delete_event, this does not
        call AssociationManager - run recalculate_all() right after a
        successful correction, since a changed magnitude/epicenter can
        make this event a candidate (or stop being one) for others, not
        just change its own chosen reference.
        """
        if event_id not in self.active_events:
            return OperationResult(False, "Event " + str(event_id) + " is not an active event.")

        if reporting_station_id not in self.stations:
            return OperationResult(False, "Unknown station: " + str(reporting_station_id) + ".")

        errors = validate_ranges(event_id, magnitude, depth_km, epicenter_x, epicenter_y)
        if errors:
            return OperationResult(False, " ".join(errors))

        event = self.active_events[event_id]
        old_key = Key(event.getPriority(), event.getMagnitude(), event.getEventId())

        epicenter = Point(epicenter_x, epicenter_y)
        is_in_populated_zone = belongs_to_populated_zone(epicenter, self.zones)
        new_priority = calculate_priority(magnitude, depth_km, is_in_populated_zone)
        new_key = Key(new_priority, magnitude, event_id)

        self.history.record()

        event.setMagnitude(magnitude)
        event.setDepth_km(depth_km)
        event.setEpicenter(epicenter)
        event.setPriority(new_priority)
        if occurred_at is not None:
            event.setOcurredAt(occurred_at)
        event.setReview(event.getReview() + 1 if review is None else review)
        event.setStatus(AttetionStatus.PENDING)
        if reporting_station_id not in event.getStations():
            event.getStations().append(reporting_station_id)

        self.tree.delete(old_key)
        self.tree.insert(new_key, event_id)
        self.association_manager.recalculate_all()
        self.metrics.increment("corrections_accepted")

        return OperationResult(True, "Event " + str(event_id) + " corrected with priority "
                                + str(new_priority) + ".", event)

    def undo(self) -> OperationResult:
        if not self.history.undo():
            return OperationResult(False, "No hay acciones para deshacer.")
        return OperationResult(True, "Acción deshecha.")

    def redo(self) -> OperationResult:
        if not self.history.redo():
            return OperationResult(False, "No hay acciones para rehacer.")
        return OperationResult(True, "Acción rehecha.")
