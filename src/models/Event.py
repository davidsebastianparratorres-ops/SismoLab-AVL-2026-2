from controllers.AttetionStaus import AttetionStatus
from src.models import Point
# Base class for the sysmic events that can be registered in the system. This class contains the common attributes of these events
class Event:
    
    def __init__(
        self, 
        event_id="", 
        magnitude=float, 
        epicenter=Point, 
        depth=float, 
        status="", 
        associatedEvents=[], 
        stations="", 
        ocurredAt="",
        priority=int, 
        review=int):
        self.__event_id = event_id
        self.__magnitude = magnitude
        self.__epicenter = epicenter
        self.__depth = depth
        self.__status = status
        self.__associatedEvents = associatedEvents
        self.__stations = stations
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

    def getReview(self):
        return self.__review

    def setReview(self, review):
        self.__review = review
    
    @classmethod
    def create_new(cls, event_id, magnitude, epicenter, depth, ocurredAt, origin_station_id, priority):
        return cls(
            event_id=event_id,
            magnitude=magnitude,
            epicenter=epicenter,
            depth=depth,
            status=AttetionStatus.PENDING,
            associatedEvents=[],
            stations={origin_station_id},
            ocurredAt=ocurredAt,
            priority=priority,
            review=1
        )