import matplotlib.pyplot as plt
import streamlit as st

from src.controllers.TreeComparison import ORDER_LABELS
from src.presentation.styles.theme import (
    TREE_NORMAL_NODE_COLOR,
    TREE_UNBALANCED_NODE_COLOR,
    TREE_EDGE_COLOR,
    TREE_FONT_COLOR,
)

MAX_DRAWN_NODES = 60  # beyond this a drawing is unreadable; the metrics still show everything


def _layout(root):
    """Iterative layout: x = inorder position, y = -depth. No overlaps and no
    recursion, so a degenerate chain is drawn without hitting the recursion limit.
    Also returns each node's real balance factor (recomputed, not the stored one)."""
    positions, edges, order = {}, [], []
    stack, current, index = [], root, 0
    # inorder with explicit stack, tracking depth
    current_depth = 0
    while stack or current is not None:
        while current is not None:
            stack.append((current, current_depth))
            current = current.getLeft()
            current_depth += 1
        current, current_depth = stack.pop()
        positions[id(current)] = (index, -current_depth)
        order.append(current)
        index += 1
        current = current.getRight()
        current_depth += 1

    heights = {}
    pre, walk = [], [root]
    while walk:
        node = walk.pop()
        pre.append(node)
        for child in (node.getLeft(), node.getRight()):
            if child is not None:
                edges.append((id(node), id(child)))
                walk.append(child)
    balance = {}
    for node in reversed(pre):
        left = heights[id(node.getLeft())] if node.getLeft() is not None else -1
        right = heights[id(node.getRight())] if node.getRight() is not None else -1
        heights[id(node)] = 1 + max(left, right)
        balance[id(node)] = left - right
    return order, positions, edges, balance


def draw_tree(ax, root, title):
    ax.set_title(title, fontsize=11)
    ax.axis("off")
    if root is None:
        ax.text(0.5, 0.5, "Árbol vacío", ha="center", va="center")
        return
    order, positions, edges, balance = _layout(root)
    if len(order) > MAX_DRAWN_NODES:
        ax.text(0.5, 0.5, f"{len(order)} nodos: demasiados para dibujar.\nUsa las métricas de la tabla.",
                ha="center", va="center", transform=ax.transAxes)
        return
    for parent_id, child_id in edges:
        (x1, y1), (x2, y2) = positions[parent_id], positions[child_id]
        ax.plot([x1, x2], [y1, y2], color=TREE_EDGE_COLOR, linewidth=1, zorder=1)
    size = 700 if len(order) <= 15 else 320 if len(order) <= 30 else 150
    font = 8 if len(order) <= 15 else 6 if len(order) <= 30 else 4
    for node in order:
        x, y = positions[id(node)]
        color = TREE_UNBALANCED_NODE_COLOR if abs(balance[id(node)]) > 1 else TREE_NORMAL_NODE_COLOR
        ax.scatter([x], [y], s=size, color=color, zorder=2)
        ax.text(x, y, str(node.getEventId()), color=TREE_FONT_COLOR, fontsize=font,
                ha="center", va="center", zorder=3)
    ax.margins(0.08)


def _fmt(value):
    """Everything is shown as text: a table column that mixes integers with averages would
    otherwise be turned into decimals (15 -> 15.0000)."""
    if value is None:
        return "-"
    return f"{value:.2f}" if isinstance(value, float) else str(value)


def _metrics_rows(result):
    avl, bst = result.avl, result.bst
    ratio = (bst.average_comparisons / avl.average_comparisons) if avl.average_comparisons else 0.0
    rows = [
        {"Métrica": "Nodos", "AVL": avl.nodes, "BST": bst.nodes},
        {"Métrica": "Raíz (id)", "AVL": avl.root_id, "BST": bst.root_id},
        {"Métrica": "Altura", "AVL": avl.height, "BST": bst.height},
        {"Métrica": "Profundidad máxima", "AVL": avl.max_depth, "BST": bst.max_depth},
        {"Métrica": "Hojas", "AVL": avl.leaves, "BST": bst.leaves},
        {"Métrica": "Comparaciones totales (buscar cada clave)", "AVL": avl.total_comparisons,
         "BST": bst.total_comparisons},
        {"Métrica": "Comparaciones promedio", "AVL": round(avl.average_comparisons, 2),
         "BST": round(bst.average_comparisons, 2)},
        {"Métrica": "Comparaciones en el peor caso", "AVL": avl.max_comparisons, "BST": bst.max_comparisons},
        {"Métrica": "Rotaciones realizadas", "AVL": avl.rotations, "BST": bst.rotations},
    ]
    rows = [{key: _fmt(value) for key, value in row.items()} for row in rows]
    return rows, ratio


def render_comparison(result):
    """Side-by-side drawing of both trees plus the structural metrics (sections 11, 12 and 15)."""
    fig, (ax_avl, ax_bst) = plt.subplots(1, 2, figsize=(11, 4.2))
    draw_tree(ax_avl, result.avl_tree.getRoot(), f"AVL (altura {result.avl.height})")
    draw_tree(ax_bst, result.bst_tree.getRoot(), f"BST sin balanceo (altura {result.bst.height})")
    st.pyplot(fig)
    plt.close(fig)
    st.caption("Naranja: nodo con |factor de balance| > 1. Ambos árboles recibieron los mismos eventos, "
               "con el mismo comparador (prioridad, magnitud, identificador) y en el mismo orden.")

    rows, ratio = _metrics_rows(result)
    st.table(rows)
    if result.avl.nodes:
        st.write(f"Buscar todas las claves cuesta en promedio **{result.avl.average_comparisons:.2f}** "
                 f"comparaciones en el AVL y **{result.bst.average_comparisons:.2f}** en el BST "
                 f"({ratio:.1f} veces más). La altura mínima posible con {result.avl.nodes} nodos es "
                 f"{result.ideal_height}.")
        if result.avl.rotations:
            cases = ", ".join(f"{case}: {count}" for case, count in result.avl.rotation_cases.items() if count)
            st.caption("El AVL mantuvo su balance con rotaciones (" + (cases or "sin casos dobles") + "); "
                       "el BST no rota nunca.")


def render_orders_table(results):
    rows = []
    for result in results:
        rows.append({
            "Orden de inserción": ORDER_LABELS[result.order],
            "Altura AVL": result.avl.height, "Altura BST": result.bst.height,
            "Hojas AVL": result.avl.leaves, "Hojas BST": result.bst.leaves,
            "Comp. promedio AVL": round(result.avl.average_comparisons, 2),
            "Comp. promedio BST": round(result.bst.average_comparisons, 2),
        })
    st.table([{key: _fmt(value) for key, value in row.items()} for row in rows])