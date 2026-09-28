"""Point 3: manual event creation (range validation, review 1, pending)."""
import pytest
from datetime import timedelta

from src.controllers.AttetionStatus import AttetionStatus
from src.models.Key import Key
from tests.helpers import CLOCK_START, add_event, build_scenery


def create(scenery, **overrides):
    args = dict(event_id=1, magnitude=5.0, depth_km=10.0, epicenter_x=100.0,
                epicenter_y=100.0, occurred_at=CLOCK_START - timedelta(hours=1),
                origin_station_id="EST1")
    args.update(overrides)
    return scenery.create_event(**args)


def test_valid_event_is_registered_pending_review_one():
    scenery = build_scenery()
    result = create(scenery)
    assert result.success
    event = scenery.active_events[1]
    assert event is result.event
    assert event.getStatus() == AttetionStatus.PENDING
    assert event.getReview() == 1
    assert event.getStations() == ["EST1"]
    assert event.getPriority() == 2  # 5.0, not in a populated zone


def test_event_is_inserted_in_tree_with_its_key():
    scenery = build_scenery()
    add_event(scenery, 1, 5.0)
    node = scenery.tree.search(Key(2, 5.0, 1))
    assert node is not None
    assert node.getEventId() == 1


def test_creation_is_pushed_to_undo_stack():
    scenery = build_scenery()
    add_event(scenery, 42, 5.0)
    assert scenery.undo_stack.peek() == ("CREATION", 42)


@pytest.mark.parametrize("field, value", [
    ("event_id", 1), ("event_id", 999999),
    ("magnitude", -2.0), ("magnitude", 10.0),
    ("depth_km", 0.0), ("depth_km", 700.0),
    ("epicenter_x", 0.0), ("epicenter_x", 1000.0),
    ("epicenter_y", 0.0), ("epicenter_y", 1000.0),
])
def test_inclusive_range_limits_are_accepted(field, value):
    assert create(build_scenery(), **{field: value}).success


@pytest.mark.parametrize("field, value", [
    ("event_id", 0), ("event_id", 1000000),
    ("magnitude", -2.1), ("magnitude", 10.1),
    ("depth_km", -0.1), ("depth_km", 700.1),
    ("epicenter_x", -0.1), ("epicenter_x", 1000.1),
    ("epicenter_y", -0.1), ("epicenter_y", 1000.1),
])
def test_out_of_range_values_are_rejected(field, value):
    scenery = build_scenery()
    result = create(scenery, **{field: value})
    assert not result.success
    assert scenery.active_events == {}
    assert scenery.tree.getRoot() is None


@pytest.mark.parametrize("field", ["magnitude", "depth_km", "epicenter_x", "epicenter_y"])
def test_more_than_one_decimal_is_rejected(field):
    result = create(build_scenery(), **{field: 5.55})
    assert not result.success
    assert "one decimal" in result.message


def test_duplicate_active_id_is_rejected_and_first_event_kept():
    scenery = build_scenery()
    first = add_event(scenery, 1, 5.0)
    result = create(scenery, magnitude=7.0)
    assert not result.success
    assert "already in use" in result.message
    assert scenery.active_events[1] is first


def test_eliminated_id_cannot_be_reused():
    scenery = build_scenery()
    scenery.eliminated_ids.add(5)
    assert not create(scenery, event_id=5).success


def test_archived_id_cannot_be_reused():
    # Spec: archived events keep their identity, data and associations in the history.
    scenery = build_scenery()
    add_event(scenery, 5, 5.0)
    scenery.archived_events[5] = scenery.active_events.pop(5)
    assert not create(scenery, event_id=5).success


def test_unknown_station_is_rejected():
    result = create(build_scenery(), origin_station_id="NOPE")
    assert not result.success
    assert "Unknown station" in result.message


def test_future_occurrence_is_rejected_but_equal_to_clock_is_accepted():
    scenery = build_scenery()
    assert not create(scenery, occurred_at=CLOCK_START + timedelta(seconds=1)).success
    assert create(scenery, occurred_at=CLOCK_START).success


def test_several_errors_are_reported_together():
    result = create(build_scenery(), magnitude=11.0, depth_km=800.0)
    assert not result.success
    assert "Magnitude" in result.message and "Depth" in result.message
