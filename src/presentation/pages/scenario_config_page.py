from datetime import timedelta

import streamlit as st

from src.controllers.StressManager import StressManager
from src.presentation.views.audit_views import render_audit_report


def render_scenario_config_page():
    st.markdown("### Configuración del escenario")

    # Zones and stations are immutable once created (no edit, no delete),
    # so each tab below is just an add-form plus a read-only table - there
    # is deliberately no edit/remove control anywhere on this page.
    tab_zones, tab_stations, tab_clock, tab_audit = st.tabs(
        ["Zonas", "Estaciones", "Reloj y parámetros", "Auditoría y modo de ejecución"]
    )

    with tab_zones:
        _render_zones_tab()

    with tab_stations:
        _render_stations_tab()

    with tab_clock:
        _render_clock_tab()

    with tab_audit:
        _render_audit_tab()


def _render_zones_tab():
    scenery = st.session_state.scenery

    with st.form("add_zone_form"):
        x_min = st.number_input("x mínimo", min_value=0.0, max_value=1000.0, step=0.1, format="%.1f", key="zone_x_min")
        x_max = st.number_input("x máximo", min_value=0.0, max_value=1000.0, step=0.1, format="%.1f", key="zone_x_max")
        y_min = st.number_input("y mínimo", min_value=0.0, max_value=1000.0, step=0.1, format="%.1f", key="zone_y_min")
        y_max = st.number_input("y máximo", min_value=0.0, max_value=1000.0, step=0.1, format="%.1f", key="zone_y_max")
        populated = st.checkbox("Zona poblada", key="zone_populated")
        submitted = st.form_submit_button("Agregar zona")

    if submitted:
        result = scenery.add_zone(x_min, x_max, y_min, y_max, populated)
        if result.success:
            st.success(result.message)
        else:
            st.error(result.message)

    st.markdown("#### Zonas existentes")
    if not scenery.zones:
        st.caption("No hay zonas todavía.")
        return

    rows = [
        {
            "x_min": zone.getXMin(), "x_max": zone.getXMax(),
            "y_min": zone.getYMin(), "y_max": zone.getYMax(),
            "Poblada": zone.getPopulated(),
        }
        for zone in scenery.zones
    ]
    st.table(rows)


def _render_stations_tab():
    scenery = st.session_state.scenery

    with st.form("add_station_form"):
        station_id = st.text_input("Identificador de la estación", key="station_id")
        name = st.text_input("Nombre", key="station_name")
        submitted = st.form_submit_button("Agregar estación")

    if submitted:
        result = scenery.add_station(station_id, name)
        if result.success:
            st.success(result.message)
        else:
            st.error(result.message)

    st.markdown("#### Estaciones existentes")
    if not scenery.stations:
        st.caption("No hay estaciones todavía.")
        return

    rows = [
        {"ID": station.getStationId(), "Nombre": station.getName()}
        for station in scenery.stations.values()
    ]
    st.table(rows)


def _render_clock_tab():
    """Reloj de simulación (sección 3) y parámetros configurables W, R, L, T
    (secciones 7, 9 y 10). Scenery.advance_clock / update_parameters already
    validate everything and record one undoable action each - this tab is
    pure presentation, no validation logic lives here.

    IMPORTANT: every metric/value that depends on scenery's current state is
    read AFTER the form-submission block below it is handled, not before.
    Streamlit re-runs this whole function top to bottom on every click, so
    reading scenery.simulation_clock.to_dict() at the TOP of the function
    would show the value from before this run's own advance_clock() call -
    one step behind what the user just did, which looks like "the clock
    isn't moving" even though it actually is.
    """
    scenery = st.session_state.scenery

    st.markdown("#### Reloj de simulación")

    with st.form("advance_clock_form"):
        hours = st.number_input("Horas a avanzar", min_value=0.1, step=0.5, value=1.0, key="advance_clock_hours")
        advance_submitted = st.form_submit_button("Avanzar reloj")

    if advance_submitted:
        result = scenery.advance_clock(timedelta(hours=hours))
        if result.success:
            st.success(result.message)
        else:
            st.error(result.message)

    # Read down here, after the form above was already handled this run.
    st.metric("Hora actual (UTC)", scenery.simulation_clock.to_dict()["current_time"])

    st.markdown("#### Parámetros del escenario")

    with st.form("update_parameters_form"):
        p = scenery.parameters
        new_w = st.number_input("Nuevo W (horas)", min_value=0.0, value=float(p.w), step=1.0, key="param_w")
        new_r = st.number_input("Nuevo R (km)", min_value=0.0, value=float(p.r), step=1.0, key="param_r")
        new_l = st.number_input("Nuevo L", min_value=0, value=int(p.l), step=1, key="param_l")
        new_t = st.number_input("Nuevo T (horas)", min_value=0.0, value=float(p.t), step=1.0, key="param_t")
        params_submitted = st.form_submit_button("Actualizar parámetros")

    if params_submitted:
        result = scenery.update_parameters(w=new_w, r=new_r, l=int(new_l), t=new_t)
        if result.success:
            st.success(result.message)
        else:
            st.error(result.message)

    # Same reordering fix as the clock above: read the current values for
    # display AFTER the form processing, not before.
    p = scenery.parameters
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("W (horas)", p.w)
    col2.metric("R (km)", p.r)
    col3.metric("L (límite de profundidad)", p.l)
    col4.metric("T (horas)", p.t)


def _render_audit_tab():
    """'Verificar estructura' (sección 14). StressManager se crea aquí mismo porque no
    guarda ningún estado propio - solo orquesta sobre scenery, al contrario
    de AssociationManager, que sí necesita ser el mismo objeto persistente
    entre llamadas (ver Scenery.__init__ y la corrección en event_crud_page)."""
    scenery = st.session_state.scenery
    manager = StressManager(scenery)

    if st.button("Recuperación global", disabled=not scenery.stress_mode, key="recover_button"):
        recovery = manager.recover()
        if recovery.success:
            st.success(recovery.message)
        else:
            st.error(recovery.message)
        if recovery.rotations:
            st.caption("Costo de la recuperación: " + ", ".join(
                f"{name}={value}" for name, value in recovery.rotations.items()
            ))
        if recovery.audit is not None:
            render_audit_report(recovery.audit)

    # Read down here, after the two buttons above were already handled
    # this run - same reordering reasoning as the clock tab.
    mode_label = "ESTRÉS" if scenery.stress_mode else "NORMAL"
    st.metric("Modo de ejecución actual", mode_label)

    st.markdown("#### Verificar estructura")
    st.caption("Disponible en ambos modos: revisa el árbol sin modificarlo.")
    if st.button("Verificar estructura ahora", key="verify_structure_button"):
        render_audit_report(scenery.verify_structure())