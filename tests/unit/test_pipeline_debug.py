"""Unit tests for PIPELINE_DEBUG instrumentation (offline)."""
import json
from types import SimpleNamespace

from app.agent import (
    _company_profiler_after,
    _debug_after_tool,
    _eligibility_before,
    _empty_pipeline_debug,
    _merge_pipeline_debug,
    _print_pipeline_debug_summary,
    search_tender_portals,
    security_checkpoint,
)
from app.config import config


def test_debug_disabled_by_default():
    original = config.pipeline_debug
    config.pipeline_debug = False
    try:
        result = search_tender_portals("home care")
        assert "_pipeline_debug" not in result
    finally:
        config.pipeline_debug = original


def test_security_checkpoint_seeds_debug_dict_when_enabled():
    original = config.pipeline_debug
    config.pipeline_debug = True
    try:
        ctx = SimpleNamespace(state={"company_url": "https://example-care.co.uk"})
        security_checkpoint(ctx)
        assert "pipeline_debug" in ctx.state
        assert ctx.state["pipeline_debug"]["gemini_calls"] == 0
    finally:
        config.pipeline_debug = original


def test_merge_and_after_tool_strips_internal_key():
    original = config.pipeline_debug
    config.pipeline_debug = True
    try:
        state = {"pipeline_debug": _empty_pipeline_debug()}
        tool_ctx = SimpleNamespace(state=state)
        raw = {
            "candidates": [],
            "_pipeline_debug": {
                "sources": {"contracts_finder": 3, "find_a_tender": 7},
                "discovery_deduped": 10,
                "discovery_returned": 10,
            },
        }
        cleaned = _debug_after_tool(None, {}, tool_ctx, raw)
        assert "_pipeline_debug" not in cleaned
        assert state["pipeline_debug"]["sources"]["contracts_finder"] == 3
        assert state["pipeline_debug"]["discovery_deduped"] == 10
    finally:
        config.pipeline_debug = original


def test_company_profiler_after_flags_checklist_generation():
    original = config.pipeline_debug
    config.pipeline_debug = True
    try:
        profile = {"services": ["Home Care"], "cqc_rating": "Good", "coverage_areas": ["London"]}
        ctx = SimpleNamespace(state={
            "company_profile": json.dumps(profile),
            "pipeline_debug": _empty_pipeline_debug(),
        })
        _company_profiler_after(ctx)
        assert ctx.state["pipeline_debug"]["company_checklist_from_profile"] is True
        assert ctx.state["company_checklist"]["services"] == ["Home Care"]
    finally:
        config.pipeline_debug = original


def test_eligibility_before_counts_tenders_found():
    original = config.pipeline_debug
    config.pipeline_debug = True
    try:
        ctx = SimpleNamespace(state={
            "tenders_found": json.dumps([{"title": "A"}, {"title": "B"}]),
            "pipeline_debug": _empty_pipeline_debug(),
        })
        _eligibility_before(ctx)
        assert ctx.state["pipeline_debug"]["eligibility_input_count"] == 2
    finally:
        config.pipeline_debug = original


def test_print_summary_does_not_crash(capsys):
    original = config.pipeline_debug
    config.pipeline_debug = True
    try:
        state = {
            "pipeline_debug": {
                **_empty_pipeline_debug(),
                "sources": {"contracts_finder": 2, "find_a_tender": 5},
                "discovery_deduped": 7,
                "crawl_open_count": 3,
                "eligibility_input_count": 3,
                "company_checklist_from_profile": True,
                "gemini_calls": 6,
            }
        }
        _print_pipeline_debug_summary(state)
        out = capsys.readouterr().out
        assert "Pipeline debug summary" in out
        assert "Gemini calls" in out
    finally:
        config.pipeline_debug = original
