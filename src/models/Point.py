import math


class Point:
    def __init__(self, x=0.0, y=0.0):
        self.__x = x
        self.__y = y

    def getX(self):
        return self.__x

    def setX(self, x):
        self.__x = x

    def getY(self):
        return self.__y

    def setY(self, y):
        self.__y = y

    def distance_to(self, other: "Point") -> float:
        # BUG FIX: AssociationRules.is_candidate / _is_better_candidate call
        # epicenter.distance_to(...), but Point never defined this method —
        # every association candidate check raised AttributeError. Plain
        # Euclidean distance in km, matching the x/y (km) range used by
        # EventValidator.
        return math.hypot(self.getX() - other.getX(), self.getY() - other.getY())

    def __str__(self):
        return f"Point(x={self.__x}, y={self.__y})"
