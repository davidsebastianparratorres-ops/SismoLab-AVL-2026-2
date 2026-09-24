import streamlit as st

from presentation.styles.theme import PAGE_CSS


def apply_page_config():
    st.set_page_config(layout="wide", page_title="SismoLab AVL")
    st.markdown(PAGE_CSS, unsafe_allow_html=True)