import json

from src.controllers.Topologyio import LoadResult
from src.models.AVL import AVL
from src.models.AttetionStatus import AttetionStatus
from src.models.Event import Event
from src.models.Key import Key
from src.models.Point import Point
from src.rules.EventRules import belongs_to_populated_zone, calculate_priority
from src.rules.EventValidator import validate_ranges


class InsertionIO:
    """Loads a sequence of events from JSON and inserts them one by one,
    in file order, into a tree.

    Unlike TopologyIO (which restores an already-built tree with its
    stored structure/height/balance factors), this is a raw incoming
    sequence: each event only carries its basic data, and priority/review/
    status are (re)computed fresh at insertion time, exactly like
    Scenery.create_event does for a single manual creation.

    Expected JSON shape:
    {
      "tipo": "INSERCION",
      "eventos": [
        {
          "event_id": 20, "magnitude": 5.0, "depth": 15.0,
          "epicenter": {"x": 200.0, "y": 300.0},
          "ocurredAt": "2026-09-07T10:00:00Z",
          "stations": ["EST-01"]
        },
        ...
      ]
    }
    "eventos" is a JSON array (not an id-keyed object like TopologyIO's),
    specifically because the array's order IS the insertion order that
    must be replayed - a dict's key order is an implementation detail
    nobody should have to rely on.

    tree: any Tree subclass instance (AVL() by default). Since AVL, BST
    and Tree all compare nodes through the same Key.as_tuple, calling
    load() once with an AVL() and once with a fresh BST() on the exact
    same file applies the identical comparator and the identical
    insertion order to both - the only difference left is whether the
    tree rebalances itself.
    """

    def load(self, filepath: str, zones: list = None, tree=None) -> LoadResult:
        zones = zones if zones is not None else []
        tree = tree if tree is not None else AVL()

        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        raw_events = data.get("eventos", [])
        errors = []
        events = {}
        seen_ids = set()

        for raw in raw_events:
            event_id = raw["event_id"]

            if event_id in seen_ids:
                errors.append(f"Event {event_id} appears more than once in the insertion sequence.")
                continue

            range_errors = validate_ranges(
                event_id, raw["magnitude"], raw["depth"],
                raw["epicenter"]["x"], raw["epicenter"]["y"],
            )
            if range_errors:
                errors.extend(range_errors)
                continue

            seen_ids.add(event_id)

            epicenter = Point(raw["epicenter"]["x"], raw["epicenter"]["y"])
            is_populated = belongs_to_populated_zone(epicenter, zones)
            priority = calculate_priority(raw["magnitude"], raw["depth"], is_populated)

            events[event_id] = Event(
                event_id=event_id,
                magnitude=raw["magnitude"],
                epicenter=epicenter,
                depth_km=raw["depth"],
                status=raw.get("status", AttetionStatus.PENDING),
                stations=list(raw.get("stations", [])),
                ocurredAt=raw["ocurredAt"],
                priority=priority,
                review=raw.get("review", 1),
            )

            if not errors:
                # Only mutate the tree while the sequence still looks
                # clean so far; once something is rejected we only report
                # errors, we never hand back a half-built tree.
                tree.insert(Key(priority, raw["magnitude"], event_id), event_id)

        if errors:
            return LoadResult(success=False, errors=errors)
        return LoadResult(success=True, root=tree.getRoot(), events=events)
