import streamlit as st


def render_audit_report(report):
    """Pure presentation: turns an AuditReport (src/models/AuditReport.py)
    into a readable panel. All of the actual checking logic lives in
    TreeAuditor - this function only displays what it already computed."""
    
    if report.is_valid_avl:
        st.success("La propiedad AVL se cumple. No se encontraron inconsistencias.")
    else:
        st.error("La propiedad AVL NO se cumple.")

    col1, col2, col3 = st.columns(3)
    col1.metric("Nodos examinados", report.nodes_examined)
    col2.metric("Altura del árbol", report.tree_height)
    col3.metric("Nodos desbalanceados", report.imbalanced_count)

    errors_by_event = report.errors_by_event()
    if errors_by_event:
        st.markdown("#### Inconsistencias por evento")
        for event_id, issues in errors_by_event.items():
            with st.expander(f"Evento {event_id} ({len(issues)} problema(s))"):
                for issue in issues:
                    st.write(f"**[{issue.category}]** {issue.message}")

    notes = report.notes()
    if notes:
        st.markdown("#### Avisos (desbalance esperado en modo estrés)")
        for note in notes:
            st.caption(f"Evento {note.event_id}: {note.message}")