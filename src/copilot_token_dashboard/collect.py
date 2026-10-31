from __future__ import annotations

import datetime as dt
import json
import os
import re
from pathlib import Path

import msal

from .http import ApiClient, download_report
from .normalize import github_billing, github_usage, m365_report


def load_settings(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("schema_version") != "1.0":
        raise ValueError("Configuration must use schema_version 1.0")
    return data


def required_secret(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise ValueError(f"Required secret environment variable is not configured: {name}")
    return value


def graph_token(settings: dict) -> str:
    tenant = str(settings.get("tenant_id") or "")
    client = str(settings.get("graph_client_id") or "")
    uuid = r"[a-fA-F0-9]{8}-([a-fA-F0-9]{4}-){3}[a-fA-F0-9]{12}"
    if not re.fullmatch(uuid, tenant) or not re.fullmatch(uuid, client):
        raise ValueError("A single-tenant tenant_id and graph_client_id are required")
    secret_name = settings.get("m365", {}).get(
        "client_secret_environment_variable", "CTD_GRAPH_CLIENT_SECRET")
    application = msal.ConfidentialClientApplication(
        client, authority="https://login.microsoftonline.com/" + tenant,
        client_credential=required_secret(secret_name),
    )
    result = application.acquire_token_for_client(["https://graph.microsoft.com/.default"])
    if "access_token" not in result:
        raise RuntimeError("Microsoft Graph authentication failed: " + str(result.get("error", "unknown")))
    return result["access_token"]


def write_json_lines(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as stream:
        for row in rows:
            stream.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")


def collect_github(settings: dict, date: dt.date, output: Path, include_billing: bool = False) -> dict:
    config = settings.get("github", {})
    scope_type = config.get("scope_type")
    scope_name = str(config.get("scope_name") or "")
    if scope_type not in {"enterprise", "organization"} or not re.fullmatch(r"[A-Za-z0-9_.-]+", scope_name):
        raise ValueError("Configure a valid GitHub enterprise or organization scope")
    root_scope = str(config.get("root_scope_key") or "")
    if not root_scope:
        raise ValueError("github.root_scope_key is required for explicit organization attribution")
    mapping_path = config.get("login_map_file")
    mapping = {}
    if mapping_path:
        import csv
        with Path(mapping_path).open(encoding="utf-8-sig", newline="") as stream:
            for row in csv.DictReader(stream):
                mapping[row["login"].lower()] = row["upn"].lower()
    token = required_secret(config.get("token_environment_variable", "CTD_GITHUB_TOKEN"))
    client = ApiClient("https://api.github.com", token)
    headers = {"Accept": "application/vnd.github+json",
               "X-GitHub-Api-Version": config.get("api_version", "2026-03-10")}
    prefix = "/enterprises/" if scope_type == "enterprise" else "/orgs/"
    endpoint = prefix + scope_name + "/copilot/metrics/reports/users-1-day"
    response = client.get_json(endpoint, {"day": date.isoformat()}, headers)
    links = response.get("download_links")
    if not isinstance(links, list) or not links:
        raise ValueError("The usage API did not return report download links")
    records = []
    for link in links:
        text = download_report(link).decode("utf-8-sig")
        stripped = text.lstrip()
        if stripped.startswith("["):
            value = json.loads(text)
            if not isinstance(value, list):
                raise ValueError("Unexpected usage-report JSON")
            records.extend(value)
        else:
            records.extend(json.loads(line) for line in text.splitlines() if line.strip())
    events = github_usage(records, mapping, root_scope)
    if include_billing:
        if scope_type != "enterprise":
            raise ValueError("Automatic per-user billing collection currently requires enterprise scope")
        for login in sorted({record["user_login"].lower() for record in records}):
            for kind in ("premium_request", "ai_credit"):
                body = client.get_json(
                    "/enterprises/" + scope_name + "/settings/billing/" + kind + "/usage",
                    {"year": date.year, "month": date.month, "day": date.day, "user": login}, headers,
                )
                events.extend(github_billing(body, date, login, mapping.get(login, ""), root_scope))
    write_json_lines(output, events)
    return {
        "source": "GitHub", "day": date.isoformat(), "records": len(records),
        "normalized_records": len(events), "unmapped_users": sum(
            1 for record in records if record["user_login"].lower() not in mapping),
        "billing_scope_note": "Per-user billing covers users present in this daily report; reconcile to a full billing export.",
    }


def collect_m365(settings: dict, output: Path) -> dict:
    config = settings.get("m365", {})
    period = config.get("period", "D28")
    if period not in {"D7", "D28", "D90", "D180"}:
        raise ValueError("Microsoft 365 collection supports D7, D28, D90 or D180")
    client = ApiClient("https://graph.microsoft.com", graph_token(settings))
    endpoint = "/v1.0/copilot/reports/getMicrosoft365CopilotUsageUserDetail(period='" + period + "',version='v2')"
    response = client.request("GET", endpoint)
    if response.status_code in {302, 303}:
        location = response.headers.get("Location")
        if not location:
            raise ValueError("The Graph report redirect did not include a location")
        text = download_report(location).decode("utf-8-sig")
    else:
        text = response.content.decode("utf-8-sig")
    events, summaries, status = m365_report(text, int(period[1:]))
    write_json_lines(output, events)
    write_json_lines(output.with_name(output.stem + ".period-summary.jsonl"), summaries)
    status.update({"source": "Microsoft 365", "normalized_records": len(events), "period_summaries": len(summaries)})
    return status


def collect_directory(settings: dict, output: Path) -> dict:
    client = ApiClient("https://graph.microsoft.com", graph_token(settings))
    users = client.paged_values(
        "/v1.0/users?$select=id,userPrincipalName,displayName,department,companyName,jobTitle,accountEnabled,assignedLicenses"
    )
    minimal = [
        {"id": user["id"], "upn": user.get("userPrincipalName"),
         "name": user.get("displayName"), "department": user.get("department"),
         "company": user.get("companyName"), "enabled": user.get("accountEnabled"),
         "licensed": bool(user.get("assignedLicenses"))}
        for user in users
    ]
    write_json_lines(output, minimal)
    return {"source": "Entra directory", "users": len(minimal),
            "detail": "A reviewed HR/organization mapping is required before building reporting scopes."}

