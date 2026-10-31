from __future__ import annotations

import csv
import datetime as dt
import json
from pathlib import Path

from .collect import write_json_lines
from .normalize import day, event_id, gateway_record, number, validate_event


def json_records(path: Path) -> list[dict]:
    text = path.read_text(encoding="utf-8-sig")
    if text.lstrip().startswith("["):
        value = json.loads(text)
        if not isinstance(value, list):
            raise ValueError("The import requires a JSON array or JSON lines")
        return value
    return [json.loads(line) for line in text.splitlines() if line.strip()]


def credit_record(record: dict, scope: str, currency: str, unit_price: float | None) -> dict:
    if not record.get("resourceId") or not record.get("usageDate"):
        raise ValueError("Credit exports require resourceId and usageDate")
    quantity = number(record.get("consumed"), "consumed")
    if quantity is None:
        raise ValueError("Credit consumption is missing")
    price = number(unit_price, "unit_price")
    return validate_event({
        "id": event_id("copilot-credits", record["resourceId"], record["usageDate"], record.get("environmentId")),
        "date": day(record["usageDate"]), "upn": "", "scope": scope,
        "account": str(record.get("environmentId") or record["resourceId"]),
        "platform": "Copilot Studio", "surface": "Agent credit consumption",
        "agent": str(record["resourceId"]), "model": "Not disclosed",
        "source": "Copilot credit export", "copilot_credits": quantity,
        "github_ai_credits": None, "billing_kind": "copilot-credits",
        "amount": quantity * price if price is not None else None,
        "currency": currency, "cost_basis": "estimated" if price is not None else "not reported",
        "request_unit": "not reported", "activity": quantity > 0,
    })


def audit_record(record: dict, scope: str) -> dict | None:
    if record.get("Operation") != "CopilotInteraction":
        return None
    if not record.get("Id") or not record.get("CreationTime"):
        raise ValueError("Copilot audit records require Id and CreationTime")
    data = record.get("CopilotEventData") or record.get("CopilotInteractionEventData") or {}
    messages = data.get("Messages")
    prompts = sum(message.get("isPrompt") is True for message in messages) if isinstance(messages, list) else None
    return validate_event({
        "id": event_id("audit", record["Id"]), "date": day(record["CreationTime"]),
        "upn": str(record.get("UserId") or "").lower(), "scope": scope,
        "account": str(record.get("UserId") or ""), "platform": "Microsoft 365 Copilot",
        "surface": str(data.get("AppHost") or record.get("AppHost") or "Copilot interaction"),
        "agent": str(data.get("AgentId") or "direct"), "model": "Not disclosed",
        "source": "Purview audit interaction metadata", "requests": prompts,
        "billing_kind": "licence-included", "request_unit": "audit-prompt",
        "amount": None, "currency": "USD", "cost_basis": "not usage billed", "activity": True,
    })


def focus_records(path: Path, scope: str, service_filter: str) -> list[dict]:
    if not service_filter.strip():
        raise ValueError("FOCUS imports require an explicit AI service filter")
    output = []
    with path.open(encoding="utf-8-sig", newline="") as stream:
        for record in csv.DictReader(stream):
            if service_filter.lower() not in str(record.get("ServiceName") or "").lower():
                continue
            required = ("ChargePeriodStart", "BilledCost", "BillingCurrency", "ResourceId")
            if any(record.get(field) in (None, "") for field in required):
                raise ValueError("The FOCUS export is missing required billed-cost fields")
            output.append(validate_event({
                "id": event_id("focus", record["ChargePeriodStart"], record["ResourceId"],
                               record.get("SkuId"), record.get("ChargeDescription"), record["BilledCost"]),
                "date": day(record["ChargePeriodStart"]), "upn": "", "scope": scope,
                "account": event_id("resource", record["ResourceId"])[:16],
                "platform": "Azure billed AI cost", "surface": "Unattributed billing surface",
                "model": "Not disclosed", "source": "FOCUS billed cost export",
                "amount": number(record["BilledCost"], "BilledCost", allow_negative=True),
                "currency": record["BillingCurrency"], "cost_basis": "billed",
                "billing_kind": "billed-cost", "request_unit": "not reported", "activity": False,
            }))
    if not output:
        raise ValueError("No FOCUS records matched the explicitly selected AI service")
    return output


def import_source(
    kind: str, input_file: Path, output: Path, scope: str,
    currency: str = "USD", unit_price: float | None = None, service_filter: str = "",
) -> dict:
    if not scope:
        raise ValueError("Imports require an explicit reporting scope")
    if kind == "focus":
        events = focus_records(input_file, scope, service_filter)
    else:
        records = json_records(input_file)
        events = []
        for record in records:
            if kind == "gateway":
                safe = dict(record)
                safe["scope"] = scope
                events.append(gateway_record(safe))
            elif kind == "credits":
                events.append(credit_record(record, scope, currency, unit_price))
            elif kind == "audit":
                event = audit_record(record, scope)
                if event:
                    events.append(event)
            elif kind == "normalized":
                event = dict(record)
                event["scope"] = scope
                events.append(validate_event(event))
            else:
                raise ValueError("Unsupported metadata import type")
    if not events:
        raise ValueError("The import produced no usage metadata records")
    write_json_lines(output, events)
    return {"source": kind, "normalized_records": len(events), "scope": scope,
            "prompts_or_responses_retained": False}

