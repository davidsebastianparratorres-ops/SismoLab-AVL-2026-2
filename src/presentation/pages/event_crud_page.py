from datetime import datetime, timezone

import streamlit as st

from src.controllers.EventQueries import EventQueries
from src.presentation.views.event_detail_view import render_event_detail


def render_event_crud_page():
    st.markdown("### Gestión de eventos")

    # Query first, on purpose: it's the only one of the four operations
    # that doesn't touch the tree or the undo history, so it's the safest
    # way to confirm the Scenery wiring (session_state -> Scenery ->
    # EventQueries/AssociationManager) works before adding anything that
    # mutates state. Correction and deletion tabs come next.
    tab_query, tab_create, tab_correct = st.tabs(["Consultar", "Crear", "Corregir"])

    with tab_query:
        _render_query_tab()

    with tab_create:
        _render_create_tab()

    with tab_correct:
        _render_correct_tab()


def _event_detail(scenery, event_id: int):
    """Shared by every tab that needs an event's full detail. Scenery now
    owns a single, persistent AssociationManager (scenery.association_manager,
    see Scenery.__init__) instead of a throwaway one built per call, and it
    already exposes the get_candidates/get_reference adapters itself via
    build_callbacks() - no need to hand-roll them per page anymore."""
    get_candidates, get_reference = scenery.association_manager.build_callbacks()

    return EventQueries().event_detail(
        event_id,
        scenery.tree,
        scenery.active_events,
        scenery.archived_events,
        scenery.eliminated_ids,
        get_candidates,
        get_reference,
    )


def _render_query_tab():
    scenery = st.session_state.scenery
    event_id = st.number_input(
        "ID del evento a consultar", min_value=1, step=1, key="query_event_id"
    )

    if not st.button("Consultar", key="query_event_button"):
        return

    result = _event_detail(scenery, int(event_id))
    if not result.events:
        st.warning(result.message)
        return

    render_event_detail(result.events[0])


def _render_create_tab():
    scenery = st.session_state.scenery

    if not scenery.stations:
        # Same open TODO as zones (see session_state.py): no configuration
        # page exists yet for stations, so the set is empty and every
        # creation will be rejected by create_event's own "Unknown
        # station" check until the team defines where stations come from.
        st.warning(
            "No hay estaciones todavía. Cualquier creación será rechazada hasta que "
            "existan estaciones reales en el escenario."
        )

    with st.form("create_event_form"):
        event_id = st.number_input("ID del evento", min_value=1, step=1, key="create_event_id")
        magnitude = st.number_input(
            "Magnitud", min_value=-2.0, max_value=10.0, step=0.1, format="%.1f", key="create_magnitude"
        )
        depth_km = st.number_input(
            "Profundidad (km)", min_value=0.0, max_value=700.0, step=0.1, format="%.1f", key="create_depth"
        )
        epicenter_x = st.number_input(
            "Epicentro X", min_value=0.0, max_value=1000.0, step=0.1, format="%.1f", key="create_x"
        )
        epicenter_y = st.number_input(
            "Epicentro Y", min_value=0.0, max_value=1000.0, step=0.1, format="%.1f", key="create_y"
        )
        occurred_date = st.date_input("Fecha de ocurrencia (UTC)", key="create_date")
        occurred_time = st.time_input("Hora de ocurrencia (UTC)", key="create_time")

        if scenery.stations:
            origin_station_id = st.selectbox(
                "Estación de origen", list(scenery.stations.keys()), key="create_station_select"
            )
        else:
            origin_station_id = st.text_input("Estación de origen", key="create_station_text")

        submitted = st.form_submit_button("Crear evento")

    if not submitted:
        return

    occurred_at = datetime.combine(occurred_date, occurred_time, tzinfo=timezone.utc)

    result = scenery.create_event(
        int(event_id), magnitude, depth_km, epicenter_x, epicenter_y, occurred_at, origin_station_id,
    )

    if not result.success:
        st.error(result.message)
        return

    st.success(result.message)

    # NOTE: no explicit recalculate_all() call needed here anymore -
    # Scenery.create_event now calls self.association_manager.recalculate_all()
    # internally (see Scenery.py). Calling it again here would just be
    # redundant, harmless extra work.
    render_event_detail(_event_detail(scenery, result.event.getEventId()).events[0])


def _render_correct_tab():
    scenery = st.session_state.scenery

    if not scenery.stations:
        st.warning(
            "No hay estaciones todavía. Cualquier corrección será rechazada hasta que "
            "existan estaciones reales en el escenario."
        )

    with st.form("correct_event_form"):
        event_id = st.number_input("ID del evento a corregir", min_value=1, step=1, key="correct_event_id")
        magnitude = st.number_input(
            "Nueva magnitud", min_value=-2.0, max_value=10.0, step=0.1, format="%.1f", key="correct_magnitude"
        )
        depth_km = st.number_input(
            "Nueva profundidad (km)", min_value=0.0, max_value=700.0, step=0.1, format="%.1f", key="correct_depth"
        )
        epicenter_x = st.number_input(
            "Nuevo epicentro X", min_value=0.0, max_value=1000.0, step=0.1, format="%.1f", key="correct_x"
        )
        epicenter_y = st.number_input(
            "Nuevo epicentro Y", min_value=0.0, max_value=1000.0, step=0.1, format="%.1f", key="correct_y"
        )

        if scenery.stations:
            reporting_station_id = st.selectbox(
                "Estación que reporta la corrección", list(scenery.stations.keys()), key="correct_station_select"
            )
        else:
            reporting_station_id = st.text_input("Estación que reporta la corrección", key="correct_station_text")

        submitted = st.form_submit_button("Corregir evento")

    if not submitted:
        return

    result = scenery.correct_event(
        int(event_id), magnitude, depth_km, epicenter_x, epicenter_y, reporting_station_id,
    )

    if not result.success:
        st.error(result.message)
        return

    st.success(result.message)

    # NOTE: same as creation - no explicit recalculate_all() call needed,
    # Scenery.correct_event already calls self.association_manager
    # internally (its own docstring predates that change and still says
    # otherwise - worth a quick fix by whoever touches that file next).
    render_event_detail(_event_detail(scenery, int(event_id)).events[0])
