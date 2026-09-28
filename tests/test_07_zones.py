"""Point 7: populated / unpopulated zones and epicenter membership (edge cases)."""
import pytest

from src.controllers.EventRules import belongs_to_populated_zone
from src.models.Point import Point
from src.models.Zone import Zone
from tests.helpers import add_event, build_scenery

BOX = dict(x_min=100.0, x_max=200.0, y_min=300.0, y_max=400.0)


@pytest.mark.parametrize("x, y", [
    (150.0, 350.0),                      # interior
    (100.0, 350.0), (200.0, 350.0),      # left / right edges
    (150.0, 300.0), (150.0, 400.0),      # bottom / top edges
    (100.0, 300.0), (200.0, 400.0),      # corners
    (100.0, 400.0), (200.0, 300.0),
])
def test_boundary_points_belong_to_the_zone(x, y):
    assert Zone(**BOX).contains(Point(x, y))


@pytest.mark.parametrize("x, y", [
    (99.9, 350.0), (200.1, 350.0), (150.0, 299.9), (150.0, 400.1),
    (99.9, 299.9), (200.1, 400.1),
])
def test_points_just_outside_do_not_belong(x, y):
    assert not Zone(**BOX).contains(Point(x, y))


def test_populated_flag_defaults_to_false_and_is_settable():
    zone = Zone(**BOX)
    assert zone.populated is False and zone.getPopulated() is False
    zone.setPopulated(True)
    assert zone.populated is True


def test_inside_populated_zone():
    assert belongs_to_populated_zone(Point(150.0, 350.0), [Zone(**BOX, populated=True)])


def test_inside_unpopulated_zone_is_not_populated():
    assert not belongs_to_populated_zone(Point(150.0, 350.0), [Zone(**BOX, populated=False)])


def test_outside_every_zone_and_empty_list():
    zones = [Zone(**BOX, populated=True)]
    assert not belongs_to_populated_zone(Point(0.0, 0.0), zones)
    assert not belongs_to_populated_zone(Point(150.0, 350.0), [])


def test_overlapping_zones_populated_wins_regardless_of_order():
    populated = Zone(**BOX, populated=True)
    unpopulated = Zone(**BOX, populated=False)
    point = Point(150.0, 350.0)
    assert belongs_to_populated_zone(point, [unpopulated, populated])
    assert belongs_to_populated_zone(point, [populated, unpopulated])


def test_point_on_shared_border_of_two_zones_counts_for_the_populated_one():
    left = Zone(0.0, 100.0, 0.0, 100.0, populated=False)
    right = Zone(100.0, 200.0, 0.0, 100.0, populated=True)
    assert belongs_to_populated_zone(Point(100.0, 50.0), [left, right])


# Integration: the zone decides priority through create_event
def test_populated_zone_raises_priority_for_shallow_moderate_event():
    scenery = build_scenery([Zone(**BOX, populated=True)])
    assert add_event(scenery, 1, 5.0, depth_km=30.0, x=150.0, y=350.0).getPriority() == 3


def test_same_event_outside_zone_or_too_deep_stays_medium():
    scenery = build_scenery([Zone(**BOX, populated=True)])
    assert add_event(scenery, 1, 5.0, depth_km=30.0, x=0.0, y=0.0).getPriority() == 2
    assert add_event(scenery, 2, 5.0, depth_km=30.1, x=150.0, y=350.0).getPriority() == 2


def test_epicenter_on_zone_edge_counts_as_inside_for_priority():
    scenery = build_scenery([Zone(**BOX, populated=True)])
    assert add_event(scenery, 1, 5.0, depth_km=10.0, x=100.0, y=300.0).getPriority() == 3
