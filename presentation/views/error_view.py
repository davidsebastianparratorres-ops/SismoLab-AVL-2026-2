import streamlit as st


def render_errors(errors: list, title: str = "El archivo no es válido:"):
    st.error(title)
    for err in errors:
        st.write(f"- {err}")