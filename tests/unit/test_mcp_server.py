"""Unit test for the MCP report-persistence tool. Confirms save_report
writes the report to disk and returns the path. Offline, no ADK runtime."""
from pathlib import Path

from app import mcp_server


def test_save_report_writes_file_to_reports_dir():
    marker = "# TenderBot unit-test report\nEligible: 1 tender.\n"
    result = mcp_server.save_report(marker)

    assert "saved" in result.lower()

    saved_path = Path(result.split("saved locally to", 1)[1].strip())
    try:
        assert saved_path.exists()
        assert saved_path.parent == mcp_server.REPORTS_DIR
        assert marker in saved_path.read_text(encoding="utf-8")
    finally:
        if saved_path.exists():
            saved_path.unlink()
