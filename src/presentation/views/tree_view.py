import streamlit as st
import networkx as nx
import matplotlib.pyplot as plt

from src.presentation.styles.theme import (
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
    """Pure presentation: turns a tree of Node objects into a picture."""
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


# NOTE: render_tree_queries (Section 11 query panel) used to live here,
# but it called AssociationManager(max_hours=w_hours, max_distance_km=r_km)
# and assoc_manager.build_callbacks(...) - neither exists anymore.
# AssociationManager now only takes a Scenery (W and R come from
# scenery.parameters, the single source of truth, not from constructor
# kwargs), and there never was a build_callbacks method; the project's own
# convention is to define get_candidates/get_reference as small local
# functions wherever they're needed (see tests/test_04_query_event.py).
# It also was never called from app.py, so nothing broke by removing it.
# The full event query (data, review, stations, priority, key, status,
# node depth/height/balance factor, associations) now lives in
# src/presentation/pages/event_crud_page.py, built against the real,
# current APIs: EventQueries.event_detail(...) + AssociationManager(scenery).
