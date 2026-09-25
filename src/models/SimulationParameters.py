import math
#Configurable simulation parameters W, R, L, T (Section 3).
class SimulationParameters:
   
    #W: maximum time difference (hours) to be an association candidate
    #R: maximum distance between epicenters (km) to qualify as a candidate
    #L: node depth limit for the expensive access mark, integer >= 0
    #T: minimum age (hours) for a branch to be archived


    #Default:

    W = 48.0
    R= 40.0
    L = 3
    T= 72.0

    def __init__(self, w=W, r=R, l=L, t=T):
        errors = self.validate(w, r, l, t)
        if errors:
            raise ValueError(" ".join(errors))
        self._w, self._r, self._l, self._t = w, r, l, t

    # Validation Helpers 
    @staticmethod
    def _is_positive_number(value) -> bool:
        
        return (isinstance(value, (int, float)) and not isinstance(value, bool)
                and math.isfinite(value) and value > 0)

    @staticmethod
    def validate(w, r, l, t) -> list:
        #Validates parameter values. Returns a list of error messages (empty list = valid)
        errors = []
        if not SimulationParameters._is_positive_number(w):
            errors.append("W (hours) must be a finite number greater than 0.")
        if not SimulationParameters._is_positive_number(r):
            errors.append("R (km) must be a finite number greater than 0.")
        if not (isinstance(l, int) and not isinstance(l, bool) and l >= 0):
            errors.append("L must be an integer greater than or equal to 0.")
        if not SimulationParameters._is_positive_number(t):
            errors.append("T (hours) must be a finite number greater than 0.")
        return errors

    def update(self, w=None, r=None, l=None, t=None) -> list:
        #Updates only specified parameters. Returns error messages (empty list = success).
        #Parameters passed as None retain their current value. If any resulting ->
        #value is invalid, no parameters are updated (atomic behavior).
        
        new_w = self._w if w is None else w
        new_r = self._r if r is None else r
        new_l = self._l if l is None else l
        new_t = self._t if t is None else t
        errors = self.validate(new_w, new_r, new_l, new_t)
        if errors:
            return errors
        self._w, self._r, self._l, self._t = new_w, new_r, new_l, new_t
        return []
    
    #Read-Only Properties
    @property
    def w(self): return self._w
    @property
    def r(self): return self._r
    @property
    def l(self): return self._l
    @property
    def t(self): return self._t

    #Undo || Snapshot state management
    def copy(self) -> "SimulationParameters":

        #Takes a snapshot of the parameters state for the undo stack.
        return SimulationParameters(self._w, self._r, self._l, self._t)

    def restore(self, snapshot: "SimulationParameters") -> None:
        #Restores parameters to a previous snapshot state taken with copy().
        self._w, self._r, self._l, self._t = snapshot._w, snapshot._r, snapshot._l, snapshot._t

    #Persistence -
    def to_dict(self) -> dict:
        return {"W": self._w, "R": self._r, "L": self._l, "T": self._t}

    @staticmethod
    def from_dict(data) -> tuple:
        #Returns a tuple (parameters, errors). If errors exist, parameters is None.
        if not isinstance(data, dict):
            return None, ["Parameters section must be an object."]
        missing = [key for key in ("W", "R", "L", "T") if key not in data]
        if missing:
            return None, ["Missing parameters: " + ", ".join(missing) + "."]
        errors = SimulationParameters.validate(data["W"], data["R"], data["L"], data["T"])
        if errors:
            return None, errors
        return SimulationParameters(data["W"], data["R"], data["L"], data["T"]), []