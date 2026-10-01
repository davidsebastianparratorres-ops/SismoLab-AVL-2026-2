import tempfile
import os

import streamlit as st

from src.controllers.Topologyio import TopologyIO
from src.views.views.error_view import render_errors


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
    zones = st.session_state.get("scenario_zones", [])  # TODO: pendiente de definir con el equipo
    result = TopologyIO().load(filepath, zones)
    _apply_result(result)


def _load_insertion(filepath: str):
    try:
        from src.controllers.InsertionIO import InsertionIO
    except ImportError:
        st.info("La carga por inserción todavía no está implementada.")
        return

    result = InsertionIO().load(filepath)
    _apply_result(result)


def _apply_result(result):
    if not result.success:
        render_errors(result.errors)
        return

    st.session_state.history.record()
    st.session_state.scenario_root = result.root
    st.session_state.scenario_events = result.events
    st.success("Escenario cargado correctamente.")