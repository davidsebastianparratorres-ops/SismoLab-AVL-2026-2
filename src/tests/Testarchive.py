import unittest
from datetime import datetime, timedelta, timezone

from src.controllers.BranchArchiver import BranchArchiver
from src.controllers.StressManager import StressManager
from src.controllers.TreeAuditor import TreeAuditor
from src.models.AVL import AVL
from src.tests.TestRotations import make_scenery, shape, assert_valid_avl

CLOCK = datetime(2026, 9, 7, 12, 0, tzinfo=timezone.utc)
OLD = CLOCK - timedelta(days=4)     # 96 h > T (72 h)
RECENT = CLOCK - timedelta(hours=2)


class ArchiveTestCase(unittest.TestCase):
    def setUp(self):
        self.s = make_scenery(AVL())
        self.archiver = BranchArchiver(self.s)

    def add(self, event_id, magnitude, when=OLD, depth=10.0):
        """Low-priority event unless magnitude >= 4.5 (use depth 70 for priority 2)."""
        result = self.s.create_event(event_id, magnitude, depth, event_id * 7.0, 50.0, when, "EST-01")
        self.assertTrue(result.success, result.message)

    def stress(self):
        StressManager(self.s).enter_stress()

    def archived(self):
        return sorted(self.s.archived_events)

    def active(self):
        return sorted(self.s.active_events)


class TestSelectionAndExecution(ArchiveTestCase):
    def _branch_scenario(self):
        # Stress mode keeps the exact BST shape:   1(recent)
        #                                          /       \
        #                                  2(old)           5(recent)
        #                                  /    \
        #                              3(old)  4(old)
        self.stress()
        self.add(1, 3.0, RECENT)
        self.add(2, 2.0)
        self.add(3, 1.0)
        self.add(4, 2.5)
        self.add(5, 3.5, RECENT)

    def test_eligible_branch_is_previewed_then_moved_to_the_history(self):
        self._branch_scenario()
        preview = self.archiver.preview()
        self.assertEqual((preview.root_id, sorted(preview.ids), preview.count), (2, [2, 3, 4], 3))
        self.assertIn("mayor cantidad de nodos (3)", preview.justification)
        result = self.archiver.archive()
        self.assertTrue(result.success, result.message)
        self.assertEqual((self.active(), self.archived()), ([1, 5], [2, 3, 4]))
        self.assertEqual(self.s.tree.getSize(), 2)
        self.assertEqual((self.s.metrics.get("mass_archives"), self.s.metrics.get("events_archived")), (1, 3))
        self.assertEqual(self.s.archived_events[2].getStations(), ["EST-01"])  # data kept

    def test_preview_never_modifies_anything(self):
        self._branch_scenario()
        before = shape(self.s.tree)
        self.archiver.preview()
        self.assertEqual((shape(self.s.tree), self.archived()), (before, []))

    def test_stress_mode_keeps_order_and_metadata_without_rotating(self):
        self._branch_scenario()
        rotations = self.s.metrics.get("rotations_left") + self.s.metrics.get("rotations_right")
        self.archiver.archive()
        report = TreeAuditor().audit(self.s.tree.getRoot(), self.s.active_events, stress_mode=True,
                                     archived_ids=set(self.s.archived_events))
        self.assertFalse(report.has_errors(), report.to_text())
        self.assertEqual(self.s.metrics.get("rotations_left") + self.s.metrics.get("rotations_right"), rotations)

    def test_normal_mode_rebalances_and_the_fixed_set_is_not_altered_by_rotations(self):
        for i in range(1, 12):
            self.add(i, i / 10)
        for i, m in ((20, 3.0), (21, 3.1), (22, 3.2)):
            self.add(i, m, RECENT)
        assert_valid_avl(self, self.s.tree)
        everyone = self.active()
        fixed = self.archiver.preview().ids              # decided BEFORE touching the tree
        rotations = self.s.metrics.get("rotations_left") + self.s.metrics.get("rotations_right")
        self.assertTrue(self.archiver.archive().success)
        self.assertEqual(self.archived(), sorted(fixed))                      # exactly the fixed set
        self.assertEqual(self.active(), sorted(set(everyone) - set(fixed)))   # nobody else left
        assert_valid_avl(self, self.s.tree)                                   # balance restored
        self.assertGreaterEqual(self.s.metrics.get("rotations_left")
                                + self.s.metrics.get("rotations_right"), rotations)

    def test_tie_is_broken_by_deepest_root(self):
        # Two eligible branches of size 2: {20,21} (root depth 1) and {23,24} (root depth 2).
        self.stress()
        self.add(10, 3.0, RECENT)
        self.add(20, 2.0)
        self.add(21, 1.0)
        self.add(22, 4.0, RECENT)
        self.add(23, 3.5)
        self.add(24, 3.2)
        preview = self.archiver.preview()
        self.assertEqual((preview.root_id, sorted(preview.ids)), (23, [23, 24]))
        self.assertIn("más profunda", preview.justification)

    def test_tie_on_size_and_depth_is_broken_by_highest_root_id(self):
        # {20,21} and {22,23}: both size 2, both roots at depth 1.
        self.stress()
        self.add(10, 3.0, RECENT)
        self.add(20, 2.0)
        self.add(21, 1.0)
        self.add(22, 4.0)
        self.add(23, 3.5)
        preview = self.archiver.preview()
        self.assertEqual((preview.root_id, sorted(preview.ids)), (22, [22, 23]))
        self.assertIn("mayor identificador", preview.justification)

    def test_low_priority_root_with_a_higher_priority_descendant_is_not_eligible(self):
        self.stress()
        self.add(30, 3.0)                            # old, priority 1: the root of the branch
        self.add(31, 5.0, OLD, depth=70.0)           # old, priority 2: right descendant
        self.add(32, 2.0)                            # old, priority 1: left leaf
        preview = self.archiver.preview()
        self.assertEqual((preview.root_id, preview.ids), (32, [32]))   # only the clean leaf
        self.archiver.archive()
        self.assertEqual((self.active(), self.archived()), ([30, 31], [32]))

    def test_no_eligible_branch_reports_and_keeps_the_state(self):
        self.add(1, 3.0, RECENT)
        self.add(2, 5.0, OLD, depth=70.0)            # old but priority 2
        before = shape(self.s.tree)
        self.assertIsNone(self.archiver.preview())
        result = self.archiver.archive()
        self.assertFalse(result.success)
        self.assertEqual((shape(self.s.tree), self.archived(), self.s.metrics.get("mass_archives")), (before, [], 0))

    def test_age_must_be_strictly_greater_than_T(self):
        self.add(1, 2.0, CLOCK - timedelta(hours=72))                 # exactly T: not eligible
        self.assertIsNone(self.archiver.preview())
        self.add(2, 3.0, CLOCK - timedelta(hours=72, seconds=1))      # T + 1 s: eligible
        self.assertEqual(self.archiver.preview().ids, [2])

    def test_whole_tree_can_be_archived(self):
        for i in range(1, 8):
            self.add(i, i / 10)
        result = self.archiver.archive()
        self.assertTrue(result.success)
        self.assertEqual((self.active(), self.archived(), self.s.tree.getSize()), ([], list(range(1, 8)), 0))
        self.assertIsNone(self.s.tree.getRoot())


class TestUndoAndAssociations(ArchiveTestCase):
    def test_archive_is_one_undoable_action_restoring_the_exact_topology(self):
        for i in range(1, 10):
            self.add(i, i / 10)
        self.add(20, 3.0, RECENT)
        topology, metrics = shape(self.s.tree), self.s.metrics.to_dict()
        self.archiver.archive()
        self.s.undo()                                                  # ONE undo reverts everything
        self.assertEqual(shape(self.s.tree), topology)
        self.assertEqual((self.archived(), self.s.metrics.to_dict()), ([], metrics))
        self.assertEqual(self.active(), [1, 2, 3, 4, 5, 6, 7, 8, 9, 20])
        assert_valid_avl(self, self.s.tree)

    def test_associations_survive_the_archive(self):
        self.s.update_parameters(w=500, r=1000)                        # make old events associate
        self.add(1, 3.0, OLD)
        self.add(2, 2.0, OLD + timedelta(hours=1))
        self.add(3, 3.5, RECENT)
        before = self.s.association_manager.to_dict()
        self.assertTrue(any(before.values()))
        self.archiver.archive()
        self.assertEqual(self.s.association_manager.to_dict(), before)

    def test_archive_in_stress_then_global_recovery_gives_a_valid_avl(self):
        manager = StressManager(self.s)
        manager.enter_stress()
        self.add(40, 3.0, RECENT)                    # recent root: not eligible itself
        self.add(41, 3.1, RECENT)
        for i in range(1, 30):                       # 29 old events hang as one branch on its left
            self.add(i, i / 10)
        self.assertEqual(self.archiver.preview().count, 29)
        self.archiver.archive()
        self.assertEqual(self.active(), [40, 41])
        self.assertTrue(manager.recover().success)
        assert_valid_avl(self, self.s.tree)
        self.assertEqual(self.archived(), list(range(1, 30)))


if __name__ == "__main__":
    unittest.main(verbosity=2)