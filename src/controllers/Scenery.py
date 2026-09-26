#"master class" for the events that can be registered in the system. This class contains the common attributes of these events

from src.models.Key import Key
from src.models.Point import Point
from src.models.Event import Event
from src.controllers.EventValidator import validate_event_input
from src.controllers.PriorityCalculator import calculate_priority
from src.controllers.OperationResult import OperationResult
from src.controllers.ZoneLocator import belongs_to_populated_zone
from src.controllers.TreeAuditor import TreeAuditor
from src.models.AuditReport import AuditReport

class Scenery:
    
    def __init__(self, zones, stations, simulation_clock, tree, undo_stack, parameters):
        
        self.zones = zones
        self.stations = stations
        self.simulation_clock = simulation_clock    
        self.tree = tree
        self.undo_stack = undo_stack
        self.active_events = []
        self.archived_events = []
        self.eliminated_ids = set()
        self.parameters = parameters
    
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
         return OperationResult(True, "Parámetros actualizados con éxito.")  

    def verify_structure(self, stress_mode: bool = False):
        #Executes structural verification of the active AVL tree and catalogs (Section 14).
        #Converts active and archived lists into ID-indexed dictionaries and sets
       # before delegating evaluation to TreeAuditor.
        
          active_by_id = {event.getEventId(): event for event in self.active_events}
          archived_ids = {event.getEventId() for event in self.archived_events}
          return TreeAuditor().audit(
             self.tree.getRoot(),
             active_by_id,
             stress_mode=stress_mode,
             archived_ids=archived_ids,
             eliminated_ids=self.eliminated_ids,
             )

