import math
import random
from dataclasses import dataclass, field

from src.models.AVL import AVL
from src.models.BST import BST
from src.models.Key import Key

# The tree classes insert recursively, and an ascending sequence turns the
# BST into a chain as deep as the number of events, so the comparison is
# capped well below Python's recursion limit.
MAX_COMPARISON_EVENTS = 500

ORDER_LABELS = {
    "load": "Orden de carga (el del archivo de inserción)",
    "ascending": "Ascendente por clave (peor caso del BST)",
    "descending": "Descendente por clave",
    "random": "Aleatorio (con semilla)",
}


@dataclass
class TreeMetrics:
    name: str
    nodes: int
    root_id: int
    root_key: tuple
    height: int          # recomputed bottom-up (empty tree = -1, leaf = 0)
    max_depth: int       # recomputed top-down (root = 0)
    leaves: int
    total_comparisons: int      # sum over every key of (nodes visited from the root)
    average_comparisons: float
    max_comparisons: int
    rotations: int
    rotation_cases: dict = field(default_factory=dict)


@dataclass
class ComparisonResult:
    order: str
    sequence: list       # [(priority, magnitude, event_id)] in the order inserted
    avl_tree: object
    bst_tree: object
    avl: TreeMetrics
    bst: TreeMetrics

    @property
    def ideal_height(self) -> int:
        """Smallest height any binary tree with these nodes can have."""
        return int(math.floor(math.log2(len(self.sequence)))) if self.sequence else -1


class TreeComparison:
    """Builds an AVL and a plain BST from the same events, with the same
    comparator (Key.as_tuple) and the same insertion order, and measures both
    with structural metrics (sections 11 and 12). Nothing here touches the
    live scenario: it always works on its own, fresh trees.
    """

    @staticmethod
    def keys_from_events(active_events: dict) -> list:
        return [(e.getPriority(), e.getMagnitude(), e.getEventId()) for e in active_events.values()]

    # ------------------------------------------------------------------
    # Insertion orders
    # ------------------------------------------------------------------
    @staticmethod
    def order_sequence(keys, order, seed=0, load_order=None) -> list:
        keys = list(keys)
        if order == "ascending":
            return sorted(keys)
        if order == "descending":
            return sorted(keys, reverse=True)
        if order == "random":
            shuffled = sorted(keys)  # sorted first so the same seed always gives the same order
            random.Random(seed).shuffle(shuffled)
            return shuffled
        if order == "load":
            if load_order is None:
                raise ValueError("No hay un orden de carga disponible.")
            by_id = {k[2]: k for k in keys}
            if set(by_id) != set(load_order):
                raise ValueError("El orden de carga no corresponde a los eventos actuales.")
            return [by_id[event_id] for event_id in load_order]
        raise ValueError("Orden desconocido: " + str(order))

    # ------------------------------------------------------------------
    # Building and measuring
    # ------------------------------------------------------------------
    @staticmethod
    def build_tree(tree_class, sequence):
        tree = tree_class()
        try:
            for priority, magnitude, event_id in sequence:
                tree.insert(Key(priority, magnitude, event_id), event_id)
        except RecursionError:
            raise ValueError("Demasiados eventos para construir el árbol de comparación "
                             "(máximo " + str(MAX_COMPARISON_EVENTS) + ").")
        return tree

    @classmethod
    def measure(cls, name, tree, sequence) -> TreeMetrics:
        """Reads the numbers from the trees themselves (Tree.shape / Tree.search_cost)."""
        rotation_cases = {case: tree.metrics.get("case_" + case) for case in ("LL", "RR", "LR", "RL")}
        rotations = tree.metrics.get("rotations_left") + tree.metrics.get("rotations_right")
        shape = tree.shape()
        if shape["nodes"] == 0:
            return TreeMetrics(name, 0, None, None, -1, -1, 0, 0, 0.0, 0, rotations, rotation_cases)

        costs = []
        for key in sequence:
            cost = tree.search_cost(key)
            if cost is None:
                raise ValueError("La clave " + str(key) + " no está en el árbol " + name + ".")
            costs.append(cost)
        root = tree.getRoot()
        return TreeMetrics(
            name=name, nodes=shape["nodes"], root_id=root.getEventId(), root_key=root.getKey().as_tuple,
            height=shape["height"], max_depth=shape["max_depth"], leaves=shape["leaves"],
            total_comparisons=sum(costs), average_comparisons=sum(costs) / len(costs),
            max_comparisons=max(costs), rotations=rotations, rotation_cases=rotation_cases,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    @classmethod
    def compare(cls, keys, order, seed=0, load_order=None) -> ComparisonResult:
        keys = list(keys)
        if len(keys) > MAX_COMPARISON_EVENTS:
            raise ValueError("La comparación admite como máximo " + str(MAX_COMPARISON_EVENTS) + " eventos.")
        if len({k[2] for k in keys}) != len(keys):
            raise ValueError("Hay identificadores repetidos entre los eventos.")
        sequence = cls.order_sequence(keys, order, seed, load_order)
        avl_tree = cls.build_tree(AVL, sequence)
        bst_tree = cls.build_tree(BST, sequence)
        return ComparisonResult(
            order=order, sequence=sequence, avl_tree=avl_tree, bst_tree=bst_tree,
            avl=cls.measure("AVL", avl_tree, sequence), bst=cls.measure("BST", bst_tree, sequence),
        )

    @classmethod
    def compare_all(cls, keys, seed=0, load_order=None) -> list:
        """One result per insertion order (the load order only when available)."""
        orders = (["load"] if load_order is not None else []) + ["ascending", "descending", "random"]
        return [cls.compare(keys, order, seed, load_order) for order in orders]