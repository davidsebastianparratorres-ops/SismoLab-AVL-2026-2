#"master class" for the events that can be registered in the system. This class contains the common attributes of these events
from src.models.Event import Event
from src.models.Key import Key
from src.models.Point import Point
from src.controllers.EventLookupResult import EventLookupResult
from src.controllers.EventStatus import EventStatus
from src.controllers.AttetionStatus import AttetionStatus
from src.controllers.EventValidator import validate_event_input
from src.controllers.OperationResult import OperationResult
from src.controllers.EventRules import belongs_to_populated_zone, calculate_priority
class Scenery:
    
    def __init__(self, zones, stations, simulation_clock, tree, undo_stack, parameters):
        
        self.zones = zones
        self.stations = stations
        self.simulation_clock = simulation_clock    
        self.tree = tree
        self.undo_stack = undo_stack
        self.active_events = {}
        self.archived_events = {}
        self.eliminated_ids = set()
        self.parameters = parameters
        self.access_depth_limit = 3  # section 9: initial value is 3
    
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
            or event_id in self.eliminated_ids):
            return OperationResult(False, "Identifier" +str(event_id) + " is already in use.")
        
        #validate range (section 6)
        
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
            occurred_at=occurred_at,
            origin_station_id=origin_station_id,
            priority=priority,
        )

        key = Key(event.priority, event.magnitude, event.event_id)
        self.tree.insert(key, event.event_id)
        self.active_events[event_id] = event

        self.undo_stack.push_creation(event_id)

        # Associations, metrics and visualization updates are wired in
        # once GestorAsociaciones and the metrics module exist — left as
        # the next piece to build.

        return OperationResult(True, "Event " + str(event_id) + " created with priority " + str(priority) + ".", event)
    
    
    def set_access_depth_limit(self, new_limit):
        if new_limit < 0:
            return OperationResult(False, "Access depth limit must be a non-negative integer.")
        self.access_depth_limit = new_limit
        return OperationResult(True, "Access depth limit updated to " + str(new_limit) + ".")
        
    def advance_clock(self, delta):
        #Advances simulation clock by delta time steps.
        errors = self.simulation_clock.advance(delta)
        if errors:
            return OperationResult(False, " ".join(errors))
        return OperationResult(True, "Reloj adelantado con éxito.")

    def update_parameters(self, w=None, r=None, l=None, t=None):
         #Updates simulation parameters (W, R, L, T) atomically.
         errors = self.parameters.update(w=w, r=r, l=l, t=t)
         if errors:
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

     event = self.active_events[event_id]
     event.status = AttetionStatus.REVIEWED

        
        