class Historic:
    
    def __init__(self):
        self.__archived_events = {}    # {event_id: Event} — dict for O(1) lookup, same reasoning as active events
        self.__eliminated_ids = set()  # {event_id, ...}

    # ------------------------------------------------------------------
    # Archived events
    # ------------------------------------------------------------------

    def archive(self, event_id: int, event) -> None:
        self.__archived_events[event_id] = event

    def is_archived(self, event_id: int) -> bool:
        return event_id in self.__archived_events

    def get_archived(self, event_id: int):
        return self.__archived_events.get(event_id)

    def reactivate(self, event_id: int):
        """Removes the event from the archive and hands it back to the
        caller. Historic never touches the AVL itself — putting the event
        back into the active tree is the caller's job."""
        return self.__archived_events.pop(event_id, None)

    def get_all_archived(self) -> dict:
        return dict(self.__archived_events)  # copy — callers can't mutate our storage directly

    # ------------------------------------------------------------------
    # Eliminated ids
    # ------------------------------------------------------------------

    def mark_eliminated(self, event_id: int) -> None:
        self.__eliminated_ids.add(event_id)

    def is_eliminated(self, event_id: int) -> bool:
        return event_id in self.__eliminated_ids

    def unmark_eliminated(self, event_id: int) -> None:
        # Used when undoing an elimination — reverses mark_eliminated.
        self.__eliminated_ids.discard(event_id)

    def get_eliminated_ids(self) -> set:
        return set(self.__eliminated_ids)  # copy

    # ------------------------------------------------------------------
    # Convenience
    # ------------------------------------------------------------------

    def is_known(self, event_id: int) -> bool:
        return self.is_archived(event_id) or self.is_eliminated(event_id)