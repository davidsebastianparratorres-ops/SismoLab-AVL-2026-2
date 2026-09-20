#class that represents a station, parameterized, but immutable during system execution.
class Station:
    
    def __init__(self, station_id="",name=""):
        self.__station_id = station_id
        self.__name = name

    def getStationId(self):
        return self.__station_id

    def setStationId(self, station_id):
        self.__station_id = station_id

    def getName(self):
        return self.__name

    def setName(self, name):
        self.__name = name

    