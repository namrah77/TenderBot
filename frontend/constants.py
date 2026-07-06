"""Static design + domain constants shared across the frontend package."""

# ---------------------------------------------------------------------
# Palette — semantic tones used by badges and progress bars.
# ---------------------------------------------------------------------
ACCENT = "#5B5BD6"
ACCENT_DARK = "#4343B0"
ACCENT_SOFT = "#E8E8F8"
SUCCESS = "#15803D"
SUCCESS_SOFT = "#E8F5EC"
WARNING = "#B45309"
WARNING_SOFT = "#FEF3E2"
RISK = "#B91C1C"
RISK_SOFT = "#FCE8E8"
MUTED = "#6B7280"
MUTED_SOFT = "#F1F2F4"
INK = "#111827"

# ---------------------------------------------------------------------
# Left nav — workspace is the main view; settings stays in the rail.
# ---------------------------------------------------------------------
NAV_GROUPS = [
    ("", [
        ("home", "home", "Workspace"),
    ]),
    ("System", [
        ("settings", "settings", "Settings"),
    ]),
]

NAV_ITEMS = [(pid, ic, label) for _, items in NAV_GROUPS for (pid, ic, label) in items]

# ---------------------------------------------------------------------
# Pipeline stages — keys must match agent `name=` in app/agent.py.
# ---------------------------------------------------------------------
STAGE_ORDER = [
    "security_checkpoint",
    "company_profiler",
    "tender_discovery",
    "tender_crawler",
    "eligibility_checker",
    "evaluation_agent",
    "report_generator",
]

STAGE_LABELS = {
    "security_checkpoint": "Security",
    "company_profiler": "Profile",
    "tender_discovery": "Discovery",
    "tender_crawler": "Crawler",
    "eligibility_checker": "Eligibility",
    "evaluation_agent": "Evaluation",
    "report_generator": "Report",
}

VERDICT_DISPLAY = {
    "Eligible": "Eligible",
    "Partial": "Partially Eligible",
    "Not Eligible": "Not Eligible",
}

CQC_RATINGS = ["Outstanding", "Good", "Requires Improvement", "Inadequate"]
