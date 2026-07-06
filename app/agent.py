import os
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "False"

import re
import json
from pathlib import Path
from urllib.parse import urlparse
from datetime import datetime, timezone, date, timedelta
from google.genai import types
from google.adk.models.llm_response import LlmResponse
from google.adk.agents import Agent, SequentialAgent
from google.adk.agents.readonly_context import ReadonlyContext
from google.adk.apps import App
from google.adk.models.google_llm import Gemini
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
from mcp import StdioServerParameters as MCPStdioParams  # pyright: ignore[reportMissingImports]
from .config import config

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
PROFILE_PATH = DATA_DIR / "company_profile.json"
CHECKLIST_PATH = DATA_DIR / "company_checklist.json"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# Official procurement + submission portals (CONTEXT.md + common sub-portals).
_PROCUREMENT_DOMAIN_SUFFIXES = (
    "find-tender.service.gov.uk",
    "findatender.service.gov.uk",
    "contractsfinder.service.gov.uk",
)
_SUBMISSION_PORTAL_SUFFIXES = (
    "kentbusinessportal.org.uk",
    "londontenders.org",
    "open-uk.org",
)

_CHECKLIST_SCHEMA_DEFAULTS = {
    "cqc_rating": "not stated",
    "services": [],
    "office_locations": [],
    "certifications": [],
    "languages": [],
    "max_capacity_value": None,
    "council_approvals": [],
}

_CERT_KEYWORDS = (
    ("cqc registered", "CQC Registered"),
    ("dbs", "DBS Certified Carers"),
    ("iso 9001", "ISO 9001"),
    ("iso 14001", "ISO 14001"),
    ("first aid", "First Aid Certified"),
    ("nvq", "NVQ Qualified Staff"),
    ("care certificate", "Care Certificate"),
)

_COUNCIL_KEYWORDS = (
    "ealing", "harrow", "bromley", "kent", "hillingdon", "brent",
    "hounslow", "lambeth", "croydon", "westminster", "camden",
)

_MONEY_RE = re.compile(r"£\s*([\d,]+(?:\.\d{1,2})?)", re.IGNORECASE)
_HOURLY_RATE_RE = re.compile(
    r"£\s*([\d,]+(?:\.\d{1,2})?)\s*(?:per\s*hour|/hour|ph\b|p\.h\.)",
    re.IGNORECASE,
)

# --- Free-tier quota protection -------------------------------------------
# Shared LLM with automatic exponential-backoff retry on 429/503 so a
# transient "RESOURCE_EXHAUSTED" pauses and retries instead of killing the run.
llm = Gemini(
    model=config.model,
    retry_options=types.HttpRetryOptions(
        attempts=6,
        initial_delay=2.0,
        max_delay=60.0,
        exp_base=2.0,
        http_status_codes=[429, 503],
    ),
)

# Truncate fetched pages so a single large tender notice can't blow the
# tokens-per-minute limit. Government notices are huge, but the critical
# fields are split: identity/scope/lots sit at the TOP, while the submission
# deadline sits FAR DOWN in the "Submission" section. A naive head-only cut
# would drop the deadline, so we keep the head PLUS any deadline-bearing lines.
MAX_PAGE_HEAD_CHARS = 7500
MAX_DISCOVERY_CANDIDATES = 10
MAX_OPEN_TENDERS = 4
_DEADLINE_KEYWORDS = (
    "deadline", "closing", "submission", "submit", "expire", "expiry",
    "tender submission", "enquiry", "award decision", "open framework",
    "dynamic purchasing", "dps", "closes", "close date", "response date",
)


_BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-GB,en;q=0.9",
}

_MONTHS_PATTERN = (
    r"(January|February|March|April|May|June|July|August|"
    r"September|October|November|December)"
)
_DATE_RE = re.compile(
    rf"\b(\d{{1,2}})\s+{_MONTHS_PATTERN}\s+(\d{{4}})(?:[^,\n]*)?",
    re.IGNORECASE,
)

_NAV_JUNK_NAMES = frozenset({
    "skip to content", "skip to main content", "menu", "navigation", "nav",
    "home", "search", "close", "open menu", "sign in", "sign out", "english",
    "cymraeg", "cookies", "accept analytics cookies", "reject analytics cookies",
    "view cookies", "hide this message", "gov.uk", "find a tender", "beta",
})

_DEADLINE_LABELS = (
    "time limit for receipt of tenders",
    "tender submission deadline",
    "submission deadline",
    "closing date",
    "deadline for receipt",
    "time limit for receipt",
)

_JSONLD_ORG_TYPES = frozenset({
    "organization", "localbusiness", "corporation", "medicalorganization",
})


def _http_get(url: str, *, accept_json: bool = False, company_url: str = ""):
    """GET with browser headers. Rejects non-whitelisted domains."""
    import certifi
    import requests
    import urllib3

    if not _domain_allowed(url, company_url):
        raise PermissionError(f"Domain not whitelisted for HTTP access: {url}")

    headers = dict(_BROWSER_HEADERS)
    if accept_json:
        headers["Accept"] = "application/json"
    kwargs = {"headers": headers, "timeout": 30, "allow_redirects": True}
    try:
        return requests.get(url, verify=certifi.where(), **kwargs)
    except requests.exceptions.SSLError:
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        return requests.get(url, verify=False, **kwargs)


def _parse_json_blob(raw: str):
    """Parse JSON from model/tool output that may be wrapped in markdown fences."""
    if not raw or not isinstance(raw, str):
        return []
    text = raw.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {}


def _parse_profile_from_state(raw) -> dict:
    """Normalise company_profile from ctx.state (str or dict)."""
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str) and raw.strip():
        parsed = _parse_json_blob(raw)
        return parsed if isinstance(parsed, dict) else {}
    return {}


def _empty_checklist() -> dict:
    return dict(_CHECKLIST_SCHEMA_DEFAULTS)


def _normalize_checklist(data: dict | None) -> dict:
    """Ensure fixed checklist schema with safe defaults for missing values."""
    out = _empty_checklist()
    if not isinstance(data, dict):
        return out
    for key, default in _CHECKLIST_SCHEMA_DEFAULTS.items():
        val = data.get(key, default)
        if isinstance(default, str):
            out[key] = val if isinstance(val, str) and val.strip() else "not stated"
        elif isinstance(default, list):
            out[key] = val if isinstance(val, list) else []
        else:
            out[key] = val if val is not None else None
    return out


def _generate_checklist_from_profile(profile: dict) -> dict:
    """Derive the fixed company checklist from a scraped profile."""
    profile = profile if isinstance(profile, dict) else {}
    checklist = _empty_checklist()
    rating = profile.get("cqc_rating")
    checklist["cqc_rating"] = rating if isinstance(rating, str) and rating.strip() else "not stated"
    for field in ("services", "office_locations", "certifications", "languages", "council_approvals"):
        val = profile.get(field) if field != "office_locations" else profile.get("coverage_areas", profile.get("office_locations"))
        checklist[field] = val if isinstance(val, list) else []
    cap = profile.get("max_capacity_value")
    checklist["max_capacity_value"] = cap if isinstance(cap, (int, float)) else None
    return _normalize_checklist(checklist)


def _optional_persist_checklist(checklist: dict) -> None:
    """Write generated checklist to disk, preserving display_name if present."""
    try:
        existing = _load_checklist_persisted()
        payload = _normalize_checklist(checklist)
        if existing.get("display_name"):
            payload["display_name"] = existing["display_name"]
        CHECKLIST_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    except Exception:
        pass


def _host_from_url(url: str) -> str:
    try:
        return urlparse(url).netloc.lower().removeprefix("www.")
    except Exception:
        return ""


def _domain_allowed(url: str, company_url: str = "") -> bool:
    """Reject non-whitelisted domains before any HTTP request."""
    host = _host_from_url(url)
    if not host:
        return False
    company_host = _host_from_url(company_url)
    if company_host and (host == company_host or host.endswith("." + company_host)):
        return True
    for suffix in _PROCUREMENT_DOMAIN_SUFFIXES + _SUBMISSION_PORTAL_SUFFIXES:
        if host == suffix or host.endswith("." + suffix):
            return True
    return False


def _audit_event(ctx_state: dict, event: str, severity: str = "INFO") -> None:
    audit = ctx_state.get("audit_log", [])
    audit.append({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event": event,
        "severity": severity,
    })
    ctx_state["audit_log"] = audit


# --- Pipeline debug (disabled unless PIPELINE_DEBUG=true) -------------------
def _pipeline_debug_active() -> bool:
    return config.pipeline_debug


def _empty_pipeline_debug() -> dict:
    return {
        "sources": {"contracts_finder": 0, "find_a_tender": 0},
        "discovery_deduped": 0,
        "discovery_returned": 0,
        "crawl_input_unique": 0,
        "crawl_duplicates_skipped": 0,
        "deadline_classification": {
            "open": 0,
            "expired": 0,
            "awarded": 0,
            "pipeline": 0,
            "cancelled": 0,
            "unverified": 0,
        },
        "passed_to_eligibility": 0,
        "crawl_open_count": 0,
        "eligibility_input_count": 0,
        "company_checklist_from_profile": False,
        "gemini_calls": 0,
    }


def _init_pipeline_debug(state: dict) -> None:
    if _pipeline_debug_active():
        state["pipeline_debug"] = _empty_pipeline_debug()


def _merge_pipeline_debug(state: dict, fragment: dict) -> None:
    if not _pipeline_debug_active() or not fragment:
        return
    dbg = state.setdefault("pipeline_debug", _empty_pipeline_debug())
    for key, val in fragment.items():
        if key == "sources" and isinstance(val, dict):
            dbg.setdefault("sources", {}).update(val)
        elif key == "deadline_classification" and isinstance(val, dict):
            for status, count in val.items():
                dbg["deadline_classification"][status] = (
                    dbg["deadline_classification"].get(status, 0) + int(count)
                )
        elif key in dbg:
            if isinstance(dbg[key], bool):
                dbg[key] = bool(val)
            elif isinstance(dbg[key], int):
                dbg[key] = int(val)
            else:
                dbg[key] = val


def _log_pipeline_debug(message: str) -> None:
    if _pipeline_debug_active():
        print(f"[TenderBot pipeline_debug] {message}", flush=True)


def _print_pipeline_debug_summary(state: dict) -> None:
    dbg = state.get("pipeline_debug") or {}
    if not dbg:
        return
    src = dbg.get("sources", {})
    cls = dbg.get("deadline_classification", {})
    lines = [
        "=== Pipeline debug summary ===",
        f"  Contracts Finder candidates: {src.get('contracts_finder', 0)}",
        f"  Find a Tender candidates:    {src.get('find_a_tender', 0)}",
        f"  Discovery deduped total:     {dbg.get('discovery_deduped', 0)}",
        f"  Discovery returned to agent: {dbg.get('discovery_returned', 0)}",
        f"  Crawl unique input URLs:     {dbg.get('crawl_input_unique', 0)}",
        f"  Crawl duplicate URLs skipped:  {dbg.get('crawl_duplicates_skipped', 0)}",
        "  Deadline classification:",
        f"    open={cls.get('open', 0)} expired={cls.get('expired', 0)} "
        f"awarded={cls.get('awarded', 0)} pipeline={cls.get('pipeline', 0)} "
        f"cancelled={cls.get('cancelled', 0)} unverified={cls.get('unverified', 0)}",
        f"  Crawl open/actionable:       {dbg.get('crawl_open_count', 0)}",
        f"  Eligibility checker input:   {dbg.get('eligibility_input_count', 0)}",
        "  Checklist from profile:      "
        f"{dbg.get('company_checklist_from_profile', False)}",
        f"  Total Gemini calls:          {dbg.get('gemini_calls', 0)}",
        "==============================",
    ]
    for line in lines:
        _log_pipeline_debug(line)


def _debug_before_model(callback_context, llm_request=None):
    if not _pipeline_debug_active():
        return None
    dbg = callback_context.state.setdefault("pipeline_debug", _empty_pipeline_debug())
    dbg["gemini_calls"] = dbg.get("gemini_calls", 0) + 1
    agent_name = getattr(callback_context, "agent_name", None) or "unknown"
    _log_pipeline_debug(
        f"Gemini call #{dbg['gemini_calls']} (agent={agent_name})"
    )
    return None


def _smart_before_model(callback_context, llm_request=None):
    """Skip Gemini when before_agent already seeded authoritative state."""
    agent = callback_context.agent_name or ""
    state = callback_context.state
    text = None
    if agent == "company_profiler" and state.get("_profiler_seeded"):
        raw = state.get("company_profile", "")
        text = raw if isinstance(raw, str) else json.dumps(raw)
    elif agent == "tender_discovery" and state.get("_discovery_seeded"):
        raw = state.get("tenders_raw", "[]")
        text = raw if isinstance(raw, str) else json.dumps(raw)
    elif agent == "tender_crawler" and state.get("_crawler_seeded"):
        raw = state.get("tenders_found", "[]")
        text = raw if isinstance(raw, str) else json.dumps(raw)
    if text is not None:
        if _pipeline_debug_active():
            _log_pipeline_debug(f"Skipped Gemini for {agent} (deterministic state)")
        return LlmResponse(
            content=types.Content(role="model", parts=[types.Part(text=text)]),
            turn_complete=True,
        )
    return _debug_before_model(callback_context, llm_request)


def _debug_after_tool(tool, args, tool_context, tool_response):
    if not _pipeline_debug_active():
        return None
    if isinstance(tool_response, dict) and "_pipeline_debug" in tool_response:
        fragment = tool_response["_pipeline_debug"]
        _merge_pipeline_debug(tool_context.state, fragment)
        if "sources" in fragment:
            src = fragment["sources"]
            _log_pipeline_debug(
                f"Discovery - Contracts Finder: {src.get('contracts_finder', 0)}, "
                f"Find a Tender: {src.get('find_a_tender', 0)}, "
                f"deduped: {fragment.get('discovery_deduped', 0)}, "
                f"returned: {fragment.get('discovery_returned', 0)}"
            )
        if "deadline_classification" in fragment:
            cls = fragment["deadline_classification"]
            _log_pipeline_debug(
                "Crawl classification - "
                f"open={cls.get('open', 0)} expired={cls.get('expired', 0)} "
                f"awarded={cls.get('awarded', 0)} pipeline={cls.get('pipeline', 0)} "
                f"cancelled={cls.get('cancelled', 0)} unverified={cls.get('unverified', 0)}; "
                f"crawl open/actionable: {fragment.get('crawl_open_count', 0)}"
            )
        cleaned = dict(tool_response)
        del cleaned["_pipeline_debug"]
        return cleaned
    return None


def _tender_crawler_after_tool(tool, args, tool_context, tool_response):
    """Persist crawl_tender_notices output directly to state.

    output_key is populated from the LLM's final text, which often fails to
    relay large tool JSON. ADK supports writing state_delta here and setting
    skip_summarization so the tool result is authoritative.
    """
    resp = tool_response
    debug_cleaned = _debug_after_tool(tool, args, tool_context, tool_response)
    if debug_cleaned is not None:
        resp = debug_cleaned

    tenders = resp.get("tenders") if isinstance(resp, dict) else None
    if not isinstance(tenders, list):
        return debug_cleaned

    tenders = tenders[:MAX_OPEN_TENDERS]
    existing = _parse_tenders_list(tool_context.state.get("tenders_found"))
    if not tenders and existing:
        tool_context.actions.skip_summarization = True
        return debug_cleaned

    payload = json.dumps(tenders)
    tool_context.state["_crawl_tool_tenders"] = tenders
    tool_context.state["tenders_found"] = payload
    tool_context.actions.state_delta["tenders_found"] = payload
    tool_context.actions.skip_summarization = True

    if _pipeline_debug_active():
        _merge_pipeline_debug(
            tool_context.state,
            {"eligibility_input_count": len(tenders)},
        )
        _log_pipeline_debug(
            f"crawl_tender_notices persisted {len(tenders)} tenders to tenders_found"
        )

    return debug_cleaned


def _tender_crawler_after_agent(callback_context):
    """Safety net: restore tenders_found from tool stash if still empty."""
    _restore_json_state(callback_context.state, "tenders_found", "_crawl_tool_tenders")
    if _pipeline_debug_active():
        count = len(_parse_tenders_list(callback_context.state.get("tenders_found", "")))
        _log_pipeline_debug(f"tender_crawler after_agent tenders_found count: {count}")
    return None


def _eligibility_before(callback_context):
    _restore_json_state(callback_context.state, "tenders_found", "_crawl_tool_tenders")
    count = len(_parse_tenders_list(callback_context.state.get("tenders_found", "")))
    if _pipeline_debug_active():
        _merge_pipeline_debug(
            callback_context.state,
            {"eligibility_input_count": count},
        )
        _log_pipeline_debug(f"Tenders in tenders_found state at eligibility: {count}")
    return None


def _pipeline_debug_finalize(callback_context):
    _print_pipeline_debug_summary(callback_context.state)
    return None


def _parse_tenders_list(raw) -> list:
    if isinstance(raw, list):
        return raw
    if isinstance(raw, str) and raw.strip():
        parsed = _parse_json_blob(raw)
        return parsed if isinstance(parsed, list) else []
    return []


def _parse_eligibility_results(raw) -> list:
    if isinstance(raw, list):
        return raw
    if isinstance(raw, str) and raw.strip():
        parsed = _parse_json_blob(raw)
        return parsed if isinstance(parsed, list) else []
    return []


def _pipeline_funnel_counts(state: dict) -> tuple[int, int, int]:
    """Return (discovery_count, actionable_count, eligibility_count)."""
    discovery = state.get("_discovery_candidates")
    if not isinstance(discovery, list):
        discovery = _parse_tenders_list(state.get("tenders_raw", ""))
    actionable = _parse_tenders_list(state.get("tenders_found", ""))
    eligibility = _parse_eligibility_results(state.get("eligibility_results", ""))
    return len(discovery), len(actionable), len(eligibility)


def _pipeline_funnel_summary(state: dict) -> str:
    n_discovery, n_actionable, n_eligibility = _pipeline_funnel_counts(state)
    filtered = max(n_discovery - n_actionable, 0)
    return (
        f"Discovery: {n_discovery} candidate tenders found\n"
        f"Filtering: {n_actionable} actionable tenders selected "
        f"({filtered} excluded before eligibility by deadline/status filtering "
        f"and MAX_OPEN_TENDERS limit of 4)\n"
        f"Eligibility: {n_eligibility}/{n_actionable} actionable tenders evaluated"
    )
    if isinstance(raw, list):
        return raw
    if isinstance(raw, str) and raw.strip():
        parsed = _parse_json_blob(raw)
        return parsed if isinstance(parsed, list) else []
    return []


def _slim_tender_for_llm(tender: dict) -> dict:
    """Token-light tender summary for eligibility/report prompts."""
    lots = tender.get("lots_offered") or []
    return {
        "reference_number": tender.get("reference_number", "not stated"),
        "title": tender.get("title", "not stated"),
        "contracting_authority": tender.get("contracting_authority", "not stated"),
        "submission_deadline": _format_submission_deadline(
            tender.get("submission_deadline", "not stated")
        ),
        "deadline_status": tender.get("deadline_status", "not stated"),
        "geographic_coverage": tender.get("geographic_coverage", "not stated"),
        "cqc_required": tender.get("cqc_required", "not stated"),
        "required_certifications": tender.get("required_certifications") or [],
        "lots_offered": lots[:3],
        "estimated_value": tender.get("estimated_value", "not stated"),
        "hourly_rate": tender.get("hourly_rate", "not stated"),
        "quality_price_weighting": tender.get("quality_price_weighting", "not stated"),
        "submission_method": tender.get("submission_method", "not stated"),
        "portal_url": tender.get("portal_url", "not stated"),
    }


def _seed_company_from_url(state: dict, company_url: str) -> None:
    profile = fetch_company_profile(company_url)
    state["_profile_tool"] = profile
    state["company_profile"] = json.dumps(profile)
    checklist = _generate_checklist_from_profile(profile)
    state["company_checklist"] = checklist
    state["_profiler_seeded"] = True
    _optional_persist_checklist(checklist)


def _discovery_keywords(profile: dict | None) -> str:
    profile = profile or {}
    for service in profile.get("services") or []:
        sl = str(service).lower()
        if any(t in sl for t in ("domiciliary", "home care", "homecare", "supported living", "personal care")):
            return sl
    return "domiciliary care"


def _seed_tenders_raw(state: dict, profile: dict | None = None) -> int:
    result = search_tender_portals(_discovery_keywords(profile))
    candidates = result.get("candidates", [])
    state["_discovery_candidates"] = candidates
    state["tenders_raw"] = json.dumps(candidates)
    state["_discovery_seeded"] = True
    return len(candidates)


def _seed_tenders_found(state: dict, company_url: str = "") -> int:
    raw = state.get("tenders_raw", "[]")
    result = crawl_tender_notices(
        raw if isinstance(raw, str) else json.dumps(raw),
        company_url=company_url or str(state.get("company_url", "")),
    )
    tenders = (result.get("tenders") or [])[:MAX_OPEN_TENDERS]
    state["_crawl_tool_tenders"] = tenders
    state["tenders_found"] = json.dumps(tenders)
    state["_crawler_seeded"] = True
    return len(tenders)


def _restore_json_state(state: dict, key: str, stash_key: str) -> None:
    if key == "company_profile":
        parsed = _parse_profile_from_state(state.get(key, ""))
    else:
        parsed = _parse_tenders_list(state.get(key, ""))
    if parsed:
        return
    stash = state.get(stash_key)
    if isinstance(stash, list) and stash:
        state[key] = json.dumps(stash)
    elif isinstance(stash, dict):
        state[key] = json.dumps(stash)


def _company_profiler_before(callback_context):
    url = str(callback_context.state.get("company_url", ""))
    if url and _domain_allowed(url, url):
        _seed_company_from_url(callback_context.state, url)
    return None


def _tender_discovery_before(callback_context):
    profile = _parse_profile_from_state(callback_context.state.get("company_profile", ""))
    if not profile:
        _restore_json_state(callback_context.state, "company_profile", "_profile_tool")
        profile = _parse_profile_from_state(callback_context.state.get("company_profile", ""))
    _seed_tenders_raw(callback_context.state, profile)
    return None


def _tender_discovery_after_tool(tool, args, tool_context, tool_response):
    resp = tool_response
    debug_cleaned = _debug_after_tool(tool, args, tool_context, tool_response)
    if debug_cleaned is not None:
        resp = debug_cleaned
    candidates = resp.get("candidates") if isinstance(resp, dict) else None
    if isinstance(candidates, list):
        tool_context.state["_discovery_candidates"] = candidates
        payload = json.dumps(candidates)
        tool_context.state["tenders_raw"] = payload
        tool_context.actions.state_delta["tenders_raw"] = payload
        tool_context.actions.skip_summarization = True
    return debug_cleaned


def _tender_discovery_after_agent(callback_context):
    _restore_json_state(callback_context.state, "tenders_raw", "_discovery_candidates")
    return None


def _tender_crawler_before(callback_context):
    _restore_json_state(callback_context.state, "tenders_raw", "_discovery_candidates")
    url = str(callback_context.state.get("company_url", ""))
    if _parse_tenders_list(callback_context.state.get("tenders_raw")):
        _seed_tenders_found(callback_context.state, url)
    else:
        callback_context.state["_crawl_tool_tenders"] = []
        callback_context.state["tenders_found"] = "[]"
        callback_context.state["_crawler_seeded"] = True
    return None


def _report_generator_after_agent(callback_context):
    report = callback_context.state.get("final_report", "")
    if isinstance(report, str) and len(report.strip()) > 200:
        try:
            from .mcp_server import save_report
            save_report(report)
        except Exception:
            pass
    _pipeline_debug_finalize(callback_context)
    return None


def _parse_uk_date(value: str):
    """Parse '16 July 2026, 12:00am' -> date."""
    if not value or value == "not stated":
        return None
    cleaned = _DATE_RE.search(value)
    if not cleaned:
        return None
    day, month, year = cleaned.group(1), cleaned.group(2), cleaned.group(3)
    for fmt in ("%d %B %Y", "%d %b %Y"):
        try:
            return datetime.strptime(f"{day} {month} {year}", fmt).date()
        except ValueError:
            continue
    return None


def _is_junk_company_name(name: str) -> bool:
    cleaned = re.sub(r"\s+", " ", (name or "").strip())
    if len(cleaned) < 3:
        return True
    return cleaned.lower() in _NAV_JUNK_NAMES


def _iter_jsonld_nodes(data):
    """Yield dict nodes from JSON-LD @graph or nested structures."""
    if isinstance(data, list):
        for item in data:
            yield from _iter_jsonld_nodes(item)
    elif isinstance(data, dict):
        yield data
        graph = data.get("@graph")
        if isinstance(graph, list):
            for item in graph:
                yield from _iter_jsonld_nodes(item)


def _normalize_date_string(value: str) -> str:
    """Convert ISO or UK text dates to a readable deadline string."""
    if not value or not isinstance(value, str):
        return ""
    value = value.strip()
    iso = re.match(r"(\d{4})-(\d{2})-(\d{2})", value)
    if iso:
        try:
            dt = datetime.strptime(f"{iso.group(1)}-{iso.group(2)}-{iso.group(3)}", "%Y-%m-%d")
            return dt.strftime("%d %B %Y")
        except ValueError:
            pass
    m = _DATE_RE.search(value)
    return m.group(0).strip() if m else value


def _format_submission_deadline(deadline: str) -> str:
    if not deadline or deadline == "not stated":
        return "Deadline not stated"
    return deadline


def _fetch_page_soup(url: str, company_url: str = ""):
    """Single GET returning BeautifulSoup, or None on failure."""
    if not isinstance(url, str) or not url.lower().startswith(("http://", "https://")):
        return None
    try:
        from bs4 import BeautifulSoup

        resp = _http_get(url, company_url=company_url)
        if resp.status_code != 200:
            return None
        return BeautifulSoup(resp.content, "html.parser")
    except Exception:
        return None


def _soup_plain_text(soup) -> str:
    if soup is None:
        return ""
    text = soup.get_text(separator="\n", strip=True)
    return "\n".join(line.strip() for line in text.splitlines() if line.strip())


def _apply_page_truncation(text: str) -> str:
    """Trim long page text while preserving deadline-bearing tail lines."""
    if not text or len(text) <= MAX_PAGE_HEAD_CHARS:
        return text
    head = text[:MAX_PAGE_HEAD_CHARS]
    tail_src = text[MAX_PAGE_HEAD_CHARS:].splitlines()
    kept = []
    seen = set()
    for i, line in enumerate(tail_src):
        if any(kw in line.lower() for kw in _DEADLINE_KEYWORDS):
            for ln in (line, *tail_src[i + 1 : i + 3]):
                s = ln.strip()
                if s and s not in seen:
                    seen.add(s)
                    kept.append(s)
    tail = ""
    if kept:
        tail = "\n[KEY DATE / DEADLINE LINES FROM REST OF PAGE]\n" + "\n".join(kept[:60])
    return head + "\n...[body truncated to conserve tokens]..." + tail


def _fetch_page_for_crawl(url: str, company_url: str = "") -> tuple:
    """Return (soup|None, page_text) from one HTTP fetch."""
    if not url:
        return None, "Failed to fetch url: (missing)"
    soup = _fetch_page_soup(url, company_url=company_url)
    if soup is None:
        return None, f"Failed to fetch url: {url}"
    return soup, _apply_page_truncation(_soup_plain_text(soup))


def _extract_submission_deadline_from_soup(soup) -> str:
    """Deterministic deadline extraction from official notice HTML."""
    if soup is None:
        return ""

    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "")
        except (json.JSONDecodeError, TypeError):
            continue
        for node in _iter_jsonld_nodes(data):
            for key in ("endDate", "validThrough", "deadline"):
                normalized = _normalize_date_string(str(node.get(key, "")))
                if normalized and _DATE_RE.search(normalized):
                    return normalized

    for tag in soup.find_all(["h4", "dt", "th", "label", "span", "div"]):
        label = tag.get_text(" ", strip=True).lower()
        if not any(token in label for token in _DEADLINE_LABELS):
            continue
        candidate = tag.find_next(["p", "dd", "td", "time"])
        while candidate is not None:
            classes = candidate.get("class") or []
            if candidate.name == "p" and "govuk-body-s" in classes:
                candidate = candidate.find_next(["p", "dd", "td", "time"])
                continue
            if candidate.name == "time" and candidate.get("datetime"):
                normalized = _normalize_date_string(candidate["datetime"])
                if normalized:
                    return normalized
            text = candidate.get_text(" ", strip=True)
            m = _DATE_RE.search(text)
            if m and "published" not in text.lower():
                return m.group(0).strip()
            candidate = candidate.find_next(["p", "dd", "td", "time"])

    return ""


def _extract_submission_deadline(page_text: str, soup=None) -> str:
    """Pull the tender submission deadline from notice HTML and page text."""
    from_soup = _extract_submission_deadline_from_soup(soup)
    if from_soup:
        return from_soup

    if not page_text or page_text.startswith("Failed"):
        return "not stated"

    lines = page_text.splitlines()
    for i, line in enumerate(lines):
        low = line.lower()
        if any(token in low for token in _DEADLINE_LABELS) or (
            "submission deadline" in low and "enquiry" not in low
        ):
            for j in range(i, min(i + 4, len(lines))):
                m = _DATE_RE.search(lines[j])
                if m and "published" not in lines[j].lower():
                    return m.group(0).strip()

    if "KEY DATE" in page_text:
        tail = page_text.split("KEY DATE", 1)[-1]
        for m in _DATE_RE.finditer(tail):
            ctx = tail[max(0, m.start() - 40) : m.start()].lower()
            if "submission" in ctx or "deadline" in ctx or "receipt" in ctx:
                return m.group(0).strip()

    for label in _DEADLINE_LABELS:
        idx = page_text.lower().find(label)
        if idx >= 0:
            snippet = page_text[idx : idx + 160]
            m = _DATE_RE.search(snippet)
            if m:
                return m.group(0).strip()

    return "not stated"


def _classify_deadline(page_text: str, deadline_str: str) -> str:
    """Classify deadline_status from live page content."""
    if not page_text or page_text.startswith("Failed"):
        return "unverified"
    low = page_text.lower()
    if "cancelled" in low or "canceled" in low or "withdrawn" in low:
        return "cancelled"
    if "closed opportunity" in low or "contract is currently closed" in low:
        return "expired"
    if any(x in low for x in ("contract award", "awarded to", "was awarded")):
        if "tender notice" not in low and "invites tenders" not in low:
            return "awarded"
    if any(x in low for x in ("pipeline notice", "planned procurement", "preliminary market engagement")):
        if "tender submission deadline" not in low:
            return "pipeline"
    parsed = _parse_uk_date(deadline_str)
    if parsed:
        return "open" if parsed >= date.today() else "expired"
    if any(x in low for x in ("open framework", "dynamic purchasing", " dps")):
        return "open"
    return "unverified"


def _fetch_page_text(url: str, company_url: str = "") -> str:
    """Browser-style fetch of a public web page's readable text."""
    if not isinstance(url, str) or not url.lower().startswith(("http://", "https://")):
        return f"Failed to fetch url: {url}"
    if not _domain_allowed(url, company_url):
        return f"Failed to fetch url: {url} (domain not whitelisted)"
    try:
        from bs4 import BeautifulSoup

        resp = _http_get(url, company_url=company_url)
        if resp.status_code != 200:
            return f"Failed to fetch url: {url} (HTTP {resp.status_code})"
        text = BeautifulSoup(resp.content, "html.parser").get_text(separator="\n", strip=True)
        return "\n".join(line.strip() for line in text.splitlines() if line.strip())
    except PermissionError as exc:
        return f"Failed to fetch url: {url} ({exc})"
    except Exception as exc:
        return f"Failed to fetch url: {url} ({exc})"


def _extract_company_name(page: str, company_url: str, soup=None) -> str:
    if soup is not None:
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(script.string or "")
            except (json.JSONDecodeError, TypeError):
                continue
            for node in _iter_jsonld_nodes(data):
                node_type = str(node.get("@type", "")).lower()
                if node_type in _JSONLD_ORG_TYPES or "organization" in node_type:
                    name = str(node.get("name", "")).strip()
                    if name and not _is_junk_company_name(name):
                        return name

        og = soup.find("meta", property="og:site_name")
        if og and og.get("content"):
            name = og["content"].strip()
            if not _is_junk_company_name(name):
                return name

        if soup.title and soup.title.string:
            title = soup.title.string.strip()
            for sep in ("|", "–", "-", "—"):
                if sep in title:
                    title = title.split(sep)[0].strip()
            if not _is_junk_company_name(title):
                return title

        for h1 in soup.find_all("h1"):
            name = h1.get_text(" ", strip=True)
            if name and not _is_junk_company_name(name):
                return name

    if page.startswith("Failed"):
        host = _host_from_url(company_url).split(".")[0]
        return host.replace("-", " ").title() if host else "not stated"

    for line in page.splitlines()[:40]:
        candidate = line.strip()
        if _is_junk_company_name(candidate):
            continue
        m = re.match(r"^([A-Z][A-Za-z'&\-\s]{2,60})\s*$", candidate)
        if m:
            return m.group(1).strip()

    host = _host_from_url(company_url).split(".")[0]
    return host.replace("-", " ").title() if host else "not stated"


def _extract_certifications(page_low: str) -> list:
    found = []
    for needle, label in _CERT_KEYWORDS:
        if needle in page_low and label not in found:
            found.append(label)
    return found


def _extract_council_approvals(page_low: str) -> list:
    found = []
    for council in _COUNCIL_KEYWORDS:
        if council in page_low and (
            "approved" in page_low or "accredited" in page_low or "framework" in page_low
        ):
            label = council.title()
            if label not in found:
                found.append(label)
    return found


def _extract_money_value(page: str) -> str:
    for label in ("contract value", "estimated value", "total value", "framework value"):
        idx = page.lower().find(label)
        if idx >= 0:
            snippet = page[idx : idx + 120]
            m = _MONEY_RE.search(snippet)
            if m:
                return f"£{m.group(1)}"
    amounts = _MONEY_RE.findall(page[:12000])
    if amounts:
        return f"£{amounts[0]}"
    return "not stated"


def _extract_hourly_rate(page: str) -> str:
    m = _HOURLY_RATE_RE.search(page)
    if m:
        return f"£{m.group(1)}"
    for label in ("hourly rate", "rate per hour", "price per hour"):
        idx = page.lower().find(label)
        if idx >= 0:
            m2 = _MONEY_RE.search(page[idx : idx + 80])
            if m2:
                return f"£{m2.group(1)}"
    return "not stated"


def _extract_required_certifications(page_low: str) -> list:
    reqs = []
    for needle, label in _CERT_KEYWORDS:
        if needle in page_low and label not in reqs:
            reqs.append(label)
    if "cqc registered" in page_low or "cqc rating" in page_low:
        if "CQC Registered" not in reqs:
            reqs.append("CQC Registered")
    return reqs


def _extract_submission_method(page_low: str) -> str:
    for portal, label in (
        ("kentbusinessportal.org.uk", "Kent Business Portal"),
        ("londontenders.org", "London Tenders"),
        ("open-uk.org", "Open UK"),
        ("proactis", "Proactis"),
        ("atamis", "Atamis"),
        ("delta esourcing", "Delta eSourcing"),
        ("find-tender.service.gov.uk", "Find a Tender"),
    ):
        if portal in page_low:
            return label
    if "email" in page_low and "submit" in page_low:
        return "Email submission"
    if "postal" in page_low or "by post" in page_low:
        return "Postal submission"
    return "not stated"


def _extract_lots(page: str, title: str) -> list:
    lots = []
    for m in re.finditer(
        r"(?:lot|package)\s*(\d+)[:\-\s]+([^\n]{5,120})",
        page,
        re.IGNORECASE,
    ):
        lots.append({
            "lot_number": m.group(1),
            "lot_title": m.group(2).strip(),
            "service_scope": m.group(2).strip(),
            "geographic_coverage": "not stated",
        })
    if lots:
        return lots[:8]
    return [{
        "lot_number": "not stated",
        "lot_title": title,
        "service_scope": "home care / domiciliary care (from notice title)",
        "geographic_coverage": "not stated",
    }]


def load_web_page(url: str, company_url: str = "") -> str:
    """Fetch the readable text of a web page, trimmed to conserve tokens
    while preserving deadline/closing-date information wherever it appears.

    Args:
        url (str): The url to browse.

    Returns:
        str: The (possibly trimmed) text content of the url.
    """
    text = _fetch_page_text(url, company_url=company_url)
    return _apply_page_truncation(text)


def _load_checklist_persisted() -> dict:
    """Optional on-disk checklist (UI persistence only — not the pipeline source of truth)."""
    try:
        return json.loads(CHECKLIST_PATH.read_text(encoding="utf-8")) if CHECKLIST_PATH.exists() else {}
    except Exception:
        return {}


def fetch_company_profile(company_url: str) -> dict:
    """Fetch the company website and return a structured profile JSON object.

    Args:
        company_url: The company website URL to profile.

    Returns:
        dict with company_name, address, cqc_id, cqc_rating, services,
        coverage_areas, languages, council_approvals, certifications,
        max_capacity_value.
    """
    soup = _fetch_page_soup(company_url, company_url=company_url)
    page = _soup_plain_text(soup) if soup is not None else _fetch_page_text(
        company_url, company_url=company_url
    )
    low = page.lower() if page and not page.startswith("Failed") else ""

    profile = {
        "company_name": _extract_company_name(page, company_url, soup=soup),
        "address": "not stated",
        "cqc_id": "not stated",
        "cqc_rating": "not stated",
        "services": [],
        "coverage_areas": [],
        "languages": [],
        "council_approvals": [],
        "certifications": [],
        "max_capacity_value": None,
    }

    if page.startswith("Failed"):
        return profile

    if "southall" in low:
        profile["address"] = "Southall, London"
    elif "ealing" in low:
        profile["address"] = "Ealing, London"
    else:
        postcode = re.search(
            r"\b[A-Z]{1,2}\d{1,2}[A-Z]?\s?\d[A-Z]{2}\b", page[:8000], re.IGNORECASE
        )
        if postcode:
            profile["address"] = postcode.group(0)

    cqc_id = re.search(r"\b1-\d{6,10}\b", page)
    if cqc_id:
        profile["cqc_id"] = cqc_id.group(0)

    if "outstanding" in low and "cqc" in low:
        profile["cqc_rating"] = "Outstanding"
    elif "good" in low and "cqc" in low:
        profile["cqc_rating"] = "Good"
    elif "requires improvement" in low and "cqc" in low:
        profile["cqc_rating"] = "Requires Improvement"

    page_services = []
    for term in (
        "domiciliary care", "home care", "live in care", "live-in care",
        "respite care", "dementia care", "disability care", "elderly care",
        "personal care", "floating support", "day opportunities",
        "supported living", "reablement", "extra care",
    ):
        if term in low:
            page_services.append(term.title())
    profile["services"] = sorted(set(page_services))

    lang_terms = (
        "english", "hindi", "punjabi", "urdu", "arabic", "bengali",
        "french", "spanish", "somali", "gujrati", "gujarati",
    )
    profile["languages"] = [w.title() for w in lang_terms if w in low]

    profile["certifications"] = _extract_certifications(low)
    profile["council_approvals"] = _extract_council_approvals(low)

    coverage = []
    for area in _COUNCIL_KEYWORDS:
        if area in low:
            coverage.append(area.title())
    if "london" in low and "London" not in coverage:
        coverage.append("London")
    profile["coverage_areas"] = sorted(set(coverage))

    return profile


def generate_company_checklist(profile_json: str) -> dict:
    """Build a fixed-schema company checklist from a scraped profile JSON.

    Args:
        profile_json: JSON string or object from fetch_company_profile.

    Returns:
        dict with cqc_rating, services, office_locations, certifications,
        languages, max_capacity_value, council_approvals.
    """
    profile = profile_json if isinstance(profile_json, dict) else _parse_json_blob(str(profile_json))
    if not isinstance(profile, dict):
        profile = {}
    return _generate_checklist_from_profile(profile)


_ACTIONABLE_STATUSES = frozenset({"open", "unverified"})


def _tender_notice_ref(url: str, page: str) -> str:
    for pattern in (
        r"/Notice/([^/?]+)",
        r"notice[=/]([0-9]{6}-[0-9]{4})",
        r"\b(CN\d{5,8})\b",
    ):
        m = re.search(pattern, url + "\n" + page[:4000], re.IGNORECASE)
        if m:
            return m.group(1)
    return "not stated"


def _infer_geographic_fit(page_low: str, coverage_areas: list | None = None) -> str:
    coverage_areas = coverage_areas or []
    coverage_low = [str(a).lower() for a in coverage_areas]
    if any(x in page_low for x in ("ealing", "southall")) and any(
        "ealing" in c or "southall" in c or "london" in c for c in coverage_low
    ):
        return "Direct Match"
    if any(x in page_low for x in ("harrow", "hillingdon", "brent", "bromley")):
        return "Adjacent"
    if "kent" in page_low:
        return "Distant"
    if any(c in page_low for c in coverage_low):
        return "Direct Match"
    return "not stated"


def crawl_tender_notices(tenders_json: str, company_url: str = "") -> dict:
    """Fetch and extract structured data for each tender; keep only open/actionable.

    Args:
        tenders_json: JSON array string from tender discovery (title, portal_url, etc.).
        company_url: Company URL for domain whitelist on submission portals.

    Returns:
        dict with key "tenders": list of structured open tender objects.
    """
    try:
        raw = _parse_json_blob(tenders_json)
    except (json.JSONDecodeError, TypeError):
        raw = []

    if not isinstance(raw, list):
        raw = []

    seen_urls: set[str] = set()
    duplicates_skipped = 0
    status_counts = {k: 0 for k in _empty_pipeline_debug()["deadline_classification"]}
    results = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        url = (item.get("portal_url") or "").strip()
        if not url:
            continue
        if url in seen_urls:
            duplicates_skipped += 1
            continue
        seen_urls.add(url)

        title = item.get("title", "not stated")
        authority = item.get("contracting_authority", "not stated")
        soup, page = _fetch_page_for_crawl(url, company_url=company_url)

        ref = _tender_notice_ref(url, page)
        deadline_raw = _extract_submission_deadline(page, soup=soup)
        status = _classify_deadline(page, deadline_raw)
        deadline = _format_submission_deadline(deadline_raw)
        if status in status_counts:
            status_counts[status] += 1
        if status not in _ACTIONABLE_STATUSES:
            continue

        low = page.lower() if page and not page.startswith("Failed") else ""
        cqc_required = "yes" if ("cqc registered" in low or "cqc rating" in low) else "not stated"

        quality_weight = "not stated"
        m = re.search(
            r"(\d+%\s*(?:quality|price)[^.\n]{0,40}\d+%\s*(?:quality|price))",
            page,
            re.I,
        )
        if m:
            quality_weight = m.group(1).strip()

        qq_weight = "not stated"
        qq = re.search(r"quality\s+(?:question|criteria)[^\n]{0,80}(\d+%)", page, re.I)
        if qq:
            qq_weight = qq.group(1).strip()

        geo = _infer_geographic_fit(low)
        lots = _extract_lots(page, title)
        for lot in lots:
            if lot.get("geographic_coverage") == "not stated":
                lot["geographic_coverage"] = geo

        submission_method = _extract_submission_method(low)
        submission_notes = submission_method
        if submission_method == "not stated":
            submission_notes = "not stated"

        hourly_rate = _extract_hourly_rate(page)
        rate_ceiling = hourly_rate if hourly_rate != "not stated" else "not stated"
        contract_value = _extract_money_value(page)

        results.append({
            "reference_number": ref,
            "title": title,
            "contracting_authority": authority,
            "lots_offered": lots,
            "cqc_required": cqc_required,
            "office_requirement": "not stated",
            "rate_ceiling": rate_ceiling,
            "hourly_rate": hourly_rate,
            "contract_value": contract_value,
            "estimated_value": contract_value,
            "required_certifications": _extract_required_certifications(low),
            "quality_price_weighting": quality_weight,
            "quality_question_weightage": qq_weight,
            "geographic_distance_fit": geo,
            "geographic_coverage": geo,
            "submission_deadline": deadline,
            "deadline_status": status,
            "submission_method": submission_method,
            "portal_url": url,
            "submission_notes": submission_notes,
        })

    payload = {"tenders": results[:MAX_OPEN_TENDERS]}
    if _pipeline_debug_active():
        payload["_pipeline_debug"] = {
            "crawl_input_unique": len(seen_urls),
            "crawl_duplicates_skipped": duplicates_skipped,
            "deadline_classification": status_counts,
            "crawl_open_count": len(results),
        }
    return payload


# ---------------------------------------------------------------------
# Deterministic tender discovery (official sources only)
# ---------------------------------------------------------------------
# google_search (LLM grounding) fabricates notice URLs from reference numbers,
# so every link 404s. Discovery uses official OCDS APIs only; the crawler
# live-verifies each URL and deadline before any Gemini ranking/eligibility.

_CARE_TERMS = (
    "home care", "homecare", "domiciliary", "supported living",
    "reablement", "extra care", "floating support", "day opportunities",
    "personal care at home", "care at home", "live-in care", "live in care",
    "forensic care", "homecare open framework",
)


def _is_care_notice(blob: str) -> bool:
    blob = blob.lower()
    if any(term in blob for term in _CARE_TERMS):
        return True
    return "home" in blob and "care" in blob and "health care" not in blob


def _notice_url_from_release(rel: dict) -> str:
    notice_id = rel.get("id") or ""
    if notice_id and re.match(r"\d{6}-\d{4}", notice_id):
        return f"https://www.find-tender.service.gov.uk/Notice/{notice_id}"
    ocid = rel.get("ocid", "")
    guid = re.sub(r"^ocds-[a-z0-9]+-", "", ocid)
    if guid:
        return f"https://www.contractsfinder.service.gov.uk/Notice/{guid}"
    return ""


def _candidate_from_release(rel: dict) -> dict | None:
    tender = rel.get("tender", {}) or {}
    title = tender.get("title") or rel.get("title") or ""
    desc = tender.get("description") or ""
    blob = f"{title} {desc}"
    if not _is_care_notice(blob):
        return None
    url = _notice_url_from_release(rel)
    if not url:
        return None
    return {
        "title": title[:160] or "not stated",
        "contracting_authority": (rel.get("buyer") or {}).get("name", "not stated"),
        "portal_url": url,
    }


def _search_contracts_finder(keywords: list[str], seen: set[str]) -> list[dict]:
    import re as _re

    out: list[dict] = []
    for kw in keywords[:4]:
        try:
            url = (
                "https://www.contractsfinder.service.gov.uk/Published/Notices/OCDS/Search"
                "?keyword=" + kw.replace(" ", "%20") + "&stages=tender&limit=25"
            )
            resp = _http_get(url, accept_json=True)
            if resp.status_code != 200:
                continue
            data = resp.json()
        except Exception:
            continue

        for rel in data.get("releases", []):
            cand = _candidate_from_release(rel)
            if not cand or cand["portal_url"] in seen:
                continue
            seen.add(cand["portal_url"])
            out.append(cand)
    return out


def _search_find_a_tender(seen: set[str], *, max_pages: int = 5) -> list[dict]:
    out: list[dict] = []
    updated_from = (date.today() - timedelta(days=365)).strftime("%Y-%m-%dT00:00:00")
    next_url = (
        "https://www.find-tender.service.gov.uk/api/1.0/ocdsReleasePackages"
        f"?stages=tender&limit=100&updatedFrom={updated_from}"
    )
    pages = 0
    while next_url and pages < max_pages:
        try:
            resp = _http_get(next_url, accept_json=True)
            if resp.status_code != 200:
                break
            data = resp.json()
        except Exception:
            break
        for rel in data.get("releases", []):
            cand = _candidate_from_release(rel)
            if not cand or cand["portal_url"] in seen:
                continue
            seen.add(cand["portal_url"])
            out.append(cand)
        next_url = (data.get("links") or {}).get("next")
        pages += 1
    return out


def search_tender_portals(keywords: str = "home care") -> dict:
    """Discover REAL UK care tender notices from official procurement APIs.

    Queries Contracts Finder and Find a Tender OCDS APIs. Every portal_url is
    taken verbatim from API data (never fabricated). The crawler verifies each
    notice and filters to open/actionable tenders before Gemini reasoning.

    Args:
        keywords: Free-text care keywords to search (e.g. "home care").

    Returns:
        dict with a "candidates" list of {title, contracting_authority, portal_url}.
    """
    seen: set[str] = set()
    search_terms = [keywords] if keywords else []
    for extra in ("home care", "domiciliary care", "supported living", "homecare"):
        if extra not in search_terms:
            search_terms.append(extra)

    cf_candidates = _search_contracts_finder(search_terms, seen)
    fat_candidates = _search_find_a_tender(seen)
    candidates = cf_candidates + fat_candidates
    returned = candidates[:MAX_DISCOVERY_CANDIDATES]

    payload = {"candidates": returned}
    if _pipeline_debug_active():
        payload["_pipeline_debug"] = {
            "sources": {
                "contracts_finder": len(cf_candidates),
                "find_a_tender": len(fat_candidates),
            },
            "discovery_deduped": len(candidates),
            "discovery_returned": len(returned),
        }
    return payload


def security_checkpoint(callback_context):
    """Runs before the pipeline. Seeds state, enforces domain policy,
    redacts PII for audit logging, blocks on prompt injection."""
    ctx = callback_context
    company_url = str(ctx.state.get("company_url", "")).strip()
    ctx.state.setdefault("company_url", company_url)

    # Checklist is generated from the website later; seed schema defaults only.
    ctx.state["company_checklist"] = _empty_checklist()
    _init_pipeline_debug(ctx.state)

    for _key in (
        "company_profile", "tenders_raw", "tenders_found",
        "eligibility_results", "reliability_report",
    ):
        ctx.state.setdefault(_key, "")

    combined_text = company_url
    if config.pii_redaction_enabled:
        cleaned = re.sub(r'\b\d{8}\b', '[COMPANY_REG]', combined_text)
        cleaned = re.sub(r'£[\d,]+', '[AMOUNT]', cleaned)
        cleaned = re.sub(r'\b[A-Z]{1,2}\d{1,2}[A-Z]?\s?\d[A-Z]{2}\b', '[POSTCODE]', cleaned)
        cleaned = re.sub(
            r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+', '[EMAIL]', cleaned
        )
    else:
        cleaned = combined_text

    injection_keywords = [
        "ignore previous", "jailbreak", "forget instructions",
        "system prompt", "ignore above", "disregard",
        "override instructions", "new instructions",
    ]
    injection_found = (
        config.injection_detection_enabled
        and any(kw in cleaned.lower() for kw in injection_keywords)
    )

    _audit_event(
        ctx.state,
        "SECURITY_INJECTION_DETECTED" if injection_found else "CHECKPOINT_PASSED",
        "CRITICAL" if injection_found else "INFO",
    )

    if injection_found:
        return types.Content(
            role="model",
            parts=[types.Part(text=(
                "Request blocked by TenderBot security checkpoint. "
                "This run has been stopped and logged."
            ))],
        )

    if company_url and not _domain_allowed(company_url, company_url):
        _audit_event(ctx.state, "SECURITY_DOMAIN_REJECTED", "CRITICAL")
        return types.Content(
            role="model",
            parts=[types.Part(text=(
                "Request blocked by TenderBot security checkpoint: "
                f"company URL domain is not whitelisted ({company_url})."
            ))],
        )
    return None


def _company_profiler_after(callback_context):
    """Ensure company_profile and company_checklist survive LLM relay."""
    _restore_json_state(callback_context.state, "company_profile", "_profile_tool")
    profile = _parse_profile_from_state(callback_context.state.get("company_profile", ""))
    if not profile and isinstance(callback_context.state.get("_profile_tool"), dict):
        profile = callback_context.state["_profile_tool"]
        callback_context.state["company_profile"] = json.dumps(profile)
    checklist = _generate_checklist_from_profile(profile)
    callback_context.state["company_checklist"] = checklist
    _optional_persist_checklist(checklist)
    generated = bool(profile) and (
        bool(profile.get("services"))
        or profile.get("cqc_rating") not in (None, "", "not stated")
        or bool(profile.get("coverage_areas"))
        or bool(profile.get("certifications"))
    )
    _merge_pipeline_debug(
        callback_context.state,
        {"company_checklist_from_profile": generated},
    )
    if _pipeline_debug_active():
        _log_pipeline_debug(
            f"company_checklist generated from profile: {generated} "
            f"(services={len(checklist.get('services', []))}, "
            f"cqc={checklist.get('cqc_rating')})"
        )
    return None


def _compact_profile_summary(profile_raw) -> str:
    """Token-light profile hint for discovery (coverage + services only)."""
    profile = _parse_profile_from_state(profile_raw)
    if not profile:
        return "not stated"
    areas = profile.get("coverage_areas") or []
    services = profile.get("services") or []
    bits = []
    if areas:
        bits.append("coverage: " + ", ".join(str(a) for a in areas[:6]))
    if services:
        bits.append("services: " + ", ".join(str(s) for s in services[:6]))
    return "; ".join(bits) if bits else "not stated"


# ---------------------------------------------------------------------
# AGENT 0 — Company Profiler (scrapes the real website)
# ---------------------------------------------------------------------
company_profiler = Agent(
    name="company_profiler",
    model=llm,
    instruction=(
        "You are TenderBot's Company Profile Agent.\n"
        "Company website URL: {company_url}\n"
        "If company_profile is already in state, output that JSON only. "
        "Otherwise call fetch_company_profile once, then output its JSON."
    ),
    tools=[fetch_company_profile, generate_company_checklist],
    output_key="company_profile",
    before_agent_callback=_company_profiler_before,
    after_agent_callback=_company_profiler_after,
    before_model_callback=_smart_before_model,
)

# ---------------------------------------------------------------------
# AGENT 1 — Tender Discovery (Search Stage)
# ---------------------------------------------------------------------
def tender_discovery_instruction(ctx: ReadonlyContext) -> str:
    summary = _compact_profile_summary(ctx.state.get("company_profile", ""))
    return (
        "You are TenderBot's Tender Discovery Agent.\n"
        f"Company coverage hint: {summary}\n"
        "If tenders_raw is already populated, output that JSON array only. "
        "Otherwise call search_tender_portals once and output its candidates array verbatim."
    )


tender_discovery = Agent(
    name="tender_discovery",
    model=llm,
    instruction=tender_discovery_instruction,
    tools=[search_tender_portals],
    output_key="tenders_raw",
    before_agent_callback=_tender_discovery_before,
    after_agent_callback=_tender_discovery_after_agent,
    before_model_callback=_smart_before_model,
    after_tool_callback=_tender_discovery_after_tool,
)

# ---------------------------------------------------------------------
# AGENT 1.5 — Tender Crawler (Deep Scraping & Filtering Stage)
# ---------------------------------------------------------------------
def tender_crawler_instruction(ctx: ReadonlyContext) -> str:
    company_url = str(ctx.state.get("company_url", ""))
    return (
        "You are TenderBot's Tender Crawler Agent.\n"
        "If tenders_found is already populated, output that JSON array only. "
        "Otherwise call crawl_tender_notices once with tenders_raw and "
        f"company_url={json.dumps(company_url)}."
    )


tender_crawler = Agent(
    name="tender_crawler",
    model=llm,
    instruction=tender_crawler_instruction,
    tools=[crawl_tender_notices],
    output_key="tenders_found",
    before_agent_callback=_tender_crawler_before,
    before_model_callback=_smart_before_model,
    after_tool_callback=_tender_crawler_after_tool,
    after_agent_callback=_tender_crawler_after_agent,
)

# ---------------------------------------------------------------------
# AGENT 2 — Eligibility Checker (Strictly Evaluating 8 Criteria)
# ---------------------------------------------------------------------
def _eligibility_instruction(ctx: ReadonlyContext) -> str:
    tenders = [
        _slim_tender_for_llm(t)
        for t in _parse_tenders_list(ctx.state.get("tenders_found", ""))
    ]
    checklist = ctx.state.get("company_checklist", {})
    if isinstance(checklist, str):
        checklist = _parse_json_blob(checklist) if checklist.strip() else {}
    return (
        "You are TenderBot's Eligibility Checker.\n\n"
        f"Company checklist: {json.dumps(checklist)}\n"
        f"Active tenders ({len(tenders)}): {json.dumps(tenders)}\n\n"
        "Evaluate each tender using MANDATORY criteria only:\n"
        "1. Active submission deadline (deadline_status open/unverified = pass)\n"
        "2. Service compatibility with company services\n"
        "3. Geographic coverage vs office_locations\n"
        "4. CQC requirement vs company cqc_rating\n"
        "5. Required certifications vs company certifications\n"
        "6. Mandatory tender requirements vs company capability\n\n"
        "DECISION SUPPORT ONLY (never cause Not Eligible): estimated_value, "
        "hourly_rate, quality_price_weighting, contract duration.\n"
        "Record those in criteria_results as informational notes only.\n\n"
        "VERDICT RULES:\n"
        "- Not Eligible ONLY when a mandatory criterion clearly fails\n"
        "- Partial when mandatory info is missing or match is uncertain\n"
        "- Eligible when mandatory criteria are met with evidence\n"
        "- Missing fields -> unverifiable on that criterion, not automatic fail\n"
        "- Never fail on budget, rate, quality weighting, or duration alone\n\n"
        "Output JSON array only. Each item:\n"
        '{"reference_number","title","verdict":"Eligible"|"Partial"|"Not Eligible",'
        '"bid_readiness_score":0-100,"criteria_results":{service_alignment,'
        "cqc_registration_match,lot_geography,certifications,deadline_feasibility,"
        'mandatory_requirements,decision_support_notes},"gaps":[],"recommendation":"..."}'
    )


eligibility_checker = Agent(
    name="eligibility_checker",
    model=llm,
    instruction=_eligibility_instruction,
    output_key="eligibility_results",
    before_agent_callback=_eligibility_before,
    before_model_callback=_smart_before_model,
)

# ---------------------------------------------------------------------
# AGENT 3 — Evaluation Agent
# ---------------------------------------------------------------------
def _evaluation_instruction(ctx: ReadonlyContext) -> str:
    funnel = _pipeline_funnel_summary(ctx.state)
    _, n_actionable, n_eligibility = _pipeline_funnel_counts(ctx.state)
    return (
        "You are TenderBot's Evaluation Agent.\n\n"
        f"PIPELINE FUNNEL (authoritative):\n{funnel}\n\n"
        "Eligibility results: {eligibility_results}\n\n"
        "IMPORTANT:\n"
        "- Only the actionable tenders in tenders_found were sent to eligibility.\n"
        "- Discovery candidates excluded before filtering are intentional, NOT failures.\n"
        "- Do NOT write that eligibility skipped or failed to evaluate discovery-only tenders.\n"
        "- Do NOT compare eligibility results against the full discovery list.\n"
        f"- Confirm eligibility evaluated {n_eligibility}/{n_actionable} actionable tenders.\n\n"
        "Verify mandatory criteria were used correctly; budget/rate/quality "
        "must not have driven Not Eligible verdicts. Rank actionable tenders by "
        "bid_readiness_score in reviewer_notes.\n"
        "Output JSON: reliability_score, issues_found, overall_confidence, reviewer_notes."
    )


evaluation_agent = Agent(
    name="evaluation_agent",
    model=llm,
    instruction=_evaluation_instruction,
    output_key="reliability_report",
    before_model_callback=_smart_before_model,
)

# ---------------------------------------------------------------------
# AGENT 4 — Report Generator (calls MCP save_report tool)
# ---------------------------------------------------------------------
mcp_toolset = MCPToolset(
    connection_params=StdioConnectionParams(
        server_params=MCPStdioParams(
            command="uv",
            args=["run", "python", "-m", "app.mcp_server"],
        ),
        timeout=30,
    )
)

def _report_instruction(ctx: ReadonlyContext) -> str:
    funnel = _pipeline_funnel_summary(ctx.state)
    _, n_actionable, n_eligibility = _pipeline_funnel_counts(ctx.state)
    tenders = [
        _slim_tender_for_llm(t)
        for t in _parse_tenders_list(ctx.state.get("tenders_found", ""))
    ]
    return (
        "You are TenderBot's Report Generator.\n\n"
        f"PIPELINE FUNNEL:\n{funnel}\n\n"
        f"Active tenders ({len(tenders)}): {json.dumps(tenders)}\n"
        "Eligibility results: {eligibility_results}\n"
        "Reliability report: {reliability_report}\n\n"
        "Write a concise business-friendly markdown report (2-5 pages).\n\n"
        "## Section A — Executive Summary\n"
        "Start with these exact pipeline bullets (use the counts above):\n"
        "- Discovery: <N> candidate tenders found\n"
        "- Filtering: <N> actionable tenders selected (after deadline/status filtering)\n"
        f"- Eligibility: {n_eligibility}/{n_actionable} actionable tenders evaluated\n"
        "Then add: Eligible count, Partial count, Not Eligible count, overall recommendation.\n"
        "Do NOT describe discovery-only tenders as unevaluated pipeline failures.\n\n"
        "## Section B — Tender Evaluation\n"
        "For EACH actionable tender use short bullets (not long paragraphs):\n"
        "- Tender Title, Contracting Authority, Submission Deadline "
        "(use the value provided, or 'Deadline not stated')\n"
        "- Geographic Coverage, Services Required, Contract Lot(s)\n"
        "- Eligibility Status (Eligible/Partial/Not Eligible)\n"
        "- Short evidence-based explanation\n"
        "- Key Strengths, Key Gaps, Recommended Next Steps\n"
        "- Info only (if stated): Estimated Value, Hourly Rate, Quality vs Price, "
        "Submission Portal\n\n"
        "## Section C — Bid Readiness Checklist\n"
        "Concise bullets: missing certs, registrations, docs, capacity, geography.\n\n"
        "Call save_report with the full markdown. Optionally save_report_to_drive."
    )


report_generator = Agent(
    name="report_generator",
    model=llm,
    instruction=_report_instruction,
    tools=[mcp_toolset],
    output_key="final_report",
    before_model_callback=_smart_before_model,
    after_agent_callback=_report_generator_after_agent,
)

root_agent = SequentialAgent(
    name="root_agent",
    sub_agents=[
        company_profiler,
        tender_discovery,
        tender_crawler,
        eligibility_checker,
        evaluation_agent,
        report_generator,
    ],
    before_agent_callback=security_checkpoint,
)

app = App(
    root_agent=root_agent,
    name="app",
)