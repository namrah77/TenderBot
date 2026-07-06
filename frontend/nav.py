"""Top navigation — horizontal radio, always visible in the main workspace."""
import streamlit as st

from .constants import NAV_ITEMS

_PAGE_IDS = [page_id for page_id, _icon, label in NAV_ITEMS]
_PAGE_TO_LABEL = {page_id: label for page_id, _icon, label in NAV_ITEMS}


def render_top_nav() -> None:
    active = st.session_state.get("active_page", "home")
    if active not in _PAGE_IDS:
        active = _PAGE_IDS[0]

    with st.container(key="top-nav"):
        chosen = st.radio(
            "Navigation",
            options=_PAGE_IDS,
            format_func=lambda p: _PAGE_TO_LABEL[p],
            index=_PAGE_IDS.index(active),
            horizontal=True,
            label_visibility="collapsed",
            key="main-nav-radio",
        )
        if chosen != active:
            st.session_state.active_page = chosen
            st.rerun()
