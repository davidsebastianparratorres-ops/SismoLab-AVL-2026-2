"""Point 1: event model and its data."""
from src.controllers.AttetionStatus import AttetionStatus
from src.models.Event import Event
from src.models.Key import Key
from src.models.Point import Point


def test_defaults():
    event = Event()
    assert event.getStatus() == AttetionStatus.PENDING
    assert event.getReview() == 1
    assert event.getStations() == []
    assert event.getAssociatedEvents() == []


def test_constructor_stores_every_field():
    epicenter = Point(10.5, 20.5)
    event = Event(event_id=7, magnitude=5.5, epicenter=epicenter, depth_km=12.5,
                  status=AttetionStatus.REVIEWED, stations=["EST1"],
                  ocurredAt="2026-01-01T00:00:00Z", priority=2, review=3,
                  associatedEvents=[1, 2])
    assert event.getEventId() == 7
    assert event.getMagnitude() == 5.5
    assert event.getEpicenter() is epicenter
    assert event.getDepth_km() == 12.5
    assert event.getStatus() == AttetionStatus.REVIEWED
    assert event.getStations() == ["EST1"]
    assert event.getOcurredAt() == "2026-01-01T00:00:00Z"
    assert event.getPriority() == 2
    assert event.getReview() == 3
    assert event.getAssociatedEvents() == [1, 2]


def test_hypocenter_depth_is_only_exposed_as_depth_km():
    event = Event(depth_km=33.3)
    assert event.getDepth_km() == 33.3
    assert not hasattr(event, "getDepth")


def test_setters_update_values():
    event = Event()
    event.setMagnitude(6.1)
    event.setDepth_km(5.0)
    event.setPriority(3)
    event.setReview(2)
    event.setStatus(AttetionStatus.REVIEWED)
    assert (event.getMagnitude(), event.getDepth_km(), event.getPriority(),
            event.getReview(), event.getStatus()) == (6.1, 5.0, 3, 2, AttetionStatus.REVIEWED)


def test_create_new_starts_pending_review_one_single_station():
    event = Event.create_new(event_id=1, magnitude=4.0, epicenter=Point(1.0, 2.0), depth_km=8.0,
                             ocurredAt="t", origin_station_id="EST1", priority=1)
    assert event.getStatus() == AttetionStatus.PENDING
    assert event.getReview() == 1
    assert event.getStations() == ["EST1"]
    assert event.getDepth_km() == 8.0
    assert event.getAssociatedEvents() == []


def test_default_lists_are_not_shared_between_instances():
    first, second = Event(), Event()
    first.getStations().append("EST1")
    first.getAssociatedEvents().append(9)
    assert second.getStations() == []
    assert second.getAssociatedEvents() == []


def test_key_orders_by_priority_then_magnitude_then_id():
    assert Key(1, 9.0, 99).as_tuple < Key(2, -2.0, 1).as_tuple
    assert Key(2, 4.5, 99).as_tuple < Key(2, 4.6, 1).as_tuple
    assert Key(2, 4.5, 1).as_tuple < Key(2, 4.5, 2).as_tuple


def test_key_from_event_uses_event_values():
    event = Event(event_id=5, magnitude=4.6, priority=2)
    assert Key.from_event(event).as_tuple == (2, 4.6, 5)


def test_point_distance_is_euclidean():
    assert Point(0.0, 0.0).distance_to(Point(3.0, 4.0)) == 5.0
