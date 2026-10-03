from datetime import datetime, timezone

import streamlit as st

from src.controllers.EventQueries import EventQueries
from src.presentation.views.event_detail_view import render_event_detail
from src.controllers.AssociationManager import AssociationManager

def render_event_crud_page():
    st.markdown("### Gestión de eventos")

    # Query first, on purpose: it's the only one of the four operations
    # that doesn't touch the tree or the undo history, so it's the safest
    # way to confirm the Scenery wiring (session_state -> Scenery ->
    # EventQueries/AssociationManager) works before adding anything that
    # mutates state. Correction and deletion tabs come next.
    tab_query, tab_create = st.tabs(["Consultar", "Crear"])

    with tab_query:
        _render_query_tab()

    with tab_create:
        _render_create_tab()


def _event_detail(scenery, event_id: int):
    """Shared by every tab that needs to show an event's full detail
    (query right now; create/correct will reuse this too): builds the
    get_candidates/get_reference adapters (same pattern used throughout
    the project, see tests/test_04_query_event.py) and runs the real
    EventQueries.event_detail - no duplicated query logic per tab."""
    manager = AssociationManager(scenery)

    def get_candidates(event):
        return manager.get_candidates_and_reference(event.getEventId())[0]

    def get_reference(event):
        reference_id = manager.get_candidates_and_reference(event.getEventId())[1]
        if reference_id is None:
            return None
        catalogue = {**scenery.active_events, **scenery.archived_events}
        return catalogue.get(reference_id)

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
            "No hay estaciones configuradas todavía (pendiente de definir "
            "con el equipo). Cualquier creación será rechazada hasta que "
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

    # Section 7: a new event can become a candidate reference for others
    # (and can itself gain a reference), so a full recalculation runs
    # right after - same contract already documented in
    # Scenery.create_event/correct_event/delete_event's own comments.
    AssociationManager(scenery).recalculate_all()

    render_event_detail(_event_detail(scenery, result.event.getEventId()).events[0])
