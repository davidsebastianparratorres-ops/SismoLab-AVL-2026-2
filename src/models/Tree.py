from src.models.Node import Node
from src.models.Metrics import Metrics


class Tree:
    def __init__(self, root=None):
        # Root of the tree.
        self.__root = root
        # Number of nodes currently stored in the tree.
        self.__size = self._count_nodes(root)
        # Stress mode = balancing False: same BST operations, rotations deferred.
        self.balancing = True
        # Rotation counters; Scenery replaces it with the scenario's own Metrics.
        self.metrics = Metrics()

    def getRoot(self):
        return self.__root

    def setRoot(self, root):
        # Update both root reference and tree size.
        self.__root = root
        self.__size = self._count_nodes(root)

    def getSize(self):
        return self.__size

    def setSize(self, size):
        self.__size = size

    def isEmpty(self):
        return self.__root is None

    def __str__(self):
        return f"Tree(root={self.__root}, size={self.__size})"

    def insert(self, key, event_id):
        # Insert a new node into the tree using the given key and event id.
        self.__root = self._insert_recursive(self.__root, key, event_id)
        self.__size += 1  # O(1); setRoot would recount every node

    def _insert_recursive(self, node, key, event_id):
        # Base case: create a new node if the position is empty.
        if node is None:
            new_node = Node(key, event_id)
            self._update_height(new_node)
            return new_node

        # BST insertion: smaller keys go to the left, larger ones to the right.
        if key.as_tuple < node.getKey().as_tuple:
            node.setLeft(self._insert_recursive(node.getLeft(), key, event_id))
        else:
            node.setRight(self._insert_recursive(node.getRight(), key, event_id))

        # Recalculate height after insertion.
        self._update_height(node)

        # Hook for subclasses such as AVL to add balancing behavior.
        return self._after_insert(node)

    def _update_height(self, node):
        # Height of an empty subtree is -1.
        left_height = node.getLeft().getHeight() if node.getLeft() is not None else -1
        right_height = node.getRight().getHeight() if node.getRight() is not None else -1

        # Height of current node.
        node.setHeight(1 + max(left_height, right_height))

        # Balance factor is computed as left_height - right_height.
        node.setBalanceFactor(left_height - right_height)

    # ------------------------------------------------------------------
    # Read-only measurements shared by AVL and BST (used to compare them)
    # ------------------------------------------------------------------
    def search_cost(self, key_tuple):
        """Nodes visited from the root until the key is found (depth + 1, section 9).
        Returns None when the key is not in the tree. Iterative on purpose."""
        node, visited = self.getRoot(), 0
        while node is not None:
            visited += 1
            node_key = node.getKey().as_tuple
            if key_tuple == node_key:
                return visited
            node = node.getLeft() if key_tuple < node_key else node.getRight()
        return None

    def shape(self):
        """Structure recomputed from the links (never from stored heights):
        {'nodes', 'leaves', 'height', 'max_depth'}; the empty tree has height -1."""
        root = self.getRoot()
        if root is None:
            return {"nodes": 0, "leaves": 0, "height": -1, "max_depth": -1}
        order, max_depth, leaves = [], 0, 0
        stack = [(root, 0)]
        while stack:
            node, depth = stack.pop()
            order.append(node)
            max_depth = max(max_depth, depth)
            if node.getLeft() is None and node.getRight() is None:
                leaves += 1
            if node.getRight() is not None:
                stack.append((node.getRight(), depth + 1))
            if node.getLeft() is not None:
                stack.append((node.getLeft(), depth + 1))
        heights = {}
        for node in reversed(order):  # children are processed before their parent
            left = heights[id(node.getLeft())] if node.getLeft() is not None else -1
            right = heights[id(node.getRight())] if node.getRight() is not None else -1
            heights[id(node)] = 1 + max(left, right)
        return {"nodes": len(order), "leaves": leaves, "height": heights[id(root)], "max_depth": max_depth}

    def _after_insert(self, node):
        # Default behavior for a plain BST: do nothing after insertion.
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
        # Returns depth, current height, and balance factor for a node.
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

        return None, None, None

    def get_all_depths(self):
        # Collects the depth of each event stored in the tree.
        depths = {}
        self._collect_depths(self.getRoot(), 0, depths)
        return depths

    def _collect_depths(self, node, depth, depths):
        if node is None:
            return

        depths[node.getEventId()] = depth
        self._collect_depths(node.getLeft(), depth + 1, depths)
        self._collect_depths(node.getRight(), depth + 1, depths)

    def _count_nodes(self, node):
        # Counts all nodes in the subtree rooted at 'node'.
        count, stack = 0, [node] if node is not None else []
        while stack:  # iterative: a stress-mode chain must not hit the recursion limit
            current = stack.pop()
            count += 1
            stack.extend(c for c in (current.getLeft(), current.getRight()) if c is not None)
        return count

    def inOrder(self):
        # In-order traversal: left -> node -> right.
        result = []
        self._collect_in_order(self.getRoot(), result)
        return result

    def _collect_in_order(self, node, result):
        if node is None:
            return

        self._collect_in_order(node.getLeft(), result)
        result.append(node)
        self._collect_in_order(node.getRight(), result)

    def preOrder(self):
        # Pre-order traversal: node -> left -> right.
        result = []
        self._collect_pre_order(self.getRoot(), result)
        return result

    def _collect_pre_order(self, node, result):
        if node is None:
            return

        result.append(node)
        self._collect_pre_order(node.getLeft(), result)
        self._collect_pre_order(node.getRight(), result)

    def postOrder(self):
        # Post-order traversal: left -> right -> node.
        result = []
        self._collect_post_order(self.getRoot(), result)
        return result

    def _collect_post_order(self, node, result):
        if node is None:
            return

        self._collect_post_order(node.getLeft(), result)
        self._collect_post_order(node.getRight(), result)
        result.append(node)

    def delete(self, key):
        # Deletes a node by key and returns True if it was removed.
        new_root, deleted = self._delete_recursive(self.getRoot(), key)

        if deleted:
            self.__root = new_root
            self.__size -= 1

        return deleted

    def _delete_recursive(self, node, key):
        # Recursive BST deletion.
        if node is None:
            return None, False

        if key.as_tuple < node.getKey().as_tuple:
            new_left, deleted = self._delete_recursive(node.getLeft(), key)

            if not deleted:
                return node, False

            node.setLeft(new_left)

        elif key.as_tuple > node.getKey().as_tuple:
            new_right, deleted = self._delete_recursive(node.getRight(), key)

            if not deleted:
                return node, False

            node.setRight(new_right)

        else:
            # Case 1: node has no left child; replace it with the right subtree.
            if node.getLeft() is None:
                return node.getRight(), True

            # Case 2: node has no right child; replace it with the left subtree.
            if node.getRight() is None:
                return node.getLeft(), True

            # Case 3: node has two children.
            # Replace it with the minimum node from the right subtree.
            new_right, successor = self._extract_min(node.getRight())
            successor.setLeft(node.getLeft())
            successor.setRight(new_right)
            node = successor

        self._update_height(node)
        return self._after_delete(node), True

    def _extract_min(self, node):
        # Returns the minimum node in the subtree and the subtree without it.
        if node.getLeft() is None:
            return node.getRight(), node

        new_left, minimum = self._extract_min(node.getLeft())
        node.setLeft(new_left)
        self._update_height(node)

        return self._after_delete(node), minimum

    def _after_delete(self, node):
        # Default behavior for a plain BST after deletion.
        return node