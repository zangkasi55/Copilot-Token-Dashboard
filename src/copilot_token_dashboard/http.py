from __future__ import annotations

import datetime as dt
import email.utils
import logging
import time
from collections.abc import Callable
from urllib.parse import urljoin, urlparse

import requests

LOGGER = logging.getLogger("copilot_token_dashboard")


class ApiError(RuntimeError):
    def __init__(self, status: int, origin: str) -> None:
        self.status = status
        super().__init__(f"API request failed with HTTP {status} at {origin}")


def validate_https(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("Only HTTPS URLs without embedded credentials are supported")
    if parsed.port not in (None, 443):
        raise ValueError("Only the standard HTTPS port is supported")
    if parsed.hostname in {"localhost", "127.0.0.1", "::1"}:
        raise ValueError("Local download hosts are not supported")
    return f"https://{parsed.hostname}"


def retry_delay(header: str | None, attempt: int) -> float:
    if header:
        if header.isdigit():
            if float(header) > 120:
                raise RuntimeError("Retry-After exceeds the bounded interactive wait; resume after the server's wait period")
            return float(header)
        try:
            date = email.utils.parsedate_to_datetime(header)
        except (TypeError, ValueError, OverflowError):
            LOGGER.warning("Invalid Retry-After header; using bounded backoff")
        else:
            if date.tzinfo is None:
                date = date.replace(tzinfo=dt.timezone.utc)
            delay = max(0.0, (date - dt.datetime.now(dt.timezone.utc)).total_seconds())
            if delay > 120:
                raise RuntimeError("Retry-After exceeds the bounded interactive wait; resume after the server's wait period")
            return delay
    return min(float(2 ** attempt), 30.0)


class ApiClient:
    def __init__(
        self, origin: str, token: str | None = None,
        session: requests.Session | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.origin = validate_https(origin)
        self.token = token
        self.session = session or requests.Session()
        self.sleep = sleep

    def request(
        self, method: str, path: str, *, params: dict | None = None,
        json_body: dict | None = None, headers: dict | None = None,
    ) -> requests.Response:
        url = urljoin(self.origin + "/", path)
        if validate_https(url) != self.origin:
            raise ValueError("Authenticated API requests cannot leave their configured origin")
        request_headers = {"Accept": "application/json", "User-Agent": "Copilot-Token-Dashboard/1.0"}
        if headers:
            request_headers.update(headers)
        if self.token:
            request_headers["Authorization"] = "Bearer " + self.token
        for attempt in range(4):
            response = self.session.request(
                method, url, params=params, json=json_body, headers=request_headers,
                timeout=(15, 90), allow_redirects=False,
            )
            retryable = response.status_code == 429 or (
                method.upper() in {"GET", "HEAD"} and response.status_code in {500, 502, 503, 504}
            )
            if retryable and attempt < 3:
                delay = retry_delay(response.headers.get("Retry-After"), attempt)
                LOGGER.warning("Retrying source=%s status=%s wait_seconds=%s",
                               self.origin, response.status_code, delay)
                self.sleep(delay)
                continue
            if response.status_code not in {200, 201, 202, 204, 302, 303}:
                raise ApiError(response.status_code, self.origin)
            return response
        raise RuntimeError("The bounded request loop ended unexpectedly")

    def get_json(self, path: str, params: dict | None = None, headers: dict | None = None) -> dict:
        response = self.request("GET", path, params=params, headers=headers)
        value = response.json()
        if not isinstance(value, dict):
            raise ValueError("The API returned an unexpected JSON shape")
        return value

    def paged_values(self, path: str) -> list[dict]:
        result = []
        visited = set()
        while path:
            if path in visited:
                raise ValueError("The API returned a pagination cycle")
            visited.add(path)
            body = self.get_json(path)
            values = body.get("value")
            if not isinstance(values, list):
                raise ValueError("The paged response is missing its value array")
            result.extend(values)
            path = body.get("@odata.nextLink", "")
            if path and not isinstance(path, str):
                raise ValueError("The API returned an invalid next-link value")
        return result


def download_report(url: str, maximum_bytes: int = 100_000_000) -> bytes:
    validate_https(url)
    with requests.Session() as session:
        response = session.get(
            url, headers={"User-Agent": "Copilot-Token-Dashboard/1.0"},
            timeout=(15, 90), stream=True, allow_redirects=False,
        )
        if response.status_code != 200:
            raise ApiError(response.status_code, validate_https(url))
        chunks = []
        size = 0
        for chunk in response.iter_content(64 * 1024):
            size += len(chunk)
            if size > maximum_bytes:
                raise ValueError("The report download exceeds the configured size limit")
            chunks.append(chunk)
        return b"".join(chunks)
