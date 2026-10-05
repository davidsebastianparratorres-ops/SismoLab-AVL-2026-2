import streamlit as st


def render_mode_status(scenery, report):
    """One line, always visible: the execution mode (and how far the tree is from AVL)."""
    if not scenery.stress_mode:
        st.markdown(":green[●] **Modo normal** · el árbol cumple AVL")
    elif report.imbalanced_count:
        st.markdown(f":orange[●] **MODO ESTRÉS** · {report.imbalanced_count} nodo(s) desbalanceado(s)")
    else:
        st.markdown(":orange[●] **MODO ESTRÉS** · el árbol aún cumple AVL")


def render_mode_banner(scenery, report=None):
    """The explanation of the stress mode (section 8: the interface must say that the tree may
    stop being AVL). Silent in normal mode. Pass the audit if the caller already has it."""
    if not scenery.stress_mode:
        return
    report = report or scenery.verify_structure()
    if report.imbalanced_count:
        st.warning(
            f"**Modo estrés:** el árbol NO cumple AVL ({report.imbalanced_count} nodo(s) con "
            "|factor de balance| > 1). Las rotaciones están aplazadas; la recuperación global "
            "restablece el equilibrio."
        )
    else:
        st.info("**Modo estrés:** las rotaciones están aplazadas, aunque por ahora el árbol cumple AVL.")
    if report.has_errors():
        st.error("La auditoría encontró errores de orden o de metadatos. Revisa 'Verificar estructura'.")


def render_archive_preview(preview):
    """What archiving would do, BEFORE the user confirms (section 10)."""
    st.markdown("#### Vista previa de la operación")
    st.caption("La selección representa la topología actual y queda fija para esta operación.")
    with st.container(border=True):
        root_col, count_col = st.columns(2)
        root_col.metric("Raíz de la rama", preview.root_id)
        count_col.metric("Eventos que pasarán al histórico", preview.count)
        st.markdown("**Identificadores afectados**")
        st.markdown(" · ".join(f"`{event_id}`" for event_id in preview.ids))
    with st.container(border=True):
        st.markdown("**Justificación de selección**")
        st.info(preview.justification)


def render_versions(versions):
    if not versions:
        st.caption("No hay versiones guardadas en esta carpeta.")
        return
    st.table([{"Nombre": v.name, "Guardada (UTC)": v.saved_at} for v in versions])