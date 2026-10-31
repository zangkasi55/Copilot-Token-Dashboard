from __future__ import annotations

import datetime as dt
import hashlib
import json
from collections import defaultdict
from pathlib import Path

from .normalize import Event, validate_event
from .schema import PERIODS, TABLES, Row, Tables, read_table, write_tables

COUNTERS = ("InputTokens", "CachedInputTokens", "CacheWriteTokens", "OutputTokens",
            "Requests", "AgentRuns")


def reported_sum(rows: list[Row], column: str) -> int | float | None:
    values = [row[column] for row in rows if row.get(column) is not None]
    return sum(values) if values else None


def key(*parts: object) -> str:
    return hashlib.sha256(json.dumps(parts, separators=(",", ":"), default=str).encode()).hexdigest()[:24]


def period_start(anchor: dt.date, period: Row) -> dt.date:
    if period["Mode"] == "MTD":
        return anchor.replace(day=1)
    if period["Mode"] == "YTD":
        return anchor.replace(month=1, day=1)
    return anchor - dt.timedelta(days=int(period["Days"]) - 1)


def sunday(date: dt.date) -> dt.date:
    return date - dt.timedelta(days=(date.weekday() + 1) % 7)


def last_complete_saturday(anchor: dt.date) -> dt.date:
    return anchor if anchor.weekday() == 5 else sunday(anchor) - dt.timedelta(days=1)


def mask_account(value: str) -> str:
    if "@" in value:
        local, domain = value.split("@", 1)
        return local[:2] + "***@" + domain
    return value[:2] + "***" if value else "Unattributed"


def _unique(rows: list[Row], column: str, label: str) -> dict[str, Row]:
    result = {}
    for row in rows:
        value = str(row.get(column) or "")
        if not value or value in result:
            raise ValueError(f"{label}: keys must be nonempty and unique")
        result[value] = row
    return result


class GoldBuilder:
    def __init__(self, inputs: Path, minimum: int = 6, currency: str = "USD") -> None:
        if minimum < 6:
            raise ValueError("The public package requires a minimum group size of at least six")
        if len(currency) != 3 or not currency.isupper():
            raise ValueError("The base currency must be an uppercase three-letter code")
        self.inputs, self.minimum, self.currency = inputs, minimum, currency
        self.people = read_table(inputs, "People")
        for person in self.people:
            person["UPN"] = str(person["UPN"]).strip().lower()
        self.scopes = read_table(inputs, "Scopes")
        self.access = read_table(inputs, "ScopeAccess")
        self.people_by_key = _unique(self.people, "PersonKey", "People")
        self.people_by_upn = _unique(self.people, "UPN", "People UPN")
        self.scopes_by_key = _unique(self.scopes, "ScopeKey", "Scopes")
        self.models = read_table(inputs, "Models", required=False)
        self.surfaces = read_table(inputs, "Surfaces", required=False)
        self.agents = read_table(inputs, "Agents", required=False)
        self.outcomes = read_table(inputs, "Outcomes", required=False)
        self.budgets = read_table(inputs, "Budgets", required=False)
        self.model_index = {str(row["Name"]): row for row in self.models}
        self.surface_index = {(str(row["Platform"]), str(row["Name"])): row for row in self.surfaces}
        self.agent_index = {str(row["AgentKey"]): row for row in self.agents}
        self.members: dict[str, set[str]] = {scope: set() for scope in self.scopes_by_key}
        for person in self.people:
            person["UPN"] = str(person["UPN"]).lower()
            if person.get("IsService") or person.get("IsPrivacyRestricted"):
                continue
            for scope in self.ancestors(str(person["ScopeKey"])):
                self.members[scope].add(str(person["PersonKey"]))
        self.eligible = {scope for scope, people in self.members.items() if len(people) >= minimum}
        self.accounts: dict[str, Row] = {}
        self.unpriced = 0

    def ancestors(self, scope: str) -> list[str]:
        result = []
        while scope:
            if scope not in self.scopes_by_key:
                raise ValueError("A reporting scope references an unknown parent")
            if scope in result:
                raise ValueError("The reporting-scope hierarchy contains a cycle")
            result.append(scope)
            scope = str(self.scopes_by_key[scope].get("ParentScopeKey") or "")
        return result

    def model_for(self, event: Event) -> Row:
        name = str(event.get("model") or "Not disclosed")
        if name not in self.model_index:
            row = {
                "ModelKey": key("model", name), "Name": name,
                "Provider": str(event.get("provider") or "Not disclosed"),
                "Tier": str(event.get("tier") or "Not classified"),
                "InputRate": None, "CacheReadRate": None, "CacheWriteRate": None,
                "OutputRate": None, "IsPriced": False,
            }
            self.models.append(row)
            self.model_index[name] = row
        return self.model_index[name]

    def surface_for(self, event: Event) -> Row:
        name = str(event["surface"])
        identity = (str(event["platform"]), name)
        if identity not in self.surface_index:
            row = {
                "SurfaceKey": key("surface", event["platform"], name), "Name": name,
                "Platform": str(event["platform"]),
                "SurfaceType": "API" if event["platform"] == "AI gateway" else "Not classified",
                "WorkCategory": "Not classified",
                "BillingKind": str(event.get("billing_kind") or "not reported"),
            }
            self.surfaces.append(row)
            self.surface_index[identity] = row
        return self.surface_index[identity]

    def estimate(self, event: Event, model: Row) -> float | None:
        if not model.get("IsPriced"):
            return None
        inputs, cached, output = (event.get(field) for field in (
            "input_tokens", "cached_input_tokens", "output_tokens"))
        write = event.get("cache_write_tokens")
        if any(value is None for value in (inputs, cached, output, write)):
            return None
        rates = [model.get(field) for field in (
            "InputRate", "CacheReadRate", "CacheWriteRate", "OutputRate")]
        if any(value is None for value in rates):
            return None
        uncached = inputs - cached - write
        return (uncached * rates[0] + cached * rates[1] + write * rates[2] + output * rates[3]) / 1_000_000

    def usage_rows(self, events: list[Event]) -> list[Row]:
        seen: dict[str, Event] = {}
        normalized = []
        for event in events:
            event = validate_event(event)
            identity = str(event["id"])
            if identity in seen:
                if seen[identity] != event:
                    raise ValueError("A source event identifier was reused with different content")
                continue
            seen[identity] = event
            normalized.append(event)
        billed = {
            (event.get("upn"), event["date"], event.get("model"), event["platform"])
            for event in normalized if event.get("cost_basis") == "billed" and event.get("amount") is not None
        }
        rows = []
        for event in normalized:
            person = self.people_by_upn.get(str(event.get("upn") or "").lower())
            person_key = str(person["PersonKey"]) if person else "unattributed"
            scope = str(event.get("scope") or (person["ScopeKey"] if person else ""))
            if scope not in self.scopes_by_key:
                raise ValueError("Usage requires an explicit, known reporting scope")
            model, surface = self.model_for(event), self.surface_for(event)
            agent_key = str(event.get("agent") or "direct")
            if agent_key not in self.agent_index:
                agent = {
                    "AgentKey": agent_key, "Name": "Direct use" if agent_key == "direct" else agent_key,
                    "Type": "Direct" if agent_key == "direct" else "Unregistered",
                    "ScopeKey": scope, "Platform": str(event["platform"]), "OwnerContact": "",
                    "Status": "Not reviewed", "Risk": "Not reviewed", "PublishedDate": None,
                    "MinutesSavedPerRun": None, "IsRegistered": agent_key == "direct",
                }
                self.agents.append(agent)
                self.agent_index[agent_key] = agent
            account = str(event.get("account") or event.get("upn") or "Unattributed")
            account_key = key("account", person_key, event["platform"], account)
            date = dt.date.fromisoformat(str(event["date"]))
            previous_date = self.accounts.get(account_key, {}).get("DataThroughDate")
            self.accounts[account_key] = {
                "AccountKey": account_key, "PersonKey": person_key,
                "UPN": str(person["UPN"]) if person else "",
                "Platform": str(event["platform"]), "AccountType": "Source identity",
                "MaskedId": mask_account(account),
                "DataThroughDate": max(date, previous_date) if previous_date else date,
            }
            amount = event.get("amount")
            basis = str(event.get("cost_basis") or "not reported")
            actual_key = (event.get("upn"), event["date"], event.get("model"), event["platform"])
            if amount is None and actual_key in billed:
                basis = "billed separately"
            elif amount is None and event.get("billing_kind") in {"tokens", "usage-metrics"}:
                amount = self.estimate(event, model)
                if amount is not None:
                    basis = "estimated"
            if amount is not None and event.get("currency") != self.currency:
                raise ValueError("Mixed-currency usage must be converted by an approved upstream process")
            row = {
                "RowKey": str(event["id"]), "Date": date, "PersonKey": person_key,
                "AccountKey": account_key, "SurfaceKey": surface["SurfaceKey"],
                "ModelKey": model["ModelKey"], "AgentKey": agent_key, "ScopeKey": scope,
                "InputTokens": event.get("input_tokens"), "CachedInputTokens": event.get("cached_input_tokens"),
                "CacheWriteTokens": event.get("cache_write_tokens"), "OutputTokens": event.get("output_tokens"),
                "Requests": event.get("requests"), "Sessions": event.get("sessions"),
                "AgentRuns": event.get("agent_runs"), "PremiumRequests": event.get("premium_requests"),
                "CopilotCredits": event.get("copilot_credits"), "GitHubAiCredits": event.get("github_ai_credits"),
                "Amount": amount, "Currency": self.currency, "CostBasis": basis,
                "Source": str(event["source"]), "BillingKind": str(event.get("billing_kind") or "not reported"),
                "ActivityObserved": bool(event.get("activity")), "IsAttributed": person is not None,
                "RequestUnit": str(event.get("request_unit") or "not reported"),
            }
            rows.append(row)
        if "unattributed" not in self.people_by_key:
            self.people.append({
                "PersonKey": "unattributed", "UPN": "", "DisplayName": "Unattributed service usage",
                "ScopeKey": "", "Company": "", "BusinessUnit": "", "Department": "", "Team": "",
                "JobFamily": "", "EmployeeType": "Service", "IsService": True,
                "IsPrivacyRestricted": True, "HasLicense": False,
            })
        return rows

    def active_people(self, rows: list[Row], scope: str) -> set[str]:
        return {
            str(row["PersonKey"]) for row in rows
            if row.get("ActivityObserved") and str(row["PersonKey"]) in self.members[scope]
        }

    def user_days(self, rows: list[Row], scope: str) -> int:
        return len({
            (row["PersonKey"], row["Date"]) for row in rows
            if row.get("ActivityObserved") and str(row["PersonKey"]) in self.members[scope]
        })

    def is_suppressed(self, rows: list[Row], scope: str) -> bool:
        active = len(self.active_people(rows, scope))
        return len(self.members[scope]) < self.minimum or 0 < active < self.minimum

    def metrics(self, rows: list[Row], scope: str) -> Row:
        suppressed = self.is_suppressed(rows, scope)
        result = {
            column: None if suppressed else reported_sum(rows, column)
            for column in ("Amount",) + COUNTERS
        }
        result.update({
            "ActiveUsers": None if suppressed else len(self.active_people(rows, scope)),
            "UserDays": None if suppressed else self.user_days(rows, scope),
            "PrivacySuppressed": suppressed,
            "UnpricedRows": None if suppressed else sum(
                1 for row in rows if row["Amount"] is None and row["InputTokens"] is not None
                and row["CostBasis"] != "billed separately"),
        })
        return result

    def rows_for_scope(self, rows: list[Row], scope: str) -> list[Row]:
        return [row for row in rows if scope in self.ancestors(str(row["ScopeKey"]))]

    def scope_daily(self, rows: list[Row]) -> list[Row]:
        result = []
        for scope in sorted(self.eligible):
            groups = defaultdict(list)
            for row in self.rows_for_scope(rows, scope):
                groups[(row["Date"], row["SurfaceKey"], row["ModelKey"], row["AgentKey"])].append(row)
            for dimensions, values in sorted(groups.items()):
                data = dict(zip(("Date", "SurfaceKey", "ModelKey", "AgentKey"), dimensions))
                data.update({"ScopeKey": scope, **self.metrics(values, scope)})
                result.append(data)
        return result

    def scope_periods(self, rows: list[Row], anchor: dt.date) -> list[Row]:
        result = []
        for scope in sorted(self.eligible):
            scope_rows = self.rows_for_scope(rows, scope)
            for period in PERIODS:
                start = period_start(anchor, period)
                selected = [row for row in scope_rows if start <= row["Date"] <= anchor]
                metric = self.metrics(selected, scope)
                for field in ("CacheWriteTokens",):
                    metric.pop(field, None)
                metric.update({
                    "ScopeKey": scope, "PeriodLabel": period["Label"],
                    "MemberCount": len(self.members[scope]),
                    "UnattributedAmount": None if metric["PrivacySuppressed"] else reported_sum(
                        [row for row in selected if not row["IsAttributed"]], "Amount"),
                })
                result.append(metric)
        return result

    def scope_weekly(self, rows: list[Row], anchor: dt.date) -> list[Row]:
        result = []
        end = last_complete_saturday(anchor)
        latest_week = sunday(end)
        for scope in sorted(self.eligible):
            scoped = self.rows_for_scope(rows, scope)
            history = self.active_people([row for row in scoped if row["Date"] <= end], scope)
            surfaces = {"all"} | {str(row["SurfaceKey"]) for row in scoped}
            for offset in range(13):
                start = latest_week - dt.timedelta(weeks=offset)
                for surface in sorted(surfaces):
                    selected = [
                        row for row in scoped if start <= row["Date"] <= start + dt.timedelta(days=6)
                        and (surface == "all" or row["SurfaceKey"] == surface)
                    ]
                    days = defaultdict(set)
                    for row in selected:
                        if row["ActivityObserved"] and str(row["PersonKey"]) in self.members[scope]:
                            days[str(row["PersonKey"])].add(row["Date"])
                    metric = self.metrics(selected, scope)
                    bands = {"High": 0, "Moderate": 0, "Low": 0, "None": 0, "NoRecorded": 0}
                    for person in self.members[scope]:
                        count = len(days[person])
                        band = "High" if count >= 4 else "Moderate" if count >= 2 else "Low" if count else (
                            "None" if person in history else "NoRecorded")
                        bands[band] += 1
                    record = {
                        "WeekStart": start, "ScopeKey": scope, "SurfaceKey": surface,
                        **{field: metric[field] for field in (
                            "Amount", "InputTokens", "OutputTokens", "Requests", "AgentRuns",
                            "ActiveUsers", "UserDays", "PrivacySuppressed")},
                        **{band: None if metric["PrivacySuppressed"] else count for band, count in bands.items()},
                    }
                    result.append(record)
        return result

    def agent_periods(self, rows: list[Row], anchor: dt.date) -> list[Row]:
        result = []
        end = last_complete_saturday(anchor)
        last_start, prior_start = end - dt.timedelta(days=41), end - dt.timedelta(days=83)
        for scope in sorted(self.eligible):
            scoped = self.rows_for_scope(rows, scope)
            for agent in self.agents:
                if agent["AgentKey"] == "direct":
                    continue
                agent_rows = [row for row in scoped if row["AgentKey"] == agent["AgentKey"]]
                recent = [row for row in agent_rows if last_start <= row["Date"] <= end]
                prior = [row for row in agent_rows if prior_start <= row["Date"] < last_start]
                recent_users, prior_users = len(self.active_people(recent, scope)), len(self.active_people(prior, scope))

                def intensity(values: list[Row]) -> float | None:
                    weeks = len({
                        (row["PersonKey"], sunday(row["Date"])) for row in values
                        if row["ActivityObserved"] and str(row["PersonKey"]) in self.members[scope]
                    })
                    requests = reported_sum(values, "Requests")
                    return requests / weeks if weeks and requests is not None else None

                recent_intensity, prior_intensity = intensity(recent), intensity(prior)
                trend_suppressed = 0 < recent_users < self.minimum or 0 < prior_users < self.minimum
                user_growth = (recent_users - prior_users) / prior_users if prior_users else None
                intensity_growth = (
                    (recent_intensity - prior_intensity) / prior_intensity
                    if recent_intensity is not None and prior_intensity else None
                )
                if not recent_users and not prior_users:
                    trend = "No observed activity"
                elif not prior_users:
                    trend = "New"
                elif intensity_growth is None:
                    trend = "Insufficient intensity data"
                elif abs(user_growth) <= 0.05 and abs(intensity_growth) <= 0.05:
                    trend = "Stable"
                elif user_growth >= 0 and intensity_growth >= 0:
                    trend = "Scaling"
                elif user_growth >= 0:
                    trend = "Broadening"
                elif intensity_growth >= 0:
                    trend = "Deepening"
                else:
                    trend = "Fading"
                last7 = reported_sum([row for row in agent_rows if anchor - dt.timedelta(days=6) <= row["Date"] <= anchor], "Amount")
                previous = reported_sum([row for row in agent_rows if anchor - dt.timedelta(days=34) <= row["Date"] <= anchor - dt.timedelta(days=7)], "Amount")
                average = previous / 4 if previous is not None else None
                published = agent.get("PublishedDate")
                for period in PERIODS:
                    selected = [row for row in agent_rows if period_start(anchor, period) <= row["Date"] <= anchor]
                    metric = self.metrics(selected, scope)
                    suppressed = metric["PrivacySuppressed"]
                    result.append({
                        "PeriodLabel": period["Label"], "ScopeKey": scope, "AgentKey": agent["AgentKey"],
                        **{field: metric[field] for field in (
                            "Amount", "AgentRuns", "ActiveUsers", "InputTokens", "CachedInputTokens", "OutputTokens")},
                        "Last7Amount": None if suppressed else last7,
                        "Prior4WeekAverage": None if suppressed else average,
                        "SpikeFlag": None if suppressed or last7 is None or not average else last7 >= 2 * average and last7 >= 50,
                        "Idle30Days": None if suppressed else not any(
                            row["AgentRuns"] and anchor - dt.timedelta(days=29) <= row["Date"] <= anchor
                            for row in agent_rows),
                        "NewThisMonth": bool(published and published.replace(day=1) == anchor.replace(day=1)),
                        "UsersLast6Weeks": None if suppressed or 0 < recent_users < self.minimum else recent_users,
                        "UsersPrior6Weeks": None if suppressed or 0 < prior_users < self.minimum else prior_users,
                        "IntensityLast6Weeks": None if suppressed or trend_suppressed else recent_intensity,
                        "IntensityPrior6Weeks": None if suppressed or trend_suppressed else prior_intensity,
                        "UserGrowth": None if suppressed or trend_suppressed else user_growth,
                        "IntensityGrowth": None if suppressed or trend_suppressed else intensity_growth,
                        "TrendClass": "Suppressed" if suppressed or trend_suppressed else trend,
                        "PrivacySuppressed": suppressed,
                    })
        return result

    def build(self, events: list[Event], is_demo: bool = False, summaries: list[dict] | None = None) -> Tables:
        rows = self.usage_rows(events)
        if not rows:
            raise ValueError("No normalized usage records were supplied")
        anchor = max(row["Date"] for row in rows)
        for row in self.outcomes:
            if row["ResolvedDate"] is None or row["ResolutionHours"] is None or row["ResolutionHours"] < 0:
                raise ValueError("Work outcomes require a resolution date and nonnegative elapsed hours")
            if row["HandlingMode"] not in {"Human only", "Agent-assisted", "Agent-resolved"}:
                raise ValueError("Unexpected work-outcome handling mode")
        if any(row["Currency"] != self.currency for row in self.budgets):
            raise ValueError("Budgets must use the configured base currency")
        scopes = []
        for scope in self.scopes:
            if scope["ScopeKey"] in self.eligible:
                scopes.append({**scope, "MemberCount": len(self.members[str(scope["ScopeKey"])])})
        sources = sorted({str(row["Source"]) for row in rows})
        coverage = []
        for source in sources:
            selected = [row for row in rows if row["Source"] == source]
            for metric, field in (("Input tokens", "InputTokens"), ("Cached input", "CachedInputTokens"),
                                  ("Amount", "Amount"), ("Requests", "Requests")):
                known = sum(row[field] is not None for row in selected)
                coverage.append({
                    "Source": source, "Metric": metric, "Granularity": "day",
                    "Status": "Reported" if known == len(selected) else "Partial" if known else "Not reported",
                    "AsOfDate": max(row["Date"] for row in selected),
                    "LoadedAtUTC": dt.datetime.now(dt.timezone.utc).isoformat(),
                    "RowCount": len(selected), "Detail": f"{known} of {len(selected)} records expose this field.",
                })
        period_summary = []
        for summary in summaries or []:
            person = self.people_by_upn.get(str(summary["upn"]).lower())
            if not person:
                continue
            period_summary.append({
                "PersonKey": person["PersonKey"], "Source": summary["source"],
                "StartDate": dt.date.fromisoformat(summary["start"]),
                "EndDate": dt.date.fromisoformat(summary["end"]), "Metric": summary["metric"],
                "Value": summary["value"], "Unit": summary["unit"], "IsConcealed": False,
            })
        calendar = []
        date = min(row["Date"] for row in rows).replace(month=1, day=1)
        end = anchor.replace(month=12, day=31)
        while date <= end:
            week = sunday(date)
            calendar.append({
                "Date": date, "Year": date.year, "MonthNumber": date.month,
                "Month": date.strftime("%B"), "YearMonth": date.strftime("%Y-%m"),
                "MonthStart": date.replace(day=1), "WeekStart": week,
                "WeekLabel": week.isoformat(), "DayName": date.strftime("%A"),
            })
            date += dt.timedelta(days=1)
        tables = {
            "Settings": [{"IsDemo": is_demo, "AnchorDate": anchor, "MinimumGroupSize": self.minimum,
                          "BaseCurrency": self.currency, "SchemaVersion": "1.0"}],
            "People": self.people,
            "ScopeAccess": [row for row in self.access if row["ScopeKey"] in self.eligible],
            "Scopes": scopes, "Accounts": list(self.accounts.values()), "Surfaces": self.surfaces,
            "Models": self.models, "Agents": self.agents, "UsageDaily": rows,
            "ScopeDaily": self.scope_daily(rows), "ScopeWeekly": self.scope_weekly(rows, anchor),
            "ScopePeriod": self.scope_periods(rows, anchor), "AgentPeriod": self.agent_periods(rows, anchor),
            "Outcomes": [row for row in self.outcomes if row["ScopeKey"] in self.eligible],
            "Budgets": [row for row in self.budgets if row["ScopeKey"] in self.eligible],
            "Coverage": coverage, "PeriodSummary": period_summary, "Calendar": calendar,
            "Periods": PERIODS, "Currencies": [{"Code": self.currency, "Multiplier": 1.0, "Symbol": self.currency + " "}],
            "HourlyRate": [{"Rate": value} for value in range(0, 201)],
        }
        validate_tables(tables, self.minimum, production=not is_demo)
        return tables


def validate_tables(tables: Tables, minimum: int = 6, production: bool = False) -> None:
    if minimum < 6 or not tables.get("Settings") or tables["Settings"][0]["MinimumGroupSize"] < 6:
        raise ValueError("The privacy minimum must be at least six")
    minimum = max(minimum, int(tables["Settings"][0]["MinimumGroupSize"]))
    for name, columns in TABLES.items():
        if name not in tables:
            raise ValueError(f"Required table is missing: {name}")
        for row in tables[name]:
            if set(row) - set(columns):
                raise ValueError(f"{name}: a row contains an unknown column")
    people = _unique(tables["People"], "PersonKey", "People")
    scopes = _unique(tables["Scopes"], "ScopeKey", "Scopes")
    models = _unique(tables["Models"], "ModelKey", "Models")
    surfaces = _unique(tables["Surfaces"], "SurfaceKey", "Surfaces")
    agents = _unique(tables["Agents"], "AgentKey", "Agents")
    accounts = _unique(tables["Accounts"], "AccountKey", "Accounts")
    for row in tables["UsageDaily"]:
        for field, dictionary in (("PersonKey", people), ("ModelKey", models), ("SurfaceKey", surfaces),
                                  ("AgentKey", agents), ("AccountKey", accounts)):
            if row[field] not in dictionary:
                raise ValueError(f"UsageDaily has an unknown {field}")
    for scope in scopes.values():
        if scope["MemberCount"] < minimum:
            raise ValueError("Published organization scopes must meet the privacy minimum")
    for name in ("ScopeDaily", "ScopeWeekly", "ScopePeriod", "AgentPeriod"):
        for row in tables[name]:
            if row["ScopeKey"] not in scopes:
                raise ValueError("An aggregate references an unpublished reporting scope")
            if row["PrivacySuppressed"]:
                for field in ("Amount", "InputTokens", "CachedInputTokens", "OutputTokens",
                              "Requests", "AgentRuns", "ActiveUsers", "UserDays"):
                    if field in row and row[field] is not None:
                        raise ValueError("Suppressed rows must not retain sensitive numeric facts")
    if production:
        if tables["Settings"][0]["IsDemo"]:
            raise ValueError("Production data cannot enable the synthetic demonstration mode")
        if any(str(row.get("UPN") or "").endswith("@example.com") for row in tables["People"]):
            raise ValueError("Production data cannot contain the synthetic example.com identities")


def build_from_folder(inputs: Path, output: Path, minimum: int = 6, currency: str = "USD") -> dict:
    path = inputs / "usage.jsonl"
    if not path.is_file():
        raise FileNotFoundError("The input folder requires metadata-only usage.jsonl")
    events = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    summary_path = inputs / "period-summaries.jsonl"
    summaries = [
        json.loads(line) for line in summary_path.read_text(encoding="utf-8").splitlines() if line.strip()
    ] if summary_path.is_file() else []
    tables = GoldBuilder(inputs, minimum, currency).build(events, summaries=summaries)
    write_tables(output, tables)
    return {"tables": len(tables), "usage_records": len(tables["UsageDaily"]),
            "published_scopes": len(tables["Scopes"]), "mode": "Customer data"}
