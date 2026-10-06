import json
import time
from datetime import datetime, timezone

import streamlit as st

from src.controllers.ReportProcessor import ReportProcessor
from src.models.Report import Report, ReportQueue
from src.presentation.pages.flash import show_flash, flash_and_rerun
from src.presentation.views.error_view import render_errors
from src.presentation.views.queue_view import (
    render_queue,
    render_queue_history,
    render_resolution_guide,
    render_step_result,
)


def render_queue_page():
    """Burst preparation, the visible FIFO queue and the step / continuous controls (section 8).
    Every action stores its result in session_state and reruns the app, so the tree, the undo
    buttons and this page always show the same, already updated, state."""
    scenery = st.session_state.scenery
    st.markdown(f"### Cola FIFO de reportes ({len(scenery.queue)})")
    st.caption("Recepción, orden de llegada y procesamiento controlado de reportes sísmicos.")
    show_flash("queue")

    tab_prepare, tab_file = st.tabs(["Preparar ráfaga", "Cargar ráfaga (JSON)"])
    with tab_prepare:
        _render_prepare_tab()
    with tab_file:
        _render_file_tab()

    _render_controls()
    render_queue(scenery.queue)
    render_step_result(st.session_state.get("queue_last_step"))
    render_queue_history(st.session_state.get("queue_processing_history", []))
    render_resolution_guide()


def advance_continuous_queue():
    """Continuous processing, one step per app run. Call it ONCE, as the LAST line of the app
    script, so everything (tree, history, queue) is already drawn while it waits. Any other
    user interaction interrupts the wait before the flag below is set, which pauses the loop."""
    if not st.session_state.get("queue_running"):
        return
    scenery = st.session_state.scenery
    if len(scenery.queue) == 0:
        st.session_state.queue_running = False
        st.rerun()
    st.session_state.queue_last_step = ReportProcessor(scenery).process_next()
    _record_queue_step(st.session_state.queue_last_step)
    time.sleep(st.session_state.get("queue_delay", 1.0))
    st.session_state.queue_auto = True
    st.rerun()


def _render_prepare_tab():
    scenery = st.session_state.scenery
    if not scenery.stations:
        st.warning("No hay estaciones en el escenario. Agrégalas o carga un escenario para preparar reportes.")
        return

    clock = scenery.simulation_clock.current_time
    with st.form("queue_burst_form"):
        st.caption("Configura una ráfaga: cada estación seleccionada genera un reporte con estos datos. "
                   "La ráfaga se encola completa y no se aplica hasta procesarla.")
        col_id, col_revision, col_magnitude = st.columns(3)
        event_id = col_id.number_input("ID del evento", min_value=1, max_value=999999, step=1, key="queue_event_id")
        revision = col_revision.number_input("Revisión", min_value=1, step=1, key="queue_revision")
        magnitude = col_magnitude.number_input("Magnitud", min_value=-2.0, max_value=10.0, step=0.1,
                                               format="%.1f", key="queue_magnitude")
        col_depth, col_x, col_y = st.columns(3)
        depth_km = col_depth.number_input("Profundidad (km)", min_value=0.0, max_value=700.0, step=0.1,
                                          format="%.1f", key="queue_depth")
        epicenter_x = col_x.number_input("Epicentro X", min_value=0.0, max_value=1000.0, step=0.1,
                                         format="%.1f", key="queue_x")
        epicenter_y = col_y.number_input("Epicentro Y", min_value=0.0, max_value=1000.0, step=0.1,
                                         format="%.1f", key="queue_y")
        col_date, col_time = st.columns(2)
        occurred_date = col_date.date_input("Fecha de ocurrencia (UTC)", value=clock.date(), key="queue_date")
        occurred_time = col_time.time_input("Hora de ocurrencia (UTC)", value=clock.time().replace(microsecond=0),
                                            key="queue_time")
        stations = st.multiselect("Estaciones que reportan", list(scenery.stations.keys()),
                                  default=list(scenery.stations.keys())[:1], key="queue_stations")
        submitted = st.form_submit_button("Agregar ráfaga a la cola")

    if not submitted:
        return
    if not stations:
        st.error("Elige al menos una estación.")
        return

    occurred_at = datetime.combine(occurred_date, occurred_time, tzinfo=timezone.utc)
    reports = [Report(int(event_id), magnitude, depth_km, epicenter_x, epicenter_y, occurred_at,
                      int(revision), station) for station in stations]
    ReportProcessor(scenery).enqueue(reports)
    flash_and_rerun("queue", "success", f"{len(reports)} reporte(s) agregados a la cola (una sola acción deshacible).")


def _render_file_tab():
    st.caption("Lista JSON de reportes, con el mismo formato de la clave 'cola' del escenario guardado.")
    uploaded = st.file_uploader("Archivo de ráfaga", type="json", key="queue_burst_file")
    if not st.button("Encolar ráfaga del archivo", key="queue_burst_file_button"):
        return
    if uploaded is None:
        st.warning("Sube un archivo JSON primero.")
        return
    try:
        raw = json.load(uploaded)
    except ValueError as error:
        render_errors([f"JSON inválido: {error}"], "No se pudo leer el archivo:")
        return

    queue, errors = ReportQueue.from_dicts(raw)
    if errors:
        render_errors(errors, "La ráfaga no es válida; no se encoló nada:")
        return
    ReportProcessor(st.session_state.scenery).enqueue(queue.to_list())
    flash_and_rerun("queue", "success", f"{len(queue)} reporte(s) agregados a la cola (una sola acción deshacible).")


def _render_controls():
    scenery = st.session_state.scenery
    # A run that was NOT started by advance_continuous_queue() means the user did something
    # else (undo, a form, a tab...): the continuous loop stops instead of fighting that action.
    auto = st.session_state.pop("queue_auto", False)
    if st.session_state.get("queue_running") and not auto:
        st.session_state.queue_running = False
    running = st.session_state.get("queue_running", False)
    empty = len(scenery.queue) == 0

    col_step, col_run, col_pause, col_delay = st.columns([1, 1, 1, 1])
    col_delay.number_input("Pausa entre pasos (s)", min_value=0.0, max_value=10.0, value=1.0, step=0.5,
                           key="queue_delay")
    if col_step.button("Procesar un paso", disabled=empty or running, key="queue_step_button"):
        st.session_state.queue_last_step = ReportProcessor(scenery).process_next()
        _record_queue_step(st.session_state.queue_last_step)
        st.rerun()
    if col_run.button("Procesar continuo", disabled=empty or running, key="queue_run_button"):
        st.session_state.queue_running = True
        st.session_state.queue_auto = True
        st.rerun()
    if col_pause.button("Pausar", disabled=not running, key="queue_pause_button"):
        st.session_state.queue_running = False
        st.rerun()
    if running:
        st.info("Procesamiento continuo en curso. Cualquier otra acción lo pausa.")


def _record_queue_step(step):
    if step is not None:
        st.session_state.setdefault("queue_processing_history", []).append(step)