from src.models.AttetionStatus import AttetionStatus
from src.models.EventStatus import EventStatus
from src.models.Key import Key
from src.dto.QueryResult import QueryResult, CostlyAccessEntry, AssociationsSummary, EventDetail
from src.models.SimulationClock import  ensure_datetime


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
            message += " (Habi­a menos pendientes que los solicitados, se muestran todos)."
        return QueryResult(found, nodes_examined, message)

    # ------------------------------------------------------------------
    # Query 2a: events within an inclusive magnitude range.
    # ------------------------------------------------------------------

    def events_by_magnitude_range(self, root, active_events: dict,
                               magnitude_min: float, magnitude_max: float) -> QueryResult:
        """
        The condition magnitude_min <= M <= magnitude_max is, for each priority
        p in (1, 2, 3), one CONTIGUOUS interval of keys K = (P, M, I):
        [(p, min, 0), (p, max, 999999)]. Each stack entry carries the open key
        interval (lo, hi) that its subtree must live in (inherited from ALL
        ancestors); if that interval touches none of the three, the whole
        subtree is discarded without being visited.
        Cost: O(h + k) on a balanced AVL (h = O(log n), k = matches);
        O(n) worst case on a degenerate (stress mode) tree.
        """
        if magnitude_min > magnitude_max:
            return QueryResult([], 0, "El minimo no puede ser mayor que el maximo.")
        if root is None:
            return QueryResult([], 0, "El arbol esta vacio")

        intervals = [((p, magnitude_min, 0), (p, magnitude_max, 999999)) for p in (1, 2, 3)]

        def may_contain(lo, hi):
            # Conservative test: only discards when certain.
            return any((lo is None or lo < end) and (hi is None or start < hi)
                    for start, end in intervals)

        found = []
        nodes_examined = 0
        stack = [(root, None, None)]  # (node, lo, hi); None = unbounded
        while stack:
            node, lo, hi = stack.pop()
            nodes_examined += 1
            key = node.getKey().as_tuple

            event = active_events.get(node.getEventId())
            if event is not None and magnitude_min <= event.getMagnitude() <= magnitude_max:
                found.append(event)

            right, left = node.getRight(), node.getLeft()
            if right is not None and may_contain(key, hi):
                stack.append((right, key, hi))
            if left is not None and may_contain(lo, key):
                stack.append((left, lo, key))

        message = f"Se encontraron {len(found)} evento(s) que cumplen el criterio."
        return QueryResult(found, nodes_examined, message)

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
        date_min = ensure_datetime(date_min)
        date_max = ensure_datetime(date_max)

        def matches(event):
            occurred_at = ensure_datetime(event.getOcurredAt())
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
        High-priority (3) events whose node depth is strictly greater than L.
        Search cost by key = depth + 1 (section 9).

        Safe pruning by K:
        - Left subtree of a node with P < 3: its keys are smaller, so its
        priorities are <= P < 3. It cannot contain any priority-3 event.
        - A child at depth d with stored height h has its deepest descendant
        at depth d + h; if d + h <= L nothing below can exceed L.
        Cost: O(n) worst case (e.g. a stress-mode chain of priority-3 nodes),
        usually far fewer nodes on a balanced AVL.
        """
        if root is None:
            return QueryResult([], 0, "El arbol esta vacio.")

        def can_exceed_limit(child, child_depth):
            height = child.getHeight()
            return height is None or child_depth + height > depth_limit

        results = []
        nodes_examined = 0
        stack = [(root, 0)]
        while stack:
            node, depth = stack.pop()
            nodes_examined += 1

            event = active_events.get(node.getEventId())
            if event is not None and event.getPriority() == 3 and depth > depth_limit:
                results.append(CostlyAccessEntry(event, depth, depth + 1))

            right, left = node.getRight(), node.getLeft()
            if right is not None and can_exceed_limit(right, depth + 1):
                stack.append((right, depth + 1))
            if left is not None and node.getKey().priority >= 3 and can_exceed_limit(left, depth + 1):
                stack.append((left, depth + 1))

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
