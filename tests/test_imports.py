import json

import pytest

from copilot_token_dashboard.imports import audit_record, credit_record, focus_records, import_source


def test_credit_quantities_are_not_github_units_or_guessed_user_spend():
    event = credit_record({"resourceId": "example-agent", "usageDate": "2026-05-28", "consumed": 15},
                          "example-team", "USD", None)
    assert event["copilot_credits"] == 15
    assert event["github_ai_credits"] is None
    assert event["amount"] is None
    assert event["upn"] == ""
    assert event["agent_runs"] is None


def test_credit_rate_requires_explicit_estimate():
    event = credit_record({"resourceId": "example-agent", "usageDate": "2026-05-28", "consumed": 15},
                          "example-team", "USD", 0.02)
    assert event["amount"] == pytest.approx(0.3)
    assert event["cost_basis"] == "estimated"


def test_audit_counts_keep_no_prompt_content():
    event = audit_record({
        "Id": "example-audit", "CreationTime": "2026-05-28T12:00:00Z",
        "Operation": "CopilotInteraction", "UserId": "user01@example.com",
        "CopilotEventData": {"AppHost": "Word", "Messages": [
            {"isPrompt": True, "text": "This raw content must not be retained"},
            {"isPrompt": False, "text": "Neither may this content"},
        ]},
    }, "example-team")
    assert event["requests"] == 1
    assert event["request_unit"] == "audit-prompt"
    assert "raw content" not in json.dumps(event)
    assert event["input_tokens"] is None


def test_focus_requires_explicit_service_selection(tmp_path):
    path = tmp_path / "focus.csv"
    path.write_text("ServiceName,ChargePeriodStart,BilledCost,BillingCurrency,ResourceId\n"
                    "Storage,2026-05-28,3,USD,example-resource\n", encoding="utf-8")
    with pytest.raises(ValueError, match="explicit"):
        focus_records(path, "example-team", "")
    with pytest.raises(ValueError, match="matched"):
        focus_records(path, "example-team", "Azure OpenAI")


def test_gateway_missing_cache_stays_unknown(tmp_path):
    path = tmp_path / "gateway.jsonl"
    path.write_text(json.dumps({
        "timestamp": "2026-05-28T12:00:00Z", "request_id": "example-request",
        "upn": "user01@example.com", "prompt_tokens": 1000, "completion_tokens": 100,
        "model": "Example model",
    }), encoding="utf-8")
    output = tmp_path / "normalized.jsonl"
    result = import_source("gateway", path, output, "example-team")
    event = json.loads(output.read_text(encoding="utf-8"))
    assert result["prompts_or_responses_retained"] is False
    assert event["cached_input_tokens"] is None
