
def calculate_priority(magnitude:float, depth:float, is_in_populated_zone:bool) -> int:
    if magnitude >= 6.0:
        return 3
    if magnitude >= 4.5 and depth <= 30.0 and is_in_populated_zone:
        return 3
    if magnitude >= 4.5:
        return 2
    return 1