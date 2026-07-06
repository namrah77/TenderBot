"""Verify crawl tool output is persisted to tenders_found without LLM relay."""
import json
from types import SimpleNamespace

from app.agent import (
    MAX_OPEN_TENDERS,
    _eligibility_before,
    _empty_pipeline_debug,
    _tender_crawler_after_agent,
    _tender_crawler_after_tool,
)
from app.config import config
from google.adk.events.event_actions import EventActions


def _tool_context(state: dict | None = None):
    state = state or {}
    actions = EventActions()
    return SimpleNamespace(state=state, actions=actions)


def test_crawler_after_tool_writes_state_delta_and_skips_summarization():
    tenders = [{"title": f"Tender {i}", "reference_number": f"ref-{i}"} for i in range(20)]
    tool_response = {
        "tenders": tenders,
        "_pipeline_debug": {"crawl_open_count": 20},
    }
    ctx = _tool_context({"pipeline_debug": _empty_pipeline_debug()})
    original = config.pipeline_debug
    config.pipeline_debug = True
    try:
        cleaned = _tender_crawler_after_tool(
            SimpleNamespace(name="crawl_tender_notices"),
            {},
            ctx,
            tool_response,
        )
        assert "_pipeline_debug" not in (cleaned or {})
        assert ctx.actions.skip_summarization is True
        assert "tenders_found" in ctx.actions.state_delta
        stored = json.loads(ctx.actions.state_delta["tenders_found"])
        assert len(stored) == min(20, MAX_OPEN_TENDERS)
        assert ctx.state["tenders_found"] == ctx.actions.state_delta["tenders_found"]
        assert len(ctx.state["_crawl_tool_tenders"]) == min(20, MAX_OPEN_TENDERS)
    finally:
        config.pipeline_debug = original


def test_crawler_after_agent_restores_from_stash_when_state_empty():
    stash = [{"title": "Open tender", "reference_number": "abc"}]
    ctx = SimpleNamespace(state={
        "tenders_found": "",
        "_crawl_tool_tenders": stash,
    })
    _tender_crawler_after_agent(ctx)
    assert json.loads(ctx.state["tenders_found"]) == stash


def test_eligibility_sees_same_count_as_crawler_tool():
    tenders = [{"title": "A"}, {"title": "B"}, {"title": "C"}]
    tool_ctx = _tool_context({"pipeline_debug": _empty_pipeline_debug()})
    _tender_crawler_after_tool(
        SimpleNamespace(name="crawl_tender_notices"),
        {},
        tool_ctx,
        {"tenders": tenders},
    )
    elig_ctx = SimpleNamespace(state=dict(tool_ctx.state))
    original = config.pipeline_debug
    config.pipeline_debug = True
    try:
        _eligibility_before(elig_ctx)
        assert elig_ctx.state["pipeline_debug"]["eligibility_input_count"] == 3
        assert len(json.loads(elig_ctx.state["tenders_found"])) == 3
    finally:
        config.pipeline_debug = original
