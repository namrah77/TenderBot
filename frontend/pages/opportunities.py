"""Tender Opportunities — professional tender cards with eligibility details."""
import html

import streamlit as st

from ..components import badge, card, empty_state, readiness_bar, recommended_badge, section_header
from ..data_utils import (
    derive_confidence,
    derive_strengths,
    find_tender_meta,
    is_recommended,
    readiness_tone,
    verdict_label,
    verdict_tone,
)

FILTERS = ["All", "Eligible", "Partial", "Not Eligible"]


def _render_tender_card(e: dict, tenders: list, idx: int) -> None:
    tender_meta = find_tender_meta(tenders, e)
    verdict = e.get("verdict", "Unknown")
    score = e.get("bid_readiness_score", 0)
    strengths = derive_strengths(e)
    gaps = e.get("gaps") or []
    reason = e.get("recommendation", "No summary available.")

    with card(f"opp-{idx}", "opp"):
        if is_recommended(e):
            st.markdown(recommended_badge(), unsafe_allow_html=True)

        st.markdown(
            f'<div class="tender-card-head">'
            f'<div class="tender-card-title">{html.escape(e.get("title", "Untitled tender"))}</div>'
            f'<div class="tender-card-authority">{html.escape(tender_meta.get("contracting_authority", "Authority not stated"))}</div>'
            "</div>",
            unsafe_allow_html=True,
        )

        st.markdown(
            '<div class="tender-grid">'
            f'<div><div class="tender-field-label">Deadline</div>'
            f'<div class="tender-field-value">{html.escape(str(tender_meta.get("submission_deadline", "not stated")))}</div></div>'
            f'<div><div class="tender-field-label">Eligibility</div>'
            f'<div class="tender-field-value">{badge(verdict_label(verdict), verdict_tone(verdict))}</div></div>'
            f'<div><div class="tender-field-label">Confidence</div>'
            f'<div class="tender-field-value">{derive_confidence(e)}</div></div>'
            f'<div><div class="tender-field-label">Readiness</div>'
            f'<div class="tender-field-value">{score}%</div>{readiness_bar(score, readiness_tone(score))}</div>'
            "</div>",
            unsafe_allow_html=True,
        )

        st.markdown(
            f'<div class="tender-section"><div class="tender-section-title">Recommendation</div>'
            f'<div class="tender-section-body">{html.escape(reason)}</div></div>',
            unsafe_allow_html=True,
        )

        if strengths:
            items = "".join(f'<span class="chip">{html.escape(s)}</span>' for s in strengths)
            st.markdown(
                f'<div class="tender-section"><div class="tender-section-title">Strengths</div>'
                f'<div>{items}</div></div>',
                unsafe_allow_html=True,
            )

        if gaps:
            gap_html = "".join(f'<div class="tender-gap">{html.escape(g)}</div>' for g in gaps[:5])
            st.markdown(
                f'<div class="tender-section"><div class="tender-section-title">Key Gaps</div>{gap_html}</div>',
                unsafe_allow_html=True,
            )

        portal_url = tender_meta.get("portal_url")
        if portal_url and portal_url != "not stated":
            st.link_button("Open tender on portal", portal_url, width="stretch")


def render_opportunities(data, checklist: dict, embedded: bool = False) -> None:
    if not embedded:
        section_header("Tender Opportunities", "Every open tender, evaluated")

    eligibility = (data or {}).get("eligibility_results") or []
    tenders = (data or {}).get("tenders_found") or []

    if not data:
        empty_state("No opportunities", "Run an analysis to discover and evaluate tenders.")
        return
    if not eligibility:
        st.warning("No eligibility results — the last run may have found zero open tenders.")
        return

    chosen = st.pills("Filter", FILTERS, default="All", key="opp-filter", label_visibility="collapsed")
    ranked = sorted(eligibility, key=lambda e: e.get("bid_readiness_score", 0) or 0, reverse=True)
    if chosen and chosen != "All":
        ranked = [e for e in ranked if e.get("verdict") == chosen]

    st.caption(f"Showing {len(ranked)} of {len(eligibility)} evaluated opportunities")

    for idx, e in enumerate(ranked):
        _render_tender_card(e, tenders, idx)
