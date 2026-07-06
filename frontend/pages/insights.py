"""Pipeline Insights — debug metrics and run summary (presentation only)."""
import streamlit as st

from ..components import card, empty_state, section_header


def _insight_stat(value: str, label: str) -> str:
    return (
        '<div class="insight-stat">'
        f'<div class="insight-stat-value">{value}</div>'
        f'<div class="insight-stat-label">{label}</div>'
        "</div>"
    )


def render_insights(data, embedded: bool = False) -> None:
    if not embedded:
        section_header("Pipeline Insights", "Run diagnostics & summary")

    if not data:
        empty_state("No insights yet", "Run an analysis to see pipeline metrics.")
        return
    if data.get("error"):
        st.error(f"Pipeline error: {data['error']}")
        return

    dbg = data.get("pipeline_debug") or {}
    tenders = data.get("tenders_found") or []
    eligibility = data.get("eligibility_results") or []
    src = dbg.get("sources", {}) if dbg else {}
    cls = dbg.get("deadline_classification", {}) if dbg else {}

    discovery_candidates = (
        dbg.get("discovery_deduped")
        or dbg.get("discovery_returned")
        or sum(src.values())
        or "—"
    )
    actionable = dbg.get("crawl_open_count") or dbg.get("eligibility_input_count") or len(tenders)
    evaluated = len(eligibility)
    gemini_calls = dbg.get("gemini_calls", "—") if dbg else "—"

    from ..data_utils import execution_duration
    duration = execution_duration(data)

    stats_html = "".join([
        _insight_stat(str(discovery_candidates), "Discovery candidates"),
        _insight_stat(str(actionable), "Actionable tenders"),
        _insight_stat(str(evaluated), "Evaluated tenders"),
        _insight_stat(str(gemini_calls), "Gemini calls"),
        _insight_stat(duration, "Execution time"),
        _insight_stat(data.get("status", "completed").replace("_", " ").title(), "Pipeline status"),
    ])
    st.markdown(f'<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:.65rem;">{stats_html}</div>', unsafe_allow_html=True)

    if dbg:
        st.write("")
        with card("insights-summary"):
            st.markdown('<div class="panel-label">Pipeline summary</div>', unsafe_allow_html=True)
            lines = [
                f"Contracts Finder: **{src.get('contracts_finder', 0)}** candidates",
                f"Find a Tender: **{src.get('find_a_tender', 0)}** candidates",
                f"Discovery deduped: **{dbg.get('discovery_deduped', 0)}**",
                f"Crawl open/actionable: **{dbg.get('crawl_open_count', 0)}**",
                f"Eligibility input: **{dbg.get('eligibility_input_count', 0)}**",
                f"Checklist from profile: **{'Yes' if dbg.get('company_checklist_from_profile') else 'No'}**",
            ]
            for line in lines:
                st.markdown(line)

        if cls:
            st.write("")
            with card("insights-deadlines"):
                st.markdown('<div class="panel-label">Deadline classification</div>', unsafe_allow_html=True)
                cols = st.columns(len(cls))
                for col, (status, count) in zip(cols, cls.items()):
                    with col:
                        st.markdown(
                            f'<div class="insight-stat">'
                            f'<div class="insight-stat-value">{count}</div>'
                            f'<div class="insight-stat-label">{status.title()}</div></div>',
                            unsafe_allow_html=True,
                        )
    elif not embedded:
        st.info("Enable PIPELINE_DEBUG=1 in your environment for detailed pipeline metrics.")

    audit_log = data.get("audit_log") or []
    if audit_log:
        st.write("")
        with card("insights-audit"):
            st.markdown('<div class="panel-label">Recent audit events</div>', unsafe_allow_html=True)
            for entry in audit_log[-6:]:
                if isinstance(entry, dict):
                    st.markdown(f"- **{entry.get('event', 'Event')}** · {entry.get('timestamp', '')}")
                else:
                    st.markdown(f"- {entry}")
