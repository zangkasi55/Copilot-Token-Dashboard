from __future__ import annotations

import csv
import datetime as dt
import json
import math
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import TypeAlias

Cell: TypeAlias = str | int | float | bool | dt.date | None
Row: TypeAlias = dict[str, Cell]
Tables: TypeAlias = dict[str, list[Row]]

TABLES: dict[str, dict[str, str]] = {
    "Settings": {
        "IsDemo": "bool", "AnchorDate": "date", "MinimumGroupSize": "int",
        "BaseCurrency": "text", "SchemaVersion": "text",
    },
    "People": {
        "PersonKey": "text", "UPN": "text", "DisplayName": "text", "ScopeKey": "text",
        "Company": "text", "BusinessUnit": "text", "Department": "text",
        "Team": "text", "JobFamily": "text", "EmployeeType": "text",
        "IsService": "bool", "IsPrivacyRestricted": "bool", "HasLicense": "bool",
    },
    "ScopeAccess": {"ViewerUPN": "text", "ScopeKey": "text"},
    "Scopes": {
        "ScopeKey": "text", "Name": "text", "ParentScopeKey": "text",
        "Company": "text", "BusinessUnit": "text", "Department": "text",
        "Team": "text", "ScopeLevel": "text", "MemberCount": "int",
    },
    "Accounts": {
        "AccountKey": "text", "PersonKey": "text", "UPN": "text", "Platform": "text",
        "AccountType": "text", "MaskedId": "text", "DataThroughDate": "date",
    },
    "Surfaces": {
        "SurfaceKey": "text", "Name": "text", "Platform": "text",
        "SurfaceType": "text", "WorkCategory": "text", "BillingKind": "text",
    },
    "Models": {
        "ModelKey": "text", "Name": "text", "Provider": "text", "Tier": "text",
        "InputRate": "number", "CacheReadRate": "number", "CacheWriteRate": "number",
        "OutputRate": "number", "IsPriced": "bool",
    },
    "Agents": {
        "AgentKey": "text", "Name": "text", "Type": "text", "ScopeKey": "text",
        "Platform": "text", "OwnerContact": "text", "Status": "text", "Risk": "text",
        "PublishedDate": "date", "MinutesSavedPerRun": "number", "IsRegistered": "bool",
    },
    "UsageDaily": {
        "RowKey": "text", "Date": "date", "PersonKey": "text", "AccountKey": "text",
        "SurfaceKey": "text", "ModelKey": "text", "AgentKey": "text", "ScopeKey": "text",
        "InputTokens": "int", "CachedInputTokens": "int", "CacheWriteTokens": "int",
        "OutputTokens": "int", "Requests": "number", "Sessions": "int", "AgentRuns": "int",
        "PremiumRequests": "number", "CopilotCredits": "number", "GitHubAiCredits": "number",
        "Amount": "number", "Currency": "text", "CostBasis": "text", "Source": "text",
        "BillingKind": "text", "ActivityObserved": "bool", "IsAttributed": "bool",
        "RequestUnit": "text",
    },
    "ScopeDaily": {
        "Date": "date", "ScopeKey": "text", "SurfaceKey": "text", "ModelKey": "text",
        "AgentKey": "text", "Amount": "number", "InputTokens": "int",
        "CachedInputTokens": "int", "CacheWriteTokens": "int", "OutputTokens": "int",
        "Requests": "number", "AgentRuns": "int", "UserDays": "int",
        "ActiveUsers": "int", "PrivacySuppressed": "bool", "UnpricedRows": "int",
    },
    "ScopeWeekly": {
        "WeekStart": "date", "ScopeKey": "text", "SurfaceKey": "text",
        "Amount": "number", "InputTokens": "int", "OutputTokens": "int",
        "Requests": "number", "AgentRuns": "int", "ActiveUsers": "int", "UserDays": "int",
        "High": "int", "Moderate": "int", "Low": "int", "None": "int",
        "NoRecorded": "int", "PrivacySuppressed": "bool",
    },
    "ScopePeriod": {
        "PeriodLabel": "text", "ScopeKey": "text", "Amount": "number",
        "InputTokens": "int", "CachedInputTokens": "int", "OutputTokens": "int",
        "Requests": "number", "AgentRuns": "int", "ActiveUsers": "int",
        "UserDays": "int", "MemberCount": "int", "PrivacySuppressed": "bool",
        "UnpricedRows": "int", "UnattributedAmount": "number",
    },
    "AgentPeriod": {
        "PeriodLabel": "text", "ScopeKey": "text", "AgentKey": "text",
        "Amount": "number", "AgentRuns": "int", "ActiveUsers": "int",
        "InputTokens": "int", "CachedInputTokens": "int", "OutputTokens": "int",
        "Last7Amount": "number", "Prior4WeekAverage": "number", "SpikeFlag": "bool",
        "Idle30Days": "bool", "NewThisMonth": "bool",
        "UsersLast6Weeks": "int", "UsersPrior6Weeks": "int",
        "IntensityLast6Weeks": "number", "IntensityPrior6Weeks": "number",
        "UserGrowth": "number", "IntensityGrowth": "number",
        "TrendClass": "text", "PrivacySuppressed": "bool",
    },
    "Outcomes": {
        "RecordKey": "text", "ResolvedDate": "date", "ScopeKey": "text",
        "AgentKey": "text", "Category": "text", "Priority": "text",
        "HandlingMode": "text", "ResolutionHours": "number",
        "HumanEffortMinutes": "number", "CSAT": "number",
    },
    "Budgets": {
        "MonthStart": "date", "ScopeKey": "text", "Platform": "text",
        "BudgetAmount": "number", "Currency": "text",
    },
    "Coverage": {
        "Source": "text", "Metric": "text", "Granularity": "text", "Status": "text",
        "AsOfDate": "date", "LoadedAtUTC": "text", "RowCount": "int", "Detail": "text",
    },
    "PeriodSummary": {
        "PersonKey": "text", "Source": "text", "StartDate": "date", "EndDate": "date",
        "Metric": "text", "Value": "number", "Unit": "text", "IsConcealed": "bool",
    },
    "Calendar": {
        "Date": "date", "Year": "int", "MonthNumber": "int", "Month": "text",
        "YearMonth": "text", "MonthStart": "date", "WeekStart": "date",
        "WeekLabel": "text", "DayName": "text",
    },
    "Periods": {"Label": "text", "Mode": "text", "Days": "int", "SortOrder": "int"},
    "Currencies": {"Code": "text", "Multiplier": "number", "Symbol": "text"},
    "HourlyRate": {"Rate": "number"},
}

PERIODS: list[Row] = [
    {"Label": "Last 7 days", "Mode": "Rolling", "Days": 7, "SortOrder": 1},
    {"Label": "Last 28 days", "Mode": "Rolling", "Days": 28, "SortOrder": 2},
    {"Label": "Last 90 days", "Mode": "Rolling", "Days": 90, "SortOrder": 3},
    {"Label": "Month to date", "Mode": "MTD", "Days": 0, "SortOrder": 4},
    {"Label": "Year to date", "Mode": "YTD", "Days": 0, "SortOrder": 5},
]


def parse_cell(value: object, kind: str, location: str) -> Cell:
    if value is None or value == "":
        return None
    if kind == "text":
        return str(value)
    if kind == "date":
        if isinstance(value, dt.datetime):
            return value.date()
        if isinstance(value, dt.date):
            return value
        return dt.date.fromisoformat(str(value)[:10])
    if kind == "bool":
        if value in (True, "True", "TRUE", "true", "1", 1):
            return True
        if value in (False, "False", "FALSE", "false", "0", 0):
            return False
        raise ValueError(f"{location}: expected a Boolean")
    if kind == "int":
        try:
            exact = Decimal(str(value))
        except InvalidOperation as error:
            raise ValueError(f"{location}: expected an integer") from error
        if not exact.is_finite() or exact != exact.to_integral_value() or abs(exact) > 9223372036854775807:
            raise ValueError(f"{location}: expected a signed 64-bit integer")
        return int(exact)
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"{location}: expected a finite number")
    return number


def read_table(folder: Path, name: str, required: bool = True) -> list[Row]:
    path = folder / f"{name}.csv"
    if not path.is_file():
        if required:
            raise FileNotFoundError(f"Required data table is missing: {name}.csv")
        return []
    columns = TABLES[name]
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames != list(columns):
            raise ValueError(f"{name}.csv: headers must match the published data contract")
        rows = []
        for index, row in enumerate(reader, start=2):
            if None in row or any(value is None for value in row.values()):
                raise ValueError(f"{name}.csv:{index}: column count does not match the contract")
            rows.append({
                column: parse_cell(row[column], kind, f"{name}:{index}:{column}")
                for column, kind in columns.items()
            })
        return rows


def write_table(folder: Path, name: str, rows: list[Row]) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    with (folder / f"{name}.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(TABLES[name]))
        writer.writeheader()
        for row in rows:
            unknown = set(row) - set(TABLES[name])
            if unknown:
                raise ValueError(f"{name}: unknown columns {sorted(unknown)}")
            writer.writerow({
                key: value.isoformat() if isinstance(value, dt.date) else value
                for key, value in row.items()
            })


def write_tables(folder: Path, tables: Tables) -> None:
    for name in TABLES:
        if name not in tables:
            raise ValueError(f"The build did not produce required table {name}")
        write_table(folder, name, tables[name])
    (folder / "data-contract.json").write_text(
        json.dumps({"version": "1.0", "tables": TABLES}, indent=2), encoding="utf-8"
    )
