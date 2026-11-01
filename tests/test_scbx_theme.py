import base64
import hashlib
import json
from pathlib import Path

import pytest

from copilot_token_dashboard.deploy import DISPLAY_NAME, report_parts
from tools.build_pbit_sources import build as compiler_sources
from tools.build_powerbi import PALETTE, THEME_FILE, build

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def project(tmp_path):
    path = tmp_path / "powerbi"
    build(ROOT / "sample_data", path)
    return path


def test_full_supplied_theme_settings_are_preserved():
    theme = json.loads(THEME_FILE.read_text(encoding="utf-8"))
    canonical = json.dumps(theme, sort_keys=True, separators=(",", ":")).encode()
    assert hashlib.sha256(canonical).hexdigest() == "a540b8ad2a1c0645fb446a0f4cf30b07912cc03fb950ffd27e971efba718e340"
    assert PALETTE["primary"] == "#8F47BF"
    assert PALETTE["gold"] == "#FCAF17"
    assert PALETTE["title"] == "#4B2885"
    assert PALETTE["page"] == "#F7F3FC"


def test_theme_is_registered_and_embedded_in_pbir(project):
    report = project / "Copilot Token Dashboard.Report"
    definition = json.loads((report / "definition" / "report.json").read_text())
    assert definition["themeCollection"]["customTheme"]["name"] == "SCBX_Theme"
    assert definition["themeCollection"]["customTheme"]["type"] == "RegisteredResources"
    assert definition["resourcePackages"][0]["items"] == [
        {"name": "SCBX_Theme", "path": "SCBX_Theme.json", "type": "CustomTheme"}
    ]
    assert (report / "StaticResources" / "RegisteredResources" / "SCBX_Theme.json").read_bytes() == THEME_FILE.read_bytes()


def test_every_page_has_scbx_headers_background_and_one_gold_accent(project):
    report = project / "Copilot Token Dashboard.Report" / "definition" / "pages"
    pages = list(report.glob("*/page.json"))
    assert len(pages) == 10
    for path in pages:
        page = json.loads(path.read_text())
        assert page["objects"]["background"][0]["properties"]["color"]["solid"]["color"]["expr"]["Literal"]["Value"] == "'#F7F3FC'"
        visuals = [json.loads(file.read_text()) for file in (path.parent / "visuals").glob("*/visual.json")]
        shapes = [visual for visual in visuals if visual["visual"]["visualType"] == "shape"]
        assert len(shapes) == 1
        assert shapes[0]["position"]["height"] == 4
        assert "query" not in shapes[0]["visual"]
        headers = [visual for visual in visuals if visual["position"]["y"] == 0]
        assert len(headers) == 2
        for header in headers:
            objects = header["visual"]["visualContainerObjects"]
            assert objects["background"][0]["properties"]["color"]["solid"]["color"]["expr"]["Literal"]["Value"] == "'#8F47BF'"
            assert objects["title"][0]["properties"]["fontColor"]["solid"]["color"]["expr"]["Literal"]["Value"] == "'#FFFFFF'"


def test_regeneration_does_not_duplicate_old_visuals(project):
    build(ROOT / "sample_data", project)
    manifest = json.loads((project / "build-manifest.json").read_text())
    files = list(project.glob("*.Report/definition/pages/*/visuals/*/visual.json"))
    assert manifest["variant"] == "SCBX"
    assert manifest["visualCount"] == len(files) == 156


def test_compiler_preserves_theme_resource_types_and_page_formatting(project, tmp_path):
    model = tmp_path / "model"
    model.mkdir()
    output = tmp_path / "compiler"
    compiler_sources(project, model, output)
    layout = json.loads((output / "Report" / "report.json").read_text())
    config = json.loads(layout["config"])
    assert config["themeCollection"]["customTheme"]["type"] == 1
    assert config["themeCollection"]["customTheme"]["name"] == "SCBX_Theme"
    package = layout["resourcePackages"][0]["resourcePackage"]
    assert package["type"] == 1
    assert package["items"][0]["type"] == 201
    assert (output / "StaticResources" / "RegisteredResources" / "SCBX_Theme.json").read_bytes() == THEME_FILE.read_bytes()
    for section in layout["sections"]:
        assert "background" in json.loads(section["config"])["objects"]
        for visual in section["visualContainers"]:
            if json.loads(visual["config"])["singleVisual"]["visualType"] == "shape":
                assert "query" not in visual


def test_tenant_report_definition_keeps_the_registered_theme(project):
    parts = report_parts(project, "33333333-3333-4333-8333-333333333333")
    theme = next(part for part in parts if part["path"] == "StaticResources/RegisteredResources/SCBX_Theme.json")
    assert base64.b64decode(theme["payload"]) == THEME_FILE.read_bytes()
    assert DISPLAY_NAME == "SCBX Copilot Token Dashboard"
