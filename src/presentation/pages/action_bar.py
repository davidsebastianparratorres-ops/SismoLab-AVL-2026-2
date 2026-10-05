import streamlit as st

from src.controllers.StressManager import StressManager
from src.presentation.pages.flash import show_flash, flash_and_rerun
from src.presentation.pages.structure_page import render_archive_panel, render_versions_panel
from src.presentation.views.queue_view import describe_rotations
from src.presentation.views.structure_view import render_mode_status, render_mode_banner


@st.dialog("Archivar rama antigua")
def _archive_dialog():
    render_archive_panel()


@st.dialog("Versiones del escenario", width="large")
def _versions_dialog():
    render_versions_panel(key_prefix="dialog_")


def render_action_bar():
    """The actions that used to be buried in tabs, always one click away: execution mode
    (enter stress / global recovery), archive of old branches and named versions. Archive and
    versions open as pop-ups; every action reruns the app, so everything is drawn already updated."""
    scenery = st.session_state.scenery
    report = scenery.verify_structure()
    show_flash("structure")

    col_status, col_mode, col_archive, col_versions = st.columns([3, 2, 2, 2])
    with col_status:
        render_mode_status(scenery, report)
    with col_mode:
        _render_mode_button(scenery)
    with col_archive:
        if st.button("Archivar rama…", key="open_archive_dialog"):
            _archive_dialog()
    with col_versions:
        if st.button("Versiones…", key="open_versions_dialog"):
            _versions_dialog()
    render_mode_banner(scenery, report)


def _render_mode_button(scenery):
    manager = StressManager(scenery)
    if not scenery.stress_mode:
        if st.button("Activar modo estrés", key="bar_enter_stress"):
            result = manager.enter_stress()
            flash_and_rerun("structure", "success" if result.success else "error", result.message)
        return
    if st.button("Recuperar equilibrio (AVL)", key="bar_recover", type="primary"):
        result = manager.recover()                 # audits first and last; one undoable action
        message = result.message
        if result.rotations:
            message += " Costo: " + describe_rotations(result.rotations) + "."
        flash_and_rerun("structure", "success" if result.success else "error", message)