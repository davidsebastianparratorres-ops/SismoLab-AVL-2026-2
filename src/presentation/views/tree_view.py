import streamlit as st
import networkx as nx
import matplotlib.pyplot as plt
from src.controllers.EventQueries import EventQueries
from src.rules.AssociationManage import AssociationManager

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


   #Queries Component Section 11
def render_tree_queries(active_events: dict, archived_events: dict, w_hours: float = 24.0, r_km: float = 50.0):
    """Renderiza el panel interactivo para ejecutar las consultas sobre el árbol AVL."""
    st.divider()
    st.subheader("Consultas de la Sección 11")

    # Deferred invocation to avoid circular imports at startup
    

    tab1, tab2 = st.tabs(["Consulta de Asociaciones", "Otras Consultas"])

    with tab1:
        target_id = st.number_input("ID del evento a consultar:", min_value=1, max_value=999999, value=1, step=1)
        
        if st.button("Ejecutar Consulta de Asociaciones"):
            assoc_manager = AssociationManager(max_hours=w_hours, max_distance_km=r_km)
            get_candidates, get_reference = assoc_manager.build_callbacks(active_events, archived_events)
            
            queries = EventQueries()
            result = queries.event_associations(
                event_id=int(target_id),
                active_events=active_events,
                archived_events=archived_events,
                get_candidates=get_candidates,
                get_reference=get_reference
            )

            st.info(result.message)
            st.metric(label="Nodos examinados en el árbol", value=result.nodes_examined)

            if result.events:
                summary = result.events[0]
                st.write("**Referencia Elegida:**", summary.chosen_reference if summary.chosen_reference else "Ninguna")
                st.write(f"**Candidatos en rango ({len(summary.candidates)}):**", summary.candidates)
                st.write(f"**Eventos que lo referencian ({len(summary.referenced_by)}):**", summary.referenced_by)