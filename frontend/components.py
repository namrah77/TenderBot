"""Small, reusable rendering building blocks shared by every page."""
from contextlib import contextmanager
import html
import json

import streamlit as st
import streamlit.components.v1 as components

from .constants import STAGE_LABELS, STAGE_ORDER
from .data_utils import TONE_COLORS

_ICON_PATHS = {
    "target": '<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5"/><circle cx="12" cy="12" r="1.4"/>',
    "check": '<path d="M20 6 9 17l-5-5"/>',
    "search": '<circle cx="11" cy="11" r="7"/><path d="m21 21-4.3-4.3"/>',
    "trend": '<path d="M3 17l6-6 4 4 7-7"/><path d="M17 8h4v4"/>',
    "globe": '<circle cx="12" cy="12" r="9"/><path d="M3 12h18"/><path d="M12 3a15 15 0 0 1 0 18a15 15 0 0 1 0-18"/>',
    "clipboard": '<rect x="6" y="4" width="12" height="17" rx="2"/><path d="M9 4V3h6v1"/><path d="M9 10h6M9 14h6"/>',
    "shield": '<path d="M12 3l7 3v5c0 4.5-3 7.5-7 9c-4-1.5-7-4.5-7-9V6z"/>',
    "home": '<path d="M4 10.5 12 4l8 6.5V20a1 1 0 0 1-1 1h-5v-6H10v6H5a1 1 0 0 1-1-1z"/>',
    "building": '<rect x="5" y="3" width="14" height="18" rx="2"/><path d="M9 7h2M13 7h2M9 11h2M13 11h2M9 15h2M13 15h2"/>',
    "compass": '<circle cx="12" cy="12" r="9"/><path d="m16 8-4 8-2-4-4-2z"/>',
    "file": '<path d="M8 4h8l4 4v12a1 1 0 0 1-1 1H8a1 1 0 0 1-1-1V5a1 1 0 0 1 1-1z"/><path d="M16 4v4h4"/>',
    "chart": '<path d="M4 20V4"/><path d="M8 20v-8M12 20V8M16 20v-12M20 20v-5"/>',
    "settings": '<circle cx="12" cy="12" r="3"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/>',
    "star": '<path d="M12 3l2.4 5.7L21 9.5l-4.5 3.9L18 19l-6-3.5L6 19l1.5-5.6L3 9.5l6.6-.8z"/>',
    "sparkles": '<path d="M12 3l1.2 3.6L17 8l-3.6 1.2L12 13l-1.2-3.6L7 8l3.8-1.4z"/>',
    "activity": '<path d="M22 12h-4l-3 9L9 3l-3 9H2"/>',
    "users": '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75"/>',
    "layers": '<path d="M12 2 2 7l10 5 10-5-10-5z"/><path d="m2 17 10 5 10-5M2 12l10 5 10-5"/>',
    "clock": '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
    "zap": '<path d="M13 2 3 14h9l-1 8 10-12h-9z"/>',
}


def icon(name: str, size: int = 20) -> str:
    body = _ICON_PATHS.get(name, "")
    return (
        f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" '
        f'stroke="currentColor" stroke-width="1.9" stroke-linecap="round" '
        f'stroke-linejoin="round">{body}</svg>'
    )


@contextmanager
def card(key: str, extra_class: str = ""):
    full_key = f"card-{extra_class}-{key}" if extra_class else f"card-{key}"
    with st.container(key=full_key, border=False):
        yield


def badge(text: str, tone: str = "muted") -> str:
    color = TONE_COLORS.get(tone, TONE_COLORS["muted"])
    soft = f"{color}22" if tone != "muted" else "var(--tb-line)"
    return f'<span class="badge" style="background:{soft};color:{color};">{html.escape(text)}</span>'


def pulse_dot(tone: str) -> str:
    return f'<span class="pulse-dot tone-{tone}"></span>'


def status_dot(tone: str) -> str:
    return f'<span class="dot tone-{tone}"></span>'


def recommended_badge() -> str:
    return f'<span class="badge-recommended">{icon("star", 12)} Top match</span>'


def readiness_bar(score, tone: str) -> str:
    try:
        pct = max(0, min(100, float(score)))
    except (TypeError, ValueError):
        pct = 0
    color = TONE_COLORS.get(tone, TONE_COLORS["muted"])
    return (
        '<div class="readiness-track">'
        f'<div class="readiness-fill" style="width:{pct}%;background:{color};"></div>'
        "</div>"
    )


def chip_row(items) -> str:
    if not items:
        return '<span class="muted-note">Not stated</span>'
    return "".join(f'<span class="chip">{html.escape(str(i))}</span>' for i in items)


def workspace_header() -> None:
    st.markdown(
        '<div class="ws-header">'
        '<h1 class="ws-title">TenderBot</h1>'
        '<p class="ws-subtitle">AI Tender Intelligence for UK Care Providers</p>'
        '<p class="ws-desc">Profile your organisation, discover open tenders, evaluate eligibility, '
        "and generate a feasibility report — all in one agent workspace.</p>"
        "</div>",
        unsafe_allow_html=True,
    )


def status_card(icon_name: str, title: str, value: str, helper: str) -> str:
    return (
        '<div class="status-card">'
        f'<div class="status-card-ic">{icon(icon_name, 17)}</div>'
        f'<div class="status-card-title">{html.escape(title)}</div>'
        f'<div class="status-card-value">{html.escape(value)}</div>'
        f'<div class="status-card-help">{html.escape(helper)}</div>'
        "</div>"
    )


def status_cards_row(cards: list[tuple]) -> None:
    html_cards = "".join(status_card(*c) for c in cards)
    st.markdown(f'<div class="status-row">{html_cards}</div>', unsafe_allow_html=True)


def render_timeline_html(completed: set, active: str | None, timestamps: dict) -> str:
    rows = []
    for i, stage in enumerate(STAGE_ORDER):
        label = STAGE_LABELS[stage]
        ts = timestamps.get(stage, "")
        is_last = i == len(STAGE_ORDER) - 1
        if stage in completed:
            dot_class, mark, title_class = "done", icon("check", 12), "timeline-title"
        elif stage == active:
            dot_class, mark, title_class = "active", "●", "timeline-title"
        else:
            dot_class, mark, title_class = "pending", str(i + 1), "timeline-title pending-text"

        line_html = "" if is_last else '<div class="timeline-line"></div>'
        rows.append(
            '<div class="timeline-item">'
            '<div class="timeline-rail">'
            f'<div class="timeline-dot {dot_class}">{mark}</div>'
            f"{line_html}"
            "</div>"
            '<div class="timeline-body">'
            f'<div class="{title_class}">{label}</div>'
            f'<div class="timeline-time">{ts}</div>'
            "</div>"
            "</div>"
        )
    return "".join(rows)


def pipeline_progress_pct(completed: set, active: str | None) -> int:
    done = len(completed)
    if active:
        done += 0.5
    return min(100, int(done / len(STAGE_ORDER) * 100))


def copy_to_clipboard_button(text: str, label: str = "Copy Report", key: str = "copy") -> None:
    escaped = json_escape(text)
    components.html(
        f"""
        <button id="{key}" style="
            background: var(--tb-surface, #fff); color: var(--tb-ink-2, #374151);
            border: 1px solid var(--tb-line-strong, #D1D5DB); border-radius: 9px;
            padding: .45rem 1rem; font-weight: 600; font-size: .86rem; cursor: pointer;
            font-family: Inter, sans-serif; width: 100%;
        ">{html.escape(label)}</button>
        <script>
        document.getElementById("{key}").onclick = function() {{
            navigator.clipboard.writeText({escaped});
            this.textContent = "Copied!";
            setTimeout(() => this.textContent = {json_escape(label)}, 2000);
        }};
        </script>
        """,
        height=42,
    )


def json_escape(text: str) -> str:
    return json.dumps(text)


def kpi_card(key: str, icon_name: str, label: str, value: str, sub: str = "", sub_tone: str = "muted"):
    sub_html = ""
    if sub:
        color = TONE_COLORS.get(sub_tone, TONE_COLORS["muted"])
        sub_html = f'<div class="kpi-sub" style="color:{color};font-size:.78rem;margin-top:.4rem;">{html.escape(sub)}</div>'
    with card(key, "kpi"):
        st.markdown(
            f'<div class="kpi-icon">{icon(icon_name)}</div>'
            f'<div class="kpi-value">{html.escape(value)}</div>'
            f'<div class="kpi-label">{html.escape(label)}</div>'
            f"{sub_html}",
            unsafe_allow_html=True,
        )


def section_header(eyebrow: str, heading: str):
    st.markdown(
        f'<div class="section-eyebrow">{html.escape(eyebrow)}</div>'
        f'<div class="section-heading">{html.escape(heading)}</div>',
        unsafe_allow_html=True,
    )


def card_title(icon_name: str, title: str, subtitle: str = ""):
    sub_html = f'<div class="card-sub">{html.escape(subtitle)}</div>' if subtitle else ""
    st.markdown(
        f'<div class="card-title"><span class="card-title-ic">{icon(icon_name)}</span>{html.escape(title)}</div>'
        f"{sub_html}",
        unsafe_allow_html=True,
    )


def empty_state(title: str, body: str) -> None:
    st.markdown(
        f'<div class="empty-state">'
        f'<div class="empty-state-title">{html.escape(title)}</div>'
        f'<div>{html.escape(body)}</div></div>',
        unsafe_allow_html=True,
    )
