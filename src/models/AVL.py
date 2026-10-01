from .Tree import Tree


class AVL(Tree):
    def __init__(self, root=None):
        # Initialize AVL tree with an optional root.
        super().__init__(root)

    def getHeight(self):
        # Returns the height of the root, or -1 if the tree is empty.
        root = self.getRoot()
        return root.getHeight() if root is not None else -1

    def getBalanceFactor(self):
        # Returns the root balance factor, or 0 if the tree is empty.
        root = self.getRoot()
        return root.getBalanceFactor() if root is not None else 0

    def setHeight(self, height):
        # Updates the root height only.
        root = self.getRoot()
        if root is not None:
            root.setHeight(height)

    def setBalanceFactor(self, balanceFactor):
        # Updates the root balance factor only.
        root = self.getRoot()
        if root is not None:
            root.setBalanceFactor(balanceFactor)

    def _after_insert(self, node):
        # Rebalance the tree after insertion.
        return self._rebalance(node)

    def _after_delete(self, node):
        # Rebalance the tree after deletion.
        return self._rebalance(node)

    def _rebalance(self, node):
        # Get the balance factor for the current node.
        balance = node.getBalanceFactor()

        # Left-heavy case.
        if balance > 1:
            # Left-right case: rotate left first on the left child.
            if node.getLeft().getBalanceFactor() < 0:
                node.setLeft(self._rotate_left(node.getLeft()))
            return self._rotate_right(node)

        # Right-heavy case.
        if balance < -1:
            # Right-left case: rotate right first on the right child.
            if node.getRight().getBalanceFactor() > 0:
                node.setRight(self._rotate_right(node.getRight()))
            return self._rotate_left(node)

        return node

    def _rotate_left(self, node):
        # Left rotation around the given node.
        new_root = node.getRight()
        transferred_subtree = new_root.getLeft()

        # Perform the rotation.
        new_root.setLeft(node)
        node.setRight(transferred_subtree)

        # Recalculate heights.
        self._update_height(node)
        self._update_height(new_root)
        return new_root

    def _rotate_right(self, node):
        # Right rotation around the given node.
        new_root = node.getLeft()
        transferred_subtree = new_root.getRight()

        # Perform the rotation.
        new_root.setRight(node)
        node.setLeft(transferred_subtree)

        # Recalculate heights.
        self._update_height(node)
        self._update_height(new_root)
        return new_root
