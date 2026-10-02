"""Generates the reproducible data files and the evidence report for the
section 16 cases 'Reporte tardio' and 'Persistencia y consistencia'.

Run from the repository root:   python tests/generate_test_data.py
Writes: data/caso_*.json, data/persistencia_*.json, evidencias/evidencia_casos.md
"""
import copy
import json
import os
import sys

sys.path.insert(0, ".")

from datetime import datetime, timezone

from src.models.AVL import AVL
from src.models.BST import BST
from src.models.Zone import Zone
from src.models.Station import Station
from src.models.SimulationClock import SimulationClock
from src.models.SimulationParameters import SimulationParameters
from src.controllers.Scenery import Scenery
from src.controllers.ScenarioPackage import ScenarioPackage

DATA_DIR = "data"
EVIDENCE_DIR = "evidencias"


def utc(hour, minute):
    return datetime(2026, 9, 7, hour, minute, 0, tzinfo=timezone.utc)


def make_scenery(tree):
    # Initial state shared by every case: two adjacent zones (the border x = 500
    # belongs to both), one station, clock at 2026-09-07T12:00:00Z, W=48, R=40, L=3, T=72.
    return Scenery(
        zones=[Zone(0.0, 500.0, 0.0, 1000.0, False), Zone(500.0, 1000.0, 0.0, 1000.0, True)],
        stations={"EST-01": Station("EST-01", "Norte")},
        simulation_clock=SimulationClock(utc(12, 0)),
        tree=tree,
        parameters=SimulationParameters(),
    )


def create(scenery, event_id, magnitude, depth, x, y, when):
    result = scenery.create_event(event_id, magnitude, depth, x, y, when, "EST-01")
    assert result.success, result.message


def write_json(name, data):
    path = os.path.join(DATA_DIR, name)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    return path


def reference_of(scenery, event_id):
    stored = scenery.association_manager.associations.get(event_id)
    return stored.reference_id if stored else None


checks = []  # (case, description, expected, obtained)


def check(case, description, expected, obtained):
    checks.append((case, description, expected, obtained))


def main():
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(EVIDENCE_DIR, exist_ok=True)
    package = ScenarioPackage()

    # ------------------------------------------------------------------
    # CASE: Reporte tardio
    # ------------------------------------------------------------------
    case = "Reporte tardío"
    scenery = make_scenery(AVL())
    create(scenery, 1, 5.6, 10.0, 100.0, 100.0, utc(10, 0))
    create(scenery, 2, 4.2, 10.0, 105.0, 100.0, utc(10, 20))
    write_json("caso_reporte_tardio_inicial.json", package.export(scenery))
    check(case, "Antes del reporte tardío: referencia del evento 2", 1, reference_of(scenery, 2))
    check(case, "Antes del reporte tardío: referencia del evento 1", None, reference_of(scenery, 1))

    create(scenery, 3, 6.1, 10.0, 102.0, 104.0, utc(9, 55))  # M 6.1 that happened at 09:55
    manager = scenery.association_manager
    cand2, _ = manager.get_candidates_and_reference(2)
    cand1, _ = manager.get_candidates_and_reference(1)
    check(case, "Candidatos nuevos del evento 2", [1, 3], sorted(e.getEventId() for e in cand2))
    check(case, "Candidatos nuevos del evento 1", [3], sorted(e.getEventId() for e in cand1))
    check(case, "Referencia elegida del evento 2 (mayor magnitud)", 3, reference_of(scenery, 2))
    check(case, "Referencia elegida del evento 1", 3, reference_of(scenery, 1))
    check(case, "Referencia del evento 3 (el más antiguo)", None, reference_of(scenery, 3))
    check(case, "Nodos en el AVL (no se crea nodo duplicado)", 3, scenery.tree.getSize())
    write_json("caso_reporte_tardio_final.json", package.export(scenery))

    scenery.undo()
    check(case, "Tras deshacer: referencia del evento 2 vuelve a", 1, reference_of(scenery, 2))
    check(case, "Tras deshacer: el evento 3 ya no está activo", False, 3 in scenery.active_events)

    # ------------------------------------------------------------------
    # CASE: Persistencia y consistencia
    # ------------------------------------------------------------------
    case = "Persistencia"
    normal = make_scenery(AVL())
    for event_id, (magnitude, x) in enumerate(
            [(5.6, 100.0), (4.2, 105.0), (6.1, 102.0), (3.0, 700.0), (4.6, 650.0)], start=1):
        create(normal, event_id, magnitude, 10.0, x, 100.0, utc(10, event_id))
    normal.correct_event(2, 6.2, 15.0, 105.0, 100.0, "EST-01")
    normal.mark_as_reviewed(3)
    normal.delete_event(4)
    normal_data = json.loads(json.dumps(package.export(normal)))
    write_json("persistencia_normal.json", normal_data)

    result = package.parse(normal_data)
    check(case, "Topología normal: el archivo se acepta", True, result.success)
    restored = make_scenery(AVL())
    package.apply(restored, result.state)
    check(case, "Topología normal: exportar lo cargado reproduce el mismo JSON",
          True, package.export(restored) == normal_data)
    check(case, "Topología normal: métrica 'correcciones aceptadas' restaurada", 1,
          restored.metrics.get("corrections_accepted"))
    check(case, "Topología normal: identificador 4 sigue retirado", True, 4 in restored.eliminated_ids)

    stress = make_scenery(BST())
    for event_id, magnitude in enumerate([3.0, 3.1, 3.2, 3.3, 3.4], start=1):
        create(stress, event_id, magnitude, 10.0, 100.0, 100.0, utc(10, event_id))
    stress.stress_mode = True
    stress_data = json.loads(json.dumps(package.export(stress)))
    write_json("persistencia_estres.json", stress_data)

    result = package.parse(stress_data)
    check(case, "Topología en estrés (modo ESTRES): el archivo se acepta", True, result.success)
    check(case, "Topología en estrés: nodos desbalanceados señalados", 3,
          result.state["imbalanced"] if result.success else None)
    as_normal = copy.deepcopy(stress_data)
    as_normal["modo"] = "NORMAL"
    check(case, "El mismo archivo declarado NORMAL se rechaza", False, package.parse(as_normal).success)

    case = "Consistencia"
    bad = copy.deepcopy(normal_data)
    first_id = next(iter(bad["eventos_activos"]))
    original_priority = bad["eventos_activos"][first_id]["priority"]
    bad["eventos_activos"][first_id]["priority"] = 3 if original_priority != 3 else 1
    write_json("persistencia_inconsistente.json", bad)

    live = make_scenery(AVL())
    for event_id, (magnitude, x) in enumerate([(5.6, 100.0), (4.2, 105.0)], start=1):
        create(live, event_id, magnitude, 10.0, x, 100.0, utc(10, event_id))
    before = package.export(live)
    undo_before = live.history.can_undo()
    result = package.parse(bad)
    check(case, "Archivo inconsistente (prioridad alterada): se rechaza", False, result.success)
    check(case, "Se informa el problema", True,
          any("prioridad almacenada" in m for m in result.errors))
    check(case, "El escenario actual no cambió", True, package.export(live) == before)
    check(case, "No se registró ninguna acción en el historial", undo_before, live.history.can_undo())

    # ------------------------------------------------------------------
    # Evidence report
    # ------------------------------------------------------------------
    lines = [
        "# Evidencia de casos mínimos (sección 16)",
        "",
        "Generado por `tests/generate_test_data.py`. Estado inicial común: zonas "
        "`[0,500]x[0,1000]` no poblada y `[500,1000]x[0,1000]` poblada, estación EST-01, "
        "reloj en 2026-09-07T12:00:00Z, W=48 h, R=40 km, L=3, T=72 h.",
        "",
    ]
    for group in ("Reporte tardío", "Persistencia", "Consistencia"):
        lines += [f"## {group}", "", "| Verificación | Esperado | Obtenido | Resultado |", "|---|---|---|---|"]
        for case_name, description, expected, obtained in checks:
            if case_name == group:
                lines.append(f"| {description} | `{expected}` | `{obtained}` | "
                             f"{'OK' if expected == obtained else 'FALLA'} |")
        lines.append("")
    failures = [c for c in checks if c[2] != c[3]]
    lines.append(f"**Total: {len(checks)} verificaciones, {len(failures)} fallas.**")
    with open(os.path.join(EVIDENCE_DIR, "evidencia_casos.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    print("\n".join(lines))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())