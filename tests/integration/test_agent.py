# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os

import pytest
from google.adk.agents.run_config import RunConfig, StreamingMode
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from app.agent import root_agent

# The full TenderBot pipeline calls Gemini and scrapes live pages, so these
# tests need a real key and an explicit test company URL. Skip cleanly when
# either is absent — e.g. on a fresh clone or in CI without secrets configured.
requires_live_pipeline = pytest.mark.skipif(
    not os.getenv("GOOGLE_API_KEY") or not os.getenv("TEST_COMPANY_URL"),
    reason="GOOGLE_API_KEY and TEST_COMPANY_URL required for live pipeline test",
)


def _run(message_text: str, company_url: str):
    session_service = InMemorySessionService()
    session = session_service.create_session_sync(user_id="test_user", app_name="test")
    session.state["company_url"] = company_url
    runner = Runner(agent=root_agent, session_service=session_service, app_name="test")
    message = types.Content(role="user", parts=[types.Part.from_text(text=message_text)])
    events = list(
        runner.run(
            new_message=message,
            user_id="test_user",
            session_id=session.id,
            run_config=RunConfig(streaming_mode=StreamingMode.SSE),
        )
    )
    return events, session


@requires_live_pipeline
def test_pipeline_streams_events() -> None:
    """The sequential pipeline should stream at least one text event."""
    company_url = os.environ["TEST_COMPANY_URL"]
    prompt = (
        f"company_url is {company_url}. "
        "Find matching tenders and generate the full report."
    )
    events, _ = _run(prompt, company_url)
    assert events, "Expected at least one streamed event"
    assert any(
        e.content and e.content.parts and any(p.text for p in e.content.parts)
        for e in events
    ), "Expected at least one event carrying text content"


@requires_live_pipeline
def test_pipeline_produces_report_and_profile() -> None:
    """After a full run the session state should hold the domain artefacts
    the UI depends on: a company profile and a final markdown report."""
    company_url = os.environ["TEST_COMPANY_URL"]
    prompt = (
        f"company_url is {company_url}. "
        "Find matching tenders and generate the full report."
    )
    _, session = _run(prompt, company_url)
    state = session.state
    assert state.get("company_profile"), "Expected company_profile in state"
    assert state.get("final_report"), "Expected final_report in state"
    report = str(state["final_report"])
    assert "Feasibility Report" in report or "Bid Readiness" in report
