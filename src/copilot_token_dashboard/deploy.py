from __future__ import annotations

import base64
import datetime as dt
import json
import os
import time
import uuid
from pathlib import Path
from urllib.parse import unquote, urlparse

from .http import ApiClient, retry_delay, validate_https
from .schema import TABLES, read_table
from .gold import validate_tables

PRODUCT = "Copilot Token Dashboard"


def token_tenant(token: str) -> str:
    parts = token.split(".")
    if len(parts) != 3:
        raise ValueError("The Fabric access token must be a tenant-scoped JWT")
    segment = parts[1] + "=" * (-len(parts[1]) % 4)
    claims = json.loads(base64.urlsafe_b64decode(segment))
    tenant = claims.get("tid")
    if not isinstance(tenant, str):
        raise ValueError("The access token does not identify its tenant")
    return str(uuid.UUID(tenant))


def part(path: str, data: bytes) -> dict:
    return {"path": path, "payload": base64.b64encode(data).decode("ascii"), "payloadType": "InlineBase64"}

def source_settings(mode: str, data_folder: Path | None, site: str = "", folder: str = "") -> dict[str, str]:
    if mode not in {"Demo", "CSV", "SharePoint"}:
        raise ValueError("Source mode must be Demo, CSV or SharePoint")
    if mode != "Demo" and (data_folder is None or not data_folder.is_dir()):
        raise ValueError("Customer data modes require an existing reporting-table folder")
    if mode == "SharePoint":
        site_url, folder_url = urlparse(site), urlparse(folder)
        if (validate_https(site) != validate_https(folder)
                or site_url.query or site_url.fragment or folder_url.query or folder_url.fragment
                or not folder.startswith(site.rstrip("/") + "/") or not folder.endswith("/")
                or ".." in unquote(folder_url.path).split("/")):
            raise ValueError("SharePoint requires an exact HTTPS folder under its site, with a trailing slash")
    return {
        "SourceMode": mode, "DataFolder": str(data_folder.resolve()) if data_folder else "",
        "SharePointSite": site, "SharePointFolder": folder,
    }


def configured_model(project: Path, mode: str, data_folder: Path | None, site: str = "", folder: str = "") -> dict:
    values = source_settings(mode, data_folder, site, folder)
    directory = project / (PRODUCT + ".SemanticModel")
    model = json.loads((directory / "model.bim").read_text(encoding="utf-8-sig"))
    parameters = {expression["name"]: expression for expression in model["model"]["expressions"]}
    if not values.keys() <= parameters.keys():
        raise ValueError("The model is missing a required source parameter")
    for name, value in values.items():
        old = parameters[name]["expression"]
        if " meta " not in old:
            raise ValueError("The model source parameter is missing its Power Query metadata")
        parameters[name]["expression"] = '"' + value.replace('"', '""') + '"' + old[old.index(" meta "):]
    return model


def semantic_parts(project: Path, mode: str, data_folder: Path | None, site: str, folder: str) -> list[dict]:
    directory = project / (PRODUCT + ".SemanticModel")
    model = configured_model(project, mode, data_folder, site, folder)
    return [
        part("model.bim", json.dumps(model, ensure_ascii=False).encode("utf-8")),
        part("definition.pbism", (directory / "definition.pbism").read_bytes()),
    ]


def report_parts(project: Path, model_id: str) -> list[dict]:
    directory = project / (PRODUCT + ".Report")
    definition = json.loads((directory / "definition.pbir").read_text(encoding="utf-8"))
    definition["datasetReference"] = {"byConnection": {"connectionString": "semanticmodelid=" + model_id}}
    result = [part("definition.pbir", json.dumps(definition).encode())]
    for file in sorted((directory / "definition").rglob("*.json")):
        result.append(part(file.relative_to(directory).as_posix(), file.read_bytes()))
    for file in sorted((directory / "StaticResources").rglob("*")) if (directory / "StaticResources").exists() else []:
        if file.is_file():
            result.append(part(file.relative_to(directory).as_posix(), file.read_bytes()))
    return result


class FabricDeployer:
    def __init__(self, client: ApiClient, workspace: str, timeout_seconds: int = 600) -> None:
        self.client, self.workspace = client, str(uuid.UUID(workspace))
        self.timeout_seconds = timeout_seconds

    def wait_operation(self, response, expects_item: bool = True) -> dict:
        if response.status_code in {200, 201}:
            result = response.json()
            if expects_item and not result.get("id"):
                raise ValueError("Fabric did not return a created item identifier")
            return result
        if response.status_code == 204 and not expects_item:
            return {}
        if response.status_code != 202:
            raise ValueError("Fabric returned an unexpected provisioning status")
        location = response.headers.get("Location")
        if not location:
            raise ValueError("Fabric did not return its long-running operation location")
        deadline = time.monotonic() + self.timeout_seconds
        while time.monotonic() < deadline:
            self.client.sleep(retry_delay(response.headers.get("Retry-After"), 1))
            status_response = self.client.request("GET", location)
            status = status_response.json().get("status")
            if status == "Succeeded":
                if not expects_item:
                    return {}
                result = self.client.get_json(location.rstrip("/") + "/result")
                if not result.get("id"):
                    raise ValueError("The completed operation did not return an item identifier")
                return result
            if status in {"Failed", "Cancelled"}:
                raise RuntimeError("Fabric provisioning ended with status " + str(status))
            if status not in {"NotStarted", "Running"}:
                raise ValueError("Fabric returned an unknown operation status")
            response = status_response
        raise TimeoutError("Fabric provisioning is still running; inspect the workspace before retrying")

    def existing(self, kind: str, name: str) -> dict | None:
        path = f"/v1/workspaces/{self.workspace}/{kind}"
        matches, visited = [], set()
        while path:
            if path in visited:
                raise ValueError("Fabric item listing returned a continuation cycle")
            visited.add(path)
            response = self.client.get_json(path)
            items = response.get("value")
            continuation = response.get("continuationUri")
            if (not isinstance(items, list) or (continuation is not None and not isinstance(continuation, str))
                    or any(not isinstance(item, dict) or not item.get("id")
                           or not isinstance(item.get("displayName"), str) for item in items)):
                raise ValueError("Fabric item listing has an invalid response shape")
            for item in items:
                if item.get("displayName") == name:
                    matches.append(item)
            path = continuation or ""
        if len(matches) > 1:
            raise ValueError("More than one item matches the requested display name")
        return matches[0] if matches else None

    def publish(self, kind: str, name: str, parts: list[dict], update: bool = False) -> dict:
        existing = self.existing(kind, name)
        if existing:
            if not update:
                raise ValueError("The workspace already contains this item; use --update explicitly")
            item_id = existing["id"]
            response = self.client.request(
                "POST", f"/v1/workspaces/{self.workspace}/{kind}/{item_id}/updateDefinition",
                json_body={"definition": {"parts": parts}},
            )
            self.wait_operation(response, expects_item=False)
            return existing
        response = self.client.request(
            "POST", f"/v1/workspaces/{self.workspace}/{kind}",
            json_body={"displayName": name, "description": "Tenant-owned AI usage reporting.",
                       "definition": {"parts": parts}},
        )
        return self.wait_operation(response)


def deploy(
    project: Path, tenant: str, workspace: str, mode: str,
    data_folder: Path | None = None, site: str = "", folder: str = "",
    update: bool = False, output: Path | None = None,
) -> dict:
    tenant, workspace = str(uuid.UUID(tenant)), str(uuid.UUID(workspace))
    source_settings(mode, data_folder, site, folder)
    if mode != "Demo":
        if not data_folder:
            raise ValueError("Customer deployments require a locally validated reporting-table folder")
        tables = {name: read_table(data_folder, name) for name in TABLES}
        validate_tables(tables, production=True)
    token = os.environ.get("CTD_FABRIC_ACCESS_TOKEN")
    if not token:
        raise ValueError("Set CTD_FABRIC_ACCESS_TOKEN through your own tenant authentication")
    if token_tenant(token) != tenant:
        raise ValueError("The Fabric token belongs to a different tenant; deployment stopped")
    client = ApiClient("https://api.fabric.microsoft.com", token)
    publisher = FabricDeployer(client, workspace)
    model = publisher.publish(
        "semanticModels", PRODUCT, semantic_parts(project, mode, data_folder, site, folder), update)
    report = publisher.publish(
        "reports", PRODUCT, report_parts(project, model["id"]), update)
    result = {
        "tenant_id": tenant, "workspace_id": workspace, "semantic_model_id": model["id"],
        "report_id": report["id"], "source_mode": mode,
        "state": "Provisioned; security and refresh configuration required",
        "report_url": f"https://app.powerbi.com/groups/{workspace}/reports/{report['id']}",
        "next_steps": [
            "Assign approved security groups to the Viewer semantic-model role.",
            "Configure tenant-owned data-source credentials and gateway if required.",
            "Refresh the semantic model and verify expected values.",
            "Test as actual Viewer users, then create and publish the Power BI app audiences.",
        ],
        "completed_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
    }
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result
