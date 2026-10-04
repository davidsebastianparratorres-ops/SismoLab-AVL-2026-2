# Run with: streamlit run app.py

import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import streamlit as st
from src.presentation.pages.queries_page import render_queries_page

from src.presentation.pages.page_config import apply_page_config
from src.presentation.pages.session_state import init_session_state
from src.presentation.pages.scenario_load_page import render_scenario_load_page
from src.presentation.pages.scenario_config_page import render_scenario_config_page
from src.presentation.pages.event_crud_page import render_event_crud_page
from src.presentation.views.tree_view import render_tree
from src.presentation.views.history_view import render_historic, render_undo_redo_controls
from src.presentation.pages.queue_page import render_queue_page, advance_continuous_queue


def main():
    apply_page_config()
    init_session_state()

    st.markdown("<h1 style='text-align:center;'>SismoLab AVL</h1>", unsafe_allow_html=True)
    scenery = st.session_state.scenery
    left, right = st.columns([1, 2])

    with left:
        render_scenario_load_page()
        render_scenario_config_page()
        render_event_crud_page()
        render_queries_page()

    with right:
        tab_tree, tab_historic, tab_queue = st.tabs(["Árbol", "Histórico", "Cola"])
        render_undo_redo_controls(scenery.history)
        tab_tree, tab_historic = st.tabs(["Árbol", "Histórico"])
        with tab_tree:
            render_tree(scenery.tree.getRoot())
        with tab_historic:
            render_historic(scenery)
        with tab_queue:
            render_queue_page()
            
    advance_continuous_queue()
            


if __name__ == "__main__":
    main()