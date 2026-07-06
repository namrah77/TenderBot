"""Unit tests for deterministic company name and deadline extractors."""
import json

from bs4 import BeautifulSoup

from app.agent import (
    _extract_company_name,
    _extract_submission_deadline,
    _format_submission_deadline,
    _pipeline_funnel_counts,
    _pipeline_funnel_summary,
)

_SAMPLE_URL = "https://example-care.co.uk"
_SAMPLE_NAME = "Example Care Co"


def test_company_name_from_json_ld():
    html = f"""
    <html><head>
    <script type="application/ld+json">
    {{"@context":"https://schema.org","@graph":[
      {{"@type":"Organization","name":"{_SAMPLE_NAME}","url":"{_SAMPLE_URL}"}}
    ]}}
    </script>
    <meta property="og:site_name" content="{_SAMPLE_NAME}"/>
    <title>Trusted Homecare | {_SAMPLE_NAME}</title>
    </head><body>
    <a href="#main">Skip to content</a>
    <h1>Best Home Care Services</h1>
    </body></html>
    """
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(separator="\n", strip=True)
    assert _extract_company_name(text, _SAMPLE_URL, soup=soup) == _SAMPLE_NAME


def test_company_name_ignores_skip_to_content_without_schema():
    page = f"Skip to content\nMenu\n{_SAMPLE_NAME}\nHome Care Services"
    assert _extract_company_name(page, _SAMPLE_URL) == "Example Care Co"


def test_deadline_from_find_a_tender_h4_pattern():
    html = """
    <html><body>
    <h4 class="govuk-heading-s">IV.2.2) Time limit for receipt of tenders or requests to participate</h4>
    <p class="govuk-body-s">Local time zone</p>
    <p class="govuk-body">24 July 2026</p>
    </body></html>
    """
    soup = BeautifulSoup(html, "html.parser")
    assert _extract_submission_deadline("", soup=soup) == "24 July 2026"
    assert _format_submission_deadline("24 July 2026") == "24 July 2026"
    assert _format_submission_deadline("not stated") == "Deadline not stated"


def test_deadline_from_json_ld_end_date():
    html = """
    <script type="application/ld+json">
    {"@type":"Event","name":"Tender","endDate":"2026-07-24"}
    </script>
    """
    soup = BeautifulSoup(html, "html.parser")
    assert _extract_submission_deadline("", soup=soup) == "24 July 2026"


def test_pipeline_funnel_summary_wording():
    state = {
        "_discovery_candidates": [{"title": f"T{i}"} for i in range(10)],
        "tenders_found": json.dumps([{"title": f"A{i}"} for i in range(4)]),
        "eligibility_results": json.dumps([{"title": f"A{i}"} for i in range(4)]),
    }
    summary = _pipeline_funnel_summary(state)
    assert "Discovery: 10 candidate tenders found" in summary
    assert "Filtering: 4 actionable tenders selected" in summary
    assert "6 excluded before eligibility" in summary
    assert "Eligibility: 4/4 actionable tenders evaluated" in summary
    assert _pipeline_funnel_counts(state) == (10, 4, 4)
