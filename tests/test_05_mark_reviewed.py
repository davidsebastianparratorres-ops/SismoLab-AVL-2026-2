"""Point 5: marking an event as reviewed."""
import pytest

from src.controllers.AttetionStatus import AttetionStatus
from src.models.Key import Key
from tests.helpers import add_event, build_scenery


def test_pending_event_becomes_reviewed():
    scenery = build_scenery()
    event = add_event(scenery, 1, 5.0)
    result = scenery.mark_as_reviewed(1)
    assert result.success
    assert result.event is event
    assert event.getStatus() == AttetionStatus.REVIEWED
    assert scenery.get_event(1).event.getStatus() == AttetionStatus.REVIEWED


def test_marking_twice_is_harmless():
    scenery = build_scenery()
    add_event(scenery, 1, 5.0)
    assert scenery.mark_as_reviewed(1).success
    assert scenery.mark_as_reviewed(1).success
    assert scenery.active_events[1].getStatus() == AttetionStatus.REVIEWED


def test_only_the_target_event_changes():
    scenery = build_scenery()
    add_event(scenery, 1, 5.0)
    other = add_event(scenery, 2, 5.5)
    scenery.mark_as_reviewed(1)
    assert other.getStatus() == AttetionStatus.PENDING


def test_priority_key_and_tree_position_are_unchanged():
    scenery = build_scenery()
    event = add_event(scenery, 1, 5.0)
    scenery.mark_as_reviewed(1)
    assert event.getPriority() == 2
    assert scenery.tree.search(Key(2, 5.0, 1)) is not None


@pytest.mark.parametrize("setup", ["unknown", "archived", "eliminated"])
def test_non_active_events_cannot_be_marked(setup):
    scenery = build_scenery()
    if setup == "archived":
        add_event(scenery, 1, 5.0)
        scenery.archived_events[1] = scenery.active_events.pop(1)
    elif setup == "eliminated":
        scenery.eliminated_ids.add(1)
    result = scenery.mark_as_reviewed(1)
    assert not result.success
    assert "not an active event" in result.message
