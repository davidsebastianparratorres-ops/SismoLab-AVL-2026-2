"""Point 4: querying one event.

There is no single method that joins catalog + tree + associations, so the
`full_query` helper below stitches together the pieces that exist today.
"""
from src.controllers.AssociationManager import AssociationManager
from src.controllers.AttetionStatus import AttetionStatus
from src.controllers.EventStatus import EventStatus
from src.models.Key import Key
from tests.helpers import add_event, build_scenery


def full_query(scenery, manager, event_id):
    lookup = scenery.get_event(event_id)
    if lookup.event is None:
        return lookup.location_status, None
    event = lookup.event
    key = Key(event.getPriority(), event.getMagnitude(), event.getEventId())
    depth, height, balance = scenery.tree.locate_node_info(key)
    candidates, reference_id = manager.get_candidates_and_reference(event_id)
    return lookup.location_status, {
        "event": event, "key": key.as_tuple, "depth": depth, "height": height,
        "balance": balance, "candidates": candidates, "reference_id": reference_id,
    }


def balanced_three_node_scenery():
    """Root id10 (prio 2), left id5 (prio 1), right id20 (prio 3)."""
    scenery = build_scenery()
    add_event(scenery, 10, 5.0)   # priority 2
    add_event(scenery, 5, 3.0)    # priority 1
    add_event(scenery, 20, 6.5)   # priority 3
    return scenery


def test_active_event_shows_current_data():
    scenery = balanced_three_node_scenery()
    status, info = full_query(scenery, AssociationManager(scenery), 10)
    event = info["event"]
    assert status == EventStatus.ACTIVE
    assert (event.getMagnitude(), event.getDepth_km(), event.getPriority()) == (5.0, 10.0, 2)
    assert event.getReview() == 1
    assert event.getStatus() == AttetionStatus.PENDING
    assert event.getStations() == ["EST1"]
    assert info["key"] == (2, 5.0, 10)


def test_node_depth_height_and_balance_factor():
    scenery = balanced_three_node_scenery()
    manager = AssociationManager(scenery)
    assert full_query(scenery, manager, 10)[1]["depth"] == 0
    assert (full_query(scenery, manager, 10)[1]["height"], full_query(scenery, manager, 10)[1]["balance"]) == (1, 0)
    for leaf_id in (5, 20):
        info = full_query(scenery, manager, leaf_id)[1]
        assert (info["depth"], info["height"], info["balance"]) == (1, 0, 0)


def test_unbalanced_root_reports_positive_balance_factor():
    scenery = build_scenery()
    add_event(scenery, 10, 5.0)
    add_event(scenery, 5, 3.0)    # only a left child
    info = full_query(scenery, AssociationManager(scenery), 10)[1]
    assert (info["height"], info["balance"]) == (1, 1)


def test_reviewed_state_is_visible_in_query():
    scenery = balanced_three_node_scenery()
    scenery.mark_as_reviewed(10)
    info = full_query(scenery, AssociationManager(scenery), 10)[1]
    assert info["event"].getStatus() == AttetionStatus.REVIEWED


def test_query_shows_associations():
    scenery = build_scenery()
    add_event(scenery, 1, 6.0, hours_ago=10)
    add_event(scenery, 2, 4.0, hours_ago=2)
    manager = AssociationManager(scenery)
    manager.recalculate_all()
    info = full_query(scenery, manager, 2)[1]
    assert [e.getEventId() for e in info["candidates"]] == [1]
    assert info["reference_id"] == 1


def test_archived_eliminated_and_unknown_lookups():
    scenery = balanced_three_node_scenery()
    scenery.archived_events[5] = scenery.active_events.pop(5)
    scenery.active_events.pop(20)
    scenery.eliminated_ids.add(20)
    manager = AssociationManager(scenery)
    assert full_query(scenery, manager, 5)[0] == EventStatus.ARCHIVED
    assert full_query(scenery, manager, 20) == (EventStatus.ELIMINATED, None)
    assert full_query(scenery, manager, 999) == (EventStatus.UNKNOWN, None)


def test_locate_node_info_for_missing_key_returns_none_triplet():
    scenery = balanced_three_node_scenery()
    assert scenery.tree.locate_node_info(Key(3, 9.9, 999)) == (None, None, None)
