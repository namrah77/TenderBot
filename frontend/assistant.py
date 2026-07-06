"""Persistent right-hand AI assistant panel.

This is intentionally NOT a live chatbot — every "answer" below is a
canned template filled in with real values already produced by the
agent pipeline (eligibility_results, reliability_report, etc.). It just
gives the user a fast, conversational way to re-surface data that is
already on screen elsewhere.
"""
import streamlit as st

from .components import card, icon
from .data_utils import derive_confidence

PROMPTS = [
    ("top_reco", "Why is the top tender recommended?"),
    ("checklist", "Prepare a bid checklist"),
    ("compare", "Compare the top 2 tenders"),
    ("missing_docs", "Show missing documents"),
]


def _ranked(eligibility):
    return sorted(eligibility, key=lambda e: e.get("bid_readiness_score", 0) or 0, reverse=True)


def _answer(topic: str, data: dict) -> str:
    eligibility = data.get("eligibility_results") or []
    tenders = data.get("tenders_found") or []
    ranked = _ranked(eligibility)

    if not ranked:
        return "I don't have any evaluated opportunities yet — run an analysis first."

    if topic == "top_reco":
        top = ranked[0]
        title = top.get("title", "This tender")
        reasons = top.get("recommendation", "It scored well against our eligibility criteria.")
        return (
            f"<b>{title}</b> is our top match with a bid readiness of "
            f"{top.get('bid_readiness_score', 0)}% and a verdict of "
            f"<b>{top.get('verdict', 'Unknown')}</b>. {reasons}"
        )

    if topic == "checklist":
        items = []
        for e in ranked:
            for g in (e.get("gaps") or [])[:2]:
                items.append(f"{e.get('title', 'Tender')}: {g}")
        if not items:
            return "No outstanding gaps were found — every evaluated tender looks bid-ready."
        bullet_list = "".join(f"<li>{i}</li>" for i in items[:6])
        return f"Here's a consolidated checklist across all tenders:<ul>{bullet_list}</ul>"

    if topic == "compare":
        if len(ranked) < 2:
            return "I only have one evaluated tender so far — run a scan to find more to compare."
        a, b = ranked[0], ranked[1]
        return (
            f"<b>{a.get('title')}</b>: {a.get('verdict')} · {a.get('bid_readiness_score', 0)}% readiness · "
            f"confidence {derive_confidence(a)}<br/>"
            f"<b>{b.get('title')}</b>: {b.get('verdict')} · {b.get('bid_readiness_score', 0)}% readiness · "
            f"confidence {derive_confidence(b)}"
        )

    if topic == "missing_docs":
        all_gaps = []
        for e in ranked:
            for g in (e.get("gaps") or []):
                all_gaps.append(f"{e.get('title', 'Tender')} — {g}")
        if not all_gaps:
            return "No missing documents were flagged across the current tenders."
        bullet_list = "".join(f"<li>{i}</li>" for i in all_gaps[:8])
        return f"Missing or unverifiable items found:<ul>{bullet_list}</ul>"

    return "I'm not sure how to help with that yet."


def render_assistant_panel(data) -> None:
    with card("assistant"):
        st.markdown(
            '<div class="assistant-header">'
            f'<div class="assistant-avatar">{icon("sparkles", 17)}</div>'
            'AI Assistant</div>',
            unsafe_allow_html=True,
        )

        if not data:
            st.markdown(
                '<div class="assistant-bubble">Hello. I\'m ready to analyse procurement '
                "opportunities for you. Add your company details in Settings and run your "
                "first scan from Agent Home.</div>",
                unsafe_allow_html=True,
            )
            return

        if data.get("error"):
            st.markdown(
                f'<div class="assistant-bubble">The last run hit an error: '
                f'<b>{data["error"]}</b>. Check Settings and try again.</div>',
                unsafe_allow_html=True,
            )
            return

        eligibility = data.get("eligibility_results") or []
        tenders = data.get("tenders_found") or []
        recommended_n = sum(1 for e in eligibility if e.get("verdict") == "Eligible")
        scores = [e.get("bid_readiness_score", 0) for e in eligibility if isinstance(e.get("bid_readiness_score"), (int, float))]
        avg_score = round(sum(scores) / len(scores)) if scores else 0

        st.markdown(
            "<div class='assistant-bubble'>Hello. I analysed today's opportunities.<br/>"
            f"Found <b>{len(tenders)}</b> opportunities. <b>{recommended_n}</b> are recommended.<br/>"
            f"Average readiness <b>{avg_score}%</b>.<br/>How can I help?</div>",
            unsafe_allow_html=True,
        )

        st.markdown('<div class="section-eyebrow" style="margin-top:.4rem;">Suggested</div>', unsafe_allow_html=True)
        for topic_id, prompt in PROMPTS:
            if st.button(prompt, key=f"assistant-prompt-{topic_id}", width="stretch"):
                st.session_state.assistant_topic = topic_id

        topic = st.session_state.get("assistant_topic")
        if topic:
            st.markdown(
                f'<div class="assistant-bubble">{_answer(topic, data)}</div>',
                unsafe_allow_html=True,
            )

        audit_log = data.get("audit_log") or []
        if audit_log:
            st.markdown('<div class="section-eyebrow" style="margin-top:.6rem;">Recent actions</div>', unsafe_allow_html=True)
            for entry in audit_log[-4:]:
                event = entry.get("event", "Event") if isinstance(entry, dict) else str(entry)
                st.markdown(f'<div class="assistant-log-item">• {event}</div>', unsafe_allow_html=True)
