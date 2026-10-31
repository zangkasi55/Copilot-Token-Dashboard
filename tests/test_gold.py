import copy
import datetime as dt

import pytest

from copilot_token_dashboard.demo import ANCHOR, generate_demo
from copilot_token_dashboard.gold import GoldBuilder, last_complete_saturday, sunday, validate_tables
from copilot_token_dashboard.schema import TABLES, read_table


@pytest.fixture
def demo(tmp_path):
    output, inputs = tmp_path / "gold", tmp_path / "inputs"
    result = generate_demo(output, inputs)
    tables = {name: read_table(output, name) for name in TABLES}
    return result, tables, inputs


def test_demo_build_is_complete_and_explicit(demo):
    result, tables, _ = demo
    assert result["synthetic"] is True
    assert len(tables) == len(TABLES)
    assert tables["Settings"][0]["IsDemo"] is True
    assert tables["Settings"][0]["MinimumGroupSize"] == 6
    assert tables["Settings"][0]["AnchorDate"] == ANCHOR
    assert len(tables["Scopes"]) == 3


def test_small_scopes_are_not_published(demo):
    _, tables, _ = demo
    assert "demo-small" not in {row["ScopeKey"] for row in tables["Scopes"]}
    assert all(row["ScopeKey"] != "demo-small" for row in tables["ScopeAccess"])


def test_suppressed_aggregates_erase_numeric_fields(demo):
    _, tables, _ = demo
    for name in ("ScopeDaily", "ScopeWeekly", "ScopePeriod", "AgentPeriod"):
        for row in tables[name]:
            if row["PrivacySuppressed"]:
                for field in ("Amount", "ActiveUsers", "UserDays", "InputTokens", "OutputTokens"):
                    assert row.get(field) is None


def test_validator_rejects_facts_hidden_only_cosmetically(demo):
    _, tables, _ = demo
    tampered = copy.deepcopy(tables)
    row = tampered["ScopeDaily"][0]
    row["PrivacySuppressed"], row["Amount"] = True, 1.0
    with pytest.raises(ValueError, match="retain"):
        validate_tables(tampered)


def test_production_rejects_demo_identities_and_mode(demo):
    _, tables, _ = demo
    with pytest.raises(ValueError, match="synthetic"):
        validate_tables(tables, production=True)


def test_minimum_cannot_be_lowered_in_a_data_file(demo):
    _, tables, _ = demo
    tables["Settings"][0]["MinimumGroupSize"] = 1
    with pytest.raises(ValueError, match="six"):
        validate_tables(tables, minimum=1)


def test_model_and_surface_keys_reconcile(demo):
    _, tables, _ = demo
    known = sum(row["Amount"] or 0 for row in tables["UsageDaily"])
    by_model = sum(
        sum(row["Amount"] or 0 for row in tables["UsageDaily"] if row["ModelKey"] == model["ModelKey"])
        for model in tables["Models"]
    )
    by_surface = sum(
        sum(row["Amount"] or 0 for row in tables["UsageDaily"] if row["SurfaceKey"] == surface["SurfaceKey"])
        for surface in tables["Surfaces"]
    )
    assert by_model == pytest.approx(known)
    assert by_surface == pytest.approx(known)


def test_completed_weeks_are_sunday_to_saturday():
    assert sunday(dt.date(2026, 5, 28)) == dt.date(2026, 5, 24)
    assert last_complete_saturday(dt.date(2026, 5, 28)) == dt.date(2026, 5, 23)
    assert last_complete_saturday(dt.date(2026, 5, 30)) == dt.date(2026, 5, 30)


def test_weekly_bands_count_each_person_once(demo):
    _, tables, _ = demo
    for row in tables["ScopeWeekly"]:
        if row["SurfaceKey"] == "all" and not row["PrivacySuppressed"]:
            scope = next(scope for scope in tables["Scopes"] if scope["ScopeKey"] == row["ScopeKey"])
            assert sum(row[field] for field in ("High", "Moderate", "Low", "None", "NoRecorded")) == scope["MemberCount"]


def test_unknown_token_prices_do_not_become_free_usage(demo):
    _, _, inputs = demo
    builder = GoldBuilder(inputs)
    row = builder.usage_rows([{
        "id": "unpriced", "date": "2026-05-28", "upn": "user01@example.com",
        "scope": "demo-engineering", "platform": "AI gateway", "surface": "Example API",
        "model": "Unlisted model", "source": "Example", "input_tokens": 1000,
        "cached_input_tokens": None, "output_tokens": 300, "activity": True,
        "billing_kind": "tokens", "request_unit": "successful-model-request",
        "currency": "USD", "amount": None,
    }])[0]
    assert row["Amount"] is None
    assert row["CostBasis"] == "not reported"
