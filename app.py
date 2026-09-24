# Run with: streamlit run app.py

import sys
import os

# Ensures the project root (this file's own folder) is always importable,
# no matter from which working directory the app gets launched.
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import streamlit as st

from presentation.pages.page_config import apply_page_config
from presentation.pages.scenario_load_page import render_scenario_load_page
from presentation.views.tree_view import render_tree


def _init_session_state():
    if "scenario_root" not in st.session_state:
        st.session_state.scenario_root = None
    if "scenario_events" not in st.session_state:
        st.session_state.scenario_events = {}


def main():
    apply_page_config()
    _init_session_state()

    st.markdown("<h1 style='text-align:center;'>SismoLab AVL</h1>", unsafe_allow_html=True)
    left, right = st.columns([1, 2])

    with left:
        render_scenario_load_page()
    with right:
        render_tree(st.session_state.scenario_root)


if __name__ == "__main__":
    main()