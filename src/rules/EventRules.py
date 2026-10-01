from src.models.Point import Point

def belongs_to_populated_zone(epicenter: Point, zones: list) -> bool:
    for zone in zones:
        if zone.contains(epicenter) and zone.populated:
            return True
    return False

def calculate_priority(magnitude:float, depth_km:float, is_in_populated_zone:bool) -> int:
    if magnitude >= 6.0:
        return 3
    if magnitude >= 4.5 and depth_km <= 30.0 and is_in_populated_zone:
        return 3
    if magnitude >= 4.5:
        return 2
    return 1

def search_cost(event_id, node_depths):
    node_depth = node_depths.get(event_id)
    return None if node_depth is None else node_depth + 1
