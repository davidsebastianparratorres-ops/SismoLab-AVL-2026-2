import streamlit as st


def show_flash(page: str):
    """Shows (once) the message a page left for itself before its last rerun."""
    notice = st.session_state.pop(f"flash_{page}", None)
    if notice:
        getattr(st, notice[0])(notice[1])


def flash_and_rerun(page: str, level: str, message: str):
    """An action stores its result and reruns, so the whole app is drawn from the new state."""
    st.session_state[f"flash_{page}"] = (level, message)
    st.rerun()