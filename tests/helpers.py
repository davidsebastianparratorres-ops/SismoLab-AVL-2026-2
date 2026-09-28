from datetime import datetime, timedelta, timezone

from src.controllers.Scenery import Scenery
from src.controllers.UndoStack import UndoStack
from src.models.AVL import AVL
from src.models.SimulationClock import SimulationClock
from src.models.SimulationParameters import SimulationParameters
from src.models.Station import Station

CLOCK_START = datetime(2026, 1, 10, 12, 0, 0, tzinfo=timezone.utc)


def build_scenery(zones=None):
    """Fresh scenery with an empty AVL, two stations and a fixed clock."""
    stations = {"EST1": Station("EST1", "Station 1"), "EST2": Station("EST2", "Station 2")}
    return Scenery(
        zones if zones is not None else [],
        stations,
        SimulationClock(CLOCK_START),
        AVL(),
        UndoStack(),
        SimulationParameters(),
    )


def add_event(scenery, event_id, magnitude, depth_km=10.0, x=500.0, y=500.0,
              hours_ago=1.0, station="EST1"):
    """Creates an event through the real create_event path and asserts success."""
    occurred_at = CLOCK_START - timedelta(hours=hours_ago)
    result = scenery.create_event(event_id, magnitude, depth_km, x, y, occurred_at, station)
    assert result.success, result.message
    return result.event
