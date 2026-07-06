"""
TenderBot MCP Server.
Exposes tools for persisting the final report: one to local disk,
one to Google Drive (optional, requires service account setup).
Runs over stdio, launched automatically by ADK via MCPToolset.
"""
import json
from datetime import datetime, timezone
from pathlib import Path
from mcp.server.fastmcp import FastMCP

REPORTS_DIR = Path(__file__).resolve().parent.parent / "data" / "reports"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

mcp = FastMCP("tenderbot-mcp")


@mcp.tool()
def save_report(report_text: str) -> str:
    """Save the final TenderBot report to local disk with a timestamp.

    Args:
        report_text: The full markdown report text to save.

    Returns:
        The local file path where the report was saved.
    """
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    path = REPORTS_DIR / f"tender_report_{timestamp}.md"
    path.write_text(report_text, encoding="utf-8")
    return f"Report saved locally to {path}"


@mcp.tool()
def save_to_drive(report_text: str, file_name: str = "") -> str:
    """Upload the final report to Google Drive as a Google Doc.

    Requires a service account JSON key at app/drive_service_account.json
    and a shared Drive folder ID set in app/config.py as
    DRIVE_FOLDER_ID. If not configured, falls back to local save only.

    Args:
        report_text: The full markdown report text to upload.
        file_name: Optional custom file name (without extension).

    Returns:
        The Drive file link, or an explanation if Drive isn't configured.
    """
    from pathlib import Path as _Path
    import os as _os

    key_path = _Path(__file__).resolve().parent / "drive_service_account.json"
    folder_id = _os.getenv("DRIVE_FOLDER_ID", "")

    if not key_path.exists() or not folder_id:
        return (
            "Drive not configured (missing service account key or "
            "DRIVE_FOLDER_ID). Report was not uploaded to Drive. "
            "Use save_report for local save."
        )

    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaInMemoryUpload

        creds = service_account.Credentials.from_service_account_file(
            str(key_path), scopes=["https://www.googleapis.com/auth/drive"]
        )
        service = build("drive", "v3", credentials=creds)

        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        name = file_name or f"TenderBot_Report_{timestamp}"

        media = MediaInMemoryUpload(
            report_text.encode("utf-8"), mimetype="text/markdown"
        )
        file_metadata = {
            "name": f"{name}.md",
            "parents": [folder_id],
        }
        created = service.files().create(
            body=file_metadata, media_body=media, fields="id, webViewLink"
        ).execute()

        return f"Report uploaded to Drive: {created.get('webViewLink')}"
    except Exception as e:
        return f"Drive upload failed: {e}. Use save_report for local save."


@mcp.tool()
def save_report_to_drive(report_text: str, file_name: str = "") -> str:
    """Alias for save_to_drive to support all skill specifications.

    Args:
        report_text: The full markdown report text to upload.
        file_name: Optional custom file name (without extension).
    """
    return save_to_drive(report_text, file_name)


if __name__ == "__main__":
    mcp.run(transport="stdio")