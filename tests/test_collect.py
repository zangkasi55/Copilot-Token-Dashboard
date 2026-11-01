import datetime as dt
import json

import pytest

from copilot_token_dashboard import collect
from copilot_token_dashboard.http import ApiError


def test_github_collection_writes_usage_and_actual_billing_amounts(tmp_path, monkeypatch):
    mapping = tmp_path / "map.csv"
    mapping.write_text("login,upn\nexample-user,user01@example.com\n", encoding="utf-8")
    settings = {"github": {
        "scope_type": "enterprise", "scope_name": "example-enterprise",
        "root_scope_key": "example-team", "login_map_file": str(mapping),
        "token_environment_variable": "EXAMPLE_TEST_TOKEN",
    }}
    monkeypatch.setenv("EXAMPLE_TEST_TOKEN", "synthetic-test-value")
    requests = []

    class Client:
        def __init__(self, origin, token):
            assert origin == "https://api.github.com"
            assert token == "synthetic-test-value"

        def get_json(self, path, params, headers):
            requests.append((path, params, headers))
            if "users-1-day" in path:
                return {"download_links": ["https://example.com/sample.ndjson"], "report_day": "2026-05-28"}
            premium = "premium_request" in path
            return {"usageItems": [{
                "sku": "premium-requests" if premium else "ai-credits",
                "unitType": "requests" if premium else "credits", "model": "Example model",
                "netAmount": 1.25 if premium else 2.5, "netQuantity": 5,
            }]}

    monkeypatch.setattr(collect, "ApiClient", Client)
    monkeypatch.setattr(collect, "download_report", lambda url: json.dumps({
        "day": "2026-05-28", "user_login": "example-user",
        "totals_by_cli": {"request_count": 3, "session_count": 1,
                          "token_usage": {"prompt_tokens_sum": 1000, "output_tokens_sum": 100}},
    }).encode("utf-8"))
    output = tmp_path / "github.jsonl"
    result = collect.collect_github(settings, dt.date(2026, 5, 28), output, include_billing=True)
    rows = [json.loads(line) for line in output.read_text().splitlines()]
    assert result["records"] == 1 and result["unmapped_users"] == 0
    assert len(rows) == 3
    assert sum(row["amount"] or 0 for row in rows) == 3.75
    assert sum(row["input_tokens"] or 0 for row in rows) == 1000
    assert all(headers["X-GitHub-Api-Version"] == "2026-03-10" for _, _, headers in requests)
    assert requests[0][1] == {"day": "2026-05-28"}


def test_m365_collector_follows_report_redirect_and_keeps_period_totals(tmp_path, monkeypatch):
    monkeypatch.setattr(collect, "graph_token", lambda settings: "synthetic-test-value")

    class Client:
        def __init__(self, origin, token):
            assert origin == "https://graph.microsoft.com"

        def request(self, method, path):
            assert method == "GET" and "period='D7',version='v2'" in path
            return type("Response", (), {
                "status_code": 302, "headers": {"Location": "https://example.com/usage.csv"},
            })()

    monkeypatch.setattr(collect, "ApiClient", Client)
    monkeypatch.setattr(collect, "download_report", lambda url: (
        "Report Refresh Date,User Principal Name,Word Copilot Last Activity Date,"
        "Prompts submitted for all apps\n"
        "2026-05-28,user01@example.com,2026-05-27,12\n"
    ).encode("utf-8"))
    output = tmp_path / "m365.jsonl"
    result = collect.collect_m365({"m365": {"period": "D7"}}, output)
    usage = json.loads(output.read_text())
    summary = json.loads(output.with_name("m365.period-summary.jsonl").read_text())
    assert result["period_summaries"] == 1
    assert usage["requests"] is None
    assert summary["value"] == 12
    assert summary["start"] == "2026-05-22"


def test_source_permission_failure_does_not_write_success_output(tmp_path, monkeypatch):
    settings = {"github": {
        "scope_type": "enterprise", "scope_name": "example-enterprise",
        "root_scope_key": "example-team", "token_environment_variable": "EXAMPLE_TEST_TOKEN",
    }}
    monkeypatch.setenv("EXAMPLE_TEST_TOKEN", "synthetic-test-value")

    class Client:
        def __init__(self, origin, token):
            pass

        def get_json(self, *args):
            raise ApiError(403, "https://api.github.com")

    monkeypatch.setattr(collect, "ApiClient", Client)
    output = tmp_path / "blocked.jsonl"
    with pytest.raises(ApiError):
        collect.collect_github(settings, dt.date(2026, 5, 28), output)
    assert not output.exists()
