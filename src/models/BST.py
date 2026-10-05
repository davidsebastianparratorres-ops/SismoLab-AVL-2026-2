from .Tree import Tree


class BST(Tree):
    """Plain binary search tree used as the baseline to compare against the AVL.

    It shares the node structure, the comparator (Key.as_tuple) and the insertion and
    deletion routines of Tree, but it NEVER rebalances: no rotations, no balance repair.
    """

    def __init__(self, root=None):
        super().__init__(root)
        self.__type = "BST"

    def getType(self):
        return self.__type

    def setType(self, type_name):
        self.__type = type_name

    def _after_insert(self, node):
        # Explicit on purpose: a BST keeps whatever shape the insertion order gives it.
        return node

    def _after_delete(self, node):
        return node

    def _str_(self):
        return f"BST(type={self.__type}, root={self.getRoot()}, size={self.getSize()})"