from __future__ import annotations

import csv
import datetime as dt
import hashlib
import io
import json
import math
import re
from collections.abc import Iterable
from decimal import Decimal, InvalidOperation

Event = dict[str, str | int | float | bool | None]

SENSITIVE_KEYS = {
    "prompt", "prompt_text", "response_text", "messages", "access_token",
    "api_key", "client_secret", "password", "document_text", "ip_address",
}


def number(value: object, field: str, integer: bool = False, allow_negative: bool = False) -> int | float | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        raise ValueError(f"{field}: Boolean values are not numeric counters")
    try:
        exact = Decimal(str(value))
    except InvalidOperation as error:
        raise ValueError(f"{field}: expected a numeric value") from error
    if not exact.is_finite() or (exact < 0 and not allow_negative):
        raise ValueError(f"{field}: expected a finite nonnegative number")
    if integer:
        if exact != exact.to_integral_value() or exact > 9223372036854775807:
            raise ValueError(f"{field}: expected an integer counter")
        return int(exact)
    numeric = float(exact)
    if not math.isfinite(numeric):
        raise ValueError(f"{field}: expected a finite number")
    return numeric


def day(value: object) -> str:
    if not isinstance(value, str):
        raise ValueError("A source date is required")
    return dt.date.fromisoformat(value[:10]).isoformat()


def event_id(*parts: object) -> str:
    return hashlib.sha256(
        json.dumps(parts, ensure_ascii=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def validate_event(event: Event) -> Event:
    if SENSITIVE_KEYS & set(event):
        raise ValueError("Usage input must contain metadata only, never secrets or prompt content")
    required = ("id", "date", "platform", "surface", "source")
    if any(not event.get(key) for key in required):
        raise ValueError("Usage metadata is missing a required identity, date or source field")
    result = dict(event)
    result["date"] = day(result["date"])
    for key in ("input_tokens", "cached_input_tokens", "cache_write_tokens",
                "output_tokens", "sessions", "agent_runs"):
        result[key] = number(result.get(key), key, integer=True)
    for key in ("requests", "premium_requests", "copilot_credits", "github_ai_credits", "amount"):
        result[key] = number(result.get(key), key, allow_negative=key == "amount")
    input_tokens = result["input_tokens"]
    cached = result["cached_input_tokens"]
    write = result["cache_write_tokens"]
    if input_tokens is not None and cached is not None and cached > input_tokens:
        raise ValueError("Cached input cannot exceed total input")
    if input_tokens is not None and cached is not None and write is not None:
        if cached + write > input_tokens:
            raise ValueError("Cache-read plus cache-write tokens cannot exceed total input")
    if result["amount"] is not None and not result.get("currency"):
        raise ValueError("An amount requires an explicit currency")
    upn = str(result.get("upn") or "").strip().lower()
    if upn and not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", upn):
        raise ValueError("An attributed usage record requires a valid UPN")
    result["upn"] = upn
    return result


def _github_usage_event(
    record: dict, surface: str, model: str | None, counts: dict,
    scope: str, upn: str, label: str,
) -> Event:
    token_usage = counts.get("token_usage") or {}
    return validate_event({
        "id": event_id("github-usage", record["day"], record["user_login"], surface, model, label),
        "date": record["day"], "upn": upn, "account": record["user_login"],
        "scope": scope, "platform": "GitHub Copilot", "surface": surface,
        "model": model or "Not disclosed", "provider": "Not disclosed", "tier": "Not classified",
        "source": "GitHub usage metrics", "billing_kind": "usage-metrics",
        "input_tokens": token_usage.get("prompt_tokens_sum"),
        "output_tokens": token_usage.get("output_tokens_sum"),
        "cached_input_tokens": None, "cache_write_tokens": None,
        "requests": counts.get("request_count"), "sessions": counts.get("session_count"),
        "request_unit": "successful-model-request", "activity": True,
        "amount": None, "currency": "USD", "cost_basis": "not reported",
    })


def github_usage(records: Iterable[dict], login_map: dict[str, str], scope: str) -> list[Event]:
    output = []
    for record in records:
        if not record.get("day") or not record.get("user_login"):
            raise ValueError("A GitHub daily record is missing day or user_login")
        login = str(record["user_login"]).lower()
        upn = login_map.get(login, "")
        clients = record.get("totals_by_client") or []
        represented = set()
        for client in clients:
            client_name = str(client.get("client") or "Unidentified client")
            represented.add(client_name)
            models = client.get("totals_by_model") or []
            if not models:
                output.append(_github_usage_event(record, client_name, None, client, scope, upn, "client"))
                continue
            for model in models:
                output.append(_github_usage_event(
                    record, client_name, model.get("model"), model, scope, upn, "model"))
            for counter in ("request_count",):
                parent = number(client.get(counter), counter)
                children = [number(model.get(counter), counter) for model in models]
                if parent is not None and all(value is not None for value in children):
                    if sum(children) > parent:
                        raise ValueError("GitHub model totals exceed the client total")
            parent_tokens = client.get("token_usage") or {}
            residual = {"token_usage": {}}
            has_residual = False
            for key in ("request_count", "session_count"):
                total = number(client.get(key), key)
                leaves = [number(model.get(key), key) for model in models]
                if total is not None and all(value is not None for value in leaves):
                    remainder = total - sum(leaves)
                    if remainder < 0:
                        raise ValueError("GitHub child metrics exceed their parent")
                    residual[key] = remainder
                    has_residual = has_residual or remainder > 0
            parent_sessions = number(client.get("session_count"), "session_count", integer=True)
            if parent_sessions is not None and all(model.get("session_count") is None for model in models):
                residual["session_count"] = parent_sessions
                has_residual = True
            for key in ("prompt_tokens_sum", "output_tokens_sum"):
                total = number(parent_tokens.get(key), key, integer=True)
                leaves = [number((model.get("token_usage") or {}).get(key), key, integer=True)
                          for model in models]
                if total is not None and all(value is not None for value in leaves):
                    remainder = total - sum(leaves)
                    if remainder < 0:
                        raise ValueError("GitHub child token totals exceed their parent")
                    residual["token_usage"][key] = remainder
                    has_residual = has_residual or remainder > 0
            if has_residual:
                output.append(_github_usage_event(record, client_name, None, residual, scope, upn, "residual"))
        cli = record.get("totals_by_cli")
        if cli and not clients:
            output.append(_github_usage_event(record, "copilot_cli", None, cli, scope, upn, "cli"))
        app = record.get("totals_by_copilot_app")
        if app and "copilot_app" not in represented:
            output.append(_github_usage_event(record, "copilot_app", None, app, scope, upn, "app"))
        if not clients and not cli and not app:
            output.append(validate_event({
                "id": event_id("github-activity", record["day"], login),
                "date": record["day"], "upn": upn, "account": login,
                "scope": scope, "platform": "GitHub Copilot", "surface": "Activity only",
                "model": "Not disclosed", "source": "GitHub usage metrics",
                "request_unit": "not reported", "billing_kind": "usage-metrics",
                "activity": bool(record.get("user_initiated_interaction_count")
                                 or record.get("code_generation_activity_count")
                                 or record.get("used_agent") or record.get("used_cli")),
                "cost_basis": "not reported", "currency": "USD",
            }))
    return output


def github_billing(body: dict, date: dt.date, login: str, upn: str, scope: str) -> list[Event]:
    items = body.get("usageItems")
    if not isinstance(items, list):
        raise ValueError("The GitHub billing response is missing usageItems")
    output = []
    for item in items:
        if "netAmount" not in item or "netQuantity" not in item:
            raise ValueError("The GitHub billing record is missing billed amount or quantity")
        unit = str(item.get("unitType") or "").lower()
        premium = "request" in unit or "premium" in str(item.get("sku") or "").lower()
        quantity = number(item["netQuantity"], "netQuantity")
        output.append(validate_event({
            "id": event_id("github-billing", date.isoformat(), login, item.get("product"),
                           item.get("sku"), item.get("model"), unit),
            "date": date.isoformat(), "upn": upn, "account": login, "scope": scope,
            "platform": "GitHub Copilot", "surface": "Unattributed billing surface",
            "model": str(item.get("model") or "Not disclosed"), "source": "GitHub billing",
            "premium_requests": quantity if premium else None,
            "github_ai_credits": None if premium else quantity,
            "copilot_credits": None, "amount": item["netAmount"], "currency": "USD",
            "cost_basis": "billed", "billing_kind": "premium-requests" if premium else "github-ai-credits",
            "activity": False, "request_unit": "not reported",
        }))
    return output


def _normal_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.lower())


def m365_report(text: str, period_days: int) -> tuple[list[Event], list[dict], dict]:
    records = list(csv.DictReader(io.StringIO(text.lstrip("\ufeff"))))
    if not records:
        raise ValueError("The Microsoft 365 report contains no records")
    events, summaries, concealed = [], [], 0
    app_names = {
        "copilotchatlastactivitydate": "Copilot Chat",
        "microsoftteamscopilotlastactivitydate": "Teams",
        "wordcopilotlastactivitydate": "Word", "excelcopilotlastactivitydate": "Excel",
        "powerpointcopilotlastactivitydate": "PowerPoint", "outlookcopilotlastactivitydate": "Outlook",
        "onenotecopilotlastactivitydate": "OneNote", "loopcopilotlastactivitydate": "Loop",
        "copilotchatworklastactivitydate": "Copilot Chat work",
        "copilotchatweblastactivitydate": "Copilot Chat web",
        "microsoft365copilotlastactivitydate": "Microsoft 365 Copilot",
        "edgelastactivitydate": "Edge", "copilotagentlastactivitydate": "Copilot Agent",
    }
    for raw in records:
        record = {_normal_key(key): value for key, value in raw.items()}
        if "userprincipalname" not in record or "reportrefreshdate" not in record:
            raise ValueError("Unexpected Microsoft 365 CSV headers; review the current report schema")
        upn = record["userprincipalname"].strip().lower()
        refresh = dt.date.fromisoformat(record["reportrefreshdate"][:10])
        is_concealed = bool(re.fullmatch(r"[a-f0-9]{32,64}", upn))
        concealed += int(is_concealed)
        if is_concealed:
            continue
        for key, surface in app_names.items():
            if record.get(key):
                date = day(record[key])
                events.append(validate_event({
                    "id": event_id("m365-presence", upn, surface, date),
                    "date": date, "upn": upn, "account": upn,
                    "platform": "Microsoft 365 Copilot", "surface": surface,
                    "model": "Not disclosed", "source": "Microsoft 365 usage reports",
                    "billing_kind": "licence-included", "activity": True,
                    "request_unit": "not reported", "amount": None, "currency": "USD",
                    "cost_basis": "not usage billed",
                }))
        for key, value in record.items():
            if ("prompt" in key and ("allapp" in key or "anyapp" in key)) or (
                "active" in key and "days" in key and ("allapp" in key or "anyapp" in key)
            ):
                summaries.append({
                    "upn": upn, "source": "Microsoft 365 usage reports",
                    "start": (refresh - dt.timedelta(days=period_days - 1)).isoformat(),
                    "end": refresh.isoformat(), "metric": "Prompts" if "prompt" in key else "Active days",
                    "value": number(value, key), "unit": "period-total", "concealed": False,
                })
    return events, summaries, {
        "records": len(records), "concealed_records": concealed,
        "detail": "Last-activity observations are not a complete reconstruction of daily usage.",
    }


def gateway_record(record: dict) -> Event:
    input_tokens = number(record.get("prompt_tokens"), "prompt_tokens", integer=True)
    cached = number(record.get("cached_tokens"), "cached_tokens", integer=True)
    return validate_event({
        "id": str(record.get("request_id") or event_id("gateway", record)),
        "date": day(record.get("timestamp")), "upn": str(record.get("upn") or "").lower(),
        "account": str(record.get("account") or ""), "scope": str(record.get("scope") or ""),
        "platform": "AI gateway", "surface": str(record.get("surface") or "API"),
        "model": str(record.get("model") or "Not disclosed"),
        "provider": str(record.get("provider") or "Not disclosed"),
        "agent": str(record.get("agent") or "direct"),
        "source": "Gateway token metadata", "billing_kind": "tokens",
        "input_tokens": input_tokens, "cached_input_tokens": cached,
        "cache_write_tokens": record.get("cache_write_tokens"),
        "output_tokens": record.get("completion_tokens"),
        "requests": 1, "agent_runs": record.get("agent_runs"),
        "request_unit": "successful-model-request", "activity": True,
        "amount": record.get("amount"), "currency": str(record.get("currency") or "USD"),
        "cost_basis": "billed" if record.get("amount") is not None else "not reported",
    })
