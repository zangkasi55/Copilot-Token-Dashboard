import datetime as dt

import pytest

from copilot_token_dashboard.normalize import (
    event_id, github_billing, github_usage, m365_report, number, validate_event,
)


def basic_event(**extra):
    return {
        "id": "example", "date": "2026-05-28", "platform": "Example",
        "surface": "Example API", "source": "Example source", **extra,
    }


def test_unknown_cache_is_not_zero():
    value = validate_event(basic_event(input_tokens=1000, output_tokens=100))
    assert value["input_tokens"] == 1000
    assert value["cached_input_tokens"] is None
    assert value["cache_write_tokens"] is None


def test_zero_is_valid_and_distinct_from_missing():
    value = validate_event(basic_event(input_tokens=0, output_tokens=0, cached_input_tokens=0))
    assert value["input_tokens"] == value["output_tokens"] == value["cached_input_tokens"] == 0
    assert value["requests"] is None


@pytest.mark.parametrize("value", [-1, float("nan"), float("inf"), True])
def test_invalid_counters_raise(value):
    with pytest.raises(ValueError):
        number(value, "counter", integer=True)


def test_large_integer_is_preserved_exactly():
    assert number("9007199254740993", "counter", integer=True) == 9007199254740993


def test_private_content_is_rejected():
    with pytest.raises(ValueError, match="metadata only"):
        validate_event(basic_event(prompt_text="This must not be ingested"))


def test_cached_tokens_cannot_exceed_total_input():
    with pytest.raises(ValueError):
        validate_event(basic_event(input_tokens=10, cached_input_tokens=11))


def test_github_client_leaves_do_not_duplicate_cli_totals():
    record = {
        "day": "2026-05-28", "user_login": "example-user",
        "totals_by_client": [{
            "client": "copilot_cli", "request_count": 3, "session_count": 2,
            "token_usage": {"prompt_tokens_sum": 1000, "output_tokens_sum": 300},
            "totals_by_model": [{
                "model": "Example model", "request_count": 3,
                "token_usage": {"prompt_tokens_sum": 1000, "output_tokens_sum": 300},
            }],
        }],
        "totals_by_cli": {
            "request_count": 3, "token_usage": {"prompt_tokens_sum": 1000, "output_tokens_sum": 300},
        },
    }
    values = github_usage([record], {"example-user": "user01@example.com"}, "example-team")
    assert sum(row["requests"] or 0 for row in values) == 3
    assert sum(row["input_tokens"] or 0 for row in values) == 1000
    assert sum(row["output_tokens"] or 0 for row in values) == 300
    assert sum(row["sessions"] or 0 for row in values) == 2
    assert all(row["cached_input_tokens"] is None for row in values)


def test_github_residual_tokens_are_preserved():
    record = {
        "day": "2026-05-28", "user_login": "example-user",
        "totals_by_client": [{
            "client": "example-client", "request_count": 4,
            "token_usage": {"prompt_tokens_sum": 1300, "output_tokens_sum": 400},
            "totals_by_model": [{
                "model": "Example model", "request_count": 3,
                "token_usage": {"prompt_tokens_sum": 1000, "output_tokens_sum": 300},
            }],
        }],
    }
    values = github_usage([record], {}, "example-team")
    assert sum(row["input_tokens"] or 0 for row in values) == 1300
    assert sum(row["requests"] or 0 for row in values) == 4
    assert values[-1]["model"] == "Not disclosed"


def test_billing_uses_actual_net_amount_and_distinct_credit_units():
    body = {"usageItems": [{"sku": "ai-credits", "model": "Example model", "unitType": "credits",
                           "netQuantity": 25, "netAmount": 1.73, "product": "Copilot"}]}
    row = github_billing(body, dt.date(2026, 5, 28), "user", "user01@example.com", "example-team")[0]
    assert row["amount"] == 1.73
    assert row["github_ai_credits"] == 25
    assert row["copilot_credits"] is None
    assert row["surface"] == "Unattributed billing surface"
    assert row["activity"] is False


def test_refunds_are_not_silently_dropped():
    body = {"usageItems": [{"sku": "ai-credits", "model": "Example model", "unitType": "credits",
                           "netQuantity": 0, "netAmount": -1.25}]}
    row = github_billing(body, dt.date(2026, 5, 28), "user", "user01@example.com", "example-team")[0]
    assert row["amount"] == -1.25


def test_m365_period_totals_are_not_spread_into_daily_requests():
    text = (
        "Report Refresh Date,User Principal Name,Word Copilot Last Activity Date,"
        "Prompts submitted for all apps,Active Usage Days for all apps\n"
        "2026-05-28,user01@example.com,2026-05-27,24,5\n"
    )
    events, summaries, status = m365_report(text, 7)
    assert len(events) == 1
    assert events[0]["date"] == "2026-05-27"
    assert events[0]["requests"] is None
    assert events[0]["input_tokens"] is None
    assert [summary["value"] for summary in summaries] == [24, 5]
    assert all(summary["start"] == "2026-05-22" for summary in summaries)
    assert status["concealed_records"] == 0


def test_concealed_m365_names_are_not_guessed():
    text = (
        "Report Refresh Date,User Principal Name,Word Copilot Last Activity Date\n"
        "2026-05-28,0123456789abcdef0123456789abcdef,2026-05-27\n"
    )
    events, summaries, status = m365_report(text, 28)
    assert events == summaries == []
    assert status["concealed_records"] == 1


def test_model_selection_modes_do_not_reuse_event_identifiers():
    record = {
        "day": "2026-05-28", "user_login": "example-user",
        "totals_by_client": [{
            "client": "copilot_cli", "request_count": 3,
            "token_usage": {"prompt_tokens_sum": 300, "output_tokens_sum": 30},
            "totals_by_model": [
                {"model": "Example model", "model_selection_mode": "auto", "request_count": 1,
                 "token_usage": {"prompt_tokens_sum": 100, "output_tokens_sum": 10}},
                {"model": "Example model", "model_selection_mode": "user_selected", "request_count": 2,
                 "token_usage": {"prompt_tokens_sum": 200, "output_tokens_sum": 20}},
            ],
        }],
    }
    rows = github_usage([record], {}, "example-team")
    assert len({row["id"] for row in rows}) == 2
    assert sum(row["input_tokens"] for row in rows) == 300


def test_model_records_without_selection_mode_keep_existing_identifiers():
    record = {"day": "2026-05-28", "user_login": "example-user",
              "totals_by_client": [{"client": "copilot_cli", "totals_by_model": [
                  {"model": "Example model", "request_count": 1},
              ]}]}
    row = github_usage([record], {}, "example-team")[0]
    assert row["id"] == event_id(
        "github-usage", "2026-05-28", "example-user", "copilot_cli", "Example model", "model")


@pytest.mark.parametrize("flag", ["false", "true", 0, 1])
def test_activity_flags_are_not_coerced_from_truthy_strings(flag):
    with pytest.raises(ValueError, match="Boolean"):
        validate_event(basic_event(activity=flag))


def test_cache_write_cannot_exceed_input_when_cache_read_is_missing():
    with pytest.raises(ValueError, match="Cache-write"):
        validate_event(basic_event(input_tokens=10, cache_write_tokens=20))
