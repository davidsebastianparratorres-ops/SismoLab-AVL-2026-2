import copy
import json
import os
import tempfile
import unittest
from datetime import datetime, timezone

from src.models.AVL import AVL
from src.models.BST import BST
from src.models.Zone import Zone
from src.models.Station import Station
from src.models.SimulationClock import SimulationClock
from src.models.SimulationParameters import SimulationParameters
from src.controllers.Scenery import Scenery
from src.controllers.ScenarioPackage import ScenarioPackage


def utc(hour, minute):
    return datetime(2026, 9, 7, hour, minute, 0, tzinfo=timezone.utc)


def make_scenery(tree):
    return Scenery(
        zones=[Zone(0.0, 500.0, 0.0, 1000.0, False), Zone(500.0, 1000.0, 0.0, 1000.0, True)],
        stations={"EST-01": Station("EST-01", "Norte")},
        simulation_clock=SimulationClock(utc(12, 0)),
        tree=tree,
        parameters=SimulationParameters(),
    )


def fill(scenery, rows):
    """rows: (magnitude, x) per event; ids are 1..n, minutes 1..n."""
    for event_id, (magnitude, x) in enumerate(rows, start=1):
        result = scenery.create_event(event_id, magnitude, 10.0, x, 100.0, utc(10, event_id), "EST-01")
        assert result.success, result.message


class TestPersistence(unittest.TestCase):
    """Section 16 - 'Persistencia y consistencia' (the part that does not
    depend on the queue or on named versions)."""

    def setUp(self):
        self.package = ScenarioPackage()

    # --- normal topology -------------------------------------------------
    def test_normal_topology_round_trip(self):
        original = make_scenery(AVL())
        fill(original, [(5.6, 100.0), (4.2, 105.0), (6.1, 102.0), (3.0, 700.0), (4.6, 650.0)])
        original.correct_event(2, 6.2, 15.0, 105.0, 100.0, "EST-01")
        original.mark_as_reviewed(3)
        original.delete_event(4)

        exported = json.loads(json.dumps(self.package.export(original)))
        result = self.package.parse(exported)
        self.assertTrue(result.success, result.errors)

        restored = make_scenery(AVL())
        self.package.apply(restored, result.state)

        self.assertEqual(self.package.export(restored), self.package.export(original))
        self.assertEqual(restored.metrics.get("corrections_accepted"), 1)
        self.assertIn(4, restored.eliminated_ids)
        self.assertEqual(restored.association_manager.to_dict(), original.association_manager.to_dict())

    def test_loading_is_one_undoable_action(self):
        source = make_scenery(AVL())
        fill(source, [(5.6, 100.0), (4.2, 105.0)])
        state = self.package.parse(self.package.export(source)).state

        target = make_scenery(AVL())
        self.package.apply(target, state)
        self.assertEqual(len(target.active_events), 2)

        self.assertTrue(target.undo().success)
        self.assertEqual(len(target.active_events), 0)
        self.assertIsNone(target.tree.getRoot())

    # --- stress topology -------------------------------------------------
    def _degenerate_scenery(self):
        scenery = make_scenery(BST())  # no balancing: ascending keys form a chain
        fill(scenery, [(3.0, 100.0), (3.1, 100.0), (3.2, 100.0), (3.3, 100.0), (3.4, 100.0)])
        scenery.stress_mode = True
        return scenery

    def test_stress_topology_round_trip_and_is_flagged(self):
        exported = json.loads(json.dumps(self.package.export(self._degenerate_scenery())))
        self.assertEqual(exported["modo"], "ESTRES")

        result = self.package.parse(exported)
        self.assertTrue(result.success, result.errors)
        self.assertTrue(result.state["stress_mode"])
        self.assertEqual(result.state["imbalanced"], 3)  # the UI must flag this

        restored = make_scenery(BST())
        self.package.apply(restored, result.state)
        self.assertTrue(restored.stress_mode)
        self.assertEqual(self.package.export(restored), exported)  # same real topology

    def test_unbalanced_topology_is_rejected_in_normal_mode(self):
        exported = self.package.export(self._degenerate_scenery())
        exported["modo"] = "NORMAL"
        result = self.package.parse(exported)
        self.assertFalse(result.success)
        self.assertTrue(any("BALANCE" in message for message in result.errors))

    # --- inconsistent files ---------------------------------------------
    def _base_export(self):
        scenery = make_scenery(AVL())
        fill(scenery, [(5.6, 100.0), (4.2, 105.0), (6.1, 102.0)])
        return scenery, self.package.export(scenery)

    def _assert_rejected(self, tamper, expected_text):
        _, exported = self._base_export()
        tamper(exported)
        result = self.package.parse(exported)
        self.assertFalse(result.success)
        self.assertIsNone(result.state)
        self.assertTrue(any(expected_text in message for message in result.errors), result.errors)

    def test_rejects_wrong_stored_priority(self):
        self._assert_rejected(lambda d: d["eventos_activos"]["1"].update(priority=3), "prioridad almacenada")

    def test_rejects_wrong_stored_height(self):
        self._assert_rejected(lambda d: d["arbol"].update(altura=7), "HEIGHT")

    def test_rejects_wrong_stored_balance_factor(self):
        self._assert_rejected(lambda d: d["arbol"].update(factorEquilibrio=1), "BALANCE")

    def test_rejects_key_that_disagrees_with_event(self):
        self._assert_rejected(lambda d: d["arbol"]["key"].update(magnitude=0.1), "REFERENCE")

    def test_rejects_stored_associations_that_differ_from_recomputed(self):
        self._assert_rejected(lambda d: d["asociaciones"].update({"1": 3}), "asociaciones")

    def test_rejects_event_without_node(self):
        def add_orphan(d):
            d["eventos_activos"]["99"] = copy.deepcopy(d["eventos_activos"]["1"])
        self._assert_rejected(add_orphan, "no tiene nodo")

    def test_rejects_event_after_simulation_clock(self):
        self._assert_rejected(lambda d: d["eventos_activos"]["1"].update(ocurredAt="2026-09-08T10:00:00Z"),
                              "reloj")

    def test_rejects_id_that_is_active_and_eliminated(self):
        self._assert_rejected(lambda d: d["historico"]["eliminados"].append(1), "eliminado")

    def test_rejects_missing_section(self):
        self._assert_rejected(lambda d: d.pop("reloj"), "mal formado")

    def test_rejects_wrong_type_and_version(self):
        for field, value in (("tipo", "OTRO"), ("version", 99)):
            _, exported = self._base_export()
            exported[field] = value
            self.assertFalse(self.package.parse(exported).success)

    def test_failed_load_leaves_current_scenario_untouched(self):
        live, _ = self._base_export()
        before = self.package.export(live)
        undo_available_before = live.history.can_undo()

        bad = copy.deepcopy(before)
        bad["eventos_activos"]["1"]["priority"] = 3
        result = self.package.parse(bad)
        self.assertFalse(result.success)

        # Nothing was applied: same data, and no history entry was recorded.
        self.assertEqual(self.package.export(live), before)
        self.assertEqual(live.history.can_undo(), undo_available_before)

    # --- file I/O --------------------------------------------------------
    def test_file_round_trip_and_unreadable_file(self):
        scenery, _ = self._base_export()
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "scenario.json")
            self.package.save(scenery, path)
            self.assertTrue(self.package.load(path).success)

            broken = os.path.join(folder, "broken.json")
            with open(broken, "w", encoding="utf-8") as f:
                f.write("{ not json")
            self.assertFalse(self.package.load(broken).success)
            self.assertFalse(self.package.load(os.path.join(folder, "missing.json")).success)


if __name__ == "__main__":
    unittest.main(verbosity=2)