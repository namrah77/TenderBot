# TenderBot — UK Care Tender Intelligence Agent

## What This Is
Autonomous AI procurement agent for UK domiciliary/home care providers.
Input is any company website URL via session state. Searches public UK tender
portals, checks eligibility against an auto-generated checklist, produces a
ranked feasibility report. Track: Agents for Business.

## Pipeline (sequential)
Security Checkpoint → Company Profiler → Tender Discovery →
Tender Crawler → Eligibility Checker → Evaluation Agent →
Report Generator → MCP Server (save_report)

## Agents
1. Company Profiler — scrapes the session `company_url`, extracts profile/checklist
2. Tender Discovery — searches Find a Tender + Contracts Finder
3. Tender Crawler — deep-scrapes notices, keeps up to 4 actionable tenders
4. Eligibility Checker — mandatory-criteria verdicts per actionable tender
5. Evaluation Agent — reliability review of eligibility output
6. Report Generator — markdown report + MCP save_report

## Stack Rules (NEVER violate these)
- ADK 2.0 style: from google.adk.agents import Agent
- Model: gemini-2.5-flash (NEVER gemini-1.5-* or gemini-flash-latest)
- GOOGLE_GENAI_USE_VERTEXAI=False (Gemini API key only, no Vertex AI)
- NO google.auth.default() calls
- Load keys via python-dotenv from .env
- No duplicate edges in workflow graph
- Use ctx.state for all inter-agent data passing

## agent_dir = app

---

## Development Commands

### Windows (Application Control)

If `agents-cli playground` fails with `Application Control policy has blocked this file (os error 4551)`, run once after `uv sync`:

```powershell
uv run python scripts/install_windows_adk_shim.py
```

This replaces the blocked `adk.exe` wrapper with an `adk.cmd` shim so `agents-cli playground` and other `uv run adk` commands work.

| Command | Purpose |
|---------|---------|
| `agents-cli playground` | Interactive local testing |
| `uv run pytest tests/unit tests/integration` | Run unit and integration tests |
| `agents-cli eval generate` | Run agent on eval dataset, produce traces |
| `agents-cli eval grade` | Run evaluations on traces |
| `agents-cli eval compare` | Regression check between two runs |
| `agents-cli eval analyze` | Cluster failure modes |
| `agents-cli eval optimize` | Auto-tune agent prompts |
| `agents-cli lint` | Check code quality |
| `agents-cli deploy` | Deploy to dev (requires human approval) |

## Operational Rules
- Only modify code directly targeted by the request. Preserve everything else.
- NEVER change the model unless explicitly asked.
- Model 404 errors: fix GOOGLE_CLOUD_LOCATION (use "global"), not the model name.
- ADK tool imports: import the instance, not the module.
- Run Python with uv: `uv run python script.py`
- Stop on repeated errors: if same error 3+ times, fix root cause.