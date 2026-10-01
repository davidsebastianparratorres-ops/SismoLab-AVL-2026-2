# Run with: streamlit run app.py

import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import streamlit as st

from src.presentation.pages.page_config import apply_page_config
from src.presentation.pages.session_state import init_session_state
from src.presentation.pages.scenario_load_page import render_scenario_load_page
from src.presentation.views.tree_view import render_tree
from src.presentation.views.history_view import render_historic, render_undo_redo_controls


def main():
    apply_page_config()
    init_session_state()

    st.markdown("<h1 style='text-align:center;'>SismoLab AVL</h1>", unsafe_allow_html=True)
    left, right = st.columns([1, 2])

    with left:
        render_scenario_load_page()

    with right:
        render_undo_redo_controls(st.session_state.history)
        tab_tree, tab_historic = st.tabs(["Árbol", "Histórico"])
        with tab_tree:
            render_tree(st.session_state.scenario_root)
        with tab_historic:
            render_historic(st.session_state.scenario_historic)


if __name__ == "__main__":
    main()