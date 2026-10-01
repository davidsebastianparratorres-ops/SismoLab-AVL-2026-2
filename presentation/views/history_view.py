import streamlit as st


def render_historic(historic):
    st.markdown("### Histórico")

    archived = historic.get_all_archived()
    if archived:
        rows = [
            {"ID": event_id, "Magnitud": event.getMagnitude(), "Estado": event.getStatus()}
            for event_id, event in archived.items()
        ]
        st.table(rows)
    else:
        st.caption("No hay eventos archivados todavía.")

    eliminated = historic.get_eliminated_ids()
    if eliminated:
        st.markdown("**Eliminados:** " + ", ".join(str(i) for i in sorted(eliminated)))
    else:
        st.caption("No hay eventos eliminados todavía.")


def render_undo_redo_controls(history):
    col1, col2 = st.columns(2)
    with col1:
        if st.button("↩️ Deshacer", disabled=not history.can_undo(), use_container_width=True):
            history.undo()
            st.rerun()
    with col2:
        if st.button("↪️ Rehacer", disabled=not history.can_redo(), use_container_width=True):
            history.redo()
            st.rerun()