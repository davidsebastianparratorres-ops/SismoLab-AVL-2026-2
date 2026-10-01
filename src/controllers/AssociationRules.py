from src.models.SimulationClock import parse_iso_utc


def _as_datetime(value):
    """Occurred_at may be stored as a datetime or as an ISO 8601 string,
    same situation as EventQueries._as_datetime. Normalizes either into a
    comparable datetime."""
    return parse_iso_utc(value) if isinstance(value, str) else value


def hours_between(earlier_time, later_time):
    return (later_time - earlier_time).total_seconds() / 3600.0


def is_candidate(candidate_event, target_event, max_hours, max_distance_km):
    # BUG FIX: this whole function used to read event_id / magnitude /
    # occurred_at / epicenter as plain attributes. None of those exist on
    # Event — it only exposes getEventId(), getMagnitude(), getOcurredAt(),
    # getEpicenter(). Every call raised AttributeError before reaching any
    # actual candidate logic.
    if candidate_event.getEventId() == target_event.getEventId():
        return False

    if candidate_event.getMagnitude() <= target_event.getMagnitude():
        return False

    candidate_time = _as_datetime(candidate_event.getOcurredAt())
    target_time = _as_datetime(target_event.getOcurredAt())
    if candidate_time >= target_time:
        return False

    time_difference = hours_between(candidate_time, target_time)
    if time_difference > max_hours:
        return False

    distance = candidate_event.getEpicenter().distance_to(target_event.getEpicenter())
    if distance > max_distance_km:
        return False

    return True


def choose_reference(candidates, target_event):
    if len(candidates) == 0:
        return None

    best = candidates[0]
    for candidate in candidates[1:]:
        if _is_better_candidate(candidate, best, target_event):
            best = candidate
    return best


def _is_better_candidate(candidate, current_best, target_event):
    # Deterministic cascade: magnitude, then time proximity, then distance, then id
    if candidate.getMagnitude() != current_best.getMagnitude():
        return candidate.getMagnitude() > current_best.getMagnitude()

    target_time = _as_datetime(target_event.getOcurredAt())
    candidate_time_diff = hours_between(_as_datetime(candidate.getOcurredAt()), target_time)
    best_time_diff = hours_between(_as_datetime(current_best.getOcurredAt()), target_time)
    if candidate_time_diff != best_time_diff:
        return candidate_time_diff < best_time_diff

    candidate_distance = candidate.getEpicenter().distance_to(target_event.getEpicenter())
    best_distance = current_best.getEpicenter().distance_to(target_event.getEpicenter())
    if candidate_distance != best_distance:
        return candidate_distance < best_distance

    return candidate.getEventId() < current_best.getEventId()
