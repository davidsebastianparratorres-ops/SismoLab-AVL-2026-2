class Node:
    def __init__(self, Event):
        self.__value = Event
        self.__parent = None
        self.__left = None
        self.__right = None
        self.__height = None
        self.__balanceFactor = None

    def getValue(self):
        return self.__value

    def setValue(self, Event):
        self.__value = Event

    def getParent(self):
        return self.__parent

    def setParent(self, parent):
        self.__parent = parent

    def getLeft(self):
        return self.__left

    def setLeft(self, left):
        self.__left = left

    def getRight(self):
        return self.__right

    def setRight(self, right):
        self.__right = right

    def getHeight(self):
        return self.__height

    def setHeight(self, height):
        self.__height = height

    def getBalanceFactor(self):
        return self.__balanceFactor

    def setBalanceFactor(self, balanceFactor):
        self.__balanceFactor = balanceFactor