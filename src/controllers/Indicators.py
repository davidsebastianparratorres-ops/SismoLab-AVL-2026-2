from collections import deque

from src.models.AttetionStatus import AttetionStatus
from src.models.SimulationClock import ensure_datetime
from src.controllers.EventQueries import EventQueries


def tree_shape(root) -> dict:
    """Height (empty tree = -1, leaf = 0), leaf count and node count, plus the simulated
    cost of locating an event by its key (section 9: nodes visited = node depth + 1)."""
    if root is None:
        return {"height": -1, "max_depth": -1, "leaves": 0, "nodes": 0,
                "average_search_cost": 0.0, "max_search_cost": 0}
    leaves = nodes = max_depth = depth_sum = 0
    stack = [(root, 0)]
    while stack:
        node, depth = stack.pop()
        nodes += 1
        depth_sum += depth
        max_depth = max(max_depth, depth)
        left, right = node.getLeft(), node.getRight()
        if left is None and right is None:
            leaves += 1
        if right is not None:
            stack.append((right, depth + 1))
        if left is not None:
            stack.append((left, depth + 1))
    return {"height": max_depth, "max_depth": max_depth, "leaves": leaves, "nodes": nodes,
            "average_search_cost": (depth_sum + nodes) / nodes, "max_search_cost": max_depth + 1}


def traversals(root) -> dict:
    """Event ids in inorder, preorder, postorder and level order.
    All iterative: O(n) time, O(n) memory."""
    result = {"inorder": [], "preorder": [], "postorder": [], "levels": []}
    if root is None:
        return result

    # inorder
    stack, current = [], root
    while stack or current is not None:
        while current is not None:
            stack.append(current)
            current = current.getLeft()
        current = stack.pop()
        result["inorder"].append(current.getEventId())
        current = current.getRight()

    # preorder
    stack = [root]
    while stack:
        node = stack.pop()
        result["preorder"].append(node.getEventId())
        if node.getRight() is not None:
            stack.append(node.getRight())
        if node.getLeft() is not None:
            stack.append(node.getLeft())

    # postorder = reverse of (node, right, left)
    stack, reversed_order = [root], []
    while stack:
        node = stack.pop()
        reversed_order.append(node.getEventId())
        if node.getLeft() is not None:
            stack.append(node.getLeft())
        if node.getRight() is not None:
            stack.append(node.getRight())
    result["postorder"] = reversed_order[::-1]

    # level order
    queue = deque([root])
    while queue:
        node = queue.popleft()
        result["levels"].append(node.getEventId())
        if node.getLeft() is not None:
            queue.append(node.getLeft())
        if node.getRight() is not None:
            queue.append(node.getRight())

    return result


def _event_row(event, scenery):
    return {
        "id": event.getEventId(),
        "location": "Activo" if event.getEventId() in scenery.active_events else "Archivado",
        "magnitude": event.getMagnitude(),
        "depth_km": event.getDepth_km(),
        "priority": event.getPriority(),
        "review": event.getReview(),
        "attention": event.getStatus(),
        "occurred_at": ensure_datetime(event.getOcurredAt()),
        "epicenter": (event.getEpicenter().getX(), event.getEpicenter().getY()),
        "stations": list(event.getStations()),
    }


def reference_entries(scenery) -> list:
    """Every event that has a chosen reference (section 7), with both ends of the link and
    the two figures that justify it: hours between them (<= W) and distance (<= R)."""
    manager = scenery.association_manager
    rows = []
    for replica_id, association in sorted(manager.associations.items()):
        replica = manager._find_event_by_id(replica_id)
        reference = manager._find_event_by_id(association.reference_id)
        if replica is None or reference is None:
            continue
        hours = (ensure_datetime(replica.getOcurredAt()) - ensure_datetime(reference.getOcurredAt())
                 ).total_seconds() / 3600.0
        rows.append({
            "replica": _event_row(replica, scenery),
            "reference": _event_row(reference, scenery),
            "hours_apart": hours,
            "distance_km": replica.getEpicenter().distance_to(reference.getEpicenter()),
        })
    return rows


def archived_entries(scenery) -> list:
    """Events that are in the history right now (they keep identity, data and associations)."""
    manager = scenery.association_manager
    clock = scenery.simulation_clock.current_time
    rows = []
    for event_id, event in sorted(scenery.archived_events.items()):
        row = _event_row(event, scenery)
        stored = manager.associations.get(event_id)
        row["reference_id"] = stored.reference_id if stored is not None else None
        row["age_hours"] = (clock - ensure_datetime(event.getOcurredAt())).total_seconds() / 3600.0
        rows.append(row)
    return rows


def build_indicators(scenery) -> dict:
    by_priority = {1: 0, 2: 0, 3: 0}
    pending = reviewed = 0
    for event in scenery.active_events.values():
        by_priority[event.getPriority()] += 1
        if event.getStatus() == AttetionStatus.PENDING:
            pending += 1
        else:
            reviewed += 1

    root = scenery.tree.getRoot()
    costly = EventQueries().high_priority_costly_access(
        root, scenery.active_events, scenery.access_depth_limit)
    audit = scenery.verify_structure()
    counters = scenery.metrics.to_dict()

    return {
        "active": len(scenery.active_events),
        "historic": len(scenery.archived_events),
        "eliminated": len(scenery.eliminated_ids),
        "by_priority": by_priority,
        "pending": pending,
        "reviewed": reviewed,
        "costly_access": len(costly.events),
        "costly_entries": [(entry.event.getEventId(), entry.node_depth, entry.search_cost)
                           for entry in costly.events],
        "reference_entries": reference_entries(scenery),
        "archived_entries": archived_entries(scenery),
        "root_id": root.getEventId() if root is not None else None,
        "queued": len(scenery.queue),
        "with_reference": len(scenery.association_manager.associations),
        "imbalanced": audit.imbalanced_count,
        "max_imbalance": audit.max_imbalance,
        "avl_ok": audit.is_valid_avl,
        "stress_mode": bool(scenery.stress_mode),
        "elementary_rotations": counters["rotations_left"] + counters["rotations_right"],
        **tree_shape(root),
        **counters,
    }