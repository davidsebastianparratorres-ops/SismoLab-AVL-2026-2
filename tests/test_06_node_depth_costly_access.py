"""Point 6: node depth and the costly-access mark for high priority."""
import pytest

from src.controllers.AccesBudget import find_expensive_access_events, is_expensive_access
from src.controllers.EventQueries import EventQueries
from src.controllers.EventRules import search_cost
from tests.helpers import add_event, build_scenery


def high_priority_chain(length):
    """Ascending magnitudes, all priority 3 -> right-leaning chain (depths 0..length-1).
    Note: AVL does not rotate yet, so this is a plain BST chain."""
    scenery = build_scenery()
    for index in range(length):
        add_event(scenery, index + 1, 6.0 + index * 0.1)
    return scenery


def test_depths_of_a_chain_start_at_zero():
    scenery = high_priority_chain(5)
    assert scenery.tree.get_all_depths() == {1: 0, 2: 1, 3: 2, 4: 3, 5: 4}


def test_search_cost_is_depth_plus_one():
    depths = high_priority_chain(3).tree.get_all_depths()
    assert search_cost(3, depths) == 3
    assert search_cost(1, depths) == 1
    assert search_cost(999, depths) is None


def test_default_limit_is_three():
    assert build_scenery().access_depth_limit == 3


@pytest.mark.parametrize("depth, limit, expected", [
    (3, 3, False),   # equal to L is NOT costly (strictly greater)
    (4, 3, True),
    (0, 0, False),
    (1, 0, True),
])
def test_boundary_of_the_mark(depth, limit, expected):
    scenery = build_scenery()
    event = add_event(scenery, 1, 7.0)
    assert is_expensive_access(event, depth, limit) is expected


def test_only_deep_high_priority_events_are_marked():
    scenery = high_priority_chain(6)   # depths 0..5, L=3 -> ids 5 and 6 costly
    found = find_expensive_access_events(scenery, scenery.tree)
    assert sorted((e.getEventId(), d) for e, d in found) == [(5, 4), (6, 5)]


def test_non_high_priority_events_are_never_marked_even_when_deep():
    scenery = build_scenery()
    for index in range(6):                       # priority 1 chain, magnitudes -1.0 .. -0.5
        add_event(scenery, index + 1, -1.0 + index * 0.1)
    assert max(scenery.tree.get_all_depths().values()) == 5
    assert find_expensive_access_events(scenery, scenery.tree) == []


def test_raising_the_limit_clears_marks():
    scenery = high_priority_chain(6)
    assert scenery.set_access_depth_limit(5).success
    assert find_expensive_access_events(scenery, scenery.tree) == []


def test_negative_limit_is_rejected_and_keeps_previous_value():
    scenery = build_scenery()
    assert not scenery.set_access_depth_limit(-1).success
    assert scenery.access_depth_limit == 3


def test_query_module_agrees_with_access_budget_module():
    scenery = high_priority_chain(6)
    budget = {(e.getEventId(), d) for e, d in find_expensive_access_events(scenery, scenery.tree)}
    result = EventQueries().high_priority_costly_access(
        scenery.tree.getRoot(), scenery.active_events, scenery.access_depth_limit)
    queried = {(entry.event.getEventId(), entry.node_depth) for entry in result.events}
    assert budget == queried
    assert all(entry.search_cost == entry.node_depth + 1 for entry in result.events)


def test_empty_tree_has_no_costly_events():
    scenery = build_scenery()
    assert find_expensive_access_events(scenery, scenery.tree) == []
    assert EventQueries().high_priority_costly_access(None, {}, 3).events == []


def test_parameter_l_drives_the_access_limit():
    scenery = build_scenery()
    assert scenery.update_parameters(l=5).success
    assert scenery.access_depth_limit == 5
    assert scenery.parameters.l == 5


def test_set_access_depth_limit_writes_to_simulation_parameters():
    scenery = build_scenery()
    scenery.set_access_depth_limit(6)
    assert scenery.parameters.l == 6


def test_non_integer_limit_is_rejected():
    scenery = build_scenery()
    assert not scenery.set_access_depth_limit(2.5).success
    assert scenery.access_depth_limit == 3
