from src.rules.EventRules import calculate_priority as _calculate_priority


class PriorityCalculator:
    # Thin facade: the rule lives only in EventRules.
    @staticmethod
    def calculate_priority(magnitude, depth, epicenter, zone_classifier):
        is_populated = zone_classifier.is_in_populated_zone(epicenter)
        return _calculate_priority(magnitude, depth, is_populated)