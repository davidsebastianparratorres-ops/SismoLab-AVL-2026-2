from src.controllers.AttetionStatus import AttetionStatus
from src.models.Point import Point


# Base class for the seismic events that can be registered in the system.
# This class contains the common attributes of these events.
class Event:

    def __init__(
        self,
        event_id=0,
        magnitude=0.0,
        epicenter=None,
        depth=0.0,
        status=AttetionStatus.PENDING,
        associatedEvents=None,
        stations=None,
        ocurredAt="",
        priority=0, 
        review=1):
        self.__event_id = event_id
        self.__magnitude = magnitude
        self.__epicenter = epicenter if epicenter is not None else Point()
        self.__depth = depth
        self.__status = status
        self.__associatedEvents = associatedEvents if associatedEvents is not None else []
        self.__stations = stations if stations is not None else []
        self.__ocurredAt = ocurredAt
        self.__priority = priority
        self.__review = review

    def getEventId(self):
        return self.__event_id

    def setEventId(self, event_id):
        self.__event_id = event_id

    def getMagnitude(self):
        return self.__magnitude

    def setMagnitude(self, magnitude):
        self.__magnitude = magnitude

    def getEpicenter(self):
        return self.__epicenter

    def setEpicenter(self, epicenter):
        self.__epicenter = epicenter

    def getDepth(self):
        return self.__depth

    def setDepth(self, depth):
        self.__depth = depth

    def getStatus(self):
        return self.__status

    def setStatus(self, status):
        self.__status = status

    def getAssociatedEvents(self):
        return self.__associatedEvents

    def setAssociatedEvents(self, associatedEvents):
        self.__associatedEvents = associatedEvents

    def getStations(self):
        return self.__stations

    def setStations(self, stations):
        self.__stations = stations

    def getOcurredAt(self):
        return self.__ocurredAt

    def setOcurredAt(self, ocurredAt):
        self.__ocurredAt = ocurredAt

    def getPriority(self):
        return self.__priority

    def setPriority(self, priority):
        self.__priority = priority

    def getReview(self):
        return self.__review

    def setReview(self, review):
        self.__review = review

    @classmethod
    def create_new(cls, event_id, magnitude, epicenter, depth, ocurredAt, origin_station_id, priority):
        # Used only for brand-new events: always starts pending, review 1,
        # with a single reporting station. Restoring a saved/topology event
        # goes through the main constructor instead, since it may carry a
        # different status, review, or multiple stations already.
        return cls(
            event_id=event_id,
            magnitude=magnitude,
            epicenter=epicenter,
            depth=depth,
            status=AttetionStatus.PENDING,
            associatedEvents=[],
            stations=[origin_station_id],
            ocurredAt=ocurredAt,
            priority=priority,
            review=1,
        )