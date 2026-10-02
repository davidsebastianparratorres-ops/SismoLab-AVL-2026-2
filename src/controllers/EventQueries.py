from src.models.AttetionStatus import AttetionStatus
from src.models.EventStatus import EventStatus
from src.models.Key import Key
from src.dto.QueryResult import QueryResult, CostlyAccessEntry, AssociationsSummary, EventDetail
from src.models.SimulationClock import parse_iso_utc


def _as_datetime(value):
    """occurred_at may be stored as a datetime or as an ISO 8601 string,
    depending on where the event came from. This normalizes either into
    a comparable datetime so range queries work regardless of the source."""
    return parse_iso_utc(value) if isinstance(value, str) else value


class EventQueries:
    """Section 11 queries over the active AVL.

    All tree traversals use an explicit stack, never recursion, for the
    same reason as TreeAuditor: in stress mode the tree can degenerate
    into a chain of thousands of nodes and a recursive walk would hit
    Python's recursion limit exactly when the tree is at its worst.
    """

    # ------------------------------------------------------------------
    # Query 1: first k pending events, in descending order of K.
    # ------------------------------------------------------------------
    def top_k_pending(self, root, active_events: dict, k: int) -> QueryResult:
        """
        Cost: mirror of the classic iterative inorder walk (right, node,
        left instead of left, node, right) gives DESCENDING order one node
        at a time, and stops as soon as k pending events are found. In the
        worst case (few pending events hidden behind many reviewed ones)
        it still visits almost every node, so this is NOT logarithmic.
        """
        if k <= 0:
            return QueryResult([], 0, "k debe ser un entero positivo.")

        found = []
        nodes_examined = 0
        stack = []
        current = root

        while (stack or current is not None) and len(found) < k:
            while current is not None:
                stack.append(current)
                current = current.getRight()

            current = stack.pop()
            nodes_examined += 1

            event = active_events.get(current.getEventId())
            if event is not None and event.getStatus() == AttetionStatus.PENDING:
                found.append(event)

            current = current.getLeft()

        message = f"Se encontraron {len(found)} evento(s) pendiente(s)."
        if len(found) < k:
            message += " (habÃ­a menos pendientes que los solicitados, se muestran todos)."
        return QueryResult(found, nodes_examined, message)

    # ------------------------------------------------------------------
    # Query 2a: events within an inclusive magnitude range.
    # ------------------------------------------------------------------
    def events_by_magnitude_range(self, root, active_events: dict,
                                   magnitude_min: float, magnitude_max: float) -> QueryResult:
        """
        Cost: the tree's key is K = (priority, magnitude, id) sorted
        FIRST by priority, magnitude only breaks ties. Two events with the
        same magnitude but different priority can end up anywhere in the
        tree relative to each other, so it cannot be pruned using a
        magnitude range: the ENTIRE tree must be visited in the worst
        case. This query is O(n), not logarithmic.
        """
        return self.__full_scan(root, active_events, lambda event:
            magnitude_min <= event.getMagnitude() <= magnitude_max)

    # ------------------------------------------------------------------
    # Query 2b: events with hypocenter depth <= limit, within a date range.
    # ------------------------------------------------------------------
    def events_by_depth_and_date_range(self, root, active_events: dict, depth_limit: float,
                                        date_min, date_max) -> QueryResult:
        """
        Cost: same reasoning as the magnitude query. Depth and date are
        not part of K at all, so nothing about their order is reflected
        in the tree's shape. Full scan, O(n) in the worst case.
        """
        date_min = _as_datetime(date_min)
        date_max = _as_datetime(date_max)

        def matches(event):
            occurred_at = _as_datetime(event.getOcurredAt())
            return event.getDepth_km() <= depth_limit and date_min <= occurred_at <= date_max

        return self.__full_scan(root, active_events, matches)

    # ------------------------------------------------------------------
    # Query 3: candidates and chosen reference for an event, plus the
    # events that use it as their reference (section 11, third bullet).
    #
    # This query does NOT compute candidates or the selection criterion
    # itself (that belongs to the associations module, section 7). It
    # receives two callbacks instead, so it works no matter how that
    # module ends up storing its data:
    #
    #   get_candidates(event) -> list of candidate events for `event`
    #   get_reference(event)  -> the chosen reference event, or None
    #
    # What THIS method builds on its own is the reverse index
    # (referenced_by), because that only requires scanning the catalogue,
    # not knowing the selection rule.
    # ------------------------------------------------------------------
    # Query: full detail of one event (current data, review, stations,
    # priority, key, status, node depth/height/balance factor, associations).
    # ------------------------------------------------------------------
    def event_detail(self, event_id: int, tree, active_events: dict, archived_events: dict,
                      eliminated_ids: set, get_candidates, get_reference) -> QueryResult:
        """Composes get_event's location logic, Tree.locate_node_info for the
        node's own depth/height/balance factor, and event_associations for
        the association summary - instead of duplicating any of their logic.

        get_candidates/get_reference: same adapter callables used by
        event_associations, e.g. lambdas wrapping AssociationManager's
        get_candidates_and_reference(event_id).
        """
        if event_id in eliminated_ids:
            return QueryResult([], 0, f"Event {event_id} was eliminated.")

        catalogue = {**active_events, **archived_events}
        event = catalogue.get(event_id)
        if event is None:
            return QueryResult([], 0, f"Event {event_id} does not exist.")

        is_active = event_id in active_events
        key_tuple = (event.getPriority(), event.getMagnitude(), event.getEventId())

        # Archived events leave the active AVL (section 7), so they simply
        # have no node, depth, height or balance factor to report.
        node_depth = node_height = balance_factor = None
        nodes_examined = 0
        if is_active:
            node_depth, node_height, balance_factor = tree.locate_node_info(Key(*key_tuple))
            nodes_examined = node_depth + 1 if node_depth is not None else 0

        association_result = self.event_associations(
            event_id, active_events, archived_events, get_candidates, get_reference)
        nodes_examined += association_result.nodes_examined

        detail = EventDetail(
            event=event,
            location_status=EventStatus.ACTIVE if is_active else EventStatus.ARCHIVED,
            key=key_tuple,
            node_depth=node_depth,
            node_height=node_height,
            balance_factor=balance_factor,
            associations=association_result.events[0],
        )
        return QueryResult([detail], nodes_examined, f"Event {event_id}: full detail retrieved.")

    # ------------------------------------------------------------------
    def event_associations(self, event_id: int, active_events: dict, archived_events: dict,
                            get_candidates, get_reference) -> QueryResult:
        catalogue = {**active_events, **archived_events}
        event = catalogue.get(event_id)
        if event is None:
            return QueryResult([], 0, f"El evento {event_id} no existe entre los activos o archivados.")

        candidates = get_candidates(event)
        reference = get_reference(event)

        referenced_by = []
        nodes_examined = 0
        for other_id, other_event in catalogue.items():
            nodes_examined += 1
            if other_id == event_id:
                continue
            
            # CORRECCIÓN: Comparar por getEventId() en lugar de la identidad física `is`
            other_ref = get_reference(other_event)
            if other_ref is not None and other_ref.getEventId() == event.getEventId():
                referenced_by.append(other_event)

        summary = AssociationsSummary(
            event=event,
            candidates=candidates,
            chosen_reference=reference,
            referenced_by=referenced_by,
        )
        message = (f"Evento {event_id}: {len(candidates)} candidato(s), "
                   f"{'con' if reference else 'sin'} referencia elegida, "
                   f"{len(referenced_by)} evento(s) lo usan como referencia.")
        return QueryResult([summary], nodes_examined, message)

    # ------------------------------------------------------------------
    # Query 4: high-priority events with costly access.
    # ------------------------------------------------------------------
    def high_priority_costly_access(self, root, active_events: dict, depth_limit: int) -> QueryResult:
        """
        A high-priority (3) event is "costly access" when its node depth
        in the tree is strictly greater than depth_limit (L, section 9).

        For each one found, the search cost by key is (node depth + 1),
        exactly as section 9 defines it: the number of nodes visited from
        the root to locate an existing event.

        Cost: finding ALL high-priority events with costly access requires
        a full scan, O(n) in the worst case there is no way to prune by
        K, because priority alone does not determine depth in the tree
        (the AVL only guarantees the BST order, not where each priority
        group physically sits).
        """
        results = []
        nodes_examined = 0

        if root is None:
            return QueryResult([], 0, "El arbol esat vacio.")

        # Each stack entry carries (node, depth). The root has depth 0
        # (section 9).
        stack = [(root, 0)]
        while stack:
            node, depth = stack.pop()
            nodes_examined += 1

            event = active_events.get(node.getEventId())
            if event is not None and event.getPriority() == 3 and depth > depth_limit:
                search_cost = depth + 1
                results.append(CostlyAccessEntry(event, depth, search_cost))

            if node.getRight() is not None:
                stack.append((node.getRight(), depth + 1))
            if node.getLeft() is not None:
                stack.append((node.getLeft(), depth + 1))

        message = f"Se encontraron {len(results)} evento(s) de prioridad alta con acceso costoso (L={depth_limit})."
        return QueryResult(results, nodes_examined, message)

    # ------------------------------------------------------------------
    # Shared helper for queries 2a and 2b: a full traversal.
    # ------------------------------------------------------------------
    def __full_scan(self, root, active_events: dict, matches) -> QueryResult:
        found = []
        nodes_examined = 0

        if root is None:
            return QueryResult([], 0, "El arbol esta vacio")

        stack = [root]
        while stack:
            node = stack.pop()
            nodes_examined += 1

            event = active_events.get(node.getEventId())
            if event is not None and matches(event):
                found.append(event)

            if node.getRight() is not None:
                stack.append(node.getRight())
            if node.getLeft() is not None:
                stack.append(node.getLeft())

        message = f"Se encontraron {len(found)} evento(s) que cumplen el criterio."
        return QueryResult(found, nodes_examined, message)
