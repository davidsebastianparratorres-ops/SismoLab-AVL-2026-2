import json

from src.rules.EventRules import belongs_to_populated_zone, calculate_priority
from src.rules.EventValidator import validate_ranges
from src.controllers.TreeAuditor import TreeAuditor
from src.models.Node import Node
from src.models.Key import Key
from src.models.Event import Event
from src.models.Point import Point
from src.models.SimulationClock import parse_iso_utc, format_iso_utc


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

    def load(self, filepath: str, zones: list, stress_mode: bool = False) -> LoadResult:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        errors = []
        events, event_errors = self.__build_events(data.get("eventos", {}), zones)
        errors.extend(event_errors)

        seen_ids = set()
        root, tree_errors = self.__build_node(data.get("arbol"), events, seen_ids)
        errors.extend(tree_errors)

        for orphan_id in set(events.keys()) - seen_ids:
            errors.append(f"Event {orphan_id} exists in 'eventos' but has no node in 'arbol'.")

        if not errors:
            report = TreeAuditor().audit(root, events, stress_mode=stress_mode)
            errors.extend(f"[{issue.category}] Evento {issue.event_id}: {issue.message}" for issue in report.errors())

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

            try:
                occurred_at = parse_iso_utc(raw["ocurredAt"])
            except ValueError as error:
                errors.append(f"Event {event_id}: invalid ocurredAt — {error}")
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
                depth_km=raw["depth"],
                status=raw["status"],
                associatedEvents=list(raw.get("associatedEvents", [])),
                stations=list(raw.get("stations", [])),
                ocurredAt=occurred_at,
                priority=raw["priority"],
                review=raw["review"],
            )

        return events, errors

    def __build_node(self, raw_root, events: dict, seen_ids: set):
        if raw_root is None:
            return None, []

        errors = []
        root = None
        # Explicit stack instead of recursion: a stress-mode topology can be
        # a long degenerate chain of thousands of nodes, which would blow
        # Python's recursion limit right when loading matters most.
        stack = [(raw_root, None, None)]  # (raw_node, parent_node, side)

        while stack:
            raw, parent, side = stack.pop()
            if raw is None:
                continue

            event_id = raw["event_id"]
            if event_id not in events:
                errors.append(f"Node references event_id {event_id}, which is not in 'eventos'.")
                continue
            if event_id in seen_ids:
                errors.append(f"Event {event_id} appears in more than one tree position.")
                continue

            raw_key = raw["key"]
            if raw_key["identifier"] != event_id:
                errors.append(
                    f"Node event_id ({event_id}) does not match its own key identifier "
                    f"({raw_key['identifier']})."
                )
                continue
            seen_ids.add(event_id)

            node = Node(Key(raw_key["priority"], raw_key["magnitude"], raw_key["identifier"]), event_id)
            node.setParent(parent)
            node.setHeight(raw.get("altura"))
            node.setBalanceFactor(raw.get("factorEquilibrio"))

            if parent is None:
                root = node
            elif side == "left":
                parent.setLeft(node)
            else:
                parent.setRight(node)

            stack.append((raw.get("derecho"), node, "right"))
            stack.append((raw.get("izquierdo"), node, "left"))

        return root, errors

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

    def __node_to_dict(self, root):
        if root is None:
            return None

        root_dict = self.__node_shell(root)
        stack = [(root, root_dict)]

        while stack:
            node, node_dict = stack.pop()

            left = node.getLeft()
            if left is not None:
                left_dict = self.__node_shell(left)
                node_dict["izquierdo"] = left_dict
                stack.append((left, left_dict))

            right = node.getRight()
            if right is not None:
                right_dict = self.__node_shell(right)
                node_dict["derecho"] = right_dict
                stack.append((right, right_dict))

        return root_dict

    def __node_shell(self, node) -> dict:
        key = node.getKey()
        return {
            "event_id": node.getEventId(),
            "key": {"priority": key.priority, "magnitude": key.magnitude, "identifier": key.identifier},
            "altura": node.getHeight(),
            "factorEquilibrio": node.getBalanceFactor(),
            "izquierdo": None,
            "derecho": None,
        }

    def __events_to_dict(self, events: dict) -> dict:
        return {
            str(event_id): {
                "magnitude": event.getMagnitude(),
                "depth": event.getDepth_km(),
                "epicenter": {"x": event.getEpicenter().getX(), "y": event.getEpicenter().getY()},
                "status": event.getStatus(),
                "associatedEvents": list(event.getAssociatedEvents()),
                "stations": list(event.getStations()),
                "ocurredAt": format_iso_utc(event.getOcurredAt()),
                "priority": event.getPriority(),
                "review": event.getReview(),
            }
            for event_id, event in events.items()
        }