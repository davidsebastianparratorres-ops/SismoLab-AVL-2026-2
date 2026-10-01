
from typing import List, Dict
from src.rules.AssociationRules import is_candidate, choose_reference


class AssociationManager:
    #Manages the calculation of candidates and references by injecting parameters W and R.

    def __init__(self, max_hours: float, max_distance_km: float):
        self.max_hours = max_hours
        self.max_distance_km = max_distance_km

    def get_candidates_for_event(self, target_event, catalogue: Dict) -> List:
        
        #Returns all events in the catalog that are candidates for the target event.
        candidates = []
        for other_event in catalogue.values():
            if is_candidate(other_event, target_event, self.max_hours, self.max_distance_km):
                candidates.append(other_event)
        return candidates

    def get_reference_for_event(self, target_event, catalogue: Dict):
         #Calculate the selected reference using the deterministic cascade.
        candidates = self.get_candidates_for_event(target_event, catalogue)
        return choose_reference(candidates, target_event)

    def build_callbacks(self, active_events: dict, archived_events: dict):
        #Generate the two callback functions ready to be passed to EventQueries.event_associations.
        catalogue = {**active_events, **archived_events}
        
        def get_candidates_cb(event):
            return self.get_candidates_for_event(event, catalogue)

        def get_reference_cb(event):
            return self.get_reference_for_event(event, catalogue)

        return get_candidates_cb, get_reference_cb