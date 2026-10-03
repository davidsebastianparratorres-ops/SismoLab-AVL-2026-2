import copy
import json
import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone

from src.controllers.ReportProcessor import ReportProcessor, Decision
from src.controllers.ScenarioPackage import ScenarioPackage
from src.controllers.StressManager import StressManager
from src.controllers.VersionStore import VersionStore
from src.models.AVL import AVL
from src.tests.TestRotations import make_scenery
from src.tests.TestUndo import fingerprint, populated, a_report


def rich_scenery(stress=False):
    """A scenery with everything a version must carry: events, queue, params, clock, metrics, mode."""
    s = populated(stress=stress)
    ReportProcessor(s).enqueue([
        a_report(revision=2, magnitude=3.3),                            # -> update
        a_report(event_id=2, magnitude=0.2, epicenter_x=18.0),          # same data as event 2 -> confirm
        a_report(event_id=777, magnitude=11.0)])                        # out of range -> rejected later
    s.update_parameters(w=12.0, r=75.0, t=48.0)
    s.set_access_depth_limit(2)
    s.advance_clock(timedelta(hours=3))
    s.mark_as_reviewed(3)
    return s


class VersionTestCase(unittest.TestCase):
    def setUp(self):
        self._dir = tempfile.TemporaryDirectory()
        self.addCleanup(self._dir.cleanup)
        self.directory = self._dir.name

    def store(self):
        return VersionStore(self.directory)           # a NEW store each time = a program restart


class TestSaveAndRestore(VersionTestCase):
    def test_version_survives_a_restart_and_restores_the_exact_state(self):
        original = rich_scenery()
        expected = fingerprint(original)
        self.assertTrue(self.store().save(original, "Antes del sismo").success)

        fresh = make_scenery(AVL())                    # "restarted" program: empty scenery, new store
        self.assertNotEqual(fingerprint(fresh), expected)
        result = self.store().restore(fresh, "Antes del sismo")
        self.assertTrue(result.success, result.message)
        self.assertEqual(fingerprint(fresh), expected)  # data, topology, history, queue, clock, params, mode, metrics

    def test_stress_version_restores_the_degraded_topology_and_the_mode(self):
        original = rich_scenery(stress=True)
        expected = fingerprint(original)
        self.assertTrue(original.stress_mode)
        self.store().save(original, "estres")
        fresh = make_scenery(AVL())
        self.assertTrue(self.store().restore(fresh, "estres").success)
        self.assertEqual(fingerprint(fresh), expected)
        self.assertTrue(fresh.stress_mode)
        self.assertTrue(StressManager(fresh).recover().success)   # and it can still be repaired

    def test_section_16_restore_after_restart_then_undo_a_correction_and_a_queue_step(self):
        self.store().save(rich_scenery(), "base")
        s = make_scenery(AVL())
        empty = fingerprint(s)
        self.store().restore(s, "base")
        restored = fingerprint(s)

        s.correct_event(1, 6.2, 15.0, 9.0, 50.0, "EST-01")        # a correction...
        self.assertNotEqual(fingerprint(s), restored)
        s.undo()                                                   # ...is undone
        self.assertEqual(fingerprint(s), restored)

        step = ReportProcessor(s).process_next()                   # a queue step...
        self.assertIsNotNone(step)
        self.assertNotEqual(fingerprint(s), restored)
        s.undo()                                                   # ...is undone, report back at the head
        self.assertEqual(fingerprint(s), restored)

        s.undo()                                                   # restoring the version is undoable too
        self.assertEqual(fingerprint(s), empty)

    def test_restoring_replaces_the_state_even_when_the_scenery_already_has_data(self):
        self.store().save(populated(), "v1")
        s = rich_scenery()
        self.store().restore(s, "v1")
        self.assertEqual(fingerprint(s), fingerprint(populated()))
        self.assertEqual(len(s.queue), 0)

    def test_a_version_holds_neither_the_undo_stack_nor_other_versions(self):
        self.store().save(rich_scenery(), "uno")
        self.store().save(rich_scenery(), "dos")
        with open(os.path.join(self.directory, "version_dos.json"), encoding="utf-8") as f:
            document = json.load(f)
        self.assertEqual(set(document), {"tipo", "nombre", "guardada", "escenario"})
        self.assertFalse({"versiones", "historial", "undo", "pila"} & set(document["escenario"]))
        self.assertEqual(len(document["escenario"]["eventos_activos"]), 8)


class TestNamesAndFiles(VersionTestCase):
    def test_invalid_names_are_refused_and_nothing_is_written(self):
        s = populated()
        for bad in ("", "   ", "../escape", "a/b", "a\\b", "x" * 41, "punto.json", None, 5):
            with self.subTest(name=bad):
                self.assertFalse(self.store().save(s, bad).success)
                self.assertFalse(self.store().restore(s, bad).success)
        self.assertEqual(os.listdir(self.directory), [])

    def test_duplicate_names_are_refused_even_if_they_only_differ_in_case(self):
        a, b = populated(), rich_scenery()
        self.assertTrue(self.store().save(a, "Prueba").success)
        self.assertFalse(self.store().save(b, "prueba").success)
        fresh = make_scenery(AVL())
        self.store().restore(fresh, "PRUEBA")
        self.assertEqual(fingerprint(fresh), fingerprint(a))       # the original was not overwritten

    def test_save_leaves_no_temporary_files(self):
        self.store().save(populated(), "limpia")
        self.assertEqual(os.listdir(self.directory), ["version_limpia.json"])

    def test_list_is_oldest_first_and_skips_unreadable_files(self):
        clock = iter(datetime(2026, 9, 7, h, tzinfo=timezone.utc) for h in (9, 8, 10))
        store = VersionStore(self.directory, now=lambda: next(clock))
        for name in ("tercera", "primera", "segunda"):
            store.save(populated(), name)
        with open(os.path.join(self.directory, "version_rota.json"), "w") as f:
            f.write("{ not json")
        self.assertEqual([v.name for v in store.list()], ["primera", "tercera", "segunda"])
        self.assertEqual(VersionStore(os.path.join(self.directory, "no_existe")).list(), [])

    def test_unknown_missing_or_damaged_versions_fail_without_touching_the_scenery(self):
        self.store().save(populated(), "buena")
        path = os.path.join(self.directory, "version_buena.json")
        with open(path, encoding="utf-8") as f:
            good = json.load(f)
        damaged = copy.deepcopy(good)
        damaged["escenario"]["eventos_activos"]["1"]["priority"] = 3     # tampered derived value
        for label, content in (("tampered", json.dumps(damaged)), ("not json", "{ nope")):
            with self.subTest(case=label):
                with open(path, "w", encoding="utf-8") as f:
                    f.write(content)
                s = rich_scenery()
                before = fingerprint(s)
                self.assertFalse(self.store().restore(s, "buena").success)
                self.assertEqual(fingerprint(s), before)
                self.assertFalse(s.history.can_redo())
        s = rich_scenery()
        before = fingerprint(s)
        self.assertFalse(self.store().restore(s, "no existe").success)
        self.assertEqual(fingerprint(s), before)


class TestQueuePersistence(unittest.TestCase):
    """The queue is part of the structural export (section 12), in its original order."""

    def test_round_trip_keeps_order_and_even_out_of_range_reports(self):
        s = rich_scenery()
        package = ScenarioPackage()
        parsed = package.parse(package.export(s))
        self.assertTrue(parsed.success, parsed.errors)
        fresh = make_scenery(AVL())
        package.apply(fresh, parsed.state)
        self.assertEqual(fresh.queue.to_list(), s.queue.to_list())
        processor = ReportProcessor(fresh)
        decisions = [processor.process_next().decision for _ in range(3)]
        self.assertEqual(decisions, [Decision.UPDATED, Decision.CONFIRMED, Decision.REJECTED])

    def test_files_saved_before_the_queue_existed_still_load_with_an_empty_queue(self):
        exported = ScenarioPackage().export(rich_scenery())
        del exported["cola"]
        parsed = ScenarioPackage().parse(exported)
        self.assertTrue(parsed.success)
        self.assertEqual(len(parsed.state["queue"]), 0)

    def test_malformed_queue_entries_reject_the_whole_load(self):
        def corrupt(change):
            data = ScenarioPackage().export(rich_scenery())
            change(data["cola"])
            return ScenarioPackage().parse(data)

        cases = {
            "missing field": lambda q: q[0].pop("revision"),
            "NaN magnitude": lambda q: q[0].update(magnitude=float("nan")),
            "bool revision": lambda q: q[0].update(revision=True),
            "float event id": lambda q: q[0].update(event_id=1.5),
            "naive time": lambda q: q[0].update(ocurredAt="2026-09-03T12:00:00"),
            "station not text": lambda q: q[0].update(station=7),
            "entry not an object": lambda q: q.__setitem__(0, 5),
        }
        for label, change in cases.items():
            with self.subTest(case=label):
                result = corrupt(change)
                self.assertFalse(result.success)
                self.assertTrue(any("Cola" in message for message in result.errors), result.errors)
        data = ScenarioPackage().export(rich_scenery())
        data["cola"] = "nothing"
        self.assertFalse(ScenarioPackage().parse(data).success)


if __name__ == "__main__":
    unittest.main(verbosity=2)