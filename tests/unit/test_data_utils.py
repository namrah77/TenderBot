"""Deterministic unit tests for the pure data helpers that shape every
agent output before it reaches the UI. These run fully offline (no model,
no network) so they double as a fast regression suite for judges."""
from frontend.data_utils import (
    parse_json_field,
    verdict_tone,
    readiness_tone,
    confidence_tone,
    derive_confidence,
    is_recommended,
    matched_services,
    build_next_actions,
)


class TestParseJsonField:
    def test_parses_fenced_json_array(self):
        raw = '```json\n[{"title": "Home Care Framework"}]\n```'
        assert parse_json_field(raw, []) == [{"title": "Home Care Framework"}]

    def test_parses_plain_json_object(self):
        assert parse_json_field('{"company_name": "Example Care Co"}', {}) == {
            "company_name": "Example Care Co"
        }

    def test_extracts_json_embedded_in_prose(self):
        raw = 'Here is the result: [{"verdict": "Eligible"}] — done.'
        assert parse_json_field(raw, []) == [{"verdict": "Eligible"}]

    def test_none_returns_fallback(self):
        assert parse_json_field(None, {"fallback": True}) == {"fallback": True}

    def test_garbage_returns_fallback(self):
        assert parse_json_field("not json at all", []) == []

    def test_passthrough_when_already_parsed(self):
        data = [{"a": 1}]
        assert parse_json_field(data, []) is data


class TestTones:
    def test_verdict_tone(self):
        assert verdict_tone("Eligible") == "success"
        assert verdict_tone("Partial") == "warning"
        assert verdict_tone("Not Eligible") == "risk"
        assert verdict_tone("???") == "muted"

    def test_readiness_tone_bands(self):
        assert readiness_tone(85) == "success"
        assert readiness_tone(55) == "warning"
        assert readiness_tone(20) == "risk"
        assert readiness_tone("bad") == "muted"

    def test_confidence_tone(self):
        assert confidence_tone("High") == "success"
        assert confidence_tone("Low") == "risk"


class TestEligibilityHeuristics:
    def test_high_confidence_when_all_criteria_pass(self):
        entry = {
            "criteria_results": {"service_alignment": "Direct match", "rate_fit": "Within budget"},
            "gaps": [],
        }
        assert derive_confidence(entry) == "High"

    def test_low_confidence_when_many_unverifiable(self):
        entry = {
            "criteria_results": {
                "service_alignment": "unverifiable",
                "rate_fit": "not stated",
                "cqc_registration_match": "unclear",
            },
            "gaps": ["missing rate", "missing cqc", "missing certs", "missing office"],
        }
        assert derive_confidence(entry) == "Low"

    def test_is_recommended_requires_eligible_and_high_score(self):
        assert is_recommended({"verdict": "Eligible", "bid_readiness_score": 80}) is True
        assert is_recommended({"verdict": "Eligible", "bid_readiness_score": 40}) is False
        assert is_recommended({"verdict": "Partial", "bid_readiness_score": 95}) is False

    def test_matched_services_falls_back_to_first_three(self):
        checklist = {"services": ["home care", "respite", "live-in", "supported living"]}
        tender = {"title": "Cleaning contract", "lots_offered": []}
        assert matched_services(tender, checklist) == ["home care", "respite", "live-in"]

    def test_build_next_actions_includes_deadline(self):
        entry = {"recommendation": "Prepare bid", "gaps": ["No CQC evidence"]}
        tender = {"submission_deadline": "2026-08-01"}
        actions = build_next_actions(entry, tender)
        assert "Prepare bid" in actions
        assert any("2026-08-01" in a for a in actions)
