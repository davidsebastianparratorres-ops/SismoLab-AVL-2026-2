from collections import deque
from dataclasses import dataclass
from datetime import datetime
from src.models.SimulationClock import parse_iso_utc, format_iso_utc


@dataclass(frozen=True)
class Report:
    """One station report: the full event data plus revision and sender.
    Frozen (immutable), so snapshots can share report objects safely."""
    event_id: int
    magnitude: float
    depth_km: float
    epicenter_x: float
    epicenter_y: float
    occurred_at: datetime
    revision: int
    station_id: str
    
    
    def to_dict(self) -> dict:
        return {"event_id": self.event_id, "magnitude": self.magnitude, "depth": self.depth_km,
                "epicenter": {"x": self.epicenter_x, "y": self.epicenter_y},
                "ocurredAt": format_iso_utc(self.occurred_at), "revision": self.revision,
                "station": self.station_id}
 
    @staticmethod
    def from_dict(data):
        """Returns (report, errors). Only the SHAPE is checked: a report whose values are out of
        range is a legitimate pending report and is rejected later, when it is processed."""
        if not isinstance(data, dict):
            return None, ["Un reporte debe ser un objeto."]
        epicenter = data.get("epicenter") if isinstance(data.get("epicenter"), dict) else {}
        numbers = {"magnitude": data.get("magnitude"), "depth": data.get("depth"),
                   "epicenter.x": epicenter.get("x"), "epicenter.y": epicenter.get("y")}
        errors = [f"{name} debe ser un número finito." for name, value in numbers.items()
                  if type(value) not in (int, float) or not abs(value) < 1e12]  # also rejects NaN / inf
        errors += [f"{name} debe ser un entero." for name in ("event_id", "revision")
                   if type(data.get(name)) is not int]
        if not isinstance(data.get("station"), str):
            errors.append("station debe ser texto.")
        try:
            occurred_at = parse_iso_utc(data.get("ocurredAt"))
        except ValueError as error:
            errors.append("ocurredAt inválido: " + str(error))
        if errors:
            return None, errors
        return Report(data["event_id"], data["magnitude"], data["depth"], epicenter["x"], epicenter["y"],
                      occurred_at, data["revision"], data["station"]), []


class ReportQueue:
    """FIFO queue of pending reports. A deque gives O(1) enqueue and dequeue
    (a plain list would make dequeue O(n)). Order of arrival is never altered."""

    def __init__(self, reports=()):
        self.__items = deque(reports)

    def enqueue(self, report: Report) -> None:
        self.__items.append(report)

    def extend(self, reports) -> None:
        self.__items.extend(reports)

    def dequeue(self) -> Report:
        return self.__items.popleft()

    def peek(self):
        return self.__items[0] if self.__items else None

    def to_list(self) -> list:
        return list(self.__items)

    def __len__(self) -> int:
        return len(self.__items)

    # Undo || snapshot state management (same pattern as SimulationClock)
    def copy(self) -> "ReportQueue":
        return ReportQueue(self.__items)

    def restore(self, snapshot: "ReportQueue") -> None:
        self.__items = deque(snapshot.__items)