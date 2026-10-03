import unittest
from datetime import datetime, timedelta, timezone

from src.controllers.BranchArchiver import BranchArchiver
from src.controllers.ReportProcessor import ReportProcessor
from src.controllers.ScenarioPackage import ScenarioPackage
from src.controllers.StressManager import StressManager
from src.models.AVL import AVL
from src.models.Report import Report
from src.tests.TestRotations import make_scenery, shape

CLOCK = datetime(2026, 9, 7, 12, 0, tzinfo=timezone.utc)
OLD = CLOCK - timedelta(days=4)
RECENT = CLOCK - timedelta(hours=2)


def fingerprint(s):
    """Everything the undo stack promises to restore (section 13)."""
    events = [(i, e.getMagnitude(), e.getDepth_km(), e.getReview(), e.getStatus(),
               tuple(e.getStations()), tuple(e.getAssociatedEvents()))
              for i, e in sorted(s.active_events.items())]
    return (shape(s.tree), events, sorted(s.archived_events), sorted(s.eliminated_ids),
            s.metrics.to_dict(), s.simulation_clock.current_time, s.parameters.to_dict(),
            s.stress_mode, tuple(s.queue.to_list()), s.association_manager.to_dict())


def populated(stress=False):
    s = make_scenery(AVL())
    if stress:
        s.stress_mode = True
    for i in range(1, 7):                                  # old, low priority: an archivable branch
        assert s.create_event(i, i / 10, 10.0, i * 9.0, 50.0, OLD, "EST-01").success
    for i, m in ((10, 3.0), (11, 3.5)):
        assert s.create_event(i, m, 10.0, i * 9.0, 50.0, RECENT, "EST-01").success
    return s


def a_report(**changes):
    data = dict(event_id=1, magnitude=1.0, depth_km=10.0, epicenter_x=9.0, epicenter_y=50.0,
                occurred_at=OLD, revision=1, station_id="EST-01")
    data.update(changes)
    return Report(**data)


def enqueue_correction(s):
    ReportProcessor(s).enqueue([a_report(revision=2, magnitude=3.3)])


class TestEveryActionIsOneUndo(unittest.TestCase):
    """Section 13: each of these is an independent action, undone (and redone) in ONE step."""

    ACTIONS = {
        "alta": (lambda s: None, lambda s: s.create_event(50, 2.2, 10.0, 400.0, 400.0, RECENT, "EST-01")),
        "correccion": (lambda s: None, lambda s: s.correct_event(1, 6.2, 15.0, 9.0, 50.0, "EST-01")),
        "eliminacion": (lambda s: None, lambda s: s.delete_event(2)),
        "cambio de atencion": (lambda s: None, lambda s: s.mark_as_reviewed(3)),
        "cambio de parametros": (lambda s: None, lambda s: s.update_parameters(w=10.0)),
        "limite de profundidad": (lambda s: None, lambda s: s.set_access_depth_limit(5)),
        "avance del reloj": (lambda s: None, lambda s: s.advance_clock(timedelta(hours=1))),
        "encolar rafaga": (lambda s: None, lambda s: ReportProcessor(s).enqueue([a_report(), a_report(event_id=2)])),
        "paso de cola": (enqueue_correction, lambda s: ReportProcessor(s).process_next()),
        "archivo masivo": (lambda s: None, lambda s: BranchArchiver(s).archive()),
        "modo estres": (lambda s: None, lambda s: StressManager(s).enter_stress()),
        "carga": (lambda s: None, lambda s: ScenarioPackage().apply(
            s, ScenarioPackage().parse(ScenarioPackage().export(populated(stress=True))).state)),
    }

    def test_each_action_changes_the_state_and_one_undo_reverts_it_exactly(self):
        for name, (setup, action) in self.ACTIONS.items():
            with self.subTest(action=name):
                s = populated()
                setup(s)
                before = fingerprint(s)
                action(s)
                after = fingerprint(s)
                self.assertNotEqual(after, before, "the action had no visible effect")
                self.assertTrue(s.undo().success)
                self.assertEqual(fingerprint(s), before)
                self.assertTrue(s.redo().success)
                self.assertEqual(fingerprint(s), after)

    def test_global_recovery_is_one_undo(self):
        s = populated(stress=True)
        before = fingerprint(s)
        self.assertTrue(StressManager(s).recover().success)
        after = fingerprint(s)
        self.assertNotEqual(after, before)
        s.undo()
        self.assertEqual(fingerprint(s), before)
        s.redo()
        self.assertEqual(fingerprint(s), after)


class TestHistoryRobustness(unittest.TestCase):
    def test_a_rejected_action_leaves_both_stacks_untouched(self):
        s = populated()
        s.update_parameters(w=10.0)
        s.undo()                                           # leaves one entry in the redo stack
        self.assertTrue(s.history.can_redo())
        for rejected in (lambda: s.set_access_depth_limit(-1),
                         lambda: s.advance_clock(timedelta(hours=-1)),
                         lambda: s.create_event(1, 2.0, 10.0, 1.0, 1.0, RECENT, "EST-01"),   # taken id
                         lambda: s.delete_event(999),
                         lambda: s.mark_as_reviewed(999)):
            self.assertFalse(rejected().success)
            self.assertTrue(s.history.can_redo(), "a rejected action must not clear redo")
        s.redo()
        self.assertFalse(s.history.can_redo())

    def test_rejected_depth_limit_does_not_create_a_phantom_redo(self):
        s = populated()
        self.assertFalse(s.set_access_depth_limit(-5).success)
        self.assertFalse(s.history.can_redo())

    def test_nested_groups_stay_one_action(self):
        s = populated()
        stack_before = fingerprint(s)
        with s.history.single_action():
            s.create_event(50, 2.2, 10.0, 400.0, 400.0, RECENT, "EST-01")
            with s.history.single_action():                # nested: must not end the outer group
                s.create_event(51, 2.3, 10.0, 410.0, 410.0, RECENT, "EST-01")
            s.create_event(52, 2.4, 10.0, 420.0, 420.0, RECENT, "EST-01")
        self.assertEqual(len(s.active_events), 11)
        s.undo()
        self.assertEqual(fingerprint(s), stack_before)

    def test_undo_without_history_reports_instead_of_failing(self):
        s = populated()
        while s.history.can_undo():
            s.undo()
        self.assertFalse(s.undo().success)


if __name__ == "__main__":
    unittest.main(verbosity=2)