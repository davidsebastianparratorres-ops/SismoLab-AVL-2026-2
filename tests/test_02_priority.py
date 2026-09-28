"""Point 2: priority rules 3/2/1 with inclusive limits."""
import pytest

from src.controllers.EventRules import calculate_priority


@pytest.mark.parametrize("magnitude, depth_km, populated, expected", [
    # Rule 3a: magnitude >= 6.0 is always high, regardless of depth/zone
    (6.0, 700.0, False, 3),
    (6.0, 0.0, True, 3),
    (10.0, 700.0, False, 3),
    # Rule 3b: 4.5 <= m < 6.0, depth <= 30, populated zone
    (5.9, 30.0, True, 3),
    (4.5, 30.0, True, 3),
    (4.5, 0.0, True, 3),
    # Falls to medium when any of depth / zone condition fails
    (5.9, 30.1, True, 2),
    (5.9, 30.0, False, 2),
    (4.5, 700.0, False, 2),
    # Rule 2 lower limit is inclusive
    (4.5, 100.0, True, 2),
    # Below 4.5 is always low (even in populated shallow zone)
    (4.4, 0.0, True, 1),
    (0.0, 0.0, True, 1),
    (-2.0, 10.0, False, 1),
])
def test_priority_rules(magnitude, depth_km, populated, expected):
    assert calculate_priority(magnitude, depth_km, populated) == expected
