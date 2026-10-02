from datetime import datetime, timezone

import streamlit as st

from src.controllers.Scenery import Scenery
from src.models.AVL import AVL
from src.models.SimulationClock import SimulationClock
from src.models.SimulationParameters import SimulationParameters


def init_session_state():
    # Option A (agreed with the team): a single Scenery instance is now the
    # one source of truth for the whole app - tree, events, history and
    # undo/redo all live inside it, instead of being split across loose
    # scenario_root / scenario_events / scenario_historic variables plus a
    # separate HistoryManager. Scenery.history is already a fully wired
    # HistoryManager (see Scenery.__init__), so st.session_state.history
    # just points at that same object instead of creating a second,
    # independent undo stack.
    #
    # Zones and stations still have no configuration page (same open TODO
    # scenario_load_page.py already had for zones), so they default to
    # empty here too, through the same st.session_state.get(..., default)
    # pattern, until the team defines where they come from.
    if "scenery" not in st.session_state:
        zones = st.session_state.get("scenario_zones", [])        # TODO: pendiente de definir con el equipo
        stations = st.session_state.get("scenario_stations", {})  # TODO: pendiente de definir con el equipo
        st.session_state.scenery = Scenery(
            zones=zones,
            stations=stations,
            simulation_clock=SimulationClock(datetime.now(timezone.utc)),
            tree=AVL(),
            parameters=SimulationParameters(),
        )

    if "history" not in st.session_state:
        st.session_state.history = st.session_state.scenery.history
