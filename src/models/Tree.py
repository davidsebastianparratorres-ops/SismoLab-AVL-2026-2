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
        self.root = self._insert_recursive(self.root, key, event_id)

    def _insert_recursive(self, node, key, event_id):
        if node is None:
            return Node(key, event_id)

        if key.as_tuple < node.key.as_tuple:
            node.left = self._insert_recursive(node.left, key, event_id)
        else:
            node.right = self._insert_recursive(node.right, key, event_id)

        self._update_height(node)
        return self._after_insert(node)  # <- hook: subclasses decide what happens here

    def _update_height(self, node):
        left_height = node.left.height if node.left is not None else -1
        right_height = node.right.height if node.right is not None else -1
        node.height = 1 + max(left_height, right_height)

    def _after_insert(self, node):
        # Base behavior: do nothing extra. Plain BST relies on this default.
        return node

    def search(self, key):
        return self._search_recursive(self.root, key)

    def _search_recursive(self, node, key):
        if node is None:
            return None
        if key.as_tuple == node.key.as_tuple:
            return node
        if key.as_tuple < node.key.as_tuple:
            return self._search_recursive(node.left, key)
        return self._search_recursive(node.right, key)

    def locate_node_info(self, key):
        depth = 0
        current = self.root
        while current is not None:
            if key.as_tuple == current.key.as_tuple:
                left_height = current.left.height if current.left is not None else -1
                right_height = current.right.height if current.right is not None else -1
                balance_factor = left_height - right_height
                return depth, current.height, balance_factor
            if key.as_tuple < current.key.as_tuple:
                current = current.left
            else:
                current = current.right
            depth += 1
        return None, None, None  # not found — shouldn't happen if get_event said ACTIVE