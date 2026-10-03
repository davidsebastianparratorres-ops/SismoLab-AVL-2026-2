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
        # Rebalance the tree after insertion (skipped in stress mode).
        return self._rebalance(node) if self.balancing else node

    def _after_delete(self, node):
        # Rebalance the tree after deletion (skipped in stress mode).
        return self._rebalance(node) if self.balancing else node

    def _rebalance(self, node):
        # Get the balance factor for the current node.
        balance = node.getBalanceFactor()

        # Left-heavy case.
        if balance > 1:
            # Left-right case: rotate left first on the left child.
            if node.getLeft().getBalanceFactor() < 0:
                node.setLeft(self._rotate_left(node.getLeft()))
                self.metrics.record_case("LR")
            else:
                self.metrics.record_case("LL")
            return self._rotate_right(node)

        # Right-heavy case.
        if balance < -1:
            # Right-left case: rotate right first on the right child.
            if node.getRight().getBalanceFactor() > 0:
                node.setRight(self._rotate_right(node.getRight()))
                self.metrics.record_case("RL")
            else: 
                self.metrics.record_case("RR")
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
        self.metrics.record_rotation("left")
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
        self.metrics.record_rotation("right")
        return new_root
    
    
        # ------------------------------------------------------------------
    # Global recovery (section 8): rotations only, never a rebuild from a list.
    # ------------------------------------------------------------------
    @staticmethod
    def _h(node):
        return node.getHeight() if node is not None else -1


    """Restores the AVL property of a (possibly badly degraded) BST, keeping every
        node and the in-order sequence. Any height difference is supported, not only 2.
 
        Bottom-up, each node is 'joined' with its two subtrees, which are already AVL.
        Termination: every join walks down ONE spine whose length is at most the height
        of an AVL subtree, and every node is joined exactly once -> finite work, O(n)
        joins. Order: only rotations and re-linking of mid between left < mid < right.
    """
    def restore_balance(self):
        root = self.getRoot()
        if root is None:
            return
        order, stack = [], [(root, None, False)] # preorder: parent before descendants
        while stack:
            node, parent, is_left = stack.pop()
            order.append((node, parent, is_left))
            if node.getRight() is not None:
                stack.append((node.getRight(), node, False))
            if node.getLeft() is not None:
                stack.append((node.getLeft(), node, True))
        for node, parent, is_left in reversed(order): # children are always joined first
            joined = self._join(node.getLeft(), node, node.getRight())
            if parent is None:
                root = joined
            elif is_left:
                parent.setLeft(joined)
            else:
                parent.setRight(joined)
        self.setRoot(root)

    def _join(self, left, mid, right):
        # Both subtrees are AVL and keys(left) < key(mid) < keys(right).
        left_h, right_h = self._h(left), self._h(right)
        if left_h > right_h + 1:
            return self._join_right(left, mid, right)
        if right_h > left_h + 1:
            return self._join_left(left, mid, right)
        mid.setLeft(left)
        mid.setRight(right)
        self._update_height(mid)
        return mid

    def _join_right(self, tall, mid, short):
        # 'tall' is taller than 'short' by more than 1: go down its right spine.
        inner, outer = tall.getRight(), tall.getLeft()
        base = self._h(inner) <= self._h(short) + 1
        if base:
            mid.setLeft(inner)
            mid.setRight(short)
            self._update_height(mid)
            joined = mid
        else:
            joined = self._join_right(inner, mid, short)
        tall.setRight(joined)
        self._update_height(tall)
        if self._h(joined) <= self._h(outer) + 1:
            return tall
        if base:
            tall.setRight(self._rotate_right(joined))
            self.metrics.record_case("RL")
        else:
            self.metrics.record_case("RR")
        return self._rotate_left(tall)

    def _join_left(self, short, mid, tall):
        # Mirror of _join_right: 'tall' is on the right, go down its left spine.
        inner, outer = tall.getLeft(), tall.getRight()
        base = self._h(inner) <= self._h(short) + 1
        if base:
            mid.setLeft(short)
            mid.setRight(inner)
            self._update_height(mid)
            joined = mid
        else:
            joined = self._join_left(short, mid, inner)
        tall.setLeft(joined)
        self._update_height(tall)
        if self._h(joined) <= self._h(outer) + 1:
            return tall
        if base:
            tall.setLeft(self._rotate_left(joined))
            self.metrics.record_case("LR")
        else:
            self.metrics.record_case("LL")
        return self._rotate_right(tall)
