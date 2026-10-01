class Key:
    def __init__(self, priority: int, magnitude: float, identifier: int):
        self.priority = priority
        self.magnitude = magnitude
        self.identifier = identifier
        # Native tuple: Python compares tuples element by element,
        # left to right, stopping at the first differing component
        # which is exactly the lexicographic rule from section 5.
        self.as_tuple = (priority, magnitude, identifier)

    @classmethod
    def from_event(cls, event):
        # BUG FIX: was reading event.priority / event.magnitude /
        # event.identifier none of which exist on Event (private
        # attributes, only exposed via getPriority()/getMagnitude()/
        # getEventId()).
        return cls(event.getPriority(), event.getMagnitude(), event.getEventId())
