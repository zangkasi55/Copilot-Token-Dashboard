import json
from pathlib import Path

from tools.build_powerbi import measures, model_definition
from copilot_token_dashboard.demo import generate_demo


def test_generated_model_is_tenant_neutral_and_privacy_separated(tmp_path):
    data = tmp_path / "data"
    generate_demo(data, tmp_path / "inputs")
    model = model_definition(data)["model"]
    roles = model["roles"]
    assert [role["name"] for role in roles] == ["Viewer"]
    filters = {item["name"]: item["filterExpression"] for item in roles[0]["tablePermissions"]}
    assert "USERPRINCIPALNAME()" in filters["People"]
    assert "USERPRINCIPALNAME()" in filters["Accounts"]
    assert "USERPRINCIPALNAME()" in filters["Scopes"]
    assert all(filters[name] == "[PrivacySuppressed]=FALSE()"
               for name in ("ScopeDaily", "ScopeWeekly", "ScopePeriod", "AgentPeriod"))
    aggregates = {table["name"]: table for table in model["tables"] if table["name"].startswith("Scope")}
    for name, table in aggregates.items():
        if name != "ScopeAccess":
            assert not {"UPN", "PersonKey", "DisplayName"} & {column["name"] for column in table["columns"]}
    text = json.dumps(model)
    assert "powerbi.com/groups/me/apps" not in text
    assert "client_secret" not in text


def test_measures_use_explicit_unknowns_and_no_boolean_max():
    definitions = {item["name"]: item["expression"] for item in measures()}
    assert "MAX(Settings[IsDemo])" not in "\n".join(definitions.values())
    assert "not reported" not in definitions["My Uncached Input Tokens"].lower()
    assert "IF([My Cache Coverage Gaps]=0 && [My Cache Write Coverage Gaps]=0" in definitions["My Uncached Input Tokens"]
    assert "IF" in definitions["My Cache Hit Ratio"]
    assert "user01@example.com" in definitions["Viewer UPN"]
    assert "USERPRINCIPALNAME()" in definitions["Viewer UPN"]
