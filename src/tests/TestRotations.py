import random
import unittest
from datetime import datetime, timezone

from src.controllers.Scenery import Scenery
from src.models.AVL import AVL
from src.models.Key import Key
from src.models.SimulationClock import SimulationClock
from src.models.SimulationParameters import SimulationParameters
from src.models.Station import Station


def insert_all(tree, magnitudes):
    for i, m in enumerate(magnitudes, start=1):
        tree.insert(Key(1, m, i), i)


def make_scenery(tree):
    return Scenery([], {"EST-01": Station("EST-01", "Norte")},
                   SimulationClock(datetime(2026, 9, 7, 12, 0, tzinfo=timezone.utc)),
                   tree, SimulationParameters())


class TestRotationCounters(unittest.TestCase):
    """The four AVL cases are counted, a double case = 1 case + 2 rotations."""

    def _run(self, magnitudes):
        tree = AVL()
        insert_all(tree, magnitudes)
        return tree.metrics

    def test_ll(self):
        m = self._run([3.0, 2.0, 1.0])
        self.assertEqual((m.get("case_LL"), m.get("rotations_right"), m.get("rotations_left")), (1, 1, 0))

    def test_rr(self):
        m = self._run([1.0, 2.0, 3.0])
        self.assertEqual((m.get("case_RR"), m.get("rotations_left"), m.get("rotations_right")), (1, 1, 0))

    def test_lr(self):
        m = self._run([3.0, 1.0, 2.0])
        self.assertEqual((m.get("case_LR"), m.get("rotations_left"), m.get("rotations_right")), (1, 1, 1))

    def test_rl(self):
        m = self._run([1.0, 3.0, 2.0])
        self.assertEqual((m.get("case_RL"), m.get("rotations_left"), m.get("rotations_right")), (1, 1, 1))


class TestStressFlag(unittest.TestCase):
    def test_deferred_balancing_keeps_bst_order_and_metadata(self):
        tree = AVL()
        tree.balancing = False
        insert_all(tree, [i / 10 for i in range(500)])
        self.assertEqual((tree.getSize(), tree.getHeight()), (500, 499))
        self.assertEqual(tree.metrics.get("rotations_left") + tree.metrics.get("rotations_right"), 0)
        ids = [n.getEventId() for n in tree.inOrder()]
        self.assertEqual(ids, sorted(ids))                       # BST order intact
        self.assertEqual(tree.getBalanceFactor(), -499)          # metadata still exact

    def test_size_is_incremental_and_exact(self):
        tree, keys = AVL(), list(range(1, 200))
        random.Random(7).shuffle(keys)
        for k in keys:
            tree.insert(Key(1, k / 10, k), k)
        for k in keys[:120]:
            self.assertTrue(tree.delete(Key(1, k / 10, k)))
        self.assertEqual(tree.getSize(), 79)
        self.assertEqual(tree.getSize(), tree._count_nodes(tree.getRoot()))
        self.assertFalse(tree.delete(Key(1, 99.9, 999)))
        self.assertEqual(tree.getSize(), 79)

    def test_scenery_stress_mode_and_undo(self):
        s = make_scenery(AVL())
        s.stress_mode = True
        self.assertFalse(s.tree.balancing)
        s.stress_mode = False
        for i, m in enumerate([1.0, 2.0, 3.0], start=1):
            s.create_event(i, m, 10.0, 100.0, 100.0,
                           datetime(2026, 9, 7, 10, i, tzinfo=timezone.utc), "EST-01")
        self.assertEqual(s.metrics.get("case_RR"), 1)   # tree reports into scenery metrics
        s.undo()
        self.assertEqual(s.metrics.get("case_RR"), 0)   # and undo restores the counters

    def test_snapshot_restores_mode(self):
        s = make_scenery(AVL())
        s.set_access_depth_limit(5)        # records a snapshot taken in normal mode
        s.stress_mode = True
        s.undo()
        self.assertFalse(s.stress_mode)


if __name__ == "__main__":
    unittest.main(verbosity=2)