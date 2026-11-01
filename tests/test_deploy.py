import base64
import json
import uuid

import pytest

from copilot_token_dashboard.deploy import FabricDeployer, report_parts, token_tenant
from copilot_token_dashboard.http import ApiClient, ApiError

TENANT = "11111111-1111-4111-8111-111111111111"
WORKSPACE = "22222222-2222-4222-8222-222222222222"
MODEL = "33333333-3333-4333-8333-333333333333"


class Response:
    def __init__(self, status, body=None, headers=None):
        self.status_code, self.body, self.headers = status, body or {}, headers or {}

    def json(self):
        return self.body


class Session:
    def __init__(self, responses):
        self.responses, self.calls = list(responses), []

    def request(self, method, url, **kwargs):
        self.calls.append((method, url, kwargs))
        return self.responses.pop(0)


def client(responses):
    session = Session(responses)
    return ApiClient("https://api.fabric.microsoft.com", "example-not-a-live-token", session, lambda _: None), session


def test_tenant_is_explicitly_checked_without_logging_token():
    payload = base64.urlsafe_b64encode(json.dumps({"tid": TENANT}).encode()).decode().rstrip("=")
    assert token_tenant("header." + payload + ".signature") == TENANT
    with pytest.raises(ValueError, match="tenant-scoped"):
        token_tenant("opaque")


def test_create_item_and_complete_operation():
    operation = "https://api.fabric.microsoft.com/v1/operations/example"
    api, session = client([
        Response(200, {"value": []}),
        Response(202, headers={"Location": operation, "Retry-After": "0"}),
        Response(200, {"status": "Running"}, {"Retry-After": "0"}),
        Response(200, {"status": "Succeeded"}),
        Response(200, {"id": MODEL, "displayName": "Example"}),
    ])
    item = FabricDeployer(api, WORKSPACE).publish("semanticModels", "Example", [{"path": "model.bim"}])
    assert item["id"] == MODEL
    assert session.calls[1][1].endswith("/semanticModels")
    assert session.calls[-1][1].endswith("/result")


def test_existing_content_requires_explicit_update():
    api, session = client([Response(200, {"value": [{"id": MODEL, "displayName": "Example"}]})])
    with pytest.raises(ValueError, match="--update"):
        FabricDeployer(api, WORKSPACE).publish("semanticModels", "Example", [])
    assert len(session.calls) == 1


def test_failed_operation_is_not_success_shaped():
    operation = "https://api.fabric.microsoft.com/v1/operations/example"
    api, _ = client([Response(200, {"status": "Failed"})])
    response = Response(202, headers={"Location": operation, "Retry-After": "0"})
    with pytest.raises(RuntimeError, match="Failed"):
        FabricDeployer(api, WORKSPACE).wait_operation(response)


def test_created_item_must_have_identifier():
    api, _ = client([])
    with pytest.raises(ValueError, match="identifier"):
        FabricDeployer(api, WORKSPACE).wait_operation(Response(201, {"displayName": "Example"}))


def test_creation_post_is_not_blindly_replayed():
    api, session = client([Response(503), Response(201, {"id": MODEL})])
    with pytest.raises(ApiError):
        api.request("POST", "/v1/workspaces/" + WORKSPACE + "/semanticModels", json_body={"displayName": "Example"})
    assert len(session.calls) == 1


def test_report_rebinding_uses_published_model_identifier(tmp_path):
    folder = tmp_path / "Copilot Token Dashboard.Report"
    (folder / "definition").mkdir(parents=True)
    (folder / "definition.pbir").write_text(json.dumps({
        "version": "4.0",
        "datasetReference": {"byPath": {"path": "../Local.SemanticModel"}},
    }), encoding="utf-8")
    (folder / "definition" / "report.json").write_text("{}", encoding="utf-8")
    parts = report_parts(tmp_path, MODEL)
    definition = json.loads(base64.b64decode(parts[0]["payload"]))
    assert definition["datasetReference"] == {
        "byConnection": {"connectionString": "semanticmodelid=" + MODEL}
    }
    assert "byPath" not in json.dumps(definition)
    assert all(item["payloadType"] == "InlineBase64" for item in parts)


@pytest.mark.parametrize("body", [
    {"unexpected": "shape"},
    {"value": {}},
    {"value": [None]},
    {"value": [], "continuationUri": 1},
])
def test_invalid_workspace_listing_is_not_treated_as_empty(body):
    api, session = client([Response(200, body)])
    with pytest.raises(ValueError, match="listing"):
        FabricDeployer(api, WORKSPACE).existing("reports", "Example")
    assert len(session.calls) == 1


def test_valid_empty_listing_accepts_null_continuation():
    api, _ = client([Response(200, {"value": [], "continuationUri": None})])
    assert FabricDeployer(api, WORKSPACE).existing("reports", "Example") is None
