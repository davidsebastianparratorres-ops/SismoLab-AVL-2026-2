from typing import List, Tuple
from src.models.Point import Point
from src.models.Zone import Zone


class ZoneClassifier:
    #Geographic classifier that complies with the Boundary Rule of Section 3.

    DEFAULT_OFFSHORE_ZONE = Zone(0.0, 1000.0, 0.0, 1000.0, populated=False)

    def __init__(self, zones: List[Zone] = None):
        self.zones: List[Zone] = zones if zones is not None else []

    def add_zone(self, zone: Zone) -> None:
        self.zones.append(zone)

    def is_in_populated_zone(self, epicenter: Point) -> bool:
        '''Determine whether the epicenter is on or over the edge of a populated zone.

          Edge Rule (Section 3): If it lies on the boundary between two zones,
         classify it as populated if AT LEAST ONE of the two is populated.'''
        
        matching_zones = [z for z in self.zones if z.contains(epicenter)]
        if not matching_zones:
            return False
        return any(z.getPopulated() for z in matching_zones)

    def classify(self, epicenter: Point) -> Tuple[Zone, List[Zone]]:
        #Returns the representative zone and all zones affected by the epicenter.
        matching = [z for z in self.zones if z.contains(epicenter)]
        if not matching:
            return self.DEFAULT_OFFSHORE_ZONE, []

        #At edges/overlaps, prioritize the populated area.
        matching_sorted = sorted(matching, key=lambda z: (1 if z.getPopulated() else 0), reverse=True)
        return matching_sorted[0], matching