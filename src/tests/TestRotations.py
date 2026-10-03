import random
import unittest
from datetime import datetime, timezone

from src.controllers.Scenery import Scenery
from src.controllers.StressManager import StressManager
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


def shape(tree):
    """Real topology as (event_id, left_id, right_id) in preorder: it compares exact structures."""
    out, stack = [], [tree.getRoot()] if tree.getRoot() else []
    while stack:
        n = stack.pop()
        out.append((n.getEventId(), n.getLeft().getEventId() if n.getLeft() else None,
                    n.getRight().getEventId() if n.getRight() else None))
        stack.extend(c for c in (n.getRight(), n.getLeft()) if c)
    return out


def assert_valid_avl(case, tree):
    """Recomputes every height from scratch (never trusting the stored ones)."""
    def check(node):
        if node is None:
            return -1
        lh, rh = check(node.getLeft()), check(node.getRight())
        case.assertEqual(node.getHeight(), 1 + max(lh, rh))
        case.assertEqual(node.getBalanceFactor(), lh - rh)
        case.assertLessEqual(abs(lh - rh), 1)
        return 1 + max(lh, rh)
    check(tree.getRoot())


class TestRestoreBalance(unittest.TestCase):
    def _degrade(self, keys, mixed_priorities=False):
        tree = AVL()
        tree.balancing = False
        for k in keys:
            tree.insert(Key(1 + k % 3 if mixed_priorities else 1, k / 10, k), k)
        return tree

    def _recover_and_compare(self, tree):
        nodes_before = {id(n) for n in tree.inOrder()}
        order_before = [n.getEventId() for n in tree.inOrder()]
        tree.restore_balance()
        assert_valid_avl(self, tree)
        self.assertEqual([n.getEventId() for n in tree.inOrder()], order_before)  # same order
        self.assertEqual({id(n) for n in tree.inOrder()}, nodes_before)            # same nodes
        self.assertEqual(tree.getSize(), len(order_before))

    def test_height_differences_larger_than_two(self):
        for keys in (range(1, 201), range(200, 0, -1)):               # full chains, diff ~199
            tree = self._degrade(keys)
            self.assertGreater(abs(tree.getBalanceFactor()), 100)
            self._recover_and_compare(tree)
        zigzag = [50 + (i // 2 + 1) * (1 if i % 2 else -1) for i in range(80)]  # alternating sides
        self._recover_and_compare(self._degrade(zigzag))

    def test_random_degraded_trees_including_deletions(self):
        rng = random.Random(2026)
        for _ in range(60):
            keys = rng.sample(range(1, 400), rng.randint(0, 150))
            tree = self._degrade(sorted(keys) if rng.random() < .5 else keys, mixed_priorities=True)
            for k in rng.sample(keys, len(keys) // 3):                  # deletions in stress mode too
                tree.delete(Key(1 + k % 3, k / 10, k))
            self._recover_and_compare(tree)

    def test_empty_single_and_already_balanced(self):
        self._recover_and_compare(AVL())
        self._recover_and_compare(self._degrade([5]))
        tree = AVL()
        insert_all(tree, [3.0, 1.0, 2.0, 5.0, 4.0])
        rotations = tree.metrics.get("rotations_left") + tree.metrics.get("rotations_right")
        self._recover_and_compare(tree)                                # nothing to fix
        self.assertEqual(tree.metrics.get("rotations_left") + tree.metrics.get("rotations_right"), rotations)

    def test_recovery_cost_is_reported_by_the_counters(self):
        tree = self._degrade(range(1, 100))
        tree.restore_balance()
        self.assertGreater(tree.metrics.get("rotations_left") + tree.metrics.get("rotations_right"), 0)
        self.assertGreater(sum(tree.metrics.get(c) for c in ("case_LL", "case_RR", "case_LR", "case_RL")), 0)

    def test_after_recovery_normal_inserts_keep_working(self):
        tree = self._degrade(range(1, 60))
        tree.restore_balance()
        tree.balancing = True
        for k in range(60, 120):
            tree.insert(Key(1, k / 10, k), k)
        assert_valid_avl(self, tree)


class TestGlobalRecovery(unittest.TestCase):
    def setUp(self):
        self.s = make_scenery(AVL())
        self.manager = StressManager(self.s)
        self.manager.enter_stress()
        for i in range(1, 41):  # magnitude grows while the time goes back: many associations
            self.s.create_event(i, i / 10, 10.0, 100.0, 100.0,
                                datetime(2026, 9, 7, 11, 59 - i, tzinfo=timezone.utc), "EST-01")

    def associations(self):
        return {i: e.getAssociatedEvents() and list(e.getAssociatedEvents()) for i, e in self.s.active_events.items()}

    def test_recovery_leaves_stress_only_after_a_clean_audit(self):
        self.assertTrue(self.s.stress_mode)
        self.assertEqual(self.s.tree.getHeight(), 39)                  # real degradation
        result = self.manager.recover()
        self.assertTrue(result.success, result.message)
        self.assertTrue(result.audit.is_valid_avl)
        self.assertFalse(self.s.stress_mode)
        self.assertGreater(result.imbalanced_before, 30)
        self.assertGreater(sum(result.rotations.values()), 0)
        assert_valid_avl(self, self.s.tree)

    def test_identities_order_and_associations_are_preserved(self):
        ids, assoc = sorted(self.s.active_events), self.associations()
        self.assertTrue(any(assoc.values()))                           # there ARE associations
        keys = [n.getKey().as_tuple for n in self.s.tree.inOrder()]
        self.manager.recover()
        self.assertEqual(sorted(self.s.active_events), ids)
        self.assertEqual(self.associations(), assoc)
        self.assertEqual([n.getKey().as_tuple for n in self.s.tree.inOrder()], keys)

    def test_recovery_is_one_undoable_action_restoring_exact_topology(self):
        degraded = shape(self.s.tree)
        counters = self.s.metrics.to_dict()
        self.manager.recover()
        self.s.undo()
        self.assertEqual(shape(self.s.tree), degraded)
        self.assertTrue(self.s.stress_mode)
        self.assertEqual(self.s.metrics.to_dict(), counters)

    def test_refuses_when_already_normal_or_already_stress(self):
        self.assertFalse(self.manager.enter_stress().success)          # already stress
        self.manager.recover()
        self.assertFalse(self.manager.recover().success)               # already normal

    def test_refuses_without_touching_a_tree_with_broken_order(self):
        root = self.s.tree.getRoot()
        root.setLeft(root.getRight())                                  # larger keys on the left side
        root.setRight(None)
        broken = shape(self.s.tree)
        result = self.manager.recover()
        self.assertFalse(result.success)
        self.assertTrue(result.audit.has_errors())
        self.assertTrue(self.s.stress_mode)
        self.assertEqual(shape(self.s.tree), broken)                   # rotations never ran

    def test_enter_stress_is_undoable(self):
        s = make_scenery(AVL())
        StressManager(s).enter_stress()
        self.assertTrue(s.stress_mode)
        s.undo()
        self.assertFalse(s.stress_mode)


if __name__ == "__main__":
    unittest.main(verbosity=2)