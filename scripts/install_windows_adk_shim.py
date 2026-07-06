"""Install a Windows-safe adk.cmd shim for Application Control policies.

Windows Application Control often blocks pip/uv console script wrappers such as
`.venv/Scripts/adk.exe` (os error 4551). The shim delegates to the already-trusted
Python interpreter via `python -m google.adk.cli`, which unblocks `uv run adk` and
`agents-cli playground`.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

SHIM_CONTENT = '@echo off\r\n"%~dp0python.exe" -m google.adk.cli %*\r\n'


def project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def install_shim() -> int:
    if os.name != "nt":
        print("No action needed on non-Windows platforms.")
        return 0

    scripts_dir = project_root() / ".venv" / "Scripts"
    adk_exe = scripts_dir / "adk.exe"
    adk_cmd = scripts_dir / "adk.cmd"
    adk_bak = scripts_dir / "adk.exe.bak"

    if not scripts_dir.is_dir():
        print("Missing .venv/Scripts. Run `uv sync` first.")
        return 1

    if adk_exe.exists():
        if adk_bak.exists():
            adk_exe.unlink()
        else:
            shutil.move(adk_exe, adk_bak)

    adk_cmd.write_text(SHIM_CONTENT, encoding="ascii")
    print(f"Installed {adk_cmd}")

    result = subprocess.run(
        ["uv", "run", "adk", "--version"],
        cwd=project_root(),
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(result.stdout, end="")
        print(result.stderr, end="", file=sys.stderr)
        print("Shim installed, but `uv run adk --version` failed.", file=sys.stderr)
        return result.returncode

    version = result.stdout.strip() or result.stderr.strip()
    print(f"Verified: uv run adk --version -> {version}")
    return 0


def main() -> int:
    return install_shim()


if __name__ == "__main__":
    raise SystemExit(main())
