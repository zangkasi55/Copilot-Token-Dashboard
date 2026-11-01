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


def test_billing_only_personal_amounts_are_suppressed(demo):
    _, tables, inputs = demo
    builder = GoldBuilder(inputs)
    row = copy.deepcopy(tables["UsageDaily"][0])
    row["ActivityObserved"] = False
    row["Amount"] = 73.5
    metric = builder.metrics([row], "demo-root")
    assert metric["PrivacySuppressed"] is True
    assert metric["Amount"] is None
    assert metric["ActiveUsers"] is None


def test_privacy_restricted_people_are_excluded_from_scope_facts(demo):
    _, tables, inputs = demo
    builder = GoldBuilder(inputs)
    row = copy.deepcopy(tables["UsageDaily"][0])
    builder.people_by_key[str(row["PersonKey"])]["IsPrivacyRestricted"] = True
    assert builder.rows_for_scope([row], "demo-root") == []


@pytest.mark.parametrize("flag", [None, "False", 0])
def test_demo_flag_must_be_an_explicit_boolean(demo, flag):
    _, tables, _ = demo
    tables["Settings"][0]["IsDemo"] = flag
    with pytest.raises(ValueError, match="Boolean"):
        validate_tables(tables)


def test_settings_must_contain_exactly_one_row(demo):
    _, tables, _ = demo
    tables["Settings"].append(dict(tables["Settings"][0]))
    with pytest.raises(ValueError, match="exactly one"):
        validate_tables(tables)


def test_unsuppressed_small_active_cohort_is_rejected(demo):
    _, tables, _ = demo
    tables["ScopeDaily"][0].update(ActiveUsers=1, PrivacySuppressed=False)
    with pytest.raises(ValueError, match="cohort"):
        validate_tables(tables)


@pytest.mark.parametrize("count", [None, -1, 99])
def test_unsuppressed_cohort_requires_a_valid_reported_count(demo, count):
    _, tables, _ = demo
    tables["ScopeDaily"][0].update(ActiveUsers=count, PrivacySuppressed=False)
    with pytest.raises(ValueError, match="cohort"):
        validate_tables(tables)


def test_suppressed_weekly_bands_cannot_retain_counts(demo):
    _, tables, _ = demo
    row = tables["ScopeWeekly"][0]
    row.update(PrivacySuppressed=True)
    for field in ("Amount", "InputTokens", "OutputTokens", "Requests", "AgentRuns",
                  "ActiveUsers", "UserDays"):
        row[field] = None
    row["High"] = 1
    with pytest.raises(ValueError, match="retain"):
        validate_tables(tables)


@pytest.mark.parametrize("table,field,value", [
    ("Outcomes", "AgentKey", "nonexistent-agent"),
    ("Outcomes", "ScopeKey", "nonexistent-scope"),
    ("Accounts", "PersonKey", "nonexistent-person"),
    ("ScopeDaily", "ModelKey", "nonexistent-model"),
])
def test_all_reported_fact_references_must_exist(demo, table, field, value):
    _, tables, _ = demo
    tables[table][0][field] = value
    with pytest.raises(ValueError, match="unknown"):
        validate_tables(tables)


def test_early_year_build_includes_all_completed_week_dates(demo):
    _, _, inputs = demo
    event = {
        "id": "january-example", "date": "2026-01-02", "upn": "user01@example.com",
        "scope": "demo-engineering", "platform": "AI gateway", "surface": "Example API",
        "model": "Example model", "source": "Example", "activity": True,
        "requests": 1, "currency": "USD",
    }
    tables = GoldBuilder(inputs).build([event], is_demo=True)
    dates = {row["Date"] for row in tables["Calendar"]}
    assert all(row["WeekStart"] in dates for row in tables["ScopeWeekly"])
