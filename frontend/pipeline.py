"""Runs the existing TenderBot agent pipeline (app.agent.root_agent) and
streams live progress into the Agent Activity Timeline. This module only
*invokes* the pipeline — it never redefines or alters agent behaviour.
"""
import os

os.environ.setdefault("GOOGLE_CLOUD_PROJECT", "dummy-project")
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "False"

from datetime import datetime

import streamlit as st
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from app.agent import root_agent

from .components import render_timeline_html
from .constants import STAGE_ORDER
from .data_utils import parse_json_field


def run_pipeline(company_url: str, timeline_slot) -> None:
    """Executes the pipeline exactly as before, but consumes the ADK
    event stream one event at a time (instead of materialising it into a
    list) so the timeline placeholder can animate as each agent in the
    SequentialAgent completes its work."""
    st.session_state.running = True
    st.session_state.pipeline_started_at = datetime.now()
    completed: set[str] = set()
    active = None
    timestamps: dict[str, str] = {}

    def draw():
        st.session_state.pipeline_progress = {
            "completed": set(completed),
            "active": active,
            "timestamps": dict(timestamps),
        }
        timeline_slot.markdown(
            render_timeline_html(completed, active, timestamps), unsafe_allow_html=True
        )

    draw()
    try:
        session_service = InMemorySessionService()
        session = session_service.create_session_sync(
            user_id="streamlit_user", app_name="tenderbot_dashboard"
        )
        session.state["company_url"] = company_url

        runner = Runner(agent=root_agent, session_service=session_service, app_name="tenderbot_dashboard")
        message = types.Content(
            role="user",
            parts=[types.Part(text=f"company_url is {company_url}. Find matching tenders and generate the full report.")],
        )

        # security_checkpoint runs inside the before_agent_callback, so it
        # has already completed by the time the first event streams back.
        timestamps["security_checkpoint"] = datetime.now().strftime("%H:%M:%S")
        completed.add("security_checkpoint")
        active = STAGE_ORDER[1]
        draw()

        for event in runner.run(new_message=message, user_id="streamlit_user", session_id=session.id):
            author = getattr(event, "author", "") or ""
            if author in STAGE_ORDER and author != active:
                idx = STAGE_ORDER.index(author)
                for s in STAGE_ORDER[:idx]:
                    completed.add(s)
                if author not in timestamps:
                    timestamps[author] = datetime.now().strftime("%H:%M:%S")
                active = author
                draw()

        completed.update(STAGE_ORDER)
        active = None
        draw()

        state = session_service.get_session_sync(
            app_name="tenderbot_dashboard",
            user_id="streamlit_user",
            session_id=session.id,
        ).state
        tenders_found = parse_json_field(state.get("tenders_found"), [])
        eligibility_results = parse_json_field(state.get("eligibility_results"), [])
        st.session_state.run_state = {
            "run_time": datetime.now().strftime("%d %b %Y, %H:%M"),
            "company_profile": parse_json_field(state.get("company_profile"), {}),
            "company_checklist": parse_json_field(state.get("company_checklist"), {}),
            "tenders_found": tenders_found,
            "eligibility_results": eligibility_results,
            "reliability_report": parse_json_field(state.get("reliability_report"), {}),
            "final_report": state.get("final_report", "No report generated."),
            "audit_log": state.get("audit_log", []),
            "pipeline_debug": state.get("pipeline_debug"),
            "stage_timestamps": timestamps,
            "company_url": company_url,
            # Distinguish "ran fine but found nothing" from a hard error, so the
            # UI can show a clean empty-state instead of a blank/again report.
            "status": "no_open_tenders" if not tenders_found else "completed",
        }
    except Exception as ex:
        st.session_state.run_state = {"error": str(ex)}
    finally:
        st.session_state.running = False
