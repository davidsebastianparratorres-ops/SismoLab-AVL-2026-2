from models.Point import Point

def belongs_to_populated_zone(epicenter: Point, zones: list) -> bool:
    for zone in zones:
        if zone.contains(epicenter) and zone.populated:
            return True
    return False

def calculate_priority(magnitude:float, depth:float, is_in_populated_zone:bool) -> int:
    if magnitude >= 6.0:
        return 3
    if magnitude >= 4.5 and depth <= 30.0 and is_in_populated_zone:
        return 3
    if magnitude >= 4.5:
        return 2
    return 1

def search_cost(event_id, node_depths):
    depth = node_depths.get(event_id)
    return None if depth is None else depth + 1