from src.models.Point import Point
from src.rules.ZoneClassifier import ZoneClassifier


class PriorityCalculator:
    #Deterministic priority calculator based on the strict order of Section 4.

    @staticmethod
    def calculate_priority(magnitude: float, depth: float, epicenter: Point, zone_classifier: ZoneClassifier) -> int:
        
          #Derives the event priority (3: High, 2: Medium, 1: Low).


        is_populated = zone_classifier.is_in_populated_zone(epicenter)

        # Priority 3 (High): M ≥ 6.0; or M ≥ 4.5 and H ≤ 30.0 km in a populated area.
        if magnitude >= 6.0:
            return 3
        if magnitude >= 4.5 and depth <= 30.0 and is_populated:
            return 3

        # Priority 2 (Medium): Not High and M >= 4.5.
        if magnitude >= 4.5:
            return 2

        # Priority 1 (Low): Any other case.
        return 1