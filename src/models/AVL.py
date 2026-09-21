from .Tree import Tree


class AVL2(Tree):
    def __init__(self, root=None):
        super().__init__(root)
        self.__height = 0
        self.__balanceFactor = 0

    def getHeight(self):
        return self.__height

    def setHeight(self, height):
        self.__height = height

    def getBalanceFactor(self):
        return self.__balanceFactor

    def setBalanceFactor(self, balanceFactor):
            self.__balanceFactor = balanceFactor

    def __str__(self):
        return (
            f"AVL(height={self.__height}, balanceFactor={self.__balanceFactor}, "
            f"root={self.getRoot()}, size={self.getSize()})"
        )
