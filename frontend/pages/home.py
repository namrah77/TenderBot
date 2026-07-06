"""Agent Workspace — header, status cards, input + timeline, results tabs."""
from datetime import datetime

import streamlit as st

from ..components import (
    card,
    card_title,
    empty_state,
    pipeline_progress_pct,
    render_timeline_html,
    status_cards_row,
    workspace_header,
)
from ..constants import STAGE_LABELS, STAGE_ORDER
from ..data_utils import execution_duration
from ..pipeline import run_pipeline
from .bid_workspace import render_bid_workspace
from .insights import render_insights
from .opportunities import render_opportunities
from .profile import render_profile


@st.fragment(run_every="1s")
def _live_timer(started_at: datetime | None) -> None:
    if not started_at:
        return
    elapsed = int((datetime.now() - started_at).total_seconds())
    mins, secs = divmod(elapsed, 60)
    display = f"{mins}m {secs:02d}s" if mins else f"{secs}s"
    st.markdown(f"**Execution time:** {display}", unsafe_allow_html=True)


def _pipeline_status(data, running: bool) -> tuple[str, str, str]:
    if running:
        return "Running", "Agent pipeline in progress", "tone-warning"
    if not data:
        return "Idle", "Ready to analyse", "tone-muted"
    if data.get("error"):
        return "Error", "Last run failed", "tone-risk"
    return "Complete", data.get("run_time", "Finished"), "tone-success"


def _render_status_cards(data, running: bool) -> None:
    profile = (data or {}).get("company_profile", {}) or {}
    company_name = profile.get("company_name", "")
    has_profile = bool(company_name and company_name != "not stated")

    tenders = (data or {}).get("tenders_found") or []
    eligibility = (data or {}).get("eligibility_results") or []
    report = (data or {}).get("final_report", "")
    has_report = bool(report and report != "No report generated.")

    pipe_val, pipe_help, _ = _pipeline_status(data, running)

    status_cards_row([
        ("activity", "Pipeline Status", pipe_val, pipe_help),
        ("building", "Company Profile", company_name if has_profile else "Not loaded", "From website scrape"),
        ("search", "Open Tenders", str(len(tenders)), "Actionable opportunities found"),
        ("check", "Evaluated", str(len(eligibility)), "Eligibility assessments"),
        ("file", "Report Generated", "Yes" if has_report else "No", "Feasibility report ready"),
    ])


def _render_input_workspace(data, running: bool) -> None:
    company_url = st.session_state.get("saved_url", "")

    with card("input-workspace"):
        card_title("globe", "Input Workspace", "Enter a UK care provider website to start analysis.")

        if company_url:
            st.text_input(
                "Company website URL",
                value=company_url,
                disabled=True,
                help="Change URL in Settings",
            )
        else:
            company_url = st.text_input(
                "Company website URL",
                placeholder="https://yourcompany.co.uk",
                key="workspace-url-input",
            )
            if company_url:
                st.session_state.saved_url = company_url

        url_to_use = st.session_state.get("saved_url", "") or company_url
        run_clicked = st.button(
            "Run Analysis",
            type="primary",
            disabled=running or not url_to_use,
            key="workspace-run-btn",
            width="stretch",
        )

        progress = st.session_state.get("pipeline_progress") or {}
        completed = progress.get("completed") or set()
        active = progress.get("active")
        pct = pipeline_progress_pct(completed, active) if running else (
            100 if data and not data.get("error") else 0
        )

        stage_label = STAGE_LABELS.get(active, "—") if running else (
            "Complete" if data and not data.get("error") else "—"
        )

        st.markdown(
            f'<div class="progress-track"><div class="progress-fill" style="width:{pct}%;"></div></div>'
            f'<div class="run-meta"><span>Stage: <strong>{stage_label}</strong></span></div>',
            unsafe_allow_html=True,
        )

        if running:
            _live_timer(st.session_state.get("pipeline_started_at"))
        elif data and not data.get("error"):
            st.markdown(
                f'<div class="run-meta"><span>Last run: <strong>{data.get("run_time", "—")}</strong></span>'
                f'<span>Duration: <strong>{execution_duration(data)}</strong></span></div>',
                unsafe_allow_html=True,
            )

        if run_clicked and url_to_use:
            st.session_state.saved_url = url_to_use
            timeline_slot = st.session_state.get("_timeline_slot")
            if timeline_slot is not None:
                run_pipeline(url_to_use, timeline_slot)
            st.rerun()


def _render_pipeline_timeline(data, running: bool) -> None:
    with card("pipeline-timeline"):
        st.markdown('<div class="panel-label">Pipeline Timeline</div>', unsafe_allow_html=True)
        timeline_slot = st.empty()
        st.session_state["_timeline_slot"] = timeline_slot

        if running:
            progress = st.session_state.get("pipeline_progress") or {}
            completed = progress.get("completed") or set()
            active = progress.get("active")
            timestamps = progress.get("timestamps") or {}
        else:
            timestamps = (data or {}).get("stage_timestamps", {}) or {}
            completed = set(timestamps.keys()) if timestamps else set()
            active = None
            if data and not data.get("error") and not completed:
                completed = {STAGE_ORDER[0]}

        timeline_slot.markdown(
            render_timeline_html(completed, active, timestamps),
            unsafe_allow_html=True,
        )


def _render_results_tabs(data, checklist: dict) -> None:
    st.markdown('<div class="panel-label" style="margin-top:.5rem;">Results</div>', unsafe_allow_html=True)
    tab_profile, tab_opps, tab_report, tab_insights = st.tabs([
        "Company Profile",
        "Tender Opportunities",
        "Feasibility Report",
        "Pipeline Insights",
    ])

    with tab_profile:
        render_profile(data, checklist, embedded=True)

    with tab_opps:
        render_opportunities(data, checklist, embedded=True)

    with tab_report:
        render_bid_workspace(data, embedded=True)

    with tab_insights:
        render_insights(data, embedded=True)


def render_home(data, display_name: str = "", checklist: dict | None = None) -> None:
    checklist = checklist or {}
    running = st.session_state.get("running", False)

    workspace_header()
    _render_status_cards(data, running)

    col_left, col_right = st.columns([1.05, 1], gap="medium")
    with col_right:
        _render_pipeline_timeline(data, running)
    with col_left:
        _render_input_workspace(data, running)

    if data and data.get("error"):
        st.error(f"Pipeline error: {data['error']}")
        return

    if not data and not running:
        st.write("")
        empty_state(
            "No analysis yet",
            "Enter your company website URL and click Run Analysis to start the agent pipeline.",
        )
        return

    if data and not data.get("error"):
        st.write("")
        _render_results_tabs(data, checklist)
