import unittest
from datetime import datetime, timezone

from src.models.AVL import AVL
from src.models.Metrics import Metrics
from src.models.Station import Station
from src.models.SimulationClock import SimulationClock
from src.models.SimulationParameters import SimulationParameters
from src.controllers.Scenery import Scenery
from src.controllers.Indicators import build_indicators, traversals


def utc(hour, minute):
    return datetime(2026, 9, 7, hour, minute, 0, tzinfo=timezone.utc)


class TestMetricsClass(unittest.TestCase):

    def test_increment_and_unknown_name(self):
        m = Metrics()
        m.increment("conflicts")
        m.record_case("LR")
        m.record_rotation("left")
        m.record_rotation("right")
        self.assertEqual((m.get("conflicts"), m.get("case_LR")), (1, 1))
        self.assertEqual((m.get("rotations_left"), m.get("rotations_right")), (1, 1))
        with self.assertRaises(KeyError):
            m.increment("nope")

    def test_copy_is_independent_and_restore_works(self):
        m = Metrics()
        snap = m.copy()
        m.increment("reports_discarded", 3)
        self.assertEqual(snap.get("reports_discarded"), 0)
        m.restore(snap)
        self.assertEqual(m.get("reports_discarded"), 0)

    def test_dict_round_trip_and_validation(self):
        m = Metrics()
        m.increment("mass_archives", 2)
        loaded, errors = Metrics.from_dict(m.to_dict())
        self.assertEqual(errors, [])
        self.assertEqual(loaded.to_dict(), m.to_dict())

        bad = m.to_dict()
        bad["conflicts"] = -1
        del bad["case_LL"]
        loaded, errors = Metrics.from_dict(bad)
        self.assertIsNone(loaded)
        self.assertEqual(len(errors), 2)


class TestMetricsInScenery(unittest.TestCase):

    def setUp(self):
        self.scenery = Scenery(
            zones=[],
            stations={"EST-01": Station("EST-01", "Norte")},
            simulation_clock=SimulationClock(utc(12, 0)),
            tree=AVL(),
            parameters=SimulationParameters(),
        )

    def _create(self, event_id, magnitude, when=utc(10, 0)):
        result = self.scenery.create_event(event_id, magnitude, 10.0, 100.0, 100.0, when, "EST-01")
        self.assertTrue(result.success, result.message)

    def test_correction_increments_and_undo_restores(self):
        self._create(1, 4.8)
        self.assertTrue(self.scenery.correct_event(1, 6.2, 15.0, 100.0, 100.0, "EST-01").success)
        self.assertEqual(self.scenery.metrics.get("corrections_accepted"), 1)

        self.scenery.undo()
        self.assertEqual(self.scenery.metrics.get("corrections_accepted"), 0)

        self.scenery.redo()
        self.assertEqual(self.scenery.metrics.get("corrections_accepted"), 1)

    def test_rejected_correction_does_not_count(self):
        self._create(1, 4.8)
        self.assertFalse(self.scenery.correct_event(1, 99.0, 15.0, 100.0, 100.0, "EST-01").success)
        self.assertEqual(self.scenery.metrics.get("corrections_accepted"), 0)

    def test_indicators(self):
        self._create(1, 5.6)   # priority 2
        self._create(2, 3.0)   # priority 1
        self._create(3, 6.5)   # priority 3
        self.scenery.mark_as_reviewed(2)

        ind = build_indicators(self.scenery)
        self.assertEqual(ind["active"], 3)
        self.assertEqual(ind["by_priority"], {1: 1, 2: 1, 3: 1})
        self.assertEqual(ind["pending"], 2)
        self.assertEqual((ind["height"], ind["leaves"], ind["nodes"]), (1, 2, 3))
        self.assertEqual(ind["costly_access"], 0)          # L = 3

        self.scenery.update_parameters(l=0)
        self.assertEqual(build_indicators(self.scenery)["costly_access"], 1)  # event 3 at depth 1

    def test_traversals(self):
        self._create(1, 5.6)
        self._create(2, 3.0)
        self._create(3, 6.5)
        t = traversals(self.scenery.tree.getRoot())
        self.assertEqual(t["inorder"], [2, 1, 3])     # ascending K
        self.assertEqual(t["preorder"], [1, 2, 3])
        self.assertEqual(t["postorder"], [2, 3, 1])
        self.assertEqual(t["levels"], [1, 2, 3])


if __name__ == "__main__":
    unittest.main(verbosity=2)