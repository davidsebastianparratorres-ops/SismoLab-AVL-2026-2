import json

from src.controllers.PriorityCalculator import calculate_priority
from src.controllers.ZoneLocator import belongs_to_populated_zone
from src.controllers.EventValidator import validate_ranges
from src.models.Node import Node
from src.models.Key import Key
from src.models.Event import Event
from src.models.Point import Point


class LoadResult:
    """Success: carries the tree root and the events dict.
    Failure: carries the list of problems found; root/events stay None so
    a partial build is never mistaken for a valid one."""

    def __init__(self, success: bool, errors: list = None, root=None, events: dict = None):
        self.success = success
        self.errors = errors if errors is not None else []
        self.root = root
        self.events = events


class TopologyIO:
    """Reads and writes the topology JSON format:
    { "tipo": "TOPOLOGIA", "arbol": {...nested nodes...}, "eventos": {...by id...} }

    Load and save live together on purpose: both depend on the exact same
    schema, so keeping them in one place means that schema is defined once,
    not duplicated across two files that could quietly drift apart.
    """

    # ------------------------------------------------------------------
    # Load
    # ------------------------------------------------------------------

    def load(self, filepath: str, zones: list) -> LoadResult:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        errors = []
        events, event_errors = self.__build_events(data.get("eventos", {}), zones)
        errors.extend(event_errors)

        seen_ids = set()
        root, tree_errors = self.__build_node(data.get("arbol"), events, seen_ids, parent=None)
        errors.extend(tree_errors)

        for orphan_id in set(events.keys()) - seen_ids:
            errors.append(f"Event {orphan_id} exists in 'eventos' but has no node in 'arbol'.")

        if not errors:
            errors.extend(self.__validate_bst_order(root))
            errors.extend(self.__validate_stored_metadata(root))

        if errors:
            return LoadResult(success=False, errors=errors)
        return LoadResult(success=True, root=root, events=events)

    def __build_events(self, raw_events: dict, zones: list) -> tuple:
        events, errors = {}, []

        for id_str, raw in raw_events.items():
            event_id = int(id_str)
            range_errors = validate_ranges(
                event_id, raw["magnitude"], raw["depth"],
                raw["epicenter"]["x"], raw["epicenter"]["y"],
            )
            if range_errors:
                errors.extend(range_errors)
                continue

            epicenter = Point(raw["epicenter"]["x"], raw["epicenter"]["y"])
            is_populated = belongs_to_populated_zone(epicenter, zones)
            expected_priority = calculate_priority(raw["magnitude"], raw["depth"], is_populated)

            if expected_priority != raw["priority"]:
                errors.append(
                    f"Event {event_id}: stored priority ({raw['priority']}) does not "
                    f"match the recalculated priority ({expected_priority})."
                )
                continue

            events[event_id] = Event(
                event_id=event_id,
                magnitude=raw["magnitude"],
                epicenter=epicenter,
                depth=raw["depth"],
                status=raw["status"],
                associatedEvents=list(raw.get("associatedEvents", [])),
                stations=list(raw.get("stations", [])),
                ocurredAt=raw["ocurredAt"],
                priority=raw["priority"],
                review=raw["review"],
            )

        return events, errors

    def __build_node(self, raw_node, events: dict, seen_ids: set, parent) -> tuple:
        if raw_node is None:
            return None, []

        event_id = raw_node["event_id"]
        if event_id not in events:
            return None, [f"Node references event_id {event_id}, which is not in 'eventos'."]
        if event_id in seen_ids:
            return None, [f"Event {event_id} appears in more than one tree position."]
        seen_ids.add(event_id)

        raw_key = raw_node["key"]
        if raw_key["identifier"] != event_id:
            return None, [
                f"Node event_id ({event_id}) does not match its own key identifier "
                f"({raw_key['identifier']})."
            ]

        node = Node(Key(raw_key["priority"], raw_key["magnitude"], raw_key["identifier"]), event_id)
        node.setParent(parent)
        node.setHeight(raw_node.get("altura"))
        node.setBalanceFactor(raw_node.get("factorEquilibrio"))

        left, left_errors = self.__build_node(raw_node.get("izquierdo"), events, seen_ids, node)
        right, right_errors = self.__build_node(raw_node.get("derecho"), events, seen_ids, node)
        node.setLeft(left)
        node.setRight(right)

        return node, left_errors + right_errors

    def __validate_bst_order(self, node, lower=None, upper=None) -> list:
        # Checked against every ancestor's bound, not just the immediate
        # parent — section 14 requires this, a local check is not enough.
        if node is None:
            return []
        key = node.getKey().as_tuple
        errors = []
        if lower is not None and key <= lower:
            errors.append(f"Event {node.getEventId()}: key {key} violates BST order.")
        if upper is not None and key >= upper:
            errors.append(f"Event {node.getEventId()}: key {key} violates BST order.")
        errors += self.__validate_bst_order(node.getLeft(), lower, key)
        errors += self.__validate_bst_order(node.getRight(), key, upper)
        return errors

    def __validate_stored_metadata(self, root) -> list:
        errors = []

        def compute(node):
            if node is None:
                return -1  # height of an empty subtree (section 14)
            left_h = compute(node.getLeft())
            right_h = compute(node.getRight())
            real_height = 1 + max(left_h, right_h)
            real_bf = left_h - right_h

            if node.getHeight() is not None and node.getHeight() != real_height:
                errors.append(f"Event {node.getEventId()}: stored height does not match the real one.")
            if node.getBalanceFactor() is not None and node.getBalanceFactor() != real_bf:
                errors.append(f"Event {node.getEventId()}: stored balance factor does not match the real one.")
            return real_height

        compute(root)
        return errors

    # ------------------------------------------------------------------
    # Save
    # ------------------------------------------------------------------

    def save(self, root, events: dict, filepath: str) -> None:
        data = {
            "tipo": "TOPOLOGIA",
            "arbol": self.__node_to_dict(root),
            "eventos": self.__events_to_dict(events),
        }
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

    def __node_to_dict(self, node):
        if node is None:
            return None
        key = node.getKey()
        return {
            "event_id": node.getEventId(),
            "key": {"priority": key.priority, "magnitude": key.magnitude, "identifier": key.identifier},
            "altura": node.getHeight(),
            "factorEquilibrio": node.getBalanceFactor(),
            "izquierdo": self.__node_to_dict(node.getLeft()),
            "derecho": self.__node_to_dict(node.getRight()),
        }

    def __events_to_dict(self, events: dict) -> dict:
        return {
            str(event_id): {
                "magnitude": event.getMagnitude(),
                "depth": event.getDepth(),
                "epicenter": {"x": event.getEpicenter().getX(), "y": event.getEpicenter().getY()},
                "status": event.getStatus(),
                "associatedEvents": list(event.getAssociatedEvents()),
                "stations": list(event.getStations()),
                "ocurredAt": event.getOcurredAt(),
                "priority": event.getPriority(),
                "review": event.getReview(),
            }
            for event_id, event in events.items()
        }