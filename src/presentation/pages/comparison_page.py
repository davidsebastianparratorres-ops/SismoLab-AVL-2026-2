import streamlit as st

from src.controllers.TreeComparison import TreeComparison, ORDER_LABELS, MAX_COMPARISON_EVENTS
from src.presentation.views.comparison_view import render_comparison, render_orders_table


def available_load_order(keys):
    """The insertion order of the last insertion-mode load, but only while it still
    describes exactly the events that are active now."""
    sequence = st.session_state.get("insertion_sequence")
    if sequence is not None and set(sequence) == {k[2] for k in keys}:
        return list(sequence)
    return None


def render_comparison_page():
    """AVL vs BST for the active events (sections 11, 12 and 15). It builds two fresh
    trees from the current events, so the live scenario is never modified."""
    scenery = st.session_state.scenery
    st.markdown("### Comparación AVL vs BST")

    keys = TreeComparison.keys_from_events(scenery.active_events)
    if not keys:
        st.info("No hay eventos activos para comparar. Carga un escenario o crea eventos.")
        return
    if len(keys) > MAX_COMPARISON_EVENTS:
        st.warning(f"La comparación admite hasta {MAX_COMPARISON_EVENTS} eventos; hay {len(keys)}.")
        return

    load_order = available_load_order(keys)
    orders = (["load"] if load_order is not None else []) + ["ascending", "descending", "random"]
    order = st.selectbox("Orden de inserción", orders, format_func=lambda o: ORDER_LABELS[o],
                         key="comparison_order")
    seed = 0
    if order == "random":
        seed = int(st.number_input("Semilla", min_value=0, value=0, step=1, key="comparison_seed"))

    try:
        render_comparison(TreeComparison.compare(keys, order, seed, load_order))
        st.markdown("#### Mismos eventos, distintos órdenes de inserción")
        render_orders_table(TreeComparison.compare_all(keys, seed, load_order))
    except ValueError as error:
        st.error(str(error))