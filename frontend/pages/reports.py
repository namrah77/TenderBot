"""Reports — per-tender report cards for the current run, plus the
archive of previously saved reports (written to disk by the MCP
save_report tool)."""
import streamlit as st

from ..components import badge, card, section_header
from ..data_utils import REPORTS_DIR, readiness_tone, verdict_tone


def _tender_markdown(e: dict, reliability: dict) -> str:
    lines = [
        f"# {e.get('title', 'Tender')}",
        "",
        f"- **Recommendation:** {e.get('recommendation', 'not stated')}",
        f"- **Eligibility:** {e.get('verdict', 'Unknown')}",
        f"- **Bid readiness:** {e.get('bid_readiness_score', 0)}%",
        f"- **Reliability:** {reliability.get('reliability_score', '—')}%",
        "",
        "## Gaps",
    ]
    gaps = e.get("gaps") or []
    lines += [f"- {g}" for g in gaps] if gaps else ["- None flagged"]
    return "\n".join(lines)


def _render_current_reports(data) -> None:
    eligibility = (data or {}).get("eligibility_results") or []
    reliability = (data or {}).get("reliability_report", {}) or {}
    if not eligibility:
        st.info("No evaluated tenders yet — run an analysis from Agent Home.")
        return

    for idx, e in enumerate(eligibility):
        with card(f"report-{idx}", "report"):
            cols = st.columns([2.4, 1, 1, 1, 1])
            with cols[0]:
                st.markdown(f"**{e.get('title', 'Tender')}**")
                st.markdown(f'<div class="muted-note">{e.get("recommendation", "")}</div>', unsafe_allow_html=True)
            with cols[1]:
                st.markdown('<div class="profile-field-label">Eligibility</div>', unsafe_allow_html=True)
                st.markdown(badge(e.get("verdict", "Unknown"), verdict_tone(e.get("verdict"))), unsafe_allow_html=True)
            with cols[2]:
                st.markdown('<div class="profile-field-label">Readiness</div>', unsafe_allow_html=True)
                score = e.get("bid_readiness_score", 0)
                st.markdown(f'<div class="profile-field-value">{score}%</div>', unsafe_allow_html=True)
            with cols[3]:
                st.markdown('<div class="profile-field-label">Reliability</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="profile-field-value">{reliability.get("reliability_score", "—")}%</div>', unsafe_allow_html=True)
            with cols[4]:
                st.download_button(
                    ":material/download: Download",
                    data=_tender_markdown(e, reliability),
                    file_name=f"{e.get('title', 'tender').replace(' ', '_')[:40]}.md",
                    mime="text/markdown",
                    key=f"dl-report-{idx}",
                    width="stretch",
                )


def _render_archive() -> None:
    files = sorted(REPORTS_DIR.glob("*.md"), reverse=True) if REPORTS_DIR.exists() else []
    if not files:
        st.markdown('<span class="muted-note">No archived reports yet — saved reports will appear here after a run.</span>', unsafe_allow_html=True)
        return

    for f in files:
        state_key = f"report-preview-{f.name}"
        if state_key not in st.session_state:
            st.session_state[state_key] = False
        with card(f"archive-{f.name}", "report"):
            cols = st.columns([3, 1, 1])
            with cols[0]:
                st.markdown(f"**{f.stem.replace('_', ' ')}**")
            with cols[1]:
                if st.button("Preview", key=f"preview-{f.name}", width="stretch"):
                    st.session_state[state_key] = not st.session_state[state_key]
                    st.rerun()
            with cols[2]:
                st.download_button(
                    ":material/download: Download", data=f.read_text(encoding="utf-8"), file_name=f.name,
                    mime="text/markdown", key=f"dl-archive-{f.name}", width="stretch",
                )
            if st.session_state[state_key]:
                st.markdown("<hr/>", unsafe_allow_html=True)
                st.markdown(f.read_text(encoding="utf-8"))


def render_reports(data) -> None:
    section_header("Reports", "This run & your report archive")
    st.markdown("**Current run**")
    _render_current_reports(data)

    st.write("")
    st.markdown("**Report archive**")
    _render_archive()
