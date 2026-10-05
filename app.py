# Run with: streamlit run app.py

import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import streamlit as st

from src.presentation.pages.action_bar import render_action_bar
from src.presentation.pages.comparison_page import render_comparison_page
from src.presentation.pages.event_crud_page import render_event_crud_page
from src.presentation.pages.page_config import apply_page_config
from src.presentation.pages.queries_page import render_queries_page
from src.presentation.pages.queue_page import advance_continuous_queue, render_queue_page
from src.presentation.pages.scenario_config_page import render_scenario_config_page
from src.presentation.pages.scenario_load_page import render_scenario_load_page
from src.presentation.pages.scenario_package_page import render_scenario_package_page
from src.presentation.pages.session_state import init_session_state
from src.presentation.pages.structure_page import render_structure_page
from src.presentation.views.history_view import render_historic, render_undo_redo_controls
from src.presentation.views.spatial_view import render_spatial_map
from src.presentation.views.tree_view import render_tree


def main():
    apply_page_config()
    init_session_state()

    st.markdown("<h1 style='text-align:center;'>SismoLab AVL</h1>", unsafe_allow_html=True)
    scenery = st.session_state.scenery

    # Render the current mode after page actions have had a chance to change it.
    action_bar = st.container()
    left, right = st.columns([1, 2])

    with left:
        render_scenario_load_page()
        render_scenario_config_page()
        render_event_crud_page()
        render_queries_page()
        render_scenario_package_page()

    with right:
        render_undo_redo_controls(scenery.history)
        tab_tree, tab_spatial, tab_historic, tab_queue, tab_compare, tab_structure = st.tabs(
            ["Árbol", "Plano X/Y", "Histórico", f"Cola ({len(scenery.queue)})",
             "AVL vs BST", "Archivo y versiones"]
        )
        with tab_tree:
            render_tree(scenery.tree.getRoot())
        with tab_spatial:
            render_spatial_map(scenery)
        with tab_historic:
            render_historic(scenery)
        with tab_queue:
            render_queue_page()
        with tab_compare:
            render_comparison_page()
        with tab_structure:
            render_structure_page()

    with action_bar:
        render_action_bar()

    advance_continuous_queue()  # Must remain last; continuous processing reruns after drawing the UI.


if __name__ == "__main__":
    main()
