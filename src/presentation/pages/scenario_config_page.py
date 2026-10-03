import streamlit as st


def render_scenario_config_page():
    st.markdown("### Configuración del escenario")

    # Zones and stations are immutable once created (no edit, no delete),
    # so each tab below is just an add-form plus a read-only table - there
    # is deliberately no edit/remove control anywhere on this page.
    tab_zones, tab_stations = st.tabs(["Zonas", "Estaciones"])

    with tab_zones:
        _render_zones_tab()

    with tab_stations:
        _render_stations_tab()


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
