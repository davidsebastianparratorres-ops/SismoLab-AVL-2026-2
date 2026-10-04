import json

import streamlit as st

from src.controllers.ScenarioPackage import ScenarioPackage


def render_scenario_package_page():
    """'Guardado estructural' (sección 12): el paquete completo del
    escenario -topología, histórico, cola, asociaciones, reloj,
    parámetros, métricas y modo-, no solo los eventos sueltos que ya
    maneja 'Cargar escenario' (Topologyio/InsertionIO).

    Guardar entrega un archivo para descargar (no hay disco del lado del
    usuario en una app de Streamlit); cargar lee el archivo que el propio
    usuario sube, en memoria, sin pasar por ningún filepath del servidor.
    """
    st.markdown("### Guardado estructural completo")

    tab_save, tab_load = st.tabs(["Guardar escenario", "Cargar escenario"])

    with tab_save:
        _render_save_tab()

    with tab_load:
        _render_load_tab()


def _render_save_tab():
    scenery = st.session_state.scenery
    st.caption(
        "Exporta la topología activa, el histórico, la cola de reportes, las "
        "asociaciones, el reloj, los parámetros, las métricas y el modo de "
        "ejecución en un solo archivo JSON."
    )

    data = ScenarioPackage().export(scenery)
    file_bytes = json.dumps(data, indent=2, ensure_ascii=False).encode("utf-8")

    st.download_button(
        "Descargar escenario (.json)",
        data=file_bytes,
        file_name="escenario.json",
        mime="application/json",
        key="download_scenario_button",
    )


def _render_load_tab():
    """Carga todo o nada: si parse() encuentra cualquier inconsistencia
    (orden, alturas, balance, asociaciones que no coinciden con lo
    recalculado, identidades duplicadas, eventos posteriores al reloj,
    etc.) nada se aplica y el escenario actual queda exactamente como
    estaba - apply() solo se llama después de que parse() ya tuvo éxito.
    """
    scenery = st.session_state.scenery

    uploaded_file = st.file_uploader(
        "Archivo de escenario (.json)", type="json", key="scenario_package_uploader"
    )
    if uploaded_file is None:
        return

    if not st.button("Cargar escenario", key="load_scenario_package_button"):
        return

    try:
        data = json.loads(uploaded_file.getvalue().decode("utf-8"))
    except json.JSONDecodeError as error:
        st.error("El archivo no es JSON válido: " + str(error))
        return

    result = ScenarioPackage().parse(data)
    if not result.success:
        st.error("No se pudo cargar el escenario. El estado actual no se modificó.")
        for error_message in result.errors:
            st.write("- " + error_message)
        return

    ScenarioPackage().apply(scenery, result.state)

    if result.state["stress_mode"]:
        st.warning(
            "El escenario se cargó en modo ESTRÉS"
            + (f", con {result.state['imbalanced']} nodo(s) desbalanceado(s)."
               if result.state["imbalanced"] else ".")
        )
    st.success("Escenario cargado correctamente.")