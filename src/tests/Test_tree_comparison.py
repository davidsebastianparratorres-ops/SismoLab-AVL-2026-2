import unittest

from src.controllers.TreeComparison import TreeComparison, MAX_COMPARISON_EVENTS


def keys(n):
    """n keys with strictly ascending (priority, magnitude, id)."""
    return [(1, round(1.0 + i * 0.1, 1), 100 + i) for i in range(n)]


class TestTreeComparison(unittest.TestCase):

    def test_ascending_order_degenerates_the_bst_but_not_the_avl(self):
        result = TreeComparison.compare(keys(15), "ascending")
        self.assertEqual((result.avl.height, result.bst.height), (3, 14))
        self.assertEqual((result.avl.leaves, result.bst.leaves), (8, 1))
        # BST: 1 + 2 + ... + 15 comparisons. Perfect AVL: 1*1 + 2*2 + 4*3 + 8*4.
        self.assertEqual(result.bst.total_comparisons, 120)
        self.assertEqual(result.avl.total_comparisons, 49)
        self.assertEqual(result.bst.max_comparisons, 15)
        self.assertEqual(result.avl.max_comparisons, 4)
        self.assertGreater(result.avl.rotations, 0)
        self.assertEqual(result.bst.rotations, 0)

    def test_height_matches_max_depth_and_ideal_height_is_a_lower_bound(self):
        for order in ("ascending", "descending", "random"):
            result = TreeComparison.compare(keys(40), order, seed=7)
            for metrics in (result.avl, result.bst):
                self.assertEqual(metrics.height, metrics.max_depth)
                self.assertEqual(metrics.nodes, 40)
                self.assertGreaterEqual(metrics.height, result.ideal_height)
            self.assertLessEqual(result.avl.height, result.bst.height)

    def test_both_trees_hold_the_same_keys_and_same_inorder(self):
        result = TreeComparison.compare(keys(25), "random", seed=3)

        def inorder(root):
            out, stack, current = [], [], root
            while stack or current is not None:
                while current is not None:
                    stack.append(current)
                    current = current.getLeft()
                current = stack.pop()
                out.append(current.getKey().as_tuple)
                current = current.getRight()
            return out

        self.assertEqual(inorder(result.avl_tree.getRoot()), inorder(result.bst_tree.getRoot()))
        self.assertEqual(inorder(result.avl_tree.getRoot()), sorted(keys(25)))

    def test_random_order_is_reproducible_by_seed(self):
        a = TreeComparison.order_sequence(keys(20), "random", seed=5)
        b = TreeComparison.order_sequence(keys(20), "random", seed=5)
        c = TreeComparison.order_sequence(keys(20), "random", seed=6)
        self.assertEqual(a, b)
        self.assertNotEqual(a, c)
        self.assertEqual(sorted(a), sorted(keys(20)))

    def test_load_order_is_replayed_as_given(self):
        data = keys(6)
        load_order = [data[3][2], data[0][2], data[5][2], data[1][2], data[4][2], data[2][2]]
        sequence = TreeComparison.order_sequence(data, "load", load_order=load_order)
        self.assertEqual([k[2] for k in sequence], load_order)
        with self.assertRaises(ValueError):
            TreeComparison.order_sequence(data, "load", load_order=load_order[:-1])
        with self.assertRaises(ValueError):
            TreeComparison.order_sequence(data, "load")

    def test_comparator_uses_priority_then_magnitude_then_id(self):
        data = [(3, 5.2, 10), (2, 5.8, 20), (3, 6.1, 30), (3, 5.2, 5), (3, 5.2, 25)]
        result = TreeComparison.compare(data, "load", load_order=[10, 20, 30, 5, 25])
        self.assertEqual(result.bst.root_key, (3, 5.2, 10))
        bst_root = result.bst_tree.getRoot()
        self.assertEqual(bst_root.getLeft().getKey().as_tuple, (2, 5.8, 20))   # lower priority -> left
        self.assertEqual(bst_root.getRight().getKey().as_tuple, (3, 6.1, 30))  # same priority, bigger M -> right

    def test_compare_all_returns_one_row_per_order(self):
        rows = TreeComparison.compare_all(keys(10), load_order=[k[2] for k in keys(10)])
        self.assertEqual([r.order for r in rows], ["load", "ascending", "descending", "random"])
        rows = TreeComparison.compare_all(keys(10))
        self.assertEqual([r.order for r in rows], ["ascending", "descending", "random"])

    def test_empty_single_and_invalid_inputs(self):
        empty = TreeComparison.compare([], "ascending")
        self.assertEqual((empty.avl.height, empty.bst.nodes, empty.ideal_height), (-1, 0, -1))
        one = TreeComparison.compare(keys(1), "ascending")
        self.assertEqual((one.avl.height, one.avl.leaves, one.avl.average_comparisons), (0, 1, 1.0))
        with self.assertRaises(ValueError):
            TreeComparison.compare([(1, 1.0, 1), (1, 2.0, 1)], "ascending")   # repeated id
        with self.assertRaises(ValueError):
            TreeComparison.compare(keys(MAX_COMPARISON_EVENTS + 1), "ascending")
        with self.assertRaises(ValueError):
            TreeComparison.order_sequence(keys(3), "sideways")

    def test_largest_allowed_ascending_input_does_not_crash(self):
        result = TreeComparison.compare(keys(MAX_COMPARISON_EVENTS), "ascending")
        self.assertEqual(result.bst.height, MAX_COMPARISON_EVENTS - 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)