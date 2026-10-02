from collections import deque

from src.models.AttetionStatus import AttetionStatus
from src.controllers.EventQueries import EventQueries


def tree_shape(root) -> dict:
    """Height (empty tree = -1, leaf = 0), leaf count and node count."""
    if root is None:
        return {"height": -1, "leaves": 0, "nodes": 0}
    leaves = nodes = max_depth = 0
    stack = [(root, 0)]
    while stack:
        node, depth = stack.pop()
        nodes += 1
        max_depth = max(max_depth, depth)
        left, right = node.getLeft(), node.getRight()
        if left is None and right is None:
            leaves += 1
        if right is not None:
            stack.append((right, depth + 1))
        if left is not None:
            stack.append((left, depth + 1))
    return {"height": max_depth, "leaves": leaves, "nodes": nodes}


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


def build_indicators(scenery) -> dict:
    by_priority = {1: 0, 2: 0, 3: 0}
    pending = 0
    for event in scenery.active_events.values():
        by_priority[event.getPriority()] += 1
        if event.getStatus() == AttetionStatus.PENDING:
            pending += 1

    costly = EventQueries().high_priority_costly_access(
        scenery.tree.getRoot(), scenery.active_events, scenery.access_depth_limit)

    return {
        "active": len(scenery.active_events),
        "historic": len(scenery.archived_events),
        "by_priority": by_priority,
        "pending": pending,
        "costly_access": len(costly.events),
        **tree_shape(scenery.tree.getRoot()),
        **scenery.metrics.to_dict(),
    }