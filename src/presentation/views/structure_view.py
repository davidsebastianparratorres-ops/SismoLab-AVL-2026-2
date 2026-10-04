import streamlit as st


def render_mode_banner(scenery):
    """The execution mode, visible from every page (section 8: in stress mode the interface
    must say that the tree may stop being AVL). Silent in normal mode."""
    if not scenery.stress_mode:
        return
    report = scenery.verify_structure()
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
    st.markdown(f"**Rama elegida:** raíz {preview.root_id}, {preview.count} evento(s).")
    st.write("**Identificadores afectados:** " + ", ".join(str(i) for i in sorted(preview.ids)))
    st.caption(preview.justification)


def render_versions(versions):
    if not versions:
        st.caption("No hay versiones guardadas en esta carpeta.")
        return
    st.table([{"Nombre": v.name, "Guardada (UTC)": v.saved_at} for v in versions])