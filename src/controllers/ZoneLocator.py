
from models.Point import Point

def belongs_to_populated_zone(epicenter: Point, zones: list) -> bool:
    for zone in zones:
        if zone.contains(epicenter) and zone.populated:
            return True
    return False