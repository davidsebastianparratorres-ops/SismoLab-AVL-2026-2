from src.models.Event import Event
from src.models.Key import Key
from src.models.Point import Point
from src.controllers.EventLookupResult import EventLookupResult
from src.controllers.EventStatus import EventStatus
from src.controllers.AttetionStatus import AttetionStatus
from src.controllers.EventValidator import validate_event_input
from src.controllers.OperationResult import OperationResult
from src.controllers.EventRules import belongs_to_populated_zone, calculate_priority
from src.controllers.HistoryManager import HistoryManager
from src.controllers.ScenarioSnapshot import take_snapshot, restore_snapshot


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
        # Memento-style undo/redo: record() takes a full snapshot before a
        # change, instead of each action writing its own inverse by hand.
        self.history = HistoryManager(lambda: take_snapshot(self), lambda s: restore_snapshot(self, s))

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
        # â€” none of those exist on Event as plain attributes (private,
        # only exposed via getPriority()/getMagnitude()/getEventId()).
        # This raised AttributeError on every single create_event() call.
        key = Key(event.getPriority(), event.getMagnitude(), event.getEventId())

        self.history.record()
        self.tree.insert(key, event.getEventId())
        self.active_events[event_id] = event

        # Associations, metrics and visualization updates are wired in
        # once GestorAsociaciones and the metrics module exist â€” left as
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
        self.history.record()
        errors = self.simulation_clock.advance(delta)
        if errors:
            self.history.undo()
            return OperationResult(False, " ".join(errors))
        return OperationResult(True, "Reloj adelantado con Ã©xito.")

    def update_parameters(self, w=None, r=None, l=None, t=None):
        self.history.record()
        errors = self.parameters.update(w=w, r=r, l=l, t=t)
        if errors:
            self.history.undo()
            return OperationResult(False, " ".join(errors))
        return OperationResult(True, "Parameters updated.")

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
        # touching the private __status â€” getStatus() kept returning
        # PENDING forever. Also, the function fell off the end without a
        # return, so callers got None instead of an OperationResult.
        event.setStatus(AttetionStatus.REVIEWED)
        return OperationResult(True, "Event " + str(event_id) + " marked as reviewed.", event)

    def undo(self) -> OperationResult:
        if not self.history.undo():
            return OperationResult(False, "No hay acciones para deshacer.")
        return OperationResult(True, "Acción deshecha.")

    def redo(self) -> OperationResult:
        if not self.history.redo():
            return OperationResult(False, "No hay acciones para rehacer.")
        return OperationResult(True, "Acción rehecha.")