"""Settings — company URL + checklist editing, plus the security audit
log (kept, just no longer a raw st.table)."""
import streamlit as st

from ..components import card, card_title, icon, section_header, status_dot
from ..constants import CQC_RATINGS
from ..data_utils import csv_to_list, save_checklist
from ..pipeline import run_pipeline


def render_settings(checklist: dict, data) -> None:
    section_header("Settings", "Company details & connection")

    with card("settings-url"):
        card_title(icon("globe"), "Company website", "The site TenderBot profiles before every scan.")
        display_name = st.text_input(
            "Your name",
            value=checklist.get("display_name", st.session_state.get("display_name", "")),
            placeholder="e.g. Alex",
            help="Shown in the welcome greeting on Agent Home.",
        )
        st.session_state["display_name"] = display_name
        company_url = st.text_input(
            "Company website URL",
            value=st.session_state.get("saved_url", ""),
            placeholder="https://yourcompany.co.uk",
            label_visibility="collapsed",
        )
        st.session_state["saved_url"] = company_url

    with card("settings-checklist"):
        card_title(icon("clipboard"), "Company checklist", "Auto-generated from your website on each run. Optional overrides saved here.")

        cqc_rating = st.selectbox(
            "CQC rating", CQC_RATINGS,
            index=CQC_RATINGS.index(checklist.get("cqc_rating", "Good")) if checklist.get("cqc_rating") in CQC_RATINGS else 1,
        )
        max_capacity_value = st.number_input(
            "Max contract capacity (£, optional)",
            min_value=0, max_value=500_000_000,
            value=int(checklist.get("max_capacity_value") or 0), step=10_000,
        )
        office_locations_str = st.text_area(
            "Office / branch locations (comma-separated)",
            value=", ".join(checklist.get("office_locations", [])),
        )
        certifications_str = st.text_area(
            "Certifications held (comma-separated)",
            value=", ".join(checklist.get("certifications", [])),
        )
        services_str = st.text_area(
            "Services offered (comma-separated)",
            value=", ".join(checklist.get("services", [])),
        )
        languages_str = st.text_area(
            "Languages (comma-separated, optional override)",
            value=", ".join(checklist.get("languages", [])),
        )

        col_save, col_run = st.columns(2)
        with col_save:
            if st.button("Save checklist", type="primary", width="stretch"):
                save_checklist({
                    "display_name": display_name,
                    "office_locations": csv_to_list(office_locations_str),
                    "certifications": csv_to_list(certifications_str),
                    "max_capacity_value": max_capacity_value or None,
                    "services": csv_to_list(services_str),
                    "languages": csv_to_list(languages_str),
                    "cqc_rating": cqc_rating,
                    "council_approvals": csv_to_list(checklist.get("council_approvals", [])),
                })
                st.success("Checklist saved.")
                st.rerun()
        with col_run:
            running = st.session_state.get("running", False)
            if st.button("Save & Run Agent", width="stretch", disabled=not company_url or running):
                save_checklist({
                    "display_name": display_name,
                    "office_locations": csv_to_list(office_locations_str),
                    "certifications": csv_to_list(certifications_str),
                    "max_capacity_value": max_capacity_value or None,
                    "services": csv_to_list(services_str),
                    "languages": csv_to_list(languages_str),
                    "cqc_rating": cqc_rating,
                    "council_approvals": csv_to_list(checklist.get("council_approvals", [])),
                })
                timeline_slot = st.empty()
                run_pipeline(company_url, timeline_slot)
                st.rerun()

    audit_log = (data or {}).get("audit_log") or []
    with card("settings-audit"):
        card_title(icon("shield"), "Security & audit log", "Guardrail events recorded on the last run.")
        if not audit_log:
            st.markdown('<span class="muted-note">No audit events recorded yet.</span>', unsafe_allow_html=True)
        else:
            for entry in audit_log:
                if not isinstance(entry, dict):
                    st.markdown(f"- {entry}")
                    continue
                severity = entry.get("severity", "INFO")
                tone = {"CRITICAL": "risk", "WARNING": "warning"}.get(severity, "success")
                st.markdown(
                    f'<div style="font-size:.83rem;margin-bottom:.3rem;">{status_dot(tone)}'
                    f'<b>{entry.get("event", "Event")}</b> '
                    f'<span class="muted-note">· {entry.get("timestamp", "")}</span></div>',
                    unsafe_allow_html=True,
                )

    if st.button("Reset last analysis"):
        st.session_state.run_state = None
        st.rerun()
