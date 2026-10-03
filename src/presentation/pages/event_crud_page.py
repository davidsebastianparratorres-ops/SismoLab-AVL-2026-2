import streamlit as st

from src.controllers.EventQueries import EventQueries
from src.presentation.views.event_detail_view import render_event_detail


def render_event_crud_page():
    st.markdown("### Gestión de eventos")

    # Query first, on purpose: it's the only one of the four operations
    # that doesn't touch the tree or the undo history, so it's the safest
    # way to confirm the Scenery wiring (session_state -> Scenery ->
    # EventQueries/AssociationManager) works before adding anything that
    # mutates state. Creation, correction and deletion tabs come next.
    (tab_query,) = st.tabs(["Consultar"])

    with tab_query:
        _render_query_tab()


def _render_query_tab():
    scenery = st.session_state.scenery
    event_id = st.number_input(
        "ID del evento a consultar", min_value=1, step=1, key="query_event_id"
    )

    if not st.button("Consultar", key="query_event_button"):
        return

    # BUG FIX: this used to build a throwaway `AssociationManager(scenery)`
    # here, which always starts with an empty `self.associations` dict and
    # never has `recalculate_all()` called on it. Candidates still came out
    # right (they are computed live), but the chosen reference and
    # "referenced by" always came out empty/None, even when a real stored
    # association existed. Reusing scenery.association_manager — the one
    # Scenery itself keeps up to date on every create/correct/delete — is
    # the fix: it is the single source of truth for associations.
    manager = scenery.association_manager

    # Same adapter pattern used throughout the project (see
    # tests/test_04_query_event.py): get_candidates/get_reference take an
    # Event object and return candidates / the chosen reference Event,
    # wrapping AssociationManager's own event_id-based API.
    def get_candidates(event):
        return manager.get_candidates_and_reference(event.getEventId())[0]

    def get_reference(event):
        reference_id = manager.get_candidates_and_reference(event.getEventId())[1]
        if reference_id is None:
            return None
        catalogue = {**scenery.active_events, **scenery.archived_events}
        return catalogue.get(reference_id)

    result = EventQueries().event_detail(
        int(event_id),
        scenery.tree,
        scenery.active_events,
        scenery.archived_events,
        scenery.eliminated_ids,
        get_candidates,
        get_reference,
    )

    if not result.events:
        st.warning(result.message)
        return

    render_event_detail(result.events[0])