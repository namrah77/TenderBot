"""All custom CSS — theme-aware, minimal, no gradients."""
import streamlit as st

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:ital,opsz,wght@0,14..32,400;0,14..32,500;0,14..32,600;0,14..32,700&display=swap');

:root {
  --tb-ink: #111827;
  --tb-ink-2: #374151;
  --tb-muted: #6B7280;
  --tb-line: #E5E7EB;
  --tb-line-strong: #D1D5DB;
  --tb-accent: #5B5BD6;
  --tb-accent-soft: #E8E8F8;
  --tb-surface: #FFFFFF;
  --tb-canvas: #F7F8FA;
  --tb-sidebar: #18181B;
  --tb-sidebar-text: #E4E4E7;
  --tb-shadow: 0 1px 2px rgba(15, 23, 42, 0.05);
  --tb-shadow-md: 0 4px 12px rgba(15, 23, 42, 0.06);
  --tb-success: #15803D;
  --tb-success-soft: #E8F5EC;
  --tb-warning: #B45309;
  --tb-warning-soft: #FEF3E2;
  --tb-risk: #B91C1C;
  --tb-risk-soft: #FCE8E8;
}

[data-theme="dark"] {
  --tb-ink: #F4F4F5;
  --tb-ink-2: #D4D4D8;
  --tb-muted: #A1A1AA;
  --tb-line: #3F3F46;
  --tb-line-strong: #52525B;
  --tb-accent: #818CF8;
  --tb-accent-soft: #27273A;
  --tb-surface: #1C1C22;
  --tb-canvas: #111114;
  --tb-sidebar: #0F0F12;
  --tb-sidebar-text: #E4E4E7;
  --tb-shadow: 0 1px 2px rgba(0, 0, 0, 0.35);
  --tb-shadow-md: 0 4px 12px rgba(0, 0, 0, 0.4);
  --tb-success: #4ADE80;
  --tb-success-soft: #14291C;
  --tb-warning: #FBBF24;
  --tb-warning-soft: #2A2210;
  --tb-risk: #F87171;
  --tb-risk-soft: #2A1414;
}

html, body, [class^="css"], [class*=" css"] {
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  -webkit-font-smoothing: antialiased;
}

.stApp { background: var(--tb-canvas); color: var(--tb-ink); }
#MainMenu, footer, [data-testid="stToolbar"] { visibility: hidden; height: 0; }
header[data-testid="stHeader"] { background: transparent; }

.block-container {
  padding: 0.75rem 1.15rem 1.75rem;
  max-width: 100%;
}

div[data-testid="stVerticalBlock"] { gap: 0.35rem; }
hr { margin: 0.5rem 0; border-color: var(--tb-line); }

/* ---- Workspace header ---- */
.ws-header { margin-bottom: 0.85rem; }
.ws-title {
  font-size: 1.4rem; font-weight: 700; letter-spacing: -0.03em;
  color: var(--tb-ink); margin: 0; line-height: 1.2;
}
.ws-subtitle {
  font-size: .88rem; font-weight: 500; color: var(--tb-ink-2);
  margin: .15rem 0 0;
}
.ws-desc {
  font-size: .8rem; color: var(--tb-muted); margin: .3rem 0 0;
  max-width: 48rem; line-height: 1.45;
}

/* ---- Status cards row ---- */
.status-row { display: flex; flex-wrap: wrap; gap: .55rem; margin: .75rem 0 1rem; }
.status-card {
  flex: 1 1 130px; min-width: 120px;
  background: var(--tb-surface);
  border: 1px solid var(--tb-line);
  border-radius: 10px;
  padding: .7rem .85rem;
  box-shadow: var(--tb-shadow);
}
.status-card-ic {
  width: 28px; height: 28px; border-radius: 7px;
  display: flex; align-items: center; justify-content: center;
  background: var(--tb-accent-soft); color: var(--tb-accent);
  margin-bottom: .4rem;
}
.status-card-ic svg { width: 15px; height: 15px; }
.status-card-title {
  font-size: .66rem; font-weight: 600; text-transform: uppercase;
  letter-spacing: .05em; color: var(--tb-muted);
}
.status-card-value {
  font-size: 1rem; font-weight: 700; color: var(--tb-ink);
  margin: .1rem 0 .05rem; letter-spacing: -0.02em;
}
.status-card-help { font-size: .68rem; color: var(--tb-muted); line-height: 1.3; }

/* ---- Generic cards ---- */
div[class*="st-key-card-"] {
  background: var(--tb-surface);
  border-radius: 12px;
  padding: 1rem 1.15rem;
  border: 1px solid var(--tb-line);
  box-shadow: var(--tb-shadow);
  margin-bottom: .65rem;
}
.card-title {
  display: flex; align-items: center; gap: .45rem;
  font-size: .9rem; font-weight: 600; color: var(--tb-ink);
  margin-bottom: .1rem;
}
.card-title .card-title-ic {
  width: 26px; height: 26px; border-radius: 7px; flex-shrink: 0;
  display: flex; align-items: center; justify-content: center;
  background: var(--tb-accent-soft); color: var(--tb-accent);
}
.card-title .card-title-ic svg { width: 14px; height: 14px; }
.card-sub { font-size: .76rem; color: var(--tb-muted); margin: 0 0 .65rem; }
.panel-label {
  font-size: .68rem; font-weight: 600; text-transform: uppercase;
  letter-spacing: .06em; color: var(--tb-muted); margin-bottom: .5rem;
}

/* ---- Input workspace ---- */
.run-meta {
  display: flex; flex-wrap: wrap; gap: 1rem; margin-top: .75rem;
  font-size: .8rem; color: var(--tb-muted);
}
.run-meta strong { color: var(--tb-ink-2); font-weight: 600; }
.progress-track {
  background: var(--tb-line); border-radius: 6px; height: 6px;
  width: 100%; overflow: hidden; margin: .65rem 0 .35rem;
}
.progress-fill {
  height: 100%; border-radius: 6px; background: var(--tb-accent);
  transition: width .35s ease;
}

/* ---- Forms ---- */
[data-testid="stWidgetLabel"] p,
div[data-testid="stMainBlockContainer"] .stTextInput label p {
  font-size: .78rem; font-weight: 600; color: var(--tb-ink-2);
}
div[data-testid="stMainBlockContainer"] div[data-baseweb="input"],
div[data-testid="stMainBlockContainer"] div[data-baseweb="textarea"],
div[data-testid="stMainBlockContainer"] div[data-baseweb="select"] > div {
  background: var(--tb-surface);
  border: 1px solid var(--tb-line-strong);
  border-radius: 10px;
  min-height: 42px;
}
div[data-testid="stMainBlockContainer"] div[data-baseweb="input"]:focus-within,
div[data-testid="stMainBlockContainer"] div[data-baseweb="textarea"]:focus-within {
  border-color: var(--tb-accent);
  box-shadow: 0 0 0 3px color-mix(in srgb, var(--tb-accent) 18%, transparent);
}
div[data-testid="stMainBlockContainer"] .stTextInput input,
div[data-testid="stMainBlockContainer"] .stTextArea textarea {
  color: var(--tb-ink); font-size: .88rem;
}

/* ---- Sidebar hidden — navigation lives in top pills ---- */
section[data-testid="stSidebar"] { display: none !important; }
[data-testid="stSidebarCollapsedControl"] { display: none !important; }
[data-testid="stExpandSidebarButton"] { display: none !important; }
[data-testid="stSidebarCollapseButton"] { display: none !important; }

section[data-testid="stMain"] > div {
  max-width: 100% !important;
}
[data-testid="stAppViewContainer"] .main .block-container {
  padding-left: 1.15rem !important;
  padding-right: 1.15rem !important;
}

/* ---- Timeline ---- */
.timeline-item { display: flex; gap: .75rem; }
.timeline-rail { display: flex; flex-direction: column; align-items: center; }
.timeline-dot {
  width: 24px; height: 24px; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-size: .65rem; flex-shrink: 0; font-weight: 700;
}
.timeline-dot.done { background: var(--tb-success); color: #fff; }
.timeline-dot.active { background: var(--tb-accent); color: #fff; }
.timeline-dot.pending { background: var(--tb-line); color: var(--tb-muted); }
.timeline-line { width: 2px; flex: 1; background: var(--tb-line); margin: 3px 0; min-height: 12px; }
.timeline-body { padding-bottom: .75rem; }
.timeline-title { font-weight: 600; color: var(--tb-ink); font-size: .8rem; }
.timeline-title.pending-text { color: var(--tb-muted); font-weight: 500; }
.timeline-time { font-size: .72rem; color: var(--tb-muted); margin-top: 1px; }

/* ---- KPI / badges / chips ---- */
.kpi-icon {
  width: 38px; height: 38px; border-radius: 10px;
  display: flex; align-items: center; justify-content: center;
  background: var(--tb-accent-soft); color: var(--tb-accent); margin-bottom: .7rem;
}
.kpi-value { font-size: 1.75rem; font-weight: 700; color: var(--tb-ink); letter-spacing: -0.02em; }
.kpi-label { font-size: .74rem; color: var(--tb-muted); text-transform: uppercase; letter-spacing: .04em; font-weight: 600; }
.badge {
  display: inline-block; padding: 3px 10px; border-radius: 6px;
  font-size: .7rem; font-weight: 600; letter-spacing: .01em;
}
.badge-recommended {
  display: inline-flex; align-items: center; gap: 4px;
  background: var(--tb-accent-soft); color: var(--tb-accent);
  padding: 3px 10px; border-radius: 6px; font-size: .68rem; font-weight: 600;
  margin-bottom: .45rem; border: 1px solid color-mix(in srgb, var(--tb-accent) 25%, transparent);
}
.chip {
  display: inline-block; background: var(--tb-accent-soft); color: var(--tb-ink-2);
  border-radius: 6px; padding: 3px 9px; font-size: .74rem; font-weight: 500;
  margin: 2px 4px 2px 0; border: 1px solid var(--tb-line);
}
.dot { display: inline-block; width: 7px; height: 7px; border-radius: 50%; margin-right: 6px; }
.dot.tone-success { background: var(--tb-success); }
.dot.tone-warning { background: var(--tb-warning); }
.dot.tone-risk { background: var(--tb-risk); }
.dot.tone-muted { background: var(--tb-muted); }
.pulse-dot { width: 8px; height: 8px; border-radius: 50%; display: inline-block; margin-right: 6px; }
.pulse-dot.tone-success { background: var(--tb-success); }
.pulse-dot.tone-warning { background: var(--tb-warning); }
.pulse-dot.tone-muted { background: var(--tb-muted); }

.readiness-track { background: var(--tb-line); border-radius: 6px; height: 6px; width: 100%; overflow: hidden; margin-top: 6px; }
.readiness-fill { height: 100%; border-radius: 6px; }

/* ---- Tender cards ---- */
.tender-card-head { margin-bottom: .65rem; }
.tender-card-title { font-size: .95rem; font-weight: 600; color: var(--tb-ink); line-height: 1.35; }
.tender-card-authority { font-size: .8rem; color: var(--tb-muted); margin-top: .15rem; }
.tender-grid {
  display: grid; grid-template-columns: repeat(auto-fit, minmax(130px, 1fr));
  gap: .65rem; margin: .75rem 0;
}
.tender-field-label {
  font-size: .68rem; text-transform: uppercase; letter-spacing: .04em;
  color: var(--tb-muted); font-weight: 600;
}
.tender-field-value { font-size: .84rem; color: var(--tb-ink); font-weight: 500; margin-top: .1rem; }
.tender-section { margin-top: .65rem; }
.tender-section-title { font-size: .72rem; font-weight: 600; text-transform: uppercase; letter-spacing: .04em; color: var(--tb-muted); margin-bottom: .25rem; }
.tender-section-body { font-size: .84rem; color: var(--tb-ink-2); line-height: 1.5; }
.tender-gap { font-size: .82rem; color: var(--tb-ink-2); margin: .15rem 0; padding-left: .65rem; border-left: 2px solid var(--tb-line); }

/* ---- Profile fields ---- */
.profile-field-label {
  font-size: .68rem; text-transform: uppercase; letter-spacing: .04em;
  color: var(--tb-muted); font-weight: 600; margin-top: .55rem;
}
.profile-field-value { font-size: .88rem; color: var(--tb-ink); font-weight: 500; }
.profile-info-card { margin-bottom: .75rem; }
.profile-info-card-title {
  font-size: .78rem; font-weight: 600; text-transform: uppercase;
  letter-spacing: .05em; color: var(--tb-muted); margin-bottom: .5rem;
}

/* ---- Report markdown ---- */
.report-md {
  background: var(--tb-surface); border: 1px solid var(--tb-line);
  border-radius: 12px; padding: 1.5rem 1.75rem;
  font-size: .9rem; line-height: 1.65; color: var(--tb-ink-2);
}
.report-md h1, .report-md h2, .report-md h3 { color: var(--tb-ink); margin-top: 1.25rem; }
.report-md h1 { font-size: 1.35rem; margin-top: 0; }
.report-md h2 { font-size: 1.1rem; }
.report-md h3 { font-size: .98rem; }
.report-md table { width: 100%; border-collapse: collapse; margin: .75rem 0; font-size: .85rem; }
.report-md th, .report-md td { border: 1px solid var(--tb-line); padding: .45rem .65rem; text-align: left; }
.report-md th { background: var(--tb-canvas); font-weight: 600; }
.report-md code {
  background: var(--tb-canvas); padding: .1rem .35rem; border-radius: 4px;
  font-size: .82rem; border: 1px solid var(--tb-line);
}
.report-md pre {
  background: var(--tb-canvas); padding: .85rem; border-radius: 8px;
  overflow-x: auto; border: 1px solid var(--tb-line);
}
.report-md ul, .report-md ol { padding-left: 1.25rem; }

/* ---- Insights ---- */
.insight-stat {
  text-align: center; padding: .85rem;
  background: var(--tb-canvas); border-radius: 10px; border: 1px solid var(--tb-line);
}
.insight-stat-value { font-size: 1.4rem; font-weight: 700; color: var(--tb-ink); }
.insight-stat-label { font-size: .72rem; color: var(--tb-muted); margin-top: .2rem; }

/* ---- Misc ---- */
.section-eyebrow { font-size: .7rem; font-weight: 600; text-transform: uppercase; letter-spacing: .07em; color: var(--tb-accent); margin-bottom: .2rem; }
.section-heading { font-size: 1.02rem; font-weight: 700; color: var(--tb-ink); margin-bottom: .55rem; letter-spacing: -0.02em; }
.muted-note { color: var(--tb-muted); font-size: .84rem; line-height: 1.5; }
.empty-state {
  text-align: center; padding: 2.5rem 1.5rem;
  background: var(--tb-surface); border: 1px dashed var(--tb-line-strong);
  border-radius: 14px; color: var(--tb-muted);
}
.empty-state-title { font-size: .95rem; font-weight: 600; color: var(--tb-ink-2); margin-bottom: .35rem; }

.stButton>button, .stDownloadButton>button {
  border-radius: 9px; font-weight: 600; font-size: .86rem;
}
div[data-testid="stMainBlockContainer"] .stButton>button[kind="primary"],
.stDownloadButton>button[kind="primary"] {
  background: var(--tb-accent); border: none; color: #fff;
}
div[data-testid="stMainBlockContainer"] .stButton>button[kind="secondary"],
.stDownloadButton>button {
  background: var(--tb-surface); border: 1px solid var(--tb-line-strong); color: var(--tb-ink-2);
}
div[data-testid="stTabs"] button { font-weight: 600; font-size: .84rem; }

/* ---- Top navigation ---- */
div[class*="st-key-top-nav"] {
  margin-bottom: .65rem;
  padding-bottom: .5rem;
  border-bottom: 1px solid var(--tb-line);
}
div[class*="st-key-top-nav"] [data-baseweb="radio"] label {
  font-size: .8rem !important;
  font-weight: 600 !important;
}
div[class*="st-key-top-nav"] [data-testid="stRadio"] {
  margin-bottom: 0 !important;
}

[data-testid="stElementToolbar"] { display: none; }
</style>
"""


def inject_css() -> None:
    st.markdown(CSS, unsafe_allow_html=True)
