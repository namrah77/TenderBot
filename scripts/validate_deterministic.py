"""Offline validation of deterministic pipeline stages (no Gemini)."""
import json
import sys

from app.agent import (
    _parse_profile_from_state,
    _parse_tenders_list,
    _seed_company_from_url,
    _seed_tenders_found,
    _seed_tenders_raw,
)


def main() -> int:
    if len(sys.argv) < 2:
        print(
            "Usage: uv run python scripts/validate_deterministic.py <company_url>",
            file=sys.stderr,
        )
        return 2
    url = sys.argv[1]
    state: dict = {"company_url": url}
    _seed_company_from_url(state, url)
    profile = _parse_profile_from_state(state.get("company_profile", ""))
    n_candidates = _seed_tenders_raw(state, profile)
    n_open = _seed_tenders_found(state, url)
    print("=== Deterministic Validation ===")
    print(f"Company profile:   {'OK' if profile else 'FAIL'}")
    print(f"Company checklist: {'OK' if state.get('company_checklist') else 'FAIL'}")
    print(f"Tender candidates: {n_candidates}")
    print(f"Open actionable:   {n_open}")
    print(f"tenders_found:   {len(_parse_tenders_list(state.get('tenders_found')))}")
    ok = bool(profile) and bool(state.get("company_checklist")) and n_open > 0
    print(f"OVERALL:           {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
