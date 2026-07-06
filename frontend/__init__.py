"""TenderBot frontend package — Streamlit presentation layer only.

Nothing in this package talks to models, tools, or the ADK pipeline
directly except ``frontend.pipeline``, which simply invokes the existing
``app.agent.root_agent`` exactly as the original dashboard did. No agent
or backend logic lives here.
"""
