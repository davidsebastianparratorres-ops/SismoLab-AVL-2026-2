import tempfile
import os
import streamlit as st

from src.controllers.ScenarioPackage import ScenarioPackage
from src.controllers.InsertionIO import InsertionIO
from src.presentation.views.error_view import render_errors


def render_scenario_load_page():
    st.markdown("### Cargar escenario")
    mode = st.radio("Modo de carga", ["Topología", "Inserción"])
    uploaded_file = st.file_uploader("Archivo JSON", type="json")

    if not st.button("Cargar"):
        return
    if uploaded_file is None:
        st.warning("Sube un archivo JSON primero.")
        return

    temp_path = os.path.join(tempfile.gettempdir(), uploaded_file.name)
    with open(temp_path, "wb") as f:
        f.write(uploaded_file.getbuffer())

    if mode == "Topología":
        _load_topology(temp_path)
    else:
        _load_insertion(temp_path)


def _load_topology(filepath: str):
    package = ScenarioPackage()
    result = package.load(filepath)
    if not result.success:
        render_errors(result.errors)
        return

    package.apply(st.session_state.scenery, result.state)
    st.session_state.pop("insertion_sequence", None)  # a topology has no insertion order

    imbalanced = result.state["imbalanced"]
    if result.state["stress_mode"]:
        st.warning(
            f"Escenario cargado en modo estrés: {imbalanced} nodo(s) con |factor de balance| > 1."
            if imbalanced else "Escenario cargado en modo estrés (el árbol está balanceado)."
        )
    else:
        st.success("Escenario cargado correctamente.")


def _load_insertion(filepath: str):
    zones = st.session_state.scenery.zones
    result = InsertionIO().load(filepath, zones)
    _apply_result(result)
    if result.success:
        # The file's order is the insertion order the AVL vs BST comparison must replay.
        st.session_state["insertion_sequence"] = list(result.events)
        st.info("La pestaña «AVL vs BST» muestra ambos árboles con este mismo orden de inserción.")


def _apply_result(result):
    if not result.success:
        render_errors(result.errors)
        return

    # A fresh load replaces the whole scenario: every loaded event starts
    # out active (neither TopologyIO nor InsertionIO produce archived or
    # eliminated events), so both of those are reset too, not just the
    # tree/events.
    scenery = st.session_state.scenery
    scenery.history.record()
    scenery.tree.setRoot(result.root)
    scenery.active_events = result.events
    scenery.archived_events = {}
    scenery.eliminated_ids = set()

    # Events loaded from a file already carry real station ids - register
    # any that aren't known yet, so the "Estaciones" page reflects what
    # was actually loaded instead of staying empty until someone re-types
    # the same ids by hand.
    station_ids = {sid for event in result.events.values() for sid in event.getStations()}
    scenery.register_known_stations(station_ids)

    st.success("Escenario cargado correctamente.")