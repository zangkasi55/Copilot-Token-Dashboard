import json
import hashlib
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from copilot_token_dashboard.deploy import configured_model, source_settings
from copilot_token_dashboard.schema import TABLES, read_table, write_tables

ROOT = Path(__file__).resolve().parents[1]


def test_csv_configuration_uses_an_absolute_folder(tmp_path, monkeypatch):
    data = tmp_path / "gold"
    data.mkdir()
    monkeypatch.chdir(tmp_path)
    values = source_settings("CSV", Path("gold"))
    assert values["DataFolder"] == str(data)


@pytest.mark.parametrize("folder", [
    "https://tenant.sharepoint.com/sites/AI-other/Gold/",
    "https://another.sharepoint.com/sites/AI/Gold/",
    "https://tenant.sharepoint.com/sites/AI/Gold",
    "https://tenant.sharepoint.com/sites/AI/../Other/",
])
def test_sharepoint_requires_the_exact_site_folder(tmp_path, folder):
    with pytest.raises(ValueError):
        source_settings("SharePoint", tmp_path, "https://tenant.sharepoint.com/sites/AI", folder)


def test_sharepoint_accepts_an_exact_folder_and_preserves_encoding(tmp_path):
    site = "https://tenant.sharepoint.com/sites/AI"
    folder = site + "/Shared%20Documents/Gold/"
    values = source_settings("SharePoint", tmp_path, site, folder)
    assert values["SharePointFolder"] == folder


def test_configured_model_preserves_parameter_metadata_without_editing_source(tmp_path):
    project = tmp_path / "project"
    model = project / "Copilot Token Dashboard.SemanticModel" / "model.bim"
    model.parent.mkdir(parents=True)
    model.write_text(json.dumps({"model": {"expressions": [
        {"name": name, "expression": '"" meta [IsParameterQuery=true]'}
        for name in ("SourceMode", "DataFolder", "SharePointSite", "SharePointFolder")
    ]}}), encoding="utf-8")
    site = "https://tenant.sharepoint.com/sites/AI"
    configured = configured_model(project, "SharePoint", tmp_path, site, site + "/Gold/")
    expressions = {item["name"]: item["expression"] for item in configured["model"]["expressions"]}
    assert expressions["SourceMode"] == '"SharePoint" meta [IsParameterQuery=true]'
    assert expressions["DataFolder"].startswith('"' + str(tmp_path) + '" meta ')
    assert json.loads(model.read_text(encoding="utf-8"))["model"]["expressions"][0]["expression"].startswith('""')


def shell_literal(value: Path | str) -> str:
    return "'" + str(value).replace("'", "''") + "'"


def run_installer(tmp_path, arguments):
    executable = shutil.which("pwsh")
    if not executable:
        pytest.skip("PowerShell 7 is required for the Windows installer integration test")
    launch = tmp_path / "opened.txt"
    wrapper = tmp_path / "test-install.ps1"
    wrapper.write_text(
        "$ErrorActionPreference = 'Stop'\n"
        "function Start-Process { param([string]$FilePath) "
        + "Set-Content -LiteralPath " + shell_literal(launch) + " -Value $FilePath }\n"
        + "Set-Location -LiteralPath " + shell_literal(tmp_path) + "\n"
        + "& " + shell_literal(ROOT / "Install.ps1") + " " + arguments + "\n",
        encoding="utf-8",
    )
    result = subprocess.run(
        [executable, "-NoProfile", "-NonInteractive", "-File", str(wrapper)],
        text=True, encoding="utf-8", capture_output=True, timeout=60,
    )
    return result, launch


def customer_fixture(tmp_path):
    tables = {name: read_table(ROOT / "sample_data", name) for name in TABLES}
    tables["Settings"][0]["IsDemo"] = False
    for name, column in (("People", "UPN"), ("Accounts", "UPN"), ("ScopeAccess", "ViewerUPN")):
        for row in tables[name]:
            if row[column]:
                row[column] = row[column].replace("example.com", "customer.example")
    data = tmp_path / "gold"
    write_tables(data, tables)
    return data


def test_local_csv_installer_copies_and_configures_without_launching_desktop(tmp_path):
    data = customer_fixture(tmp_path)
    destination = tmp_path / "installed"
    result, launch = run_installer(
        tmp_path, "-Action Local -SourceMode CSV -DataFolder 'gold' -InstallFolder " + shell_literal(destination))
    assert result.returncode == 0, result.stderr
    model = json.loads((destination / "powerbi" / "Copilot Token Dashboard.SemanticModel" / "model.bim").read_text(encoding="utf-8"))
    values = {item["name"]: item["expression"] for item in model["model"]["expressions"]}
    assert values["SourceMode"].startswith('"CSV" meta ')
    assert values["DataFolder"].startswith('"' + str(data) + '" meta ')
    assert launch.read_text().strip() == str(destination / "powerbi" / "Copilot Token Dashboard.pbip")


def test_local_sharepoint_configuration_fails_before_copying(tmp_path):
    customer_fixture(tmp_path)
    destination = tmp_path / "invalid-install"
    result, launch = run_installer(
        tmp_path, "-Action Local -SourceMode SharePoint -DataFolder 'gold' -InstallFolder "
        + shell_literal(destination))
    assert result.returncode != 0
    assert "Source configuration validation failed" in result.stderr
    assert not destination.exists()
    assert not launch.exists()


def test_local_install_does_not_overwrite_an_existing_directory(tmp_path):
    destination = tmp_path / "existing"
    destination.mkdir()
    sentinel = destination / "keep.txt"
    sentinel.write_text("existing installation", encoding="utf-8")
    result, launch = run_installer(
        tmp_path, "-Action Local -SourceMode Demo -InstallFolder " + shell_literal(destination))
    assert result.returncode != 0
    assert "already exists" in result.stderr
    assert sentinel.read_text() == "existing installation"
    assert not launch.exists()


@pytest.mark.parametrize("matches", [True, False])
def test_thai_manual_checksum_command_is_executable_and_rejects_mismatch(tmp_path, matches):
    executable = shutil.which("pwsh")
    if not executable:
        pytest.skip("PowerShell 7 is required to execute the Thai manual checksum command")
    document = (ROOT / "docs" / "INSTALLATION_TH.md").read_text(encoding="utf-8")
    section = document.split("### 3.1", 1)[1]
    command = re.search(r"```powershell\n(.*?)\n```", section, re.DOTALL).group(1)
    archive = tmp_path / "Copilot-Token-Dashboard-1.0.1-Install.zip"
    archive.write_bytes(b"synthetic checksum validation input")
    digest = hashlib.sha256(archive.read_bytes()).hexdigest() if matches else "0" * 64
    sums = tmp_path / "SHA256SUMS.txt"
    sums.write_text(digest + "  " + archive.name + "\n", encoding="utf-8")
    lines = command.splitlines()
    lines[0] = "$zip = " + shell_literal(archive)
    lines[1] = "$sums = " + shell_literal(sums)
    command = "\n".join(line for line in lines if not line.startswith("Expand-Archive "))
    script = tmp_path / "check-document.ps1"
    script.write_text("$ErrorActionPreference='Stop'\n" + command, encoding="utf-8")
    result = subprocess.run(
        [executable, "-NoProfile", "-NonInteractive", "-File", str(script)],
        text=True, encoding="utf-8", capture_output=True, timeout=30,
    )
    if matches:
        assert result.returncode == 0, result.stderr
        assert "SHA256 PASS" in result.stdout
    else:
        assert result.returncode != 0
        assert "Checksum mismatch" in result.stderr
        assert "SHA256 PASS" not in result.stdout
