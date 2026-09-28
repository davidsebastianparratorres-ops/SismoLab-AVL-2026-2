"""Point 8: associations between events (candidates, deterministic choice, recalculation)."""
import pytest

from src.controllers.AssociationManager import AssociationManager
from src.controllers.EventQueries import EventQueries
from tests.helpers import add_event, build_scenery


def ids(events):
    return sorted(event.getEventId() for event in events)


def reference_of(manager, event_id):
    association = manager.associations.get(event_id)
    return None if association is None else association.reference_id


# ---------------------------------------------------------------- candidates
def test_earlier_and_stronger_event_nearby_is_a_candidate():
    scenery = build_scenery()
    add_event(scenery, 1, 6.0, hours_ago=10)
    target = add_event(scenery, 2, 4.0, hours_ago=2)
    assert ids(AssociationManager(scenery).find_candidates(target)) == [1]


def test_equal_or_lower_magnitude_is_not_a_candidate():
    scenery = build_scenery()
    add_event(scenery, 1, 4.0, hours_ago=10)   # equal
    add_event(scenery, 3, 3.0, hours_ago=10)   # lower
    target = add_event(scenery, 2, 4.0, hours_ago=2)
    assert AssociationManager(scenery).find_candidates(target) == []


def test_same_time_or_later_event_is_not_a_candidate():
    scenery = build_scenery()
    add_event(scenery, 1, 6.0, hours_ago=2)    # same instant
    add_event(scenery, 3, 6.0, hours_ago=1)    # later
    target = add_event(scenery, 2, 4.0, hours_ago=2)
    assert AssociationManager(scenery).find_candidates(target) == []


def test_event_is_never_its_own_candidate():
    scenery = build_scenery()
    target = add_event(scenery, 1, 6.0)
    assert AssociationManager(scenery).find_candidates(target) == []


def test_time_window_is_inclusive():
    scenery = build_scenery()
    add_event(scenery, 1, 6.0, hours_ago=50)   # exactly 48 h before target
    target = add_event(scenery, 2, 4.0, hours_ago=2)
    manager = AssociationManager(scenery)
    scenery.update_parameters(w=48.0)
    assert ids(manager.find_candidates(target)) == [1]
    scenery.update_parameters(w=47.9)
    assert manager.find_candidates(target) == []


def test_distance_limit_is_inclusive():
    scenery = build_scenery()
    add_event(scenery, 1, 6.0, x=100.0, y=100.0, hours_ago=10)
    target = add_event(scenery, 2, 4.0, x=103.0, y=104.0, hours_ago=2)   # 3-4-5 triangle
    manager = AssociationManager(scenery)
    scenery.update_parameters(r=5.0)
    assert ids(manager.find_candidates(target)) == [1]
    scenery.update_parameters(r=4.9)
    assert manager.find_candidates(target) == []


def test_archived_events_are_eligible_and_eliminated_are_not():
    scenery = build_scenery()
    add_event(scenery, 1, 6.0, hours_ago=10)
    add_event(scenery, 3, 6.5, hours_ago=10)
    target = add_event(scenery, 2, 4.0, hours_ago=2)
    scenery.archived_events[1] = scenery.active_events.pop(1)
    scenery.active_events.pop(3)
    scenery.eliminated_ids.add(3)
    assert ids(AssociationManager(scenery).find_candidates(target)) == [1]


# ------------------------------------------------- deterministic selection
def pick(scenery, target_id):
    manager = AssociationManager(scenery)
    manager.recalculate_all()
    return reference_of(manager, target_id)


def test_no_candidates_means_no_reference():
    scenery = build_scenery()
    add_event(scenery, 1, 4.0)
    assert pick(scenery, 1) is None


def test_highest_magnitude_wins():
    scenery = build_scenery()
    add_event(scenery, 1, 5.0, hours_ago=5)
    add_event(scenery, 2, 6.0, hours_ago=20)
    add_event(scenery, 9, 3.0, hours_ago=1)
    assert pick(scenery, 9) == 2


def test_tie_on_magnitude_closest_in_time_wins():
    scenery = build_scenery()
    add_event(scenery, 1, 5.0, hours_ago=20)
    add_event(scenery, 2, 5.0, hours_ago=5)
    add_event(scenery, 9, 3.0, hours_ago=1)
    assert pick(scenery, 9) == 2


def test_tie_on_magnitude_and_time_closest_in_space_wins():
    scenery = build_scenery()
    add_event(scenery, 1, 5.0, x=500.0, y=530.0, hours_ago=5)
    add_event(scenery, 2, 5.0, x=500.0, y=510.0, hours_ago=5)
    add_event(scenery, 9, 3.0, x=500.0, y=500.0, hours_ago=1)
    assert pick(scenery, 9) == 2


def test_full_tie_lowest_id_wins_independent_of_creation_order():
    for creation_order in ([7, 3], [3, 7]):
        scenery = build_scenery()
        for event_id in creation_order:
            x, y = (500.0, 510.0) if event_id == 7 else (510.0, 500.0)   # both at distance 10
            add_event(scenery, event_id, 5.0, x=x, y=y, hours_ago=5)
        add_event(scenery, 9, 3.0, x=500.0, y=500.0, hours_ago=1)
        assert pick(scenery, 9) == 3


# ------------------------------------------------------------ recalculation
def test_new_event_creates_association_after_recalculation():
    scenery = build_scenery()
    manager = AssociationManager(scenery)
    add_event(scenery, 2, 4.0, hours_ago=2)
    manager.recalculate_all()
    assert manager.associations == {}
    add_event(scenery, 1, 6.0, hours_ago=10)
    manager.recalculate_all()
    assert reference_of(manager, 2) == 1


def test_better_new_candidate_replaces_reference():
    scenery = build_scenery()
    manager = AssociationManager(scenery)
    add_event(scenery, 1, 5.0, hours_ago=10)
    add_event(scenery, 2, 3.0, hours_ago=2)
    manager.recalculate_all()
    assert reference_of(manager, 2) == 1
    add_event(scenery, 3, 6.0, hours_ago=10)
    manager.recalculate_all()
    assert reference_of(manager, 2) == 3


def test_deleting_the_reference_falls_back_to_next_candidate_then_none():
    scenery = build_scenery()
    manager = AssociationManager(scenery)
    add_event(scenery, 1, 5.0, hours_ago=10)
    add_event(scenery, 3, 6.0, hours_ago=10)
    add_event(scenery, 2, 3.0, hours_ago=2)
    manager.recalculate_all()
    assert reference_of(manager, 2) == 3
    scenery.active_events.pop(3); scenery.eliminated_ids.add(3)
    manager.recalculate_all()
    assert reference_of(manager, 2) == 1
    scenery.active_events.pop(1); scenery.eliminated_ids.add(1)
    manager.recalculate_all()
    assert reference_of(manager, 2) is None


def test_correcting_reference_magnitude_below_target_drops_association():
    scenery = build_scenery()
    manager = AssociationManager(scenery)
    reference = add_event(scenery, 1, 6.0, hours_ago=10)
    add_event(scenery, 2, 4.0, hours_ago=2)
    manager.recalculate_all()
    assert reference_of(manager, 2) == 1
    reference.setMagnitude(3.0)
    manager.recalculate_all()
    assert reference_of(manager, 2) is None


def test_changing_parameters_w_and_r_updates_associations():
    scenery = build_scenery()
    manager = AssociationManager(scenery)
    add_event(scenery, 1, 6.0, x=100.0, y=100.0, hours_ago=30)
    add_event(scenery, 2, 4.0, x=130.0, y=100.0, hours_ago=2)   # 28 h, 30 km
    manager.recalculate_all()
    assert reference_of(manager, 2) == 1
    scenery.update_parameters(w=10.0)
    manager.recalculate_all()
    assert reference_of(manager, 2) is None
    scenery.update_parameters(w=48.0, r=20.0)
    manager.recalculate_all()
    assert reference_of(manager, 2) is None
    scenery.update_parameters(r=40.0)
    manager.recalculate_all()
    assert reference_of(manager, 2) == 1


def test_recalculate_for_removed_event_drops_its_stored_association():
    scenery = build_scenery()
    manager = AssociationManager(scenery)
    add_event(scenery, 1, 6.0, hours_ago=10)
    add_event(scenery, 2, 4.0, hours_ago=2)
    manager.recalculate_all()
    scenery.active_events.pop(2); scenery.eliminated_ids.add(2)
    manager.recalculate_for_event(2)
    assert 2 not in manager.associations


def test_recalculate_all_drops_association_of_a_deleted_replica():
    scenery = build_scenery()
    manager = AssociationManager(scenery)
    add_event(scenery, 1, 6.0, hours_ago=10)
    add_event(scenery, 2, 4.0, hours_ago=2)
    manager.recalculate_all()
    scenery.active_events.pop(2); scenery.eliminated_ids.add(2)
    manager.recalculate_all()
    assert 2 not in manager.associations


def test_manager_follows_scenery_parameters():
    scenery = build_scenery()
    manager = AssociationManager(scenery)
    assert (manager.max_hours, manager.max_distance_km) == (48.0, 40.0)   # defaults
    scenery.update_parameters(w=10.0, r=5.0)
    assert (manager.max_hours, manager.max_distance_km) == (10.0, 5.0)


def test_recalculate_all_also_drops_stale_association_when_reference_is_deleted():
    scenery = build_scenery()
    manager = AssociationManager(scenery)
    add_event(scenery, 1, 6.0, hours_ago=10)
    add_event(scenery, 2, 4.0, hours_ago=2)
    manager.recalculate_all()
    scenery.active_events.pop(1); scenery.eliminated_ids.add(1)
    manager.recalculate_all()
    assert manager.associations == {}


def test_recalculate_all_keeps_associations_of_archived_replicas():
    scenery = build_scenery()
    manager = AssociationManager(scenery)
    add_event(scenery, 1, 6.0, hours_ago=10)
    add_event(scenery, 2, 4.0, hours_ago=2)
    manager.recalculate_all()
    scenery.archived_events[2] = scenery.active_events.pop(2)
    manager.recalculate_all()
    assert reference_of(manager, 2) == 1


# ------------------------------------------------------------ reverse index
def test_events_referencing_and_query_summary():
    scenery = build_scenery()
    manager = AssociationManager(scenery)
    add_event(scenery, 1, 6.0, hours_ago=10)
    add_event(scenery, 2, 4.0, hours_ago=3)
    add_event(scenery, 3, 3.0, hours_ago=2)
    manager.recalculate_all()
    assert sorted(manager.get_events_referencing(1)) == [2, 3]
    assert manager.get_events_referencing(3) == []

    def get_candidates(event):
        return manager.get_candidates_and_reference(event.getEventId())[0]

    def get_reference(event):
        ref_id = manager.get_candidates_and_reference(event.getEventId())[1]
        return None if ref_id is None else scenery.active_events[ref_id]

    summary = EventQueries().event_associations(
        1, scenery.active_events, scenery.archived_events, get_candidates, get_reference).events[0]
    assert ids(summary.referenced_by) == [2, 3]
    assert summary.chosen_reference is None
