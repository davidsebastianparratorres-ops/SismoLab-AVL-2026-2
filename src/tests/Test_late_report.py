import unittest
from datetime import datetime, timezone

from src.models.AVL import AVL
from src.models.Station import Station
from src.models.SimulationClock import SimulationClock
from src.models.SimulationParameters import SimulationParameters
from src.controllers.Scenery import Scenery


def utc(hour, minute):
    return datetime(2026, 9, 7, hour, minute, 0, tzinfo=timezone.utc)


class TestLateReport(unittest.TestCase):
    """Section 16 - 'Reporte tardio': 5.6 at 10:00 and 4.2 at 10:20 arrive
    first; then a 6.1 that happened at 09:55 arrives late."""

    def setUp(self):
        self.scenery = Scenery(
            zones=[],
            stations={"EST-01": Station("EST-01", "Norte")},
            simulation_clock=SimulationClock(utc(12, 0)),
            tree=AVL(),
            parameters=SimulationParameters(),  # W=48 h, R=40 km
        )
        self.am = self.scenery.association_manager

    def _create(self, event_id, magnitude, x, y, when):
        result = self.scenery.create_event(event_id, magnitude, 10.0, x, y, when, "EST-01")
        self.assertTrue(result.success, result.message)

    def _reference_of(self, event_id):
        stored = self.am.associations.get(event_id)
        return stored.reference_id if stored else None

    def test_late_report_changes_selected_references(self):
        self._create(1, 5.6, 100.0, 100.0, utc(10, 0))
        self._create(2, 4.2, 105.0, 100.0, utc(10, 20))

        # Before the late report: 2 -> 1 (the only candidate).
        self.assertEqual(self._reference_of(2), 1)
        self.assertIsNone(self._reference_of(1))

        self._create(3, 6.1, 102.0, 104.0, utc(9, 55))

        # New candidates: for event 2 they are {1, 3}; for event 1 only {3}.
        candidates_2, _ = self.am.get_candidates_and_reference(2)
        candidates_1, _ = self.am.get_candidates_and_reference(1)
        self.assertEqual(sorted(e.getEventId() for e in candidates_2), [1, 3])
        self.assertEqual([e.getEventId() for e in candidates_1], [3])

        # Policy: highest magnitude wins -> both point to the 6.1.
        self.assertEqual(self._reference_of(2), 3)
        self.assertEqual(self._reference_of(1), 3)
        self.assertIsNone(self._reference_of(3))

        # No new node was created for existing ids, and the tree holds 3 events.
        self.assertEqual(self.scenery.tree.getSize(), 3)

    def test_undo_restores_previous_associations(self):
        self._create(1, 5.6, 100.0, 100.0, utc(10, 0))
        self._create(2, 4.2, 105.0, 100.0, utc(10, 20))
        self._create(3, 6.1, 102.0, 104.0, utc(9, 55))

        self.assertTrue(self.scenery.undo().success)

        self.assertEqual(self._reference_of(2), 1)
        self.assertIsNone(self._reference_of(1))
        self.assertNotIn(3, self.scenery.active_events)
        self.assertEqual(self.scenery.active_events[2].getAssociatedEvents(), [1])


if __name__ == "__main__":
    unittest.main(verbosity=2)