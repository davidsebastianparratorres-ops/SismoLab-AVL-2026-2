from src.rules.EventValidator import has_at_most_one_decimal

# Same bounds as an epicenter (EventValidator.validate_ranges): a zone
# outside this range could never contain a valid epicenter anyway.
ZONE_MIN = 0.0
ZONE_MAX = 1000.0


def validate_zone(x_min: float, x_max: float, y_min: float, y_max: float, existing_zones: list) -> list:
    """Zones are immutable once created (no edit, no delete - only
    addition), so this validation is the only safety net they ever get.
    """
    errors = []

    for label, value in (("x_min", x_min), ("x_max", x_max), ("y_min", y_min), ("y_max", y_max)):
        if not (ZONE_MIN <= value <= ZONE_MAX):
            errors.append(f"Zone {label} must be between {ZONE_MIN} and {ZONE_MAX} km.")
        elif not has_at_most_one_decimal(value):
            errors.append(f"Zone {label} must have at most one decimal place.")

    if errors:
        return errors  # out-of-range bounds make the checks below meaningless

    if x_min >= x_max:
        errors.append("Zone x_min must be strictly less than x_max.")
    if y_min >= y_max:
        errors.append("Zone y_min must be strictly less than y_max.")

    if errors:
        return errors

    for other in existing_zones:
        if _overlaps(x_min, x_max, y_min, y_max, other):
            errors.append("Zone overlaps with an existing zone.")
            break

    return errors


def _overlaps(x_min, x_max, y_min, y_max, other) -> bool:
    # Strict '<' on purpose: two zones that only share a border (zero
    # overlapping area) are allowed to sit side by side - only actual
    # overlapping area is rejected. This matches the already-established
    # rule that a point sitting exactly on a shared border belongs to
    # both zones (Zone.contains uses inclusive '<=').
    return (x_min < other.getXMax() and other.getXMin() < x_max
            and y_min < other.getYMax() and other.getYMin() < y_max)
