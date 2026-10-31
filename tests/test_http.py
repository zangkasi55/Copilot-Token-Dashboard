import pytest

from copilot_token_dashboard.http import ApiClient, ApiError, download_report, retry_delay, validate_https


class Response:
    def __init__(self, status, body=None, headers=None):
        self.status_code, self.body, self.headers = status, body or {}, headers or {}

    def json(self):
        return self.body


class Session:
    def __init__(self, responses):
        self.responses, self.calls = list(responses), []

    def request(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        return self.responses.pop(0)


def test_429_respects_retry_after():
    waits = []
    session = Session([Response(429, headers={"Retry-After": "3"}), Response(200, {"value": []})])
    client = ApiClient("https://api.github.com", "sensitive-example", session, waits.append)
    assert client.get_json("/example") == {"value": []}
    assert waits == [3]
    assert session.calls[0][1]["allow_redirects"] is False


def test_long_server_wait_is_not_shortened_into_an_early_retry():
    with pytest.raises(RuntimeError, match="Retry-After"):
        retry_delay("600", 0)


def test_permission_failure_is_not_retried():
    session = Session([Response(403)])
    with pytest.raises(ApiError):
        ApiClient("https://api.github.com", "sensitive-example", session).get_json("/example")
    assert len(session.calls) == 1


def test_authenticated_cross_origin_is_rejected():
    session = Session([])
    with pytest.raises(ValueError, match="configured origin"):
        ApiClient("https://graph.microsoft.com", "sensitive-example", session).get_json("https://example.com/download")
    assert session.calls == []


@pytest.mark.parametrize("url", ["http://example.com", "https://user:password@example.com",
                                  "https://localhost/file", "https://example.com:8080/file"])
def test_unsafe_download_urls_are_rejected(url):
    with pytest.raises(ValueError):
        validate_https(url)


def test_pagination_cycle_is_explicit():
    session = Session([Response(200, {"value": [], "@odata.nextLink": "/page"}),
                       Response(200, {"value": [], "@odata.nextLink": "/page"})])
    with pytest.raises(ValueError, match="cycle"):
        ApiClient("https://graph.microsoft.com", session=session).paged_values("/page")


def test_report_downloader_has_no_authorization_header(monkeypatch):
    calls = []

    class DownloadResponse:
        status_code = 200

        def iter_content(self, _):
            yield b'{"day":"2026-05-28"}\n'

    class DownloadSession:
        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def get(self, url, **kwargs):
            calls.append(kwargs)
            return DownloadResponse()

    monkeypatch.setattr("copilot_token_dashboard.http.requests.Session", DownloadSession)
    assert download_report("https://example.com/report") == b'{"day":"2026-05-28"}\n'
    assert "Authorization" not in calls[0]["headers"]

