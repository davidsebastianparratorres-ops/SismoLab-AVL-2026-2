from .Tree import Tree


class BST(Tree):
    def __init__(self, root=None):
        super().__init__(root)
        self.__type = "BST"

    def getType(self):
        return self.__type

    def setType(self, type_name):
        self.__type = type_name

    
