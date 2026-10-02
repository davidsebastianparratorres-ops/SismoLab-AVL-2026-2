import unittest
from datetime import datetime, timezone

from src.controllers.ReportProcessor import ReportProcessor, Decision
from src.controllers.Scenery import Scenery
from src.models.AVL import AVL
from src.models.Key import Key
from src.models.Report import Report
from src.models.SimulationClock import SimulationClock
from src.models.SimulationParameters import SimulationParameters
from src.models.Station import Station


def utc(hour, minute=0):
    return datetime(2026, 9, 7, hour, minute, tzinfo=timezone.utc)


def report(event_id=1, magnitude=4.8, depth=70.0, x=100.0, y=100.0, when=utc(10), revision=1, station="EST-01"):
    return Report(event_id, magnitude, depth, x, y, when, revision, station)


class ReportTestCase(unittest.TestCase):
    def setUp(self):
        self.scenery = Scenery([], {"EST-01": Station("EST-01", "Norte"), "EST-02": Station("EST-02", "Sur")},
                               SimulationClock(utc(12)), AVL(), SimulationParameters())
        self.processor = ReportProcessor(self.scenery)

    def run_report(self, *args, **kwargs):
        self.processor.enqueue([report(*args, **kwargs)])
        return self.processor.process_next()

    def event(self, event_id=1):
        return self.scenery.active_events[event_id]


class TestResolutionTable(ReportTestCase):
    def test_unknown_id_creates_event_and_first_revision_may_exceed_one(self):
        step = self.run_report(revision=3)
        self.assertEqual(step.decision, Decision.CREATED)
        self.assertEqual((self.event().getReview(), self.scenery.tree.getSize()), (3, 1))

    def test_higher_revision_updates_and_moves_node_when_priority_changes(self):
        self.run_report()                                             # M 4.8, H 70 -> priority 2
        self.assertEqual(self.event().getPriority(), 2)
        step = self.run_report(magnitude=6.2, depth=15.0, revision=2)  # -> priority 3
        self.assertEqual(step.decision, Decision.UPDATED)
        e = self.event()
        self.assertEqual((e.getPriority(), e.getReview(), e.getStatus()), (3, 2, "PENDING"))
        self.assertEqual(self.scenery.tree.getSize(), 1)
        self.assertIsNotNone(self.scenery.tree.search(Key(3, 6.2, 1)))
        self.assertIsNone(self.scenery.tree.search(Key(2, 4.8, 1)))
        self.assertEqual(self.scenery.metrics.get("corrections_accepted"), 1)

    def test_lower_revision_is_discarded_without_touching_the_event(self):
        self.run_report()
        self.run_report(magnitude=6.2, depth=15.0, revision=2)
        step = self.run_report(revision=1)                            # old data, old revision
        self.assertEqual(step.decision, Decision.OUTDATED)
        self.assertEqual((self.event().getMagnitude(), self.event().getReview()), (6.2, 2))
        self.assertEqual(self.scenery.tree.getSize(), 1)
        self.assertEqual(self.scenery.metrics.get("reports_discarded"), 1)

    def test_same_revision_same_data_confirms_and_never_duplicates_station(self):
        self.run_report()
        self.assertEqual(self.run_report(station="EST-02").decision, Decision.CONFIRMED)
        self.run_report(station="EST-02")
        self.assertEqual(self.event().getStations(), ["EST-01", "EST-02"])
        self.assertEqual(self.scenery.tree.getSize(), 1)

    def test_same_revision_different_data_is_a_conflict(self):
        self.run_report()
        step = self.run_report(magnitude=5.0)
        self.assertEqual(step.decision, Decision.CONFLICT)
        self.assertEqual(self.event().getMagnitude(), 4.8)
        self.assertEqual(self.scenery.metrics.get("conflicts"), 1)

    def test_invalid_reports_are_rejected(self):
        self.assertEqual(self.run_report(magnitude=11.0).decision, Decision.REJECTED)
        self.assertEqual(self.run_report(station="EST-99").decision, Decision.REJECTED)
        self.assertEqual(self.run_report(revision=0).decision, Decision.REJECTED)
        self.assertEqual(self.run_report(when=utc(13)).decision, Decision.REJECTED)  # after the clock
        self.assertEqual(self.scenery.tree.getSize(), 0)


class TestEliminatedAndArchived(ReportTestCase):
    def test_eliminated_id_is_rejected_until_the_elimination_is_undone(self):
        self.run_report()
        self.scenery.delete_event(1)
        self.assertEqual(self.run_report(revision=5).decision, Decision.REJECTED)
        self.assertNotIn(1, self.scenery.active_events)
        self.scenery.undo()                                           # the discarded step
        self.scenery.undo()                                           # the enqueue of that report
        self.scenery.undo()                                           # the deletion
        self.assertIn(1, self.scenery.active_events)

    def _archive(self, event_id=1):
        # Test helper: simulates what the archive operation will do.
        event = self.scenery.active_events.pop(event_id)
        self.scenery.tree.delete(Key(event.getPriority(), event.getMagnitude(), event_id))
        self.scenery.archived_events[event_id] = event

    def test_confirmation_and_old_report_do_not_reactivate(self):
        self.run_report(revision=2)
        self._archive()
        self.assertEqual(self.run_report(revision=2, station="EST-02").decision, Decision.CONFIRMED)
        self.assertEqual(self.run_report(revision=1).decision, Decision.OUTDATED)
        self.assertIn(1, self.scenery.archived_events)
        self.assertEqual(self.scenery.tree.getSize(), 0)

    def test_higher_revision_reactivates_as_pending_with_corrected_data(self):
        self.run_report(revision=2)
        self.scenery.mark_as_reviewed(1)
        self._archive()
        step = self.run_report(magnitude=6.5, depth=10.0, revision=3)
        self.assertEqual(step.decision, Decision.REACTIVATED)
        e = self.event()
        self.assertEqual((e.getMagnitude(), e.getReview(), e.getStatus()), (6.5, 3, "PENDING"))
        self.assertNotIn(1, self.scenery.archived_events)
        self.assertIsNotNone(self.scenery.tree.search(Key(3, 6.5, 1)))
        self.assertEqual(self.scenery.tree.getSize(), 1)


class TestQueueAndUndo(ReportTestCase):
    def test_queue_keeps_arrival_order_not_priority_order(self):
        self.processor.enqueue([report(1, 3.0), report(2, 7.0), report(3, 4.0)])
        self.assertEqual([r.event_id for r in self.scenery.queue.to_list()], [1, 2, 3])
        self.assertEqual(self.processor.process_next().report.event_id, 1)
        self.assertEqual(self.processor.process_next().report.event_id, 2)

    def test_empty_queue_returns_none(self):
        self.assertIsNone(self.processor.process_next())

    def test_each_step_is_one_undoable_action_and_restores_queue_position(self):
        self.processor.enqueue([report(1), report(1, revision=1, magnitude=5.0)])  # 2nd = conflict
        self.processor.process_next()
        before = self.scenery.tree.getSize()
        self.assertEqual(self.processor.process_next().decision, Decision.CONFLICT)
        self.assertEqual(len(self.scenery.queue), 0)
        self.scenery.undo()                                           # undo ONLY the discarded step
        self.assertEqual([r.magnitude for r in self.scenery.queue.to_list()], [5.0])
        self.assertEqual(self.scenery.metrics.get("conflicts"), 0)
        self.assertEqual(self.scenery.tree.getSize(), before)

    def test_correction_step_is_a_single_action(self):
        self.run_report()
        self.processor.enqueue([report(magnitude=6.2, depth=15.0, revision=2)])
        self.processor.process_next()                                 # delete + insert + recalc inside
        self.scenery.undo()                                           # one undo reverts the whole step
        self.assertEqual((self.event().getMagnitude(), self.event().getReview()), (4.8, 1))
        self.assertEqual(len(self.scenery.queue), 1)

    def test_enqueue_is_one_undoable_action(self):
        self.processor.enqueue([report(1), report(2)])
        self.scenery.undo()
        self.assertEqual(len(self.scenery.queue), 0)

    def test_step_reports_the_rotations_it_produced(self):
        self.processor.enqueue([report(1, 1.0, 10.0), report(2, 2.0, 10.0), report(3, 3.0, 10.0)])
        steps = [self.processor.process_next() for _ in range(3)]
        self.assertEqual(steps[0].rotations, {})
        self.assertEqual(steps[2].rotations, {"case_RR": 1, "rotations_left": 1})

    def test_stress_mode_steps_keep_order_without_rotating(self):
        self.scenery.stress_mode = True
        self.processor.enqueue([report(i, i / 10, 10.0) for i in range(1, 6)])
        steps = [self.processor.process_next() for _ in range(5)]
        self.assertTrue(all(s.rotations == {} for s in steps))
        self.assertEqual(self.scenery.tree.getHeight(), 4)


if __name__ == "__main__":
    unittest.main(verbosity=2)