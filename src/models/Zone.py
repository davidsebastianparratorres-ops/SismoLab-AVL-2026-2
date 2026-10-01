from src.models.Point import Point
class Zone:
    def __init__(self, x_min=0.0, x_max=0.0, y_min=0.0, y_max=0.0, populated=False):
        self.__x_min = x_min
        self.__x_max = x_max
        self.__y_min = y_min
        self.__y_max = y_max
        # BUG FIX: EventRules.belongs_to_populated_zone reads zone.populated,
        # but this attribute didn't exist anywhere on Zone. It only went
        # unnoticed because the GUI currently always loads an empty zones
        # list (see the TODO in scenario_load_page.py) â€” as soon as a real
        # Zone is constructed for a test, the old code raised AttributeError.
        self.__populated = populated

    def getXMin(self):
        return self.__x_min

    def setXMin(self, x_min):
        self.__x_min = x_min

    def getXMax(self):
        return self.__x_max

    def setXMax(self, x_max):
        self.__x_max = x_max

    def getYMin(self):
        return self.__y_min

    def setYMin(self, y_min):
        self.__y_min = y_min

    def getYMax(self):
        return self.__y_max

    def setYMax(self, y_max):
        self.__y_max = y_max

    def getPopulated(self):
        return self.__populated

    def setPopulated(self, populated):
        self.__populated = populated

    @property
    def populated(self):
        # Read-only property so EventRules.belongs_to_populated_zone's
        # existing `zone.populated` access style keeps working, without
        # duplicating the state kept in getPopulated()/setPopulated().
        return self.__populated

    def contains(self, point: Point):
        return ((self.__x_min <= point.getX() <= self.__x_max)
        and (self.__y_min <= point.getY() <= self.__y_max))
