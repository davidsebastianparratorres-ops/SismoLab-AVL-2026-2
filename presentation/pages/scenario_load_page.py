import tempfile
import os

import streamlit as st

from src.controllers.Topologyio import TopologyIO


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


def _load_topology(filepath: str):
    # TODO: replace this placeholder once the team defines where zones
    # come from (see the pending "opción A/B" discussion). Until then,
    # priority validation won't find any populated zone.
    zones = st.session_state.get("scenario_zones", [])

    result = TopologyIO().load(filepath, zones)
    _apply_result(result)


def _apply_result(result):
    if not result.success:
        st.error("El archivo no es válido:")
        for err in result.errors:
            st.write(f"- {err}")
        return

    st.session_state.scenario_root = result.root
    st.session_state.scenario_events = result.events
    st.success("Escenario cargado correctamente.")