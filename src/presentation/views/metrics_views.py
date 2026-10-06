import streamlit as st

from src.controllers.Indicators import build_indicators, traversals

PRIORITY_NAMES = {3: "Alta (3)", 2: "Media (2)", 1: "Baja (1)"}


def _row(items):
    """items: [(label, value)] shown as one row of metric cards."""
    columns = st.columns(len(items))
    for column, (label, value) in zip(columns, items):
        column.metric(label, value)


def _arrow_list(ids):
    return " → ".join(str(event_id) for event_id in ids) if ids else "(árbol vacío)"


def _fmt_time(moment):
    return moment.strftime("%Y-%m-%d %H:%M")


def _render_reference_events(entries):
    with st.expander(f"Ver los {len(entries)} evento(s) con referencia (posibles réplicas)"):
        if not entries:
            st.caption("Ningún evento tiene referencia: no hay candidatos dentro de W horas y R km.")
            return
        st.caption("Cada fila es un evento (réplica) y el evento que se eligió como su referencia: "
                   "mayor magnitud, ocurrido antes, a lo sumo W horas y R km. Puede estar activo o archivado.")
        st.table([
            {"Evento": e["replica"]["id"], "Estado": e["replica"]["location"],
             "Magnitud": f"{e['replica']['magnitude']:.1f}",
             "Referencia": e["reference"]["id"], "Estado de la referencia": e["reference"]["location"],
             "Magnitud de la referencia": f"{e['reference']['magnitude']:.1f}",
             "Horas de diferencia": f"{e['hours_apart']:.1f}", "Distancia (km)": f"{e['distance_km']:.1f}"}
            for e in entries
        ])
        used = {}
        for e in entries:
            used.setdefault(e["reference"]["id"], []).append(e["replica"]["id"])
        st.markdown("**Eventos usados como referencia**")
        st.table([
            {"Referencia": ref, "Veces usada": len(replicas), "Réplicas": ", ".join(map(str, sorted(replicas)))}
            for ref, replicas in sorted(used.items())
        ])


def _render_archived_events(entries):
    with st.expander(f"Ver los {len(entries)} evento(s) archivado(s) en el histórico"):
        if not entries:
            st.caption("No hay eventos archivados en este momento.")
            return
        st.caption("Salieron del AVL activo pero conservan identidad, datos y asociaciones. "
                   "Un reporte con revisión mayor puede reactivarlos.")
        st.table([
            {"Evento": e["id"], "Magnitud": f"{e['magnitude']:.1f}", "Profundidad (km)": f"{e['depth_km']:.1f}",
             "Prioridad": e["priority"], "Revisión": e["review"], "Atención": e["attention"],
             "Ocurrió (UTC)": _fmt_time(e["occurred_at"]), "Antigüedad (h)": f"{e['age_hours']:.0f}",
             "Epicentro": f"({e['epicenter'][0]}, {e['epicenter'][1]})",
             "Estaciones": ", ".join(e["stations"]),
             "Referencia": e["reference_id"] if e["reference_id"] is not None else "—"}
            for e in entries
        ])


def render_tree_metrics(scenery):
    """Every indicator that section 14 asks to keep visible, plus the structural figures of
    sections 8, 9 and 12 that describe the tree shown above. Read-only: it never changes
    the scenario, and every number is computed from the current state, so undo and restoring
    a version bring them back automatically."""
    data = build_indicators(scenery)

    st.markdown("### Indicadores del árbol")

    st.markdown("#### Estructura")
    _row([
        ("Eventos activos", data["active"]),
        ("Eventos históricos", data["historic"]),
        ("Altura", data["height"]),
        ("Hojas", data["leaves"]),
        ("Raíz (evento)", data["root_id"] if data["root_id"] is not None else "—"),
    ])
    _row([
        ("Profundidad máxima", data["max_depth"]),
        ("Costo medio de búsqueda", f"{data['average_search_cost']:.2f}"),
        ("Costo máximo de búsqueda", data["max_search_cost"]),
        ("IDs eliminados", data["eliminated"]),
        ("Reportes en cola", data["queued"]),
    ])
    st.caption("Costo de búsqueda = nodos visitados desde la raíz para localizar un evento por su "
               "clave (profundidad + 1). No es tiempo real.")

    st.markdown("#### Equilibrio")
    if data["avl_ok"]:
        status = "Cumple AVL"
    elif data["stress_mode"]:
        status = "No cumple (modo estrés)"
    else:
        status = "No cumple"
    _row([
        ("Propiedad AVL", status),
        ("Nodos desbalanceados", data["imbalanced"]),
        ("Mayor desbalance", data["max_imbalance"]),
        ("Modo de ejecución", "Estrés" if data["stress_mode"] else "Normal"),
    ])

    st.markdown("#### Eventos por prioridad y atención")
    _row([
        (PRIORITY_NAMES[3], data["by_priority"][3]),
        (PRIORITY_NAMES[2], data["by_priority"][2]),
        (PRIORITY_NAMES[1], data["by_priority"][1]),
        ("Pendientes de atención", data["pending"]),
        ("Revisados", data["reviewed"]),
    ])

    st.markdown("#### Operaciones acumuladas")
    _row([
        ("Correcciones aceptadas", data["corrections_accepted"]),
        ("Reportes descartados", data["reports_discarded"]),
        ("Conflictos", data["conflicts"]),
    ])
    _row([
        ("Archivos masivos", data["mass_archives"]),
        ("Eventos archivados", data["events_archived"]),
        ("Eventos con referencia", data["with_reference"]),
    ])
    _render_reference_events(data["reference_entries"])
    _render_archived_events(data["archived_entries"])
    st.caption("«Eventos archivados» es un contador acumulado de la sesión; la lista muestra los que están "
               "en el histórico ahora (los reactivados ya no aparecen).")

    st.markdown("#### Rebalanceo del AVL")
    _row([
        ("Casos LL", data["case_LL"]),
        ("Casos RR", data["case_RR"]),
        ("Casos LR", data["case_LR"]),
        ("Casos RL", data["case_RL"]),
    ])
    _row([
        ("Giros simples a la izquierda", data["rotations_left"]),
        ("Giros simples a la derecha", data["rotations_right"]),
        ("Giros elementales en total", data["elementary_rotations"]),
    ])
    st.caption("Un caso doble (LR o RL) cuenta como un caso y como dos giros elementales.")

    st.markdown(f"#### Acceso costoso (prioridad alta con profundidad > L = {scenery.access_depth_limit})")
    if data["costly_entries"]:
        st.table([
            {"Evento": event_id, "Profundidad del nodo": depth, "Límite L": scenery.access_depth_limit,
             "Nodos visitados al buscarlo": cost}
            for event_id, depth, cost in sorted(data["costly_entries"])
        ])
    else:
        st.caption("Ningún evento de prioridad alta supera el límite.")

    with st.expander("Recorridos del árbol (identificadores de evento)", expanded=True):
        order = traversals(scenery.tree.getRoot())
        st.markdown("**Inorden** (claves ascendentes)")
        st.write(_arrow_list(order["inorder"]))
        st.markdown("**Preorden**")
        st.write(_arrow_list(order["preorder"]))
        st.markdown("**Postorden**")
        st.write(_arrow_list(order["postorder"]))
        st.markdown("**Por niveles**")
        st.write(_arrow_list(order["levels"]))