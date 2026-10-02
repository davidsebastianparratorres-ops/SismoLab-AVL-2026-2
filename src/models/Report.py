from collections import deque
from dataclasses import dataclass
from datetime import datetime


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