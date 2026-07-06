"""TenderBot — Agent Workspace.

Thin orchestrator: page config, session bootstrap, and workspace routing.
All presentation logic lives in the `frontend` package.
"""
import streamlit as st

from frontend.data_utils import load_checklist
from frontend.nav import render_top_nav
from frontend.pages.home import render_home
from frontend.pages.settings import render_settings
from frontend.theme import inject_css

st.set_page_config(
    page_title="TenderBot — Agent Workspace",
    layout="wide",
    initial_sidebar_state="collapsed",
)
inject_css()

checklist_data = load_checklist()

st.session_state.setdefault("run_state", None)
st.session_state.setdefault("running", False)
st.session_state.setdefault("active_page", "home")
st.session_state.setdefault("saved_url", "")
st.session_state.setdefault("display_name", checklist_data.get("display_name", ""))
st.session_state.setdefault("assistant_topic", None)

run_state = st.session_state.run_state
if run_state and run_state.get("company_checklist"):
    checklist_data = {**checklist_data, **run_state["company_checklist"]}

render_top_nav()

if st.session_state.active_page == "settings":
    render_settings(checklist_data, run_state)
else:
    render_home(
        run_state,
        st.session_state.get("display_name", ""),
        checklist_data,
    )
