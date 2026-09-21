#"master class" for the events that can be registered in the system. This class contains the common attributes of these events

from src.models.Key import Key
from src.models.Point import Point
from src.models.Event import Event
from src.controllers.EventValidator import validate_event_input
from src.controllers.PriorityCalculator import calculate_priority
from src.controllers.OperationResult import OperationResult
from src.controllers.ZoneLocator import belongs_to_populated_zone

class Scenery:
    
    def __init__(self, zones, stations, simulation_clock, tree, undo_stack):
        
        self.zones = zones
        self.stations = stations
        self.simulation_clock = simulation_clock    
        self.tree = tree
        self.undo_stack = undo_stack
        self.active_events = []
        self.archived_events = []
        self.eliminated_ids = set()
    
    def create_event(
        self,
        event_id: int,
        magnitude: float,
        depth: float,
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
            event_id, magnitude, depth, epicenter_x, epicenter_y,
            occurred_at, origin_station_id, self.stations, self.simulation_clock
            )
        
        if errors:
            return OperationResult(False, " ".join(errors))
        
        epicenter = Point(epicenter_x, epicenter_y)
        is_in_populated_zone = belongs_to_populated_zone(epicenter, self.zones)
        priority = calculate_priority(magnitude, depth, is_in_populated_zone)
        
        



