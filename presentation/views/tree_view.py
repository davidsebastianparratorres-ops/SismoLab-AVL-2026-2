import streamlit as st
import networkx as nx
import matplotlib.pyplot as plt

from presentation.styles.theme import (
    TREE_NORMAL_NODE_COLOR,
    TREE_HIGHLIGHT_NODE_COLOR,
    TREE_EDGE_COLOR,
    TREE_FONT_COLOR,
    TREE_NODE_SIZE,
    TREE_FIGURE_SIZE,
)


def _build_graph(node, G=None, pos=None, x=0.0, y=0.0, layer=1):
    if G is None:
        G, pos = nx.DiGraph(), {}
    if node is None:
        return G, pos

    label = str(node.getEventId())
    G.add_node(label)
    pos[label] = (x, y)
    offset = 4 / (layer * 0.7)

    if node.getLeft():
        G.add_edge(label, str(node.getLeft().getEventId()))
        _build_graph(node.getLeft(), G, pos, x - offset, y - 1, layer + 1)
    if node.getRight():
        G.add_edge(label, str(node.getRight().getEventId()))
        _build_graph(node.getRight(), G, pos, x + offset, y - 1, layer + 1)

    return G, pos


def render_tree(root, highlight_id=None):
    """Pure presentation: turns a tree of Node objects into a picture.
    Knows nothing about how the tree got built (loaded, inserted, restored)
    — only needs getLeft()/getRight()/getEventId(). All colors and sizes
    come from styles/theme.py, never hardcoded here."""
    if root is None:
        st.info("Árbol vacío — carga un escenario para verlo aquí.")
        return

    G, pos = _build_graph(root)
    node_colors = [
        TREE_HIGHLIGHT_NODE_COLOR if n == str(highlight_id) else TREE_NORMAL_NODE_COLOR
        for n in G.nodes()
    ]

    fig, ax = plt.subplots(figsize=TREE_FIGURE_SIZE)
    nx.draw(
        G, pos,
        with_labels=True,
        node_color=node_colors,
        node_size=TREE_NODE_SIZE,
        font_color=TREE_FONT_COLOR,
        edge_color=TREE_EDGE_COLOR,
        ax=ax,
    )
    st.pyplot(fig)
    plt.close(fig)