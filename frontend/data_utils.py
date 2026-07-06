"""Pure data helpers: parsing agent output, checklist persistence, and
UI-level derivations (badges, confidence, matches). No Streamlit imports
here on purpose — this module only shapes data for the components layer.
"""
import json
import re
from pathlib import Path

from .constants import RISK, SUCCESS, WARNING, MUTED, VERDICT_DISPLAY

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
CHECKLIST_PATH = DATA_DIR / "company_checklist.json"
REPORTS_DIR = DATA_DIR / "reports"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)


def parse_json_field(raw, fallback):
    """Every agent output comes back as a string that MIGHT be wrapped
    in ```json fences. Parse defensively, everywhere."""
    if raw is None:
        return fallback
    if isinstance(raw, (list, dict)):
        return raw
    if isinstance(raw, str):
        match = re.search(r"(\[.*\]|\{.*\})", raw, re.DOTALL)
        text = match.group(0) if match else raw
        try:
            return json.loads(text)
        except Exception:
            return fallback
    return fallback


def load_checklist() -> dict:
    if CHECKLIST_PATH.exists():
        try:
            return json.loads(CHECKLIST_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {
        "display_name": "",
        "cqc_rating": "not stated",
        "office_locations": [],
        "certifications": [],
        "max_capacity_value": None,
        "services": [],
        "languages": [],
        "council_approvals": [],
    }


def save_checklist(data: dict) -> None:
    CHECKLIST_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")


def checklist_is_filled(checklist: dict) -> bool:
    return any([
        checklist.get("office_locations"),
        checklist.get("certifications"),
        checklist.get("max_capacity_value"),
        checklist.get("services"),
        checklist.get("cqc_rating") not in (None, "", "not stated"),
    ])


# ---------------------------------------------------------------------
# Tone mapping — every colour decision funnels through here so cards,
# badges, and progress bars always agree with each other.
# ---------------------------------------------------------------------
TONE_COLORS = {
    "success": SUCCESS,
    "warning": WARNING,
    "risk": RISK,
    "muted": MUTED,
}


def verdict_tone(verdict: str) -> str:
    return {"Eligible": "success", "Partial": "warning", "Not Eligible": "risk"}.get(verdict, "muted")


def verdict_label(verdict: str) -> str:
    return VERDICT_DISPLAY.get(verdict, verdict or "Unknown")


def confidence_tone(level: str) -> str:
    return {"High": "success", "Medium": "warning", "Low": "risk"}.get(level, "muted")


def readiness_tone(score) -> str:
    try:
        score = float(score)
    except (TypeError, ValueError):
        return "muted"
    if score >= 70:
        return "success"
    if score >= 40:
        return "warning"
    return "risk"


def criteria_tone(text) -> str:
    if not isinstance(text, str) or not text.strip():
        return "muted"
    t = text.lower()
    if any(k in t for k in ("unverifiable", "not stated", "partial", "unclear")):
        return "warning"
    if any(k in t for k in ("fail", "no match", "does not", "insufficient", "mismatch", "below")):
        return "risk"
    return "success"


def derive_confidence(eligibility_entry: dict) -> str:
    """Per-tender confidence, derived from how many criteria are
    unverifiable / how many gaps were logged. Purely a presentation
    heuristic over existing eligibility_results — no agent changes."""
    crit = eligibility_entry.get("criteria_results", {}) or {}
    gaps = eligibility_entry.get("gaps", []) or []
    shaky = sum(1 for v in crit.values() if criteria_tone(v) != "success")
    if shaky == 0 and len(gaps) <= 1:
        return "High"
    if shaky <= 2 and len(gaps) <= 3:
        return "Medium"
    return "Low"


def derive_strengths(eligibility_entry: dict) -> list[str]:
    """Surface passing criteria as human-readable strengths."""
    crit = eligibility_entry.get("criteria_results", {}) or {}
    strengths = []
    for key, value in crit.items():
        if criteria_tone(value) == "success" and isinstance(value, str) and value.strip():
            label = key.replace("_", " ").title()
            strengths.append(f"{label}: {value}")
    return strengths[:5]


def is_recommended(eligibility_entry: dict) -> bool:
    score = eligibility_entry.get("bid_readiness_score", 0) or 0
    try:
        score = float(score)
    except (TypeError, ValueError):
        score = 0
    return eligibility_entry.get("verdict") == "Eligible" and score >= 70


def matched_services(tender_meta: dict, checklist: dict) -> list:
    services = checklist.get("services", []) or []
    if not services:
        return []
    lots = tender_meta.get("lots_offered", []) or []
    scope_text = " ".join(str(l.get("service_scope", "")) for l in lots).lower()
    title_text = str(tender_meta.get("title", "")).lower()
    haystack = f"{scope_text} {title_text}"
    matched = [s for s in services if s.lower() in haystack]
    return matched if matched else services[:3]


def find_tender_meta(tenders: list, eligibility_entry: dict) -> dict:
    ref = eligibility_entry.get("reference_number")
    title = eligibility_entry.get("title")
    for t in tenders:
        if ref and t.get("reference_number") == ref:
            return t
        if title and t.get("title") == title:
            return t
    return {}


def build_next_actions(eligibility_entry: dict, tender_meta: dict) -> list:
    actions = []
    rec = eligibility_entry.get("recommendation")
    if rec:
        actions.append(rec)
    for gap in (eligibility_entry.get("gaps") or [])[:5]:
        actions.append(f"Resolve: {gap}")
    deadline = tender_meta.get("submission_deadline")
    if deadline and deadline != "not stated":
        actions.append(f"Diarise submission deadline: {deadline}")
    if not actions:
        actions.append("No outstanding actions — ready to proceed.")
    return actions


def build_requirements(tender_meta: dict) -> list:
    rows = [
        ("CQC registration required", tender_meta.get("cqc_required", "not stated")),
        ("Local office required", tender_meta.get("office_requirement", "not stated")),
        ("Hourly rate (tender)", tender_meta.get("hourly_rate", "not stated")),
        ("Rate ceiling", tender_meta.get("rate_ceiling", "not stated")),
        ("Contract value", tender_meta.get("contract_value", tender_meta.get("estimated_value", "not stated"))),
        ("Required certifications", ", ".join(tender_meta.get("required_certifications") or []) or "not stated"),
        ("Quality / price weighting", tender_meta.get("quality_price_weighting", "not stated")),
        ("Quality question weightage", tender_meta.get("quality_question_weightage", "not stated")),
        ("Geographic fit", tender_meta.get("geographic_distance_fit", "not stated")),
        ("Submission method", tender_meta.get("submission_method", "not stated")),
        ("Submission deadline", tender_meta.get("submission_deadline", "not stated")),
    ]
    return rows


def execution_duration(data: dict) -> str:
    """Human-readable run duration from stage timestamps (presentation only)."""
    timestamps = (data or {}).get("stage_timestamps") or {}
    if len(timestamps) < 2:
        return "—"
    ordered = [timestamps.get(s, "") for s in timestamps if timestamps.get(s)]
    if len(ordered) < 2:
        return "—"
    try:
        from datetime import datetime
        fmt = "%H:%M:%S"
        start = datetime.strptime(ordered[0], fmt)
        end = datetime.strptime(ordered[-1], fmt)
        delta = (end - start).total_seconds()
        if delta < 0:
            delta += 24 * 3600
        if delta < 60:
            return f"{int(delta)}s"
        mins, secs = divmod(int(delta), 60)
        return f"{mins}m {secs}s" if secs else f"{mins}m"
    except Exception:
        return "—"


def csv_to_list(raw: str) -> list:
    return [x.strip() for x in raw.split(",") if x.strip()]
