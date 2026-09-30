from src.controllers.PriorityCalculator import calculate_priority
from src.controllers.ZoneLocator import belongs_to_populated_zone
from src.controllers.AttetionStatus import AttetionStatus


class ArchiveManager:

    def __init__(self, historic):
        self.__historic = historic

    def reactivate(self, event_id: int, magnitude, depth, epicenter, ocurred_at, review, origin_station_id, zones):
        archived_event = self.__historic.reactivate(event_id)
        if archived_event is None:
            return None

        is_populated = belongs_to_populated_zone(epicenter, zones)
        priority = calculate_priority(magnitude, depth, is_populated)

        archived_event.setMagnitude(magnitude)
        archived_event.setDepth(depth)
        archived_event.setEpicenter(epicenter)
        archived_event.setOcurredAt(ocurred_at)
        archived_event.setPriority(priority)
        archived_event.setStatus(AttetionStatus.PENDING)
        archived_event.setReview(review)
        archived_event.setStations([origin_station_id])

        return archived_event

    def select_eligible_branch(self, root, active_events: dict, clock, t_hours: float):
        """Finds the eligible branch (all priority 1, age > T hours) with
        the most nodes — ties broken by deepest root, then highest event
        id. Read-only: never touches the tree, so the caller can show the
        preview before deciding to execute."""
        if root is None:
            return None, []

        preorder, depth = self.__traverse_with_depth(root)
        eligible, size = self.__compute_eligibility(preorder, active_events, clock, t_hours)

        candidates = [node for node in preorder if eligible[id(node)]]
        if not candidates:
            return None, []

        winner = max(candidates, key=lambda n: (size[id(n)], depth[id(n)], n.getEventId()))
        return winner, self.__collect_ids(winner)

    def __traverse_with_depth(self, root):
        preorder, depth = [], {}
        stack = [(root, 0)]
        while stack:
            node, d = stack.pop()
            preorder.append(node)
            depth[id(node)] = d
            if node.getRight() is not None:
                stack.append((node.getRight(), d + 1))
            if node.getLeft() is not None:
                stack.append((node.getLeft(), d + 1))
        return preorder, depth

    def __compute_eligibility(self, preorder, active_events, clock, t_hours):
        eligible, size = {}, {}
        for node in reversed(preorder):  # children resolved before their parent
            event = active_events[node.getEventId()]
            own_ok = event.getPriority() == 1 and clock.is_older_than(event.getOcurredAt(), t_hours)

            left, right = node.getLeft(), node.getRight()
            left_ok = left is None or eligible[id(left)]
            right_ok = right is None or eligible[id(right)]

            eligible[id(node)] = own_ok and left_ok and right_ok
            size[id(node)] = 1 + (size[id(left)] if left is not None else 0) + (size[id(right)] if right is not None else 0)
        return eligible, size

    def __collect_ids(self, node):
        ids, stack = [], [node]
        while stack:
            n = stack.pop()
            ids.append(n.getEventId())
            if n.getLeft() is not None:
                stack.append(n.getLeft())
            if n.getRight() is not None:
                stack.append(n.getRight())
        return ids