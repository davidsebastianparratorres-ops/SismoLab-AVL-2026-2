import json
from types import SimpleNamespace

from src.models.Event import Event
from src.models.Key import Key
from src.models.Node import Node
from src.models.Point import Point
from src.models.Zone import Zone
from src.models.Station import Station
from src.models.Metrics import Metrics
from src.models.SimulationClock import SimulationClock, parse_iso_utc, format_iso_utc, ensure_datetime
from src.models.SimulationParameters import SimulationParameters
from src.rules.EventRules import belongs_to_populated_zone, calculate_priority
from src.rules.EventValidator import validate_ranges
from src.controllers.TreeAuditor import TreeAuditor
from src.controllers.AssociationManager import AssociationManager
from src.models.Report import Report, ReportQueue

SCHEMA_VERSION = 1
MODES = ("NORMAL", "ESTRES")


class PackageResult:
    """Success: carries the fully built, validated state (nothing applied yet).
    Failure: carries the list of problems; state stays None."""

    def __init__(self, success, errors=None, state=None):
        self.success = success
        self.errors = errors if errors is not None else []
        self.state = state


class ScenarioPackage:
    """Whole-scenario export/import (section 12, 'Guardado estructural').

    Load is all-or-nothing: parse() builds and validates everything in
    temporary objects; only apply() touches the live scenery.
    """

    # ------------------------------------------------------------------
    # Export
    # ------------------------------------------------------------------
    def export(self, scenery, stress_mode=None, extras=None) -> dict:
        if stress_mode is None:
            stress_mode = getattr(scenery, "stress_mode", False)
        return {
            "tipo": "ESCENARIO",
            "version": SCHEMA_VERSION,
            "modo": "ESTRES" if stress_mode else "NORMAL",
            "reloj": scenery.simulation_clock.to_dict(),
            "parametros": scenery.parameters.to_dict(),
            "metricas": scenery.metrics.to_dict(),
            "zonas": [self._zone_to_dict(z) for z in scenery.zones],
            "estaciones": {sid: self._station_name(s) for sid, s in scenery.stations.items()},
            "arbol": self._tree_to_dict(scenery.tree.getRoot()),
            "eventos_activos": {str(i): self._event_to_dict(e) for i, e in scenery.active_events.items()},
            "historico": {
                "archivados": {str(i): self._event_to_dict(e) for i, e in scenery.archived_events.items()},
                            "cola": [report.to_dict() for report in scenery.queue.to_list()],
                "eliminados": sorted(scenery.eliminated_ids),
            },
            "asociaciones": {str(r): ref for r, ref in scenery.association_manager.to_dict().items()},
            "cola": [report.to_dict() for report in scenery.queue.to_list()],
            "extras": extras or {},
            "extras": extras or {},  # queue, versions, ... (owned by teammates)
        }

    def save(self, scenery, filepath, stress_mode=None, extras=None) -> None:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(self.export(scenery, stress_mode, extras), f, indent=2, ensure_ascii=False)

    # ------------------------------------------------------------------
    # Import: parse + validate (never touches the live scenario)
    # ------------------------------------------------------------------
    def load(self, filepath) -> PackageResult:
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, json.JSONDecodeError) as error:
            return PackageResult(False, ["No se pudo leer el archivo: " + str(error)])
        return self.parse(data)

    def parse(self, data) -> PackageResult:
        try:
            return self._parse(data)
        except (KeyError, TypeError, AttributeError, ValueError) as error:
            return PackageResult(False, ["Archivo mal formado: " + repr(error)])

    def _parse(self, data) -> PackageResult:
        if data.get("tipo") != "ESCENARIO":
            return PackageResult(False, ["El archivo no es de tipo ESCENARIO."])
        if data.get("version") != SCHEMA_VERSION:
            return PackageResult(False, ["Versión de esquema no soportada: " + str(data.get("version"))])

        errors = []
        mode = data["modo"]
        if mode not in MODES:
            errors.append("Modo inválido: " + str(mode))
        zones, e = self._zones_from(data["zonas"]); errors += e
        stations = {sid: Station(sid, name) for sid, name in data["estaciones"].items()}
        clock, e = SimulationClock.from_dict(data["reloj"]); errors += e
        params, e = SimulationParameters.from_dict(data["parametros"]); errors += e
        metrics, e = Metrics.from_dict(data["metricas"]); errors += e
        if errors:  # later stages need valid zones / clock / params
            return PackageResult(False, errors)

        stress = (mode == "ESTRES")
        events, e = self._events_from(data["eventos_activos"], zones, stations); errors += e
        archived, e = self._events_from(data["historico"]["archivados"], zones, stations); errors += e
        eliminated = {int(i) for i in data["historico"]["eliminados"]}
        queue, e = self._queue_from(data.get("cola", [])); errors += e
        # Identities must not be duplicated across active / archived / eliminated.
        for a, b, label in ((events, archived, "activo y archivado"),
                            (events, eliminated, "activo y eliminado"),
                            (archived, eliminated, "archivado y eliminado")):
            for dup in set(a) & set(b):
                errors.append(f"El identificador {dup} figura como {label} a la vez.")

        # Occurrence times may not be later than the simulation clock (section 3).
        for event in list(events.values()) + list(archived.values()):
            if event.getOcurredAt() > clock.current_time:
                errors.append(f"Evento {event.getEventId()}: ocurre después del reloj de simulación.")

        root, e = self._tree_from(data["arbol"], events); errors += e
        if errors:
            return PackageResult(False, errors)

        # Order, uniqueness, references, heights, balance factors (section 14).
        report = TreeAuditor().audit(root, events, stress_mode=stress,
                                     archived_ids=set(archived), eliminated_ids=eliminated)
        errors += [f"[{i.category}] Evento {i.event_id}: {i.message}" for i in report.errors()]
        if errors:
            return PackageResult(False, errors)

        # Stored associations must equal the deterministic recomputation.
        stored = {int(r): int(ref) for r, ref in data["asociaciones"].items()}
        scratch = SimpleNamespace(parameters=params, active_events=events, archived_events=archived)
        manager = AssociationManager(scratch)
        manager.recalculate_all()
        if manager.to_dict() != stored:
            return PackageResult(False, ["Las asociaciones almacenadas no coinciden con las recalculadas."])

        return PackageResult(True, state={
            "zones": zones, "stations": stations, "clock": clock, "parameters": params,
            "metrics": metrics, "stress_mode": stress, "root": root,
            "active_events": events, "archived_events": archived, "eliminated_ids": eliminated,
                        "associations": manager.associations, "queue": queue, "extras": data.get("extras", {}),
            "imbalanced": report.imbalanced_count,  # UI must flag this when stress is on
        })

    # ------------------------------------------------------------------
    # Apply: only called after parse() succeeded
    # ------------------------------------------------------------------
    def apply(self, scenery, state) -> None:
        scenery.history.record()  # loading is one undoable action (section 13)
        scenery.zones = state["zones"]
        scenery.stations = state["stations"]
        scenery.simulation_clock.restore(state["clock"])
        scenery.parameters.restore(state["parameters"])
        scenery.metrics.restore(state["metrics"])
        scenery.tree.setRoot(state["root"])
        scenery.active_events = state["active_events"]
        scenery.archived_events = state["archived_events"]
        scenery.eliminated_ids = state["eliminated_ids"]
        scenery.association_manager.associations = state["associations"]
        scenery.queue.restore(state["queue"])
        scenery.stress_mode = state["stress_mode"]  # attribute owned by the stress-mode owner

    # ------------------------------------------------------------------
    # Builders / serializers
    # ------------------------------------------------------------------
    @staticmethod
    def _station_name(station):
        return station.getName() if hasattr(station, "getName") else str(station)

    @staticmethod
    def _zone_to_dict(z):
        return {"x_min": z.getXMin(), "x_max": z.getXMax(),
                "y_min": z.getYMin(), "y_max": z.getYMax(), "populated": z.getPopulated()}

    @staticmethod
    def _zones_from(raw_zones):
        zones, errors = [], []
        for i, raw in enumerate(raw_zones):
            x0, x1, y0, y1 = raw["x_min"], raw["x_max"], raw["y_min"], raw["y_max"]
            if not (0.0 <= x0 < x1 <= 1000.0 and 0.0 <= y0 < y1 <= 1000.0):
                errors.append(f"Zona {i}: límites inválidos (deben estar en [0, 1000] con mín < máx).")
                continue
            if not isinstance(raw["populated"], bool):
                errors.append(f"Zona {i}: 'populated' debe ser booleano.")
                continue
            zones.append(Zone(x0, x1, y0, y1, raw["populated"]))
        return zones, errors

    @staticmethod
    def _event_to_dict(event):
        epi = event.getEpicenter()
        return {"magnitude": event.getMagnitude(), "depth": event.getDepth_km(),
                "epicenter": {"x": epi.getX(), "y": epi.getY()},
                "status": event.getStatus(), "stations": list(event.getStations()),
                "ocurredAt": format_iso_utc(ensure_datetime(event.getOcurredAt())),
                "priority": event.getPriority(), "review": event.getReview()}

    @staticmethod
    def _events_from(raw_events, zones, known_stations):
        events, errors = {}, []
        for id_str, raw in raw_events.items():
            event_id = int(id_str)
            epi = raw["epicenter"]
            problems = validate_ranges(event_id, raw["magnitude"], raw["depth"], epi["x"], epi["y"])
            if type(raw["review"]) is not int or raw["review"] < 1:
                problems.append("La revisión debe ser un entero positivo.")
            emitters = raw["stations"]
            if not emitters:
                problems.append("El evento debe tener al menos una estación con reporte aceptado.")
            elif len(set(emitters)) != len(emitters):
                problems.append("Hay estaciones repetidas.")
            problems += [f"Estación desconocida: {sid}." for sid in emitters if sid not in known_stations]
            if raw["status"] not in ("PENDING", "REVIEWED"):
                problems.append("Estado de atención inválido.")
            try:
                occurred_at = parse_iso_utc(raw["ocurredAt"])
            except ValueError as error:
                problems.append("ocurredAt inválido: " + str(error))
            if problems:
                errors += [f"Evento {event_id}: {p}" for p in problems]
                continue
            point = Point(epi["x"], epi["y"])
            expected = calculate_priority(raw["magnitude"], raw["depth"],
                                          belongs_to_populated_zone(point, zones))
            if expected != raw["priority"]:
                errors.append(f"Evento {event_id}: prioridad almacenada ({raw['priority']}) "
                              f"no coincide con la calculada ({expected}).")
                continue
            events[event_id] = Event(
                event_id=event_id, magnitude=raw["magnitude"], epicenter=point,
                depth_km=raw["depth"], status=raw["status"], stations=list(raw["stations"]),
                ocurredAt=occurred_at, priority=raw["priority"], review=raw["review"])
        return events, errors

    @staticmethod
    def _queue_from(raw_queue):
        if not isinstance(raw_queue, list):
            return None, ["La cola debe ser una lista de reportes."]
        reports, errors = [], []
        for position, raw in enumerate(raw_queue, start=1):
            report, problems = Report.from_dict(raw)
            errors += [f"Cola, reporte {position}: {p}" for p in problems]
            if report is not None:
                reports.append(report)
        return ReportQueue(reports), errors


    @staticmethod
    def _tree_to_dict(root):
        if root is None:
            return None

        def shell(node):
            k = node.getKey()
            return {"event_id": node.getEventId(),
                    "key": {"priority": k.priority, "magnitude": k.magnitude, "identifier": k.identifier},
                    "altura": node.getHeight(), "factorEquilibrio": node.getBalanceFactor(),
                    "izquierdo": None, "derecho": None}

        root_dict = shell(root)
        stack = [(root, root_dict)]
        while stack:  # explicit stack: a stress-mode chain must not hit the recursion limit
            node, d = stack.pop()
            for child, name in ((node.getLeft(), "izquierdo"), (node.getRight(), "derecho")):
                if child is not None:
                    child_dict = shell(child)
                    d[name] = child_dict
                    stack.append((child, child_dict))
        return root_dict

    @staticmethod
    def _tree_from(raw_root, events):
        errors, seen, root = [], set(), None
        stack = [(raw_root, None, None)]
        while stack:
            raw, parent, side = stack.pop()
            if raw is None:
                continue
            event_id = raw["event_id"]
            if event_id not in events:
                errors.append(f"El nodo referencia el evento {event_id}, que no está en 'eventos_activos'.")
                continue
            if event_id in seen:
                errors.append(f"El evento {event_id} aparece en más de una posición del árbol.")
                continue
            k = raw["key"]
            if k["identifier"] != event_id:
                errors.append(f"Nodo {event_id}: la clave trae otro identificador ({k['identifier']}).")
                continue
            seen.add(event_id)
            node = Node(Key(k["priority"], k["magnitude"], k["identifier"]), event_id)
            node.setParent(parent)
            node.setHeight(raw.get("altura"))
            node.setBalanceFactor(raw.get("factorEquilibrio"))
            if parent is None:
                root = node
            elif side == "left":
                parent.setLeft(node)
            else:
                parent.setRight(node)
            stack.append((raw.get("derecho"), node, "right"))
            stack.append((raw.get("izquierdo"), node, "left"))
        for orphan in set(events) - seen:
            errors.append(f"El evento {orphan} está en 'eventos_activos' pero no tiene nodo en 'arbol'.")
        return root, errors