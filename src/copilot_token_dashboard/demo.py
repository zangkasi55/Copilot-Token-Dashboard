from __future__ import annotations

import datetime as dt
import json
import random
from pathlib import Path

from .gold import GoldBuilder
from .schema import Row, write_table, write_tables

ANCHOR = dt.date(2026, 5, 28)


def generate_demo(output: Path, scratch: Path) -> dict:
    scratch.mkdir(parents=True, exist_ok=True)
    scopes: list[Row] = [
        {"ScopeKey": "demo-root", "Name": "Example organization", "ParentScopeKey": "",
         "Company": "Example organization", "BusinessUnit": "Example", "Department": "",
         "Team": "", "ScopeLevel": "Company", "MemberCount": 28},
        {"ScopeKey": "demo-engineering", "Name": "Example engineering team", "ParentScopeKey": "demo-root",
         "Company": "Example organization", "BusinessUnit": "Example", "Department": "Engineering",
         "Team": "Engineering", "ScopeLevel": "Team", "MemberCount": 12},
        {"ScopeKey": "demo-operations", "Name": "Example operations team", "ParentScopeKey": "demo-root",
         "Company": "Example organization", "BusinessUnit": "Example", "Department": "Operations",
         "Team": "Operations", "ScopeLevel": "Team", "MemberCount": 12},
        {"ScopeKey": "demo-small", "Name": "Suppressed four-person example", "ParentScopeKey": "demo-root",
         "Company": "Example organization", "BusinessUnit": "Example", "Department": "Small example",
         "Team": "Small example", "ScopeLevel": "Team", "MemberCount": 4},
    ]
    people, access = [], []
    for index in range(1, 29):
        scope = scopes[1 if index <= 12 else 2 if index <= 24 else 3]
        upn = f"user{index:02d}@example.com"
        people.append({
            "PersonKey": f"demo-person-{index:02d}", "UPN": upn, "DisplayName": f"Example person {index:02d}",
            "ScopeKey": scope["ScopeKey"], "Company": scope["Company"], "BusinessUnit": "Example",
            "Department": scope["Department"], "Team": scope["Team"], "JobFamily": "Example",
            "EmployeeType": "Employee", "IsService": False, "IsPrivacyRestricted": False, "HasLicense": True,
        })
        access.append({"ViewerUPN": upn, "ScopeKey": scope["ScopeKey"]})
    access.append({"ViewerUPN": "user01@example.com", "ScopeKey": "demo-root"})
    models = [
        {"ModelKey": "demo-balanced", "Name": "Example balanced model", "Provider": "Example provider",
         "Tier": "Balanced", "InputRate": 2.2, "CacheReadRate": 0.22, "CacheWriteRate": 2.75,
         "OutputRate": 6.6, "IsPriced": True},
        {"ModelKey": "demo-fast", "Name": "Example fast model", "Provider": "Example provider",
         "Tier": "Fast", "InputRate": 0.33, "CacheReadRate": 0.033, "CacheWriteRate": 0.4,
         "OutputRate": 1.32, "IsPriced": True},
        {"ModelKey": "demo-unknown", "Name": "Not disclosed", "Provider": "Not disclosed",
         "Tier": "Not classified", "InputRate": None, "CacheReadRate": None,
         "CacheWriteRate": None, "OutputRate": None, "IsPriced": False},
    ]
    agents = [
        {"AgentKey": "direct", "Name": "Direct use", "Type": "Direct", "ScopeKey": "demo-root",
         "Platform": "Multiple", "OwnerContact": "", "Status": "Active", "Risk": "Not applicable",
         "PublishedDate": None, "MinutesSavedPerRun": None, "IsRegistered": True},
        {"AgentKey": "demo-build", "Name": "Example build helper", "Type": "Automation",
         "ScopeKey": "demo-engineering", "Platform": "AI gateway", "OwnerContact": "engineering@example.com",
         "Status": "Active", "Risk": "Example only", "PublishedDate": dt.date(2026, 1, 5),
         "MinutesSavedPerRun": 7.5, "IsRegistered": True},
        {"AgentKey": "demo-support", "Name": "Example support helper", "Type": "Support",
         "ScopeKey": "demo-operations", "Platform": "GitHub Copilot", "OwnerContact": "operations@example.com",
         "Status": "Active", "Risk": "Example only", "PublishedDate": dt.date(2026, 2, 5),
         "MinutesSavedPerRun": 11.5, "IsRegistered": True},
        {"AgentKey": "demo-idle", "Name": "Example idle helper", "Type": "Automation",
         "ScopeKey": "demo-operations", "Platform": "AI gateway", "OwnerContact": "operations@example.com",
         "Status": "Pilot", "Risk": "Example only", "PublishedDate": dt.date(2026, 5, 5),
         "MinutesSavedPerRun": None, "IsRegistered": True},
    ]
    for name, rows in (("People", people), ("Scopes", scopes), ("ScopeAccess", access),
                       ("Models", models), ("Agents", agents)):
        write_table(scratch, name, rows)
    budgets = []
    for month in range(1, 6):
        for scope, amount in (("demo-root", 4200), ("demo-engineering", 2400), ("demo-operations", 1500)):
            budgets.append({"MonthStart": dt.date(2026, month, 1), "ScopeKey": scope,
                            "Platform": "All", "BudgetAmount": amount, "Currency": "USD"})
    write_table(scratch, "Budgets", budgets)
    outcomes = []
    for index in range(180):
        mode = ("Human only", "Agent-assisted", "Agent-resolved")[index % 3]
        outcomes.append({
            "RecordKey": f"demo-case-{index:03d}", "ResolvedDate": ANCHOR - dt.timedelta(days=index % 90),
            "ScopeKey": "demo-operations", "AgentKey": "direct" if mode == "Human only" else "demo-support",
            "Category": ("Incident", "Service request")[index % 2], "Priority": f"P{index % 3 + 1}",
            "HandlingMode": mode, "ResolutionHours": 9.5 if mode == "Human only" else 3.5 if mode == "Agent-assisted" else 1.75,
            "HumanEffortMinutes": 65 if mode == "Human only" else 25 if mode == "Agent-assisted" else 8,
            "CSAT": 3.5 if mode == "Human only" else 4.25,
        })
    write_table(scratch, "Outcomes", outcomes)
    randomizer = random.Random(8421)
    events = []
    for offset in range(140):
        date = ANCHOR - dt.timedelta(days=139 - offset)
        for person_index, person in enumerate(people, start=1):
            engineering = person_index <= 12
            active = date.weekday() in ((0, 1, 2, 3) if engineering else (0, 2, 4))
            if not active:
                continue
            inputs = 2400 + randomizer.randint(0, 900)
            recent = date >= ANCHOR - dt.timedelta(days=6)
            amount = (8.5 if recent else 0.42) if engineering else 0.18
            events.append({
                "id": f"demo-{person_index:02d}-{date.isoformat()}",
                "date": date.isoformat(), "upn": person["UPN"], "account": person["UPN"],
                "scope": person["ScopeKey"], "platform": "AI gateway" if engineering else "GitHub Copilot",
                "surface": "Example API" if engineering else "copilot_cli",
                "model": "Example balanced model" if engineering else "Example fast model",
                "provider": "Example provider", "tier": "Balanced" if engineering else "Fast",
                "agent": "demo-build" if engineering else "demo-support",
                "source": "Synthetic gateway" if engineering else "Synthetic GitHub",
                "input_tokens": inputs, "cached_input_tokens": inputs // 2, "cache_write_tokens": 0,
                "output_tokens": 450 + randomizer.randint(0, 150),
                "requests": 8 if engineering and recent else 4 if engineering else 2,
                "sessions": 2, "agent_runs": 2, "amount": amount, "currency": "USD",
                "cost_basis": "billed", "billing_kind": "tokens",
                "request_unit": "successful-model-request", "activity": True,
            })
            if engineering and date.weekday() == 0:
                events.append({
                    "id": f"demo-office-{person_index:02d}-{date.isoformat()}",
                    "date": date.isoformat(), "upn": person["UPN"], "account": person["UPN"],
                    "scope": person["ScopeKey"], "platform": "Microsoft 365 Copilot", "surface": "Word",
                    "model": "Not disclosed", "agent": "direct", "source": "Synthetic Microsoft 365",
                    "billing_kind": "licence-included", "request_unit": "not reported",
                    "amount": None, "currency": "USD", "cost_basis": "not usage billed", "activity": True,
                })
    tables = GoldBuilder(scratch).build(events, is_demo=True)
    write_tables(output, tables)
    known_amount = round(sum(row["Amount"] or 0 for row in tables["UsageDaily"]), 4)
    result = {
        "synthetic": True, "anchor": ANCHOR.isoformat(), "people": 28,
        "eligible_scopes": len(tables["Scopes"]), "usage_rows": len(tables["UsageDaily"]),
        "known_spend_all_dates": known_amount,
        "privacy_minimum": 6, "fictional_prices": True,
    }
    (output / "expected-values.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result

