"""Left navigation rail — sidebar + always-visible top nav in main area."""
import streamlit as st

from .components import pulse_dot
from .constants import NAV_GROUPS

_LOGO_SVG = (
    '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" '
    'stroke="#fff" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round">'
    '<rect x="4" y="7" width="16" height="12" rx="3"/>'
    '<path d="M12 7V4"/><circle cx="9" cy="13" r="1"/><circle cx="15" cy="13" r="1"/>'
    '<path d="M9.5 16.5h5"/></svg>'
)


def _connection_status(run_state, company_url):
    if run_state and run_state.get("error"):
        return "tone-warning", "Pipeline error"
    if run_state:
        return "tone-success", "Active"
    if company_url:
        return "tone-warning", "Ready to scan"
    return "tone-muted", "Not connected"


def render_sidebar(checklist: dict, run_state, company_url: str) -> None:
    with st.sidebar:
        st.markdown(
            '<div class="sidebar-brand">'
            f'<span class="sidebar-brand-mark">{_LOGO_SVG}</span>'
            '<span class="sidebar-brand-text">'
            '<span class="sidebar-logo">TenderBot</span>'
            '<span class="sidebar-tagline">AI Agent Workspace</span>'
            "</span></div>",
            unsafe_allow_html=True,
        )

        with st.container(key="sidebar-nav"):
            for group_label, items in NAV_GROUPS:
                if group_label:
                    st.markdown(f'<div class="nav-group">{group_label}</div>', unsafe_allow_html=True)
                for page_id, _icon_key, label in items:
                    is_active = st.session_state.active_page == page_id
                    if st.button(
                        label,
                        key=f"nav-{page_id}",
                        type="primary" if is_active else "secondary",
                        width="stretch",
                    ):
                        st.session_state.active_page = page_id
                        st.rerun()

        st.markdown('<div class="sidebar-spacer"></div>', unsafe_allow_html=True)

        profile = (run_state or {}).get("company_profile", {}) or {}
        company_name = profile.get("company_name")
        if not company_name or company_name == "not stated":
            company_name = company_url or "Not connected"

        tone, status_label = _connection_status(run_state, company_url)
        last_scan = run_state.get("run_time") if run_state else "Never scanned"

        st.markdown(
            '<div class="sidebar-status">'
            f'<div class="sidebar-status-company">{company_name}</div>'
            f'<div class="sidebar-status-meta">'
            f'{pulse_dot(tone)}{status_label} &nbsp;·&nbsp; {last_scan}'
            "</div></div>",
            unsafe_allow_html=True,
        )
