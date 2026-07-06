# TenderBot — Secure Coding Standards

## Security Rules (enforce on every code change)
- All user input MUST pass through security_checkpoint before
  reaching any LlmAgent — no exceptions
- Never hardcode API keys, credentials, or secrets anywhere
- Never log or expose raw user input — only log sanitised versions
- All external HTTP calls must be to explicitly whitelisted domains only:
  the session `company_url` host (dynamic), find-tender.service.gov.uk,
  findatender.service.gov.uk, contractsfinder.service.gov.uk, and
  approved submission portals (see `_SUBMISSION_PORTAL_SUFFIXES` in `agent.py`)
- Function nodes must always return a string route — never None

## STRIDE Threat Model for TenderBot
- Spoofing: mitigated by PII redaction in security_checkpoint
- Tampering: mitigated by read-only ctx.state access pattern
- Repudiation: mitigated by audit_log written on every call
- Information Disclosure: mitigated by never exposing ctx.state to UI
- Denial of Service: mitigated by max_iterations=3 in config.py
- Elevation of Privilege: mitigated by injection detection keywords

## Guardrails
- Agents must never fabricate data — missing fields = "not stated"
- Max 3 retries on any tool call — log and stop on failure
- System prompts must stay under 300 words each
- Use ctx.state for inter-agent data — never repeat large data in prompts
