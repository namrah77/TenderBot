"""One-shot end-to-end pipeline validation for capstone demo readiness."""
import json
import os
import sys

os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "False")

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from app.agent import root_agent
from app.config import config


def _count_list(raw) -> int:
    if isinstance(raw, list):
        return len(raw)
    if isinstance(raw, str) and raw.strip():
        try:
            data = json.loads(raw)
            return len(data) if isinstance(data, list) else 0
        except json.JSONDecodeError:
            return 0
    return 0


def main() -> int:
    if len(sys.argv) < 2:
        print(
            "Usage: uv run python scripts/validate_pipeline.py <company_url>",
            file=sys.stderr,
        )
        return 2
    company_url = sys.argv[1]
    config.pipeline_debug = os.getenv("PIPELINE_DEBUG", "").lower() in ("1", "true", "yes")

    session_service = InMemorySessionService()
    session = session_service.create_session_sync(user_id="validate", app_name="validate")
    session.state["company_url"] = company_url

    runner = Runner(agent=root_agent, session_service=session_service, app_name="validate")
    msg = types.Content(
        role="user",
        parts=[types.Part(text=f"Run full tender pipeline for {company_url}")],
    )
    list(runner.run(new_message=msg, user_id="validate", session_id=session.id))

    session = session_service.get_session_sync(
        app_name="validate", user_id="validate", session_id=session.id
    )
    state = session.state
    profile = state.get("company_profile", "")
    checklist = state.get("company_checklist", {})
    candidates = state.get("_discovery_candidates") or []
    tenders_found = state.get("tenders_found", "")
    eligibility = state.get("eligibility_results", "")
    report = state.get("final_report", "")
    dbg = state.get("pipeline_debug") or {}

    n_candidates = len(
        state.get("_discovery_candidates")
        if isinstance(state.get("_discovery_candidates"), list)
        else _count_list(state.get("tenders_raw"))
    )
    n_open = len(state.get("_crawl_tool_tenders") or []) or _count_list(tenders_found)
    n_found = _count_list(tenders_found)
    n_elig = _count_list(eligibility)
    gemini_calls = dbg.get("gemini_calls", "?")

    reports_dir = os.path.join(os.path.dirname(__file__), "..", "data", "reports")
    mcp_saved = any(f.endswith(".md") for f in os.listdir(reports_dir)) if os.path.isdir(reports_dir) else False

    print("=== Pipeline Validation ===")
    checklist_ok = bool(checklist) and checklist != {} and checklist != ""
    print(f"Company profile:        {'OK' if profile else 'FAIL'}")
    print(f"Company checklist:      {'OK' if checklist_ok else 'FAIL'}")
    print(f"Tender candidates:      {n_candidates}")
    print(f"Open actionable:        {n_open}")
    print(f"tenders_found:          {n_found}")
    print(f"Eligibility results:    {n_elig}")
    print(f"Evaluation:             {'OK' if state.get('reliability_report') else 'FAIL'}")
    print(f"Feasibility report:     {'OK' if report and len(str(report)) > 200 else 'FAIL'}")
    print(f"MCP/local save:         {'OK' if mcp_saved else 'CHECK'}")
    print(f"Gemini calls:           {gemini_calls}")

    ok = (
        bool(profile)
        and checklist_ok
        and n_found > 0
        and n_elig == n_found
        and state.get("reliability_report")
        and report
        and len(str(report)) > 200
    )
    print(f"OVERALL:                {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
