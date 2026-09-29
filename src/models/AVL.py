from .Tree import Tree


class AVL(Tree):
    def __init__(self, root=None):
        super().__init__(root)

    def getHeight(self):
        root = self.getRoot()
        return root.getHeight() if root is not None else -1

    def getBalanceFactor(self):
        root = self.getRoot()
        return root.getBalanceFactor() if root is not None else 0

    def setHeight(self, height):
        root = self.getRoot()
        if root is not None:
            root.setHeight(height)

    def setBalanceFactor(self, balanceFactor):
        root = self.getRoot()
        if root is not None:
            root.setBalanceFactor(balanceFactor)

    def _after_insert(self, node):
        balance = node.getBalanceFactor()

        # Caso izquierda-izquierda o izquierda-derecha
        if balance > 1:
            if node.getLeft().getBalanceFactor() < 0:
                node.setLeft(self._rotate_left(node.getLeft()))
            return self._rotate_right(node)

        # Caso derecha-derecha o derecha-izquierda
        if balance < -1:
            if node.getRight().getBalanceFactor() > 0:
                node.setRight(self._rotate_right(node.getRight()))
            return self._rotate_left(node)

        return node

    def _rotate_left(self, node):
        new_root = node.getRight()
        transferred_subtree = new_root.getLeft()

        new_root.setLeft(node)
        node.setRight(transferred_subtree)

        self._update_height(node)
        self._update_height(new_root)
        return new_root

    def _rotate_right(self, node):
        new_root = node.getLeft()
        transferred_subtree = new_root.getRight()

        new_root.setRight(node)
        node.setLeft(transferred_subtree)

        self._update_height(node)
        self._update_height(new_root)
        return new_root
    
    def _after_insert(self, node):
        return self._rebalance(node)

    def _after_delete(self, node):
        return self._rebalance(node)

    def _rebalance(self, node):
        balance = node.getBalanceFactor()

        if balance > 1:
            if node.getLeft().getBalanceFactor() < 0:
                node.setLeft(self._rotate_left(node.getLeft()))
            return self._rotate_right(node)

        if balance < -1:
            if node.getRight().getBalanceFactor() > 0:
                node.setRight(self._rotate_right(node.getRight()))
            return self._rotate_left(node)

        return node