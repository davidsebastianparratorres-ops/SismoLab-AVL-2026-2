from src.models.Association import Association
from src.controllers.AssociationRules import is_candidate, choose_reference

class AssociationManager:

    def __init__(self, scenery, max_hours=48.0, max_distance_km=40.0):
        self.scenery = scenery
        self.max_hours = max_hours
        self.max_distance_km = max_distance_km
        self.associations = {}  # dict[replica_id, Association] -- only entries WITH a chosen reference

    def _all_eligible_events(self):
        # "Se consideran eventos activos y archivados, pero no eliminados" (section 7)
        # BUG FIX: was self.catalog.active_events / archived_events, but the
        # constructor never set self.catalog — only self.scenery exists
        # (as _find_event_by_id already correctly used). Raised
        # AttributeError on every call.
        events = list(self.scenery.active_events.values())
        events.extend(self.scenery.archived_events.values())
        return events

    def _find_event_by_id(self, event_id):
        if event_id in self.scenery.active_events:
            return self.scenery.active_events[event_id]
        if event_id in self.scenery.archived_events:
            return self.scenery.archived_events[event_id]
        return None  # Not found or eliminated

    def find_candidates(self, target_event):
        candidates = []
        for event in self._all_eligible_events():
            if is_candidate(event, target_event, self.max_hours, self.max_distance_km):
                candidates.append(event)
        return candidates

    def recalculate_for_event(self, event_id):
        target_event = self._find_event_by_id(event_id)
        if target_event is None:
            # Event no longer eligible (e.g. deleted) -> drop any stored association
            if event_id in self.associations:
                del self.associations[event_id]
            return

        candidates = self.find_candidates(target_event)
        reference = choose_reference(candidates, target_event)

        if reference is None:
            if event_id in self.associations:
                del self.associations[event_id]
        else:
            self.associations[event_id] = Association(event_id, reference.getEventId())

    def recalculate_all(self):
        # Simple, correct approach: after any change that could affect
        # associations (create, correct, delete, or a change to W/R),
        # recompute every event's association from scratch.
        for event in self._all_eligible_events():
            self.recalculate_for_event(event.getEventId())

    def get_candidates_and_reference(self, event_id):
        target_event = self._find_event_by_id(event_id)
        if target_event is None:
            return [], None
        candidates = self.find_candidates(target_event)
        stored = self.associations.get(event_id)
        reference_id = stored.reference_id if stored is not None else None
        return candidates, reference_id

    def get_events_referencing(self, event_id):
        # "los eventos que lo utilizan como referencia" (section 11)
        referencing_ids = []
        for replica_id, association in self.associations.items():
            if association.reference_id == event_id:
                referencing_ids.append(replica_id)
        return referencing_ids
