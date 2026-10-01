import streamlit as st

from src.models.Historic import Historic
from src.controllers.HistoryManager import HistoryManager
from src.controllers.TreeSnapshot import flatten_tree, rebuild_tree, copy_event


def _snapshot():
    return {
        "tree": flatten_tree(st.session_state.scenario_root),
        "events": {eid: copy_event(e) for eid, e in st.session_state.scenario_events.items()},
        "historic": st.session_state.scenario_historic.copy(),
    }


def _restore(snapshot):
    st.session_state.scenario_root = rebuild_tree(snapshot["tree"])
    st.session_state.scenario_events = snapshot["events"]
    st.session_state.scenario_historic = snapshot["historic"]


def init_session_state():
    if "scenario_root" not in st.session_state:
        st.session_state.scenario_root = None
    if "scenario_events" not in st.session_state:
        st.session_state.scenario_events = {}
    if "scenario_historic" not in st.session_state:
        st.session_state.scenario_historic = Historic()
    if "history" not in st.session_state:
        st.session_state.history = HistoryManager(_snapshot, _restore)
        
        