import streamlit as st


def render_historic(scenery):
    st.markdown("### Histórico")

    archived = scenery.archived_events
    eliminated = scenery.eliminated_ids
    total_col, removed_col = st.columns(2)
    total_col.metric("Eventos archivados", len(archived))
    removed_col.metric("IDs eliminados", len(eliminated))

    st.markdown("#### Archivados · identidad y datos conservados")
    st.caption("Ya no pertenecen al AVL activo. Un reporte con revisión mayor puede reactivarlos.")
    if archived:
        for event_id, event in sorted(archived.items()):
            epicenter = event.getEpicenter()
            with st.container(border=True):
                st.markdown(f"**Evento {event_id}** · Archivado")
                info = st.columns(4)
                info[0].markdown(f"**Magnitud**  \n{event.getMagnitude():.1f}")
                info[1].markdown(f"**Profundidad**  \n{event.getDepth_km():.1f} km")
                info[2].markdown(f"**Revisión**  \n{event.getReview()}")
                info[3].markdown(f"**Prioridad**  \n{event.getPriority()}")
                st.caption(
                    f"Estado de atención: {event.getStatus()} · "
                    f"Epicentro: ({epicenter.getX()}, {epicenter.getY()}) · "
                    f"Ocurrencia: {event.getOcurredAt()}"
                )
                stations = event.getStations()
                associations = event.getAssociatedEvents()
                st.markdown(
                    f"**Estaciones:** {', '.join(stations) if stations else 'Ninguna'}  \n"
                    f"**Asociaciones conservadas:** "
                    f"{', '.join(str(item) for item in associations) if associations else 'Ninguna'}"
                )
    else:
        st.info("No hay eventos archivados todavía.")

    st.markdown("#### Identificadores eliminados")
    st.caption("Estos IDs no se reutilizan: los reportes recibidos para ellos se rechazan "
               "hasta que se deshaga la eliminación.")
    if eliminated:
        with st.container(border=True):
            st.markdown(" · ".join(f"`{event_id}`" for event_id in sorted(eliminated)))
    else:
        st.info("No hay identificadores eliminados.")


def render_undo_redo_controls(history):
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Deshacer", disabled=not history.can_undo(), use_container_width=True):
            history.undo()
            st.rerun()
    with col2:
        if st.button("Rehacer", disabled=not history.can_redo(), use_container_width=True):
            history.redo()
            st.rerun()
