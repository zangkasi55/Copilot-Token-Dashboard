import json
import re
from pathlib import Path

from copilot_token_dashboard import __version__

ROOT = Path(__file__).resolve().parents[1]


def test_package_build_and_installer_versions_match():
    metadata = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert re.search(r'^version = "([^"]+)"', metadata, re.MULTILINE).group(1) == __version__
    assert json.loads((ROOT / "package.json").read_text())["version"] == __version__
    assert json.loads((ROOT / "powerbi" / "build-manifest.json").read_text())["version"] == __version__
    assert f"CopilotTokenDashboard\\{__version__}" in (ROOT / "Install.ps1").read_text()
    assert f"Copilot-Token-Dashboard-{__version__}.pbit" in (ROOT / "tools" / "Build-PowerBI.ps1").read_text()
