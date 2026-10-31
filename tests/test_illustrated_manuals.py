import hashlib
import json
import shutil
from pathlib import Path

import pytest

from tools.build_sample_dashboard import PAGE_IDS, build, sample_payload

ROOT = Path(__file__).resolve().parents[1]


def test_companion_matches_the_shipped_ten_pages():
    payload = sample_payload(ROOT / "sample_data", ROOT / "powerbi")
    assert payload["isSynthetic"] is True
    assert [page["id"] for page in payload["pages"]] == PAGE_IDS
    assert payload["minimumGroupSize"] >= 6
    assert payload["viewer"] == "user01@example.com"
    assert "Not a verified Power BI screenshot" in payload["provenance"]


def test_illustrated_figures_reconcile_to_public_sample_tables():
    payload = sample_payload(ROOT / "sample_data", ROOT / "powerbi")
    snapshot = payload["snapshots"]["demo-engineering|Last 28 days"]
    assert snapshot["summary"]["Amount"] == pytest.approx(468.48)
    assert snapshot["summary"]["MemberCount"] == 12
    assert sum(row["Amount"] or 0 for row in snapshot["surfaces"]) == pytest.approx(468.48)
    assert payload["fixedPersonalSpend"] == {"7 days": 34.0, "28 days": 39.04, "Month to date": 39.04}
    assert all(scope["key"] != "demo-small" for scope in payload["scopes"])
    assert any(row["Status"] == "Not reported" for row in payload["coverage"])


def test_screenshot_provenance_records_the_input_hashes():
    payload = sample_payload(ROOT / "sample_data", ROOT / "powerbi")
    for name, digest in payload["sourceHashes"].items():
        assert hashlib.sha256((ROOT / "sample_data" / name).read_bytes()).hexdigest() == digest


def test_customer_data_cannot_be_rendered_into_public_manuals(tmp_path):
    data = tmp_path / "data"
    shutil.copytree(ROOT / "sample_data", data)
    settings = data / "Settings.csv"
    settings.write_text(settings.read_text(encoding="utf-8").replace("True,", "False,"), encoding="utf-8")
    with pytest.raises(ValueError, match="synthetic"):
        sample_payload(data, ROOT / "powerbi")


def test_generated_html_is_offline_and_theme_complete(tmp_path):
    output = tmp_path / "sample.html"
    result = build(ROOT / "sample_data", ROOT / "powerbi", output)
    html = output.read_text(encoding="utf-8")
    assert result["pages"] == 10
    assert "@@DATA@@" not in html and "@@THEME@@" not in html
    assert '<script src=' not in html and "<link " not in html
    assert "fetch(" not in html and "XMLHttpRequest" not in html
    assert "--cp-accent: #b11f4b;" in html
    assert '--cp-accent: #fd8ea1;' in html
    assert html.index('new URLSearchParams(window.location.search)') < html.index("const DATA")
    start = html.index('<script id="sample-data" type="application/json">')
    start = html.index(">", start) + 1
    payload = json.loads(html[start:html.index("</script>", start)])
    assert payload["isSynthetic"] is True


def test_manual_images_have_relative_existing_targets():
    import re
    for filename in ("INSTALLATION.md", "INSTALLATION_TH.md", "SAMPLE_DASHBOARD.md"):
        path = ROOT / "docs" / filename
        assert path.is_file(), f"Missing illustrated manual {filename}"
        for target in re.findall(r"!\[[^\]]*\]\(([^)]+)\)", path.read_text(encoding="utf-8")):
            assert not target.startswith(("http:", "https:", "file:"))
            assert (path.parent / target).is_file(), f"{filename}: missing screenshot {target}"
