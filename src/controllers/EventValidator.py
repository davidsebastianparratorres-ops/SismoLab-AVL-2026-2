def has_at_most_one_decimal(value:float) -> bool:
    
    scaled_value = value * 10
    return abs(scaled_value - round(scaled_value)) < 1e-9

def validate_event_input(
    event_id: int,
    magnitude: float,
    depth_km: float,
    epicenter_x: float,
    epicenter_y: float,
    occurred_at,
    origin_station_id: str,
    stations: dict,
    simulation_clock,
) -> list:
    errors = []

    if not (1 <= event_id <= 999999):
        errors.append("Identifier must be an integer between 1 and 999999.")

    if not (-2.0 <= magnitude <= 10.0):
        errors.append("Magnitude must be between -2.0 and 10.0.")
    elif not has_at_most_one_decimal(magnitude):
        errors.append("Magnitude must have at most one decimal place.")

    if not (0.0 <= depth_km <= 700.0):
        errors.append("Depth must be between 0.0 and 700.0 km.")
    elif not has_at_most_one_decimal(depth_km):
        errors.append("Depth must have at most one decimal place.")

    if not (0.0 <= epicenter_x <= 1000.0):
        errors.append("Epicenter x must be between 0.0 and 1000.0 km.")
    elif not has_at_most_one_decimal(epicenter_x):
        errors.append("Epicenter x must have at most one decimal place.")

    if not (0.0 <= epicenter_y <= 1000.0):
        errors.append("Epicenter y must be between 0.0 and 1000.0 km.")
    elif not has_at_most_one_decimal(epicenter_y):
        errors.append("Epicenter y must have at most one decimal place.")

    if occurred_at > simulation_clock.current_time:
        errors.append("Occurrence time cannot be later than the simulation clock.")

    if origin_station_id not in stations:
        errors.append("Unknown station: " + origin_station_id + ".")

    return errors