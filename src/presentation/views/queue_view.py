import streamlit as st

# Display names live here (presentation), so the controller keeps stable English codes.
_DECISIONS = {
    "CREATED": ("success", "Evento creado"),
    "UPDATED": ("success", "Evento actualizado (revisión mayor)"),
    "REACTIVATED": ("success", "Evento reactivado desde el histórico"),
    "CONFIRMED": ("info", "Confirmación"),
    "CONFLICT": ("warning", "Conflicto: misma revisión con datos distintos"),
    "OUTDATED": ("warning", "Reporte antiguo descartado"),
    "REJECTED": ("error", "Reporte rechazado"),
}
_ROTATIONS = {
    "case_LL": "Caso LL", "case_RR": "Caso RR", "case_LR": "Caso LR", "case_RL": "Caso RL",
    "rotations_left": "Giros simples a la izquierda", "rotations_right": "Giros simples a la derecha",
}


def describe_rotations(rotations: dict) -> str:
    """'Caso LL ×1, Giros simples a la derecha ×1' - shared by the queue and the action bar."""
    return ", ".join(f"{_ROTATIONS.get(name, name)} ×{amount}" for name, amount in rotations.items())


def render_queue(queue):
    """Pure presentation: the FIFO queue in arrival order (the first row is processed first)."""
    reports = queue.to_list()
    if not reports:
        st.info("La cola está vacía. Los reportes nuevos aparecerán aquí en el orden en que se reciban.")
        return

    st.caption(f"{len(reports)} reporte(s) pendiente(s) · FIFO: el primero recibido se procesa primero, "
               "sin importar la prioridad del evento.")
    for position, report in enumerate(reports, start=1):
        with st.container(border=True):
            identity, station, revision = st.columns([2, 2, 1])
            identity.markdown(f"**#{position:02} · Evento {report.event_id}**")
            station.markdown(f"**Estación**  \n{report.station_id}")
            revision.markdown(f"**Revisión**  \n{report.revision}")
            details = st.columns(4)
            details[0].markdown(f"**Magnitud**  \n{report.magnitude:.1f}")
            details[1].markdown(f"**Profundidad**  \n{report.depth_km:.1f} km")
            details[2].markdown(f"**Epicentro**  \n({report.epicenter_x:.1f}, {report.epicenter_y:.1f})")
            details[3].markdown(f"**Ocurrencia UTC**  \n{report.occurred_at:%Y-%m-%d %H:%M:%S}")


def render_resolution_guide():
    """Explain the report-resolution cases alongside the interactive FIFO queue."""
    with st.expander("Guía de resolución de reportes", expanded=False):
        st.caption("La revisión se compara con el evento activo o archivado. Un ID eliminado se rechaza.")
        cases = [
            ("ID desconocido", "No existe en activos ni en el histórico.", "Crear evento · CREATED"),
            ("Revisión mayor", "La revisión recibida supera la vigente.", "Actualizar; si estaba archivado, reactivar"),
            ("Igual revisión · mismos datos", "Los datos del evento coinciden.", "Confirmar reporte · sumar estación sin duplicarla"),
            ("Igual revisión · datos distintos", "La misma revisión trae otra información.", "Conflicto · rechazar sin modificar el evento"),
            ("Revisión menor", "La revisión recibida es anterior a la vigente.", "Descartar por obsoleto"),
            ("ID eliminado", "La identidad está marcada como eliminada.", "Rechazar hasta deshacer la eliminación"),
        ]
        for start in range(0, len(cases), 2):
            columns = st.columns(2)
            for column, (title, condition, outcome) in zip(columns, cases[start:start + 2]):
                with column:
                    with st.container(border=True):
                        st.markdown(f"**{title}**")
                        st.caption(condition)
                        st.markdown(f"→ {outcome}")
        st.caption("Reportes con datos inválidos o estación desconocida también se rechazan.")


def render_step_result(step):
    """Pure presentation: what the last queue step did and why (section 8)."""
    if step is None:
        return
    level, title = _DECISIONS.get(step.decision, ("info", step.decision))
    st.markdown("#### Resultado del último paso")
    with st.container(border=True):
        getattr(st, level)(f"**{title}.** {step.message}")
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Estación", step.report.station_id)
        col2.metric("Evento", step.report.event_id)
        col3.metric("Revisión recibida", step.report.revision)
        col4.metric("Decisión", title)
        if step.rotations:
            st.markdown("**Rotaciones producidas**")
            st.caption(describe_rotations(step.rotations))
        else:
            st.caption("Sin rotaciones en este paso.")


def render_queue_history(history):
    """Show every processed report and its outcome, including imported bursts."""
    st.markdown("#### Historial de procesamiento")
    with st.expander(f"Pasos procesados ({len(history)})", expanded=False):
        if not history:
            st.caption("Los resultados aparecerán aquí al procesar reportes.")
            return

        for index, step in enumerate(reversed(history), start=1):
            level, title = _DECISIONS.get(step.decision, ("info", step.decision))
            with st.container(border=True):
                st.markdown(
                    f"**Paso {len(history) - index + 1} · Evento {step.report.event_id}** "
                    f"· Estación {step.report.station_id} · Revisión {step.report.revision}"
                )
                getattr(st, level)(f"**{title}.** {step.message}")
                if step.rotations:
                    st.caption("Rotaciones: " + describe_rotations(step.rotations))
                else:
                    st.caption("Sin rotaciones.")