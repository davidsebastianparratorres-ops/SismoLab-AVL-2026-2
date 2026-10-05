from datetime import datetime, timezone

import streamlit as st

from src.controllers.EventQueries import EventQueries


def render_queries_page():
    """Section 11 queries that look across the whole catalogue (not a
    single event, which already has its own 'Consultar' tab inside
    Gestión de eventos). Each tab reports how many nodes EventQueries
    examined, since that cost is part of what the assignment asks for -
    not just the matching events themselves."""
    st.markdown("### Consultas")

    tab_pending, tab_magnitude, tab_date, tab_costly = st.tabs(
        ["Pendientes (orden descendente)", "Rango de magnitud",
         "Profundidad y fecha", "Prioridad alta con acceso costoso"]
    )

    with tab_pending:
        _render_pending_tab()

    with tab_magnitude:
        _render_magnitude_tab()

    with tab_date:
        _render_date_tab()

    with tab_costly:
        _render_costly_access_tab()


def _render_pending_tab():
    scenery = st.session_state.scenery

    k = st.number_input("Cantidad de eventos a mostrar (k)", min_value=1, step=1, key="query_pending_k")

    if not st.button("Buscar pendientes", key="query_pending_button"):
        return

    result = EventQueries().top_k_pending(scenery.tree.getRoot(), scenery.active_events, int(k))
    st.caption(f"{result.message} (nodos examinados: {result.nodes_examined})")

    if result.events:
        st.table([
            {"ID": e.getEventId(), "Prioridad": e.getPriority(), "Magnitud": e.getMagnitude()}
            for e in result.events
        ])


def _render_magnitude_tab():
    scenery = st.session_state.scenery

    col1, col2 = st.columns(2)
    magnitude_min = col1.number_input(
        "Magnitud mínima", min_value=-2.0, max_value=10.0, step=0.1, format="%.1f", key="query_mag_min"
    )
    magnitude_max = col2.number_input(
        "Magnitud máxima", min_value=-2.0, max_value=10.0, step=0.1, format="%.1f", value=10.0, key="query_mag_max"
    )

    if not st.button("Buscar por magnitud", key="query_magnitude_button"):
        return

    result = EventQueries().events_by_magnitude_range(
        scenery.tree.getRoot(), scenery.active_events, magnitude_min, magnitude_max
    )
    st.caption(f"{result.message} (nodos examinados: {result.nodes_examined})")

    if result.events:
        st.table([
            {"ID": e.getEventId(), "Prioridad": e.getPriority(), "Magnitud": e.getMagnitude()}
            for e in result.events
        ])


def _render_date_tab():
    scenery = st.session_state.scenery

    depth_limit = st.number_input(
        "Profundidad máxima del hipocentro (km)", min_value=0.0, max_value=700.0, step=0.1,
        format="%.1f", value=700.0, key="query_depth_limit"
    )
    col1, col2 = st.columns(2)
    date_min = col1.date_input("Fecha mínima (UTC)", key="query_date_min")
    date_max = col2.date_input("Fecha máxima (UTC)", key="query_date_max")

    if not st.button("Buscar por profundidad y fecha", key="query_date_button"):
        return

    start = datetime.combine(date_min, datetime.min.time(), tzinfo=timezone.utc)
    end = datetime.combine(date_max, datetime.max.time(), tzinfo=timezone.utc)

    result = EventQueries().events_by_depth_and_date_range(
        scenery.tree.getRoot(), scenery.active_events, depth_limit, start, end
    )
    st.caption(f"{result.message} (nodos examinados: {result.nodes_examined})")

    if result.events:
        st.table([
            {"ID": e.getEventId(), "Profundidad (km)": e.getDepth_km(), "Fecha": e.getOcurredAt()}
            for e in result.events
        ])


def _render_costly_access_tab():
    """Section 11, fourth bullet: high-priority (3) events whose node depth
    is strictly greater than L. Indicators.build_indicators() already calls
    this same query internally, but only keeps the COUNT for the summary
    panel - this tab is the actual detailed listing the spec asks for, with
    node depth, the L used, and the search cost (node depth + 1, section 9)
    for every event found, not just a number."""
    scenery = st.session_state.scenery

    st.caption(f"Límite de profundidad de acceso actual (L): {scenery.access_depth_limit}")

    if not st.button("Buscar prioridad alta con acceso costoso", key="query_costly_button"):
        return

    result = EventQueries().high_priority_costly_access(
        scenery.tree.getRoot(), scenery.active_events, scenery.access_depth_limit
    )
    st.caption(f"{result.message} (nodos examinados: {result.nodes_examined})")

    if result.events:
        st.table([
            {
                "ID": entry.event.getEventId(),
                "Prioridad": entry.event.getPriority(),
                "Profundidad del nodo": entry.node_depth,
                "Límite (L)": scenery.access_depth_limit,
                "Nodos visitados en la búsqueda": entry.search_cost,
            }
            for entry in result.events
        ])