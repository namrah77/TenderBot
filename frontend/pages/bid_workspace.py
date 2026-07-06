"""Feasibility Report — rendered markdown with download and copy actions."""
import re

import streamlit as st

from ..components import badge, card, copy_to_clipboard_button, empty_state, section_header
from ..data_utils import confidence_tone


def _split_report(markdown: str):
    section_a, section_b = "", ""
    match = re.search(r"##\s*Section B", markdown, re.IGNORECASE)
    if match:
        section_a = markdown[: match.start()].strip()
        section_b = markdown[match.start():].strip()
    else:
        section_a = markdown.strip()
    return section_a, section_b


def render_bid_workspace(data, embedded: bool = False) -> None:
    if not embedded:
        section_header("Feasibility Report", "Bid readiness & executive summary")

    if not data:
        empty_state("No report", "Run an analysis to generate a feasibility report.")
        return
    if data.get("error"):
        st.error(f"Pipeline error: {data['error']}")
        return

    reliability = data.get("reliability_report", {}) or {}
    final_report = data.get("final_report", "No report generated.")

    with card("bid-reliability"):
        cols = st.columns([1, 1, 3])
        with cols[0]:
            st.markdown('<div class="profile-field-label">Reliability score</div>', unsafe_allow_html=True)
            st.markdown(
                f'<div class="kpi-value" style="font-size:1.5rem;">{reliability.get("reliability_score", "—")}%</div>',
                unsafe_allow_html=True,
            )
        with cols[1]:
            conf = reliability.get("overall_confidence", "—")
            st.markdown('<div class="profile-field-label">Confidence</div>', unsafe_allow_html=True)
            st.markdown(badge(conf, confidence_tone(conf)), unsafe_allow_html=True)
        with cols[2]:
            st.markdown('<div class="profile-field-label">Reviewer notes</div>', unsafe_allow_html=True)
            st.markdown(
                f'<div class="profile-field-value">{reliability.get("reviewer_notes", "—")}</div>',
                unsafe_allow_html=True,
            )

    section_a, section_b = _split_report(final_report)

    with card("bid-report-md"):
        st.markdown('<div class="panel-label">Feasibility Report</div>', unsafe_allow_html=True)
        st.markdown(section_a or "_No feasibility summary produced._")

    if section_b:
        with card("bid-section-b"):
            st.markdown('<div class="panel-label">Bid Readiness Checklist</div>', unsafe_allow_html=True)
            st.markdown(section_b)

    col_dl, col_copy = st.columns(2)
    with col_dl:
        st.download_button(
            "Download Markdown",
            data=final_report,
            file_name="tenderbot_report.md",
            mime="text/markdown",
            width="stretch",
        )
    with col_copy:
        copy_to_clipboard_button(final_report, label="Copy Report", key="copy-report-btn")
