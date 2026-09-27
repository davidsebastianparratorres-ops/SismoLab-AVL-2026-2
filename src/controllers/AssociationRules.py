
def hours_between(earlier_time, later_time):
    return (later_time - earlier_time).total_seconds() / 3600.0


def is_candidate(candidate_event, target_event, max_hours, max_distance_km):
    if candidate_event.event_id == target_event.event_id:
        return False

    
    if candidate_event.magnitude <= target_event.magnitude:
        return False
    if candidate_event.occurred_at >= target_event.occurred_at:
        return False

    time_difference = hours_between(candidate_event.occurred_at, target_event.occurred_at)
    if time_difference > max_hours:
        return False

    distance = candidate_event.epicenter.distance_to(target_event.epicenter)
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
    if candidate.magnitude != current_best.magnitude:
        return candidate.magnitude > current_best.magnitude

    candidate_time_diff = hours_between(candidate.occurred_at, target_event.occurred_at)
    best_time_diff = hours_between(current_best.occurred_at, target_event.occurred_at)
    if candidate_time_diff != best_time_diff:
        return candidate_time_diff < best_time_diff

    candidate_distance = candidate.epicenter.distance_to(target_event.epicenter)
    best_distance = current_best.epicenter.distance_to(target_event.epicenter)
    if candidate_distance != best_distance:
        return candidate_distance < best_distance

    return candidate.event_id < current_best.event_id

