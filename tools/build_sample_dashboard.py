from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
from collections import defaultdict
from pathlib import Path

from copilot_token_dashboard.gold import period_start, reported_sum, validate_tables
from copilot_token_dashboard.schema import TABLES, Row, read_table

PAGE_IDS = [
    "overview", "personal", "organization", "momentum", "agents", "agent_detail",
    "outcomes", "value", "models", "guide",
]
METRICS = ("Amount", "InputTokens", "CachedInputTokens", "CacheWriteTokens",
           "OutputTokens", "Requests", "AgentRuns")


def metric_totals(rows: list[Row]) -> dict:
    return {field: reported_sum(rows, field) for field in METRICS}


def group_totals(rows: list[Row], field: str, dimension: dict[str, Row]) -> list[dict]:
    groups = defaultdict(list)
    for row in rows:
        groups[str(row[field])].append(row)
    return [
        {"key": identity, "name": dimension[identity]["Name"], **metric_totals(values)}
        for identity, values in sorted(groups.items())
    ]


def sample_payload(data: Path, project: Path) -> dict:
    tables = {name: read_table(data, name) for name in TABLES}
    validate_tables(tables)
    if len(tables["Settings"]) != 1 or tables["Settings"][0]["IsDemo"] is not True:
        raise ValueError("Documentation screenshots must use explicitly synthetic data")
    if any(row["UPN"] and not str(row["UPN"]).endswith("@example.com")
           for row in tables["People"]):
        raise ValueError("Only reserved-domain example identities may appear in the public illustrations")
    manifest = json.loads((project / "build-manifest.json").read_text(encoding="utf-8"))
    if [page["name"] for page in manifest["pages"]] != PAGE_IDS:
        raise ValueError("The gallery must match every page in the shipped report")
    anchor = tables["Settings"][0]["AnchorDate"]
    person = next(row for row in tables["People"] if row["UPN"] == "user01@example.com")
    personal_all = [row for row in tables["UsageDaily"] if row["PersonKey"] == person["PersonKey"]]
    surfaces = {str(row["SurfaceKey"]): row for row in tables["Surfaces"]}
    models = {str(row["ModelKey"]): row for row in tables["Models"]}
    agents = {str(row["AgentKey"]): row for row in tables["Agents"]}
    snapshots = {}
    personal = {}
    for period in tables["Periods"]:
        label = str(period["Label"])
        start = period_start(anchor, period)
        selected_personal = [row for row in personal_all if start <= row["Date"] <= anchor]
        personal[label] = {
            **metric_totals(selected_personal),
            "ActiveDays": len({row["Date"] for row in selected_personal if row["ActivityObserved"]}),
            "UnpricedRows": sum(
                row["InputTokens"] is not None and row["Amount"] is None
                and row["CostBasis"] != "billed separately" for row in selected_personal),
            "surfaces": group_totals(selected_personal, "SurfaceKey", surfaces),
            "models": group_totals(selected_personal, "ModelKey", models),
            "daily": [],
        }
        date = start
        while date <= anchor:
            values = [row for row in selected_personal if row["Date"] == date]
            amount = reported_sum(values, "Amount")
            personal[label]["daily"].append({
                "date": date.isoformat(), "amount": amount,
                "state": "reported" if amount is not None else "not reported" if values else "no records",
            })
            date += dt.timedelta(days=1)
        for scope in tables["Scopes"]:
            scope_key = scope["ScopeKey"]
            summary = next(row for row in tables["ScopePeriod"]
                           if row["ScopeKey"] == scope_key and row["PeriodLabel"] == label)
            daily = [row for row in tables["ScopeDaily"]
                     if row["ScopeKey"] == scope_key and start <= row["Date"] <= anchor
                     and not row["PrivacySuppressed"]]
            period_agents = [row for row in tables["AgentPeriod"]
                             if row["ScopeKey"] == scope_key and row["PeriodLabel"] == label
                             and not row["PrivacySuppressed"]]
            outcomes = [row for row in tables["Outcomes"]
                        if row["ScopeKey"] == scope_key and start <= row["ResolvedDate"] <= anchor]
            outcomes_by_mode = []
            for mode in ("Human only", "Agent-assisted", "Agent-resolved"):
                selected = [row for row in outcomes if row["HandlingMode"] == mode]
                elapsed = [row["ResolutionHours"] for row in selected if row["ResolutionHours"] is not None]
                effort = [row["HumanEffortMinutes"] for row in selected if row["HumanEffortMinutes"] is not None]
                outcomes_by_mode.append({
                    "name": mode, "count": len(selected),
                    "hours": sum(elapsed) / len(elapsed) if elapsed else None,
                    "effort": sum(effort) / len(effort) if effort else None,
                })
            month_budget = reported_sum(
                [row for row in tables["Budgets"]
                 if row["ScopeKey"] == scope_key and row["MonthStart"] == anchor.replace(day=1)],
                "BudgetAmount",
            )
            mtd = next(row for row in tables["ScopePeriod"]
                       if row["ScopeKey"] == scope_key and row["PeriodLabel"] == "Month to date")
            snapshots[str(scope_key) + "|" + label] = {
                "summary": summary,
                "mtd": mtd["Amount"],
                "monthBudget": month_budget,
                "surfaces": group_totals(daily, "SurfaceKey", surfaces),
                "models": [
                    {**group, "provider": models[group["key"]]["Provider"], "tier": models[group["key"]]["Tier"]}
                    for group in group_totals(daily, "ModelKey", models)
                ],
                "weekly": sorted(
                    [row for row in tables["ScopeWeekly"]
                     if row["ScopeKey"] == scope_key and row["SurfaceKey"] == "all"],
                    key=lambda row: row["WeekStart"],
                ),
                "agents": [{**row, "name": agents[str(row["AgentKey"])]["Name"]}
                           for row in period_agents],
                "outcomes": outcomes_by_mode,
            }
    fixed_spend = {}
    for label, start in (("7 days", anchor - dt.timedelta(days=6)),
                         ("28 days", anchor - dt.timedelta(days=27)),
                         ("Month to date", anchor.replace(day=1))):
        fixed_spend[label] = reported_sum(
            [row for row in personal_all if start <= row["Date"] <= anchor], "Amount")
    hashes = {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(data.glob("*.csv"))
    }
    return {
        "isSynthetic": True, "anchor": anchor, "currency": tables["Settings"][0]["BaseCurrency"],
        "minimumGroupSize": tables["Settings"][0]["MinimumGroupSize"],
        "provenance": "Browser-rendered illustration using the shipped synthetic CSVs. Not a verified Power BI screenshot.",
        "pages": [
            {"id": page["name"], "title": page["title"], "visualCount": page["visualCount"]}
            for page in manifest["pages"]
        ],
        "periods": [row["Label"] for row in tables["Periods"]],
        "scopes": [{"key": row["ScopeKey"], "name": row["Name"], "members": row["MemberCount"]}
                   for row in tables["Scopes"]],
        "viewer": person["UPN"], "personal": personal, "fixedPersonalSpend": fixed_spend,
        "accounts": [row for row in tables["Accounts"] if row["PersonKey"] == person["PersonKey"]],
        "agents": list(agents.values()),
        "coverage": [
            {field: row[field] for field in ("Source", "Metric", "Status", "AsOfDate", "RowCount", "Detail")}
            for row in tables["Coverage"]
        ],
        "snapshots": snapshots,
        "sourceHashes": hashes,
    }


def build(data: Path, project: Path, output: Path) -> dict:
    payload = sample_payload(data, project)
    template = Path(__file__).with_name("sample-dashboard.template.html").read_text(encoding="utf-8")
    theme = Path(__file__).with_name("clawpilot-theme.html").read_text(encoding="utf-8")
    encoded = json.dumps(payload, ensure_ascii=True, separators=(",", ":"), default=str).replace("<", "\\u003c")
    html = template.replace("@@THEME@@", theme).replace("@@DATA@@", encoded)
    if "@@THEME@@" in html or "@@DATA@@" in html:
        raise ValueError("The sample dashboard template did not render completely")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(html, encoding="utf-8")
    result = {
        "synthetic": True, "anchor": str(payload["anchor"]), "pages": len(payload["pages"]),
        "illustration": True, "sourceHashes": payload["sourceHashes"],
        "defaultScope": "demo-engineering", "defaultPeriod": "Last 28 days",
        "viewer": payload["viewer"], "fixedPersonalSpend": payload["fixedPersonalSpend"],
    }
    output.with_name("sample-provenance.json").write_text(
        json.dumps(result, indent=2), encoding="utf-8"
    )
    return {key: value for key, value in result.items() if key != "sourceHashes"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build the synthetic-only manual dashboard companion")
    parser.add_argument("--data", type=Path, default=Path("sample_data"))
    parser.add_argument("--project", type=Path, default=Path("powerbi"))
    parser.add_argument("--output", type=Path, default=Path("docs/assets/sample-dashboard.html"))
    args = parser.parse_args()
    print(json.dumps(build(args.data, args.project, args.output), indent=2))
