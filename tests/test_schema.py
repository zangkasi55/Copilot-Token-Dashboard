import pytest

from copilot_token_dashboard.schema import read_table


@pytest.mark.parametrize("record", [
    "True,2026-05-28,6,USD,1.0,unexpected",
    "True,2026-05-28,6,USD",
])
def test_csv_row_width_must_match_the_contract(tmp_path, record):
    (tmp_path / "Settings.csv").write_text(
        "IsDemo,AnchorDate,MinimumGroupSize,BaseCurrency,SchemaVersion\n" + record + "\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="column count"):
        read_table(tmp_path, "Settings")


def test_cli_reports_empty_settings_without_an_index_error(tmp_path, monkeypatch, caplog):
    import shutil
    from pathlib import Path
    from copilot_token_dashboard.cli import main

    source = Path(__file__).resolve().parents[1] / "sample_data"
    data = tmp_path / "gold"
    shutil.copytree(source, data)
    settings = data / "Settings.csv"
    settings.write_text(settings.read_text().splitlines()[0] + "\n", encoding="utf-8")
    monkeypatch.setattr("sys.argv", ["ctd", "validate-data", "--input", str(data)])
    assert main() == 1
    assert "exactly one row" in caplog.text
