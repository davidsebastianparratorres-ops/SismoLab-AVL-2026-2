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


def render_queue(queue):
    """Pure presentation: the FIFO queue in arrival order (the first row is processed first)."""
    reports = queue.to_list()
    if not reports:
        st.info("La cola está vacía.")
        return

    st.caption(f"{len(reports)} reporte(s) pendiente(s). Se procesan en orden de llegada, "
               "sin importar la prioridad del terremoto.")
    st.dataframe(
        [
            {
                "Posición": position,
                "Estación": r.station_id,
                "Evento": r.event_id,
                "Revisión": r.revision,
                "Magnitud": r.magnitude,
                "Profundidad (km)": r.depth_km,
                "Epicentro": f"({r.epicenter_x}, {r.epicenter_y})",
                "Hora (UTC)": r.occurred_at.strftime("%Y-%m-%d %H:%M:%S"),
            }
            for position, r in enumerate(reports, start=1)
        ],
        hide_index=True,
    )


def render_step_result(step):
    """Pure presentation: what the last queue step did and why (section 8)."""
    if step is None:
        return
    level, title = _DECISIONS.get(step.decision, ("info", step.decision))
    getattr(st, level)(f"**{title}.** {step.message}")

    col1, col2, col3 = st.columns(3)
    col1.metric("Estación", step.report.station_id)
    col2.metric("Evento", step.report.event_id)
    col3.metric("Revisión", step.report.revision)

    if step.rotations:
        st.write("**Rotaciones producidas:** " + ", ".join(
            f"{_ROTATIONS.get(name, name)} ×{amount}" for name, amount in step.rotations.items()))
    else:
        st.caption("Este paso no produjo rotaciones.")