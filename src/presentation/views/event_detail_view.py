import streamlit as st


def render_event_detail(detail):
    """Pure presentation: turns an EventDetail DTO (src/dto/QueryResult.py)
    into a readable panel. No logic lives here - event_crud_page.py already
    did all the querying before calling this."""
    event = detail.event

    st.success(f"Evento {event.getEventId()} - {detail.location_status}")

    col1, col2, col3 = st.columns(3)
    col1.metric("Magnitud", event.getMagnitude())
    col2.metric("Profundidad (km)", event.getDepth_km())
    col3.metric("Prioridad", event.getPriority())

    col4, col5, col6 = st.columns(3)
    col4.metric("Revisión", event.getReview())
    col5.metric("Estado", event.getStatus())
    col6.metric("Clave (prioridad, magnitud, id)", str(detail.key))

    epicenter = event.getEpicenter()
    st.write("**Epicentro:**", f"({epicenter.getX()}, {epicenter.getY()})")
    st.write("**Estaciones:**", ", ".join(event.getStations()) or "Ninguna")
    st.write("**Fecha de ocurrencia:**", event.getOcurredAt())

    st.markdown("#### Posición en el árbol")
    if detail.node_depth is None:
        # Archived events leave the active AVL (section 7), so there is
        # simply no node to report here.
        st.caption("Este evento está archivado: no tiene nodo en el AVL activo.")
    else:
        d1, d2, d3 = st.columns(3)
        d1.metric("Profundidad del nodo", detail.node_depth)
        d2.metric("Altura", detail.node_height)
        d3.metric("Factor de balance", detail.balance_factor)

    st.markdown("#### Asociaciones")
    associations = detail.associations
    reference = associations.chosen_reference
    st.write("**Referencia elegida:**", reference.getEventId() if reference else "Ninguna")
    st.write(
        f"**Candidatos ({len(associations.candidates)}):**",
        [c.getEventId() for c in associations.candidates] or "Ninguno",
    )
    st.write(
        f"**Eventos que lo referencian ({len(associations.referenced_by)}):**",
        [e.getEventId() for e in associations.referenced_by] or "Ninguno",
    )
