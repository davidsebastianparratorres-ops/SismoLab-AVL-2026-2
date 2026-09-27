from src.models.Node import Node


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

    def insert(self, key, event_id):
        # BUG FIX: originally did `self.root = ...`, which created a brand
        # new public attribute instead of touching the private __root.
        # getRoot() would return None forever, no matter how many events
        # were inserted.
        self.setRoot(self._insert_recursive(self.getRoot(), key, event_id))

    def _insert_recursive(self, node, key, event_id):
        if node is None:
            new_node = Node(key, event_id)
            # BUG FIX: a freshly created leaf never had its height/balance
            # factor set (they start as None on Node), so as soon as its
            # parent tried to read left/right height to compute its own,
            # it hit `None` instead of -1 and crashed with TypeError. Both
            # children of a leaf are None, so this is exactly the -1/-1
            # case _update_height already knows how to compute.
            self._update_height(new_node)
            return new_node

        # BUG FIX: Node only exposes its key/left/right through
        # getKey()/getLeft()/getRight() (and setLeft()/setRight()) — they
        # are name-mangled private attributes. The previous version read
        # and wrote node.key / node.left / node.right directly, which
        # raised AttributeError on every insert.
        if key.as_tuple < node.getKey().as_tuple:
            node.setLeft(self._insert_recursive(node.getLeft(), key, event_id))
        else:
            node.setRight(self._insert_recursive(node.getRight(), key, event_id))

        self._update_height(node)
        return self._after_insert(node)  # <- hook: subclasses decide what happens here

    def _update_height(self, node):
        left_height = node.getLeft().getHeight() if node.getLeft() is not None else -1
        right_height = node.getRight().getHeight() if node.getRight() is not None else -1
        node.setHeight(1 + max(left_height, right_height))
        # Also store the balance factor here, since nothing else was
        # setting it — TreeAuditor.verify_structure requires every node to
        # have a stored balance factor and flags it as an error otherwise.
        node.setBalanceFactor(left_height - right_height)

    def _after_insert(self, node):
        # Base behavior: do nothing extra. Plain BST relies on this default.
        # NOTE for the team: AVL still doesn't override this hook to
        # perform rotations, so trees built through insert() behave as a
        # plain BST today, not a balanced AVL. That's a missing feature,
        # not an attribute bug, so it's left untouched here.
        return node

    def search(self, key):
        return self._search_recursive(self.getRoot(), key)

    def _search_recursive(self, node, key):
        if node is None:
            return None
        if key.as_tuple == node.getKey().as_tuple:
            return node
        if key.as_tuple < node.getKey().as_tuple:
            return self._search_recursive(node.getLeft(), key)
        return self._search_recursive(node.getRight(), key)

    def locate_node_info(self, key):
        depth = 0
        current = self.getRoot()
        while current is not None:
            if key.as_tuple == current.getKey().as_tuple:
                left_height = current.getLeft().getHeight() if current.getLeft() is not None else -1
                right_height = current.getRight().getHeight() if current.getRight() is not None else -1
                balance_factor = left_height - right_height
                return depth, current.getHeight(), balance_factor
            if key.as_tuple < current.getKey().as_tuple:
                current = current.getLeft()
            else:
                current = current.getRight()
            depth += 1
        return None, None, None  # not found — shouldn't happen if get_event said ACTIVE

    def get_all_depths(self):
        depths = {}
        self._collect_depths(self.getRoot(), 0, depths)
        return depths

    def _collect_depths(self, node, depth, depths):
        if node is None:
            return
        depths[node.getEventId()] = depth
        self._collect_depths(node.getLeft(), depth + 1, depths)
        self._collect_depths(node.getRight(), depth + 1, depths)
