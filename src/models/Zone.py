from src.models.Point import Point
class Zone:
    def __init__(self, x_min=0.0, x_max=0.0, y_min=0.0, y_max=0.0):
        self.__x_min = x_min
        self.__x_max = x_max
        self.__y_min = y_min
        self.__y_max = y_max

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

    def contains(self, point: Point):
        return ((self.__x_min <= point.getX() <= self.__x_max)
        and (self.__y_min <= point.getY() <= self.__y_max))