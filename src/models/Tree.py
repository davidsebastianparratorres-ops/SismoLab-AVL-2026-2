class Tree:
    def __init__(self, root=None):
        self.__root = root
        self.__size = 0

    def getRoot(self):
        return self.__root

    def setRoot(self, root):
        self.__root = root

    def getSize(self):
        return self.__size

    def setSize(self, size):
        self.__size = size

    def isEmpty(self):
        return self.__root is None

    def __str__(self):
        return f"Tree(root={self.__root}, size={self.__size})"
