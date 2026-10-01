from src.models.Node import Node
from src.models.Key import Key
from src.models.Event import Event
from src.models.Point import Point


def flatten_tree(root) -> list:
    """Plain tuples instead of a generic deepcopy of the Node graph — no
    recursion (same reasoning as TopologyIO), and much lighter per node
    than deepcopy's reflection machinery. Entry: (event_id, priority,
    magnitude, identifier, height, balance_factor, left_id, right_id)."""
    if root is None:
        return []

    entries = []
    stack = [root]
    while stack:
        node = stack.pop()
        key = node.getKey()
        left, right = node.getLeft(), node.getRight()
        entries.append((
            node.getEventId(), key.priority, key.magnitude, key.identifier,
            node.getHeight(), node.getBalanceFactor(),
            left.getEventId() if left is not None else None,
            right.getEventId() if right is not None else None,
        ))
        if right is not None:
            stack.append(right)
        if left is not None:
            stack.append(left)

    return entries


def rebuild_tree(entries: list):
    if not entries:
        return None

    nodes = {}
    for event_id, priority, magnitude, identifier, height, bf, left_id, right_id in entries:
        node = Node(Key(priority, magnitude, identifier), event_id)
        node.setHeight(height)
        node.setBalanceFactor(bf)
        nodes[event_id] = (node, left_id, right_id)

    root_id = entries[0][0]  # first entry visited (preorder) is always the root
    for node, left_id, right_id in nodes.values():
        if left_id is not None:
            left_node = nodes[left_id][0]
            node.setLeft(left_node)
            left_node.setParent(node)
        if right_id is not None:
            right_node = nodes[right_id][0]
            node.setRight(right_node)
            right_node.setParent(node)

    return nodes[root_id][0]


def copy_event(event: Event) -> Event:
    # Event is flat (no cycles), so a direct field-by-field copy is cheap
    # and needs no recursion at all.
    epicenter = event.getEpicenter()
    return Event(
        event_id=event.getEventId(),
        magnitude=event.getMagnitude(),
        epicenter=Point(epicenter.getX(), epicenter.getY()),
        depth_km=event.getDepth_km(),
        status=event.getStatus(),
        stations=list(event.getStations()),
        ocurredAt=event.getOcurredAt(),
        priority=event.getPriority(),
        review=event.getReview(),
        associatedEvents=list(event.getAssociatedEvents()),
    )