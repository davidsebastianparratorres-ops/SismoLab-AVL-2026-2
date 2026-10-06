import streamlit as st
import networkx as nx
import plotly.graph_objects as go

from src.presentation.styles.theme import (
    TREE_NORMAL_NODE_COLOR,
    TREE_HIGHLIGHT_NODE_COLOR,
    TREE_UNBALANCED_NODE_COLOR,
    TREE_EDGE_COLOR,
    TREE_FONT_COLOR,
)
from src.controllers.EventQueries import EventQueries
from src.presentation.views.event_detail_view import render_event_detail


@st.dialog("Información del nodo AVL", width="large")
def _render_node_dialog(scenery, node):
    event_id = node.getEventId()
    get_candidates, get_reference = scenery.association_manager.build_callbacks()
    result = EventQueries().event_detail(
        event_id,
        scenery.tree,
        scenery.active_events,
        scenery.archived_events,
        scenery.eliminated_ids,
        get_candidates,
        get_reference,
    )
    if not result.events:
        st.error(result.message)
        return

    render_event_detail(result.events[0])
    parent = node.getParent()
    left = node.getLeft()
    right = node.getRight()
    st.markdown("#### Conexiones del nodo AVL")
    columns = st.columns(4)
    columns[0].metric("Clave", str(node.getKey().as_tuple))
    columns[1].metric("Padre", parent.getEventId() if parent else "Raíz")
    columns[2].metric("Hijo izquierdo", left.getEventId() if left else "Ninguno")
    columns[3].metric("Hijo derecho", right.getEventId() if right else "Ninguno")


def _find_node(root, event_id):
    if root is None:
        return None
    if root.getEventId() == event_id:
        return root
    return _find_node(root.getLeft(), event_id) or _find_node(root.getRight(), event_id)


def _build_graph(node, G=None, pos=None, x=0.0, y=0.0, layer=1):
    if G is None:
        G, pos = nx.DiGraph(), {}
    if node is None:
        return G, pos

    label = str(node.getEventId())
    G.add_node(label, unbalanced=abs(node.getBalanceFactor()) > 1)
    pos[label] = (x, y)
    offset = 4 / (layer * 0.7)

    if node.getLeft():
        G.add_edge(label, str(node.getLeft().getEventId()))
        _build_graph(node.getLeft(), G, pos, x - offset, y - 1, layer + 1)
    if node.getRight():
        G.add_edge(label, str(node.getRight().getEventId()))
        _build_graph(node.getRight(), G, pos, x + offset, y - 1, layer + 1)

    return G, pos


def render_tree(root, highlight_id=None, scenery=None):
    """Pure presentation: turns a tree of Node objects into a picture."""
    if root is None:
        st.info("Árbol vacío — carga un escenario para verlo aquí.")
        return

    G, pos = _build_graph(root)
    edge_x, edge_y = [], []
    for parent, child in G.edges():
        edge_x.extend([pos[parent][0], pos[child][0], None])
        edge_y.extend([pos[parent][1], pos[child][1], None])

    node_ids = list(G.nodes())
    node_colors = [
        TREE_HIGHLIGHT_NODE_COLOR if n == str(highlight_id)
        else TREE_UNBALANCED_NODE_COLOR if G.nodes[n]["unbalanced"]
        else TREE_NORMAL_NODE_COLOR
        for n in node_ids
    ]
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=edge_x,
        y=edge_y,
        mode="lines",
        line={"color": TREE_EDGE_COLOR, "width": 2},
        hoverinfo="skip",
        showlegend=False,
    ))
    fig.add_trace(go.Scatter(
        x=[pos[node_id][0] for node_id in node_ids],
        y=[pos[node_id][1] for node_id in node_ids],
        mode="markers+text",
        text=node_ids,
        customdata=node_ids,
        textposition="middle center",
        textfont={"color": TREE_FONT_COLOR},
        marker={"color": node_colors, "size": 38, "line": {"color": "white", "width": 1}},
        hovertemplate="Evento %{customdata}<extra></extra>",
        showlegend=False,
    ))
    tree_levels = int(max(y for _, y in pos.values()) - min(y for _, y in pos.values())) + 1
    fig.update_layout(
        height=max(420, 100 + 85 * tree_levels),
        margin={"l": 20, "r": 20, "t": 20, "b": 20},
        xaxis={"visible": False},
        yaxis={"visible": False, "scaleanchor": "x", "scaleratio": 1},
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        clickmode="event+select",
    )
    if scenery is not None:
        st.caption("Haz clic en un nodo para consultar toda su información.")
        epoch = st.session_state.setdefault("tree_chart_epoch", 0)
        selection = st.plotly_chart(
            fig,
            key=f"avl_tree_chart_{epoch}",
            on_select="rerun",
            selection_mode="points",
            width="stretch",
        )
        points = selection.selection.points
        if points:
            selected_id = int(points[-1]["customdata"])
            st.session_state.tree_chart_epoch = epoch + 1
            selected_node = _find_node(root, selected_id)
            if selected_node is not None:
                _render_node_dialog(scenery, selected_node)
    else:
        st.plotly_chart(fig, width="stretch")

    unbalanced = sum(1 for _, flag in G.nodes(data="unbalanced") if flag)
    if unbalanced:
        st.caption(f"Naranja: {unbalanced} nodo(s) con |factor de balance| > 1 (el árbol no cumple AVL).")


# NOTE: render_tree_queries (Section 11 query panel) used to live here,
# but at the time it was written it called
# AssociationManager(max_hours=w_hours, max_distance_km=r_km) and
# assoc_manager.build_callbacks(...), neither of which existed yet back
# then (W/R come from scenery.parameters, not constructor kwargs).
# build_callbacks() was added later on AssociationManager itself (no args,
# bound to the manager's own scenery) - see AssociationManager.py - so if
# you're looking for that adapter, that's where it lives now. It also was
# never called from app.py, so nothing broke by removing this function.
# The full event query (data, review, stations, priority, key, status,
# node depth/height/balance factor, associations) now lives in
# src/presentation/pages/event_crud_page.py, built against the current
# APIs: EventQueries.event_detail(...) + scenery.association_manager.