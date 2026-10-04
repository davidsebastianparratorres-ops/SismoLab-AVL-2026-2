import streamlit as st

from src.controllers.BranchArchiver import BranchArchiver
from src.controllers.VersionStore import VersionStore
from src.presentation.pages.flash import show_flash, flash_and_rerun
from src.presentation.views.structure_view import render_archive_preview, render_versions


def render_structure_page():
    """Archive of old branches (section 10) and named versions (section 13). Entering stress
    mode and the global recovery already live in the configuration page."""
    st.markdown("### Archivo y versiones")
    show_flash("structure")
    tab_archive, tab_versions = st.tabs(["Archivar rama antigua", "Versiones"])
    with tab_archive:
        _render_archive_tab()
    with tab_versions:
        _render_versions_tab()


def _render_archive_tab():
    scenery = st.session_state.scenery
    archiver = BranchArchiver(scenery)
    st.caption(f"Es elegible una rama cuyos eventos son todos de prioridad baja y de más de "
               f"T = {scenery.parameters.t} h de antigüedad (reloj de simulación: "
               f"{scenery.simulation_clock.current_time:%Y-%m-%d %H:%M} UTC).")

    preview = archiver.preview()          # read-only: shown BEFORE anything is executed
    if preview is None:
        st.info("No hay ninguna rama elegible; el estado se conserva.")
        return

    render_archive_preview(preview)
    if scenery.stress_mode:
        st.caption("Modo estrés: al archivar solo se conserva el orden del árbol, sin rotar.")
    if st.button("Archivar esta rama", key="archive_branch_button"):
        result = archiver.archive()
        flash_and_rerun("structure", "success" if result.success else "error", result.message)


def _render_versions_tab():
    scenery = st.session_state.scenery
    directory = st.text_input("Carpeta de versiones", value="versions", key="versions_dir")
    store = VersionStore(directory)

    with st.form("save_version_form"):
        name = st.text_input("Nombre de la versión", key="version_name")
        saved = st.form_submit_button("Guardar versión actual")
    if saved:
        result = store.save(scenery, name)
        flash_and_rerun("structure", "success" if result.success else "error", result.message)

    versions = store.list()
    render_versions(versions)
    if not versions:
        return
    selected = st.selectbox("Versión a restaurar", [v.name for v in versions], key="version_select")
    if st.button("Restaurar versión seleccionada", key="restore_version_button"):
        result = store.restore(scenery, selected)    # validated first; one undoable action
        flash_and_rerun("structure", "success" if result.success else "error", result.message)