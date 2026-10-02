from datetime import datetime, timedelta, timezone

def parse_iso_utc(text: str) -> datetime:
    
    #Converts an ISO 8601 string (f.e., 2026-09-07T10:00:00Z) into a timezone-aware UTC datetime.
    #Raises ValueError if not a string, not ISO 8601, or missing timezone information.
    if not isinstance(text, str):
        raise ValueError("La fecha debe ser una cadena con formato ISO 8601.")
    normalized = text.strip()
    # fromisoformat does not parse the trailing "Z" in older Python versions,
    # so it is replaced with its "+00:00" equivalent.
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    value = datetime.fromisoformat(normalized)
    if value.tzinfo is None:
        raise ValueError("La fecha debe incluir una zona horaria (use 'Z' para UTC).")
    # Convert to UTC and strip microseconds for second-level precision.
    return value.astimezone(timezone.utc).replace(microsecond=0)

def ensure_datetime(value):
    """Accepts a datetime or an ISO 8601 string and always returns an
    aware UTC datetime. Single normalization point for events that come
    from different loaders."""
    return parse_iso_utc(value) if isinstance(value, str) else value

#Converts a datetime into an ISO 8601 UTC string with second-level precision.
def format_iso_utc(value: datetime) -> str:
    return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

# Explicit simulation clock (Section 3 of the specification).
# Only advances when explicitly requested by the user and only moves forward.
# Undo does not "rewind" the clock: it uses restore() with a snapshot taken beforehand.
    
class SimulationClock:
    

    def __init__(self, start_time: datetime):
        if not isinstance(start_time, datetime) or start_time.tzinfo is None:
            raise ValueError("La hora de inicio del reloj debe ser un objeto datetime con información de zona horaria.")
        self._current_time = start_time.astimezone(timezone.utc).replace(microsecond=0)

    @property
    def current_time(self) -> datetime:
        # Solo lectura: el Ãºnico modo de cambiarlo es advance() o restore().
        return self._current_time

    @staticmethod
    def validate_advance(delta) -> list:
            if not isinstance(delta, timedelta):
                return ["El avance del reloj debe ser un intervalo de tiempo."]
            if delta <= timedelta(0):
                return ["El reloj solo puede avanzar una cantidad positiva."]
            if delta.microseconds != 0:
                return ["El avance del reloj debe ser un número entero de segundos."]
            return []
    
    def advance(self, delta) -> list:
            errors = self.validate_advance(delta)
            if errors:
                return errors
            self._current_time = self._current_time + delta
            return []

    # Event age calculations (Sections 10 and 11) 
    def age_seconds(self, occurred_at: datetime) -> int:
        #Returns the difference in seconds between the current simulation time and the event occurrence time.
        return int((self._current_time - occurred_at).total_seconds())

    def is_older_than(self, occurred_at: datetime, hours: float) -> bool:
        #Returns True if the age is STRICTLY greater than `hours` (archiving rule).
        #Compared in seconds to avoid floating-point issues.
        return self.age_seconds(occurred_at) > hours * 3600

    # Undo || Snapshot state management 
    def copy(self) -> "SimulationClock":
        #Photo of the clock to save in the undo stack.
        return SimulationClock(self._current_time)

    def restore(self, snapshot: "SimulationClock") -> None:
        #Takes a snapshot of the clock state for the undo stack.
        self._current_time = snapshot._current_time

    #Takes a snapshot of the clock state for the undo stack.
    def to_dict(self) -> dict:
        return {"current_time": format_iso_utc(self._current_time)}

    @staticmethod
    def from_dict(data) -> tuple:
        #Returns a tuple (clock, errors). If errors exist, clock is None.
        if not isinstance(data, dict) or "current_time" not in data:
            return None, ["La secciÃ³n del reloj debe contener 'current_time'."]
        try:
            return SimulationClock(parse_iso_utc(data["current_time"])), []
        except ValueError as error:
            return None, [" Hora no válida: " + str(error)]
        
    