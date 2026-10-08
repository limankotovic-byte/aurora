import io
import json
from typing import Annotated, cast

import pytest
from fastapi import FastAPI, Query
from fastapi.testclient import TestClient
from starlette.exceptions import HTTPException

from app.api.dependencies import AppResources
from app.core.exceptions import (
    AppError,
    NetworkError,
    NotFound,
    ParsingError,
    PlayerUnavailable,
    ProviderUnavailable,
    RateLimited,
    UnsupportedOperation,
)
from app.schemas.common import HealthResponse


def test_health_is_offline_and_generates_distinct_request_ids(client: TestClient) -> None:
    first = client.get("/health", headers={"X-Request-ID": "untrusted"})
    second = client.get("/health")
    assert first.status_code == 200
    assert first.json() == {"status": "ok"}
    assert len(first.headers["x-request-id"]) == 32
    assert first.headers["x-request-id"] != second.headers["x-request-id"]


def test_stage_three_routes_are_registered(client: TestClient) -> None:
    schema = client.get("/openapi.json").json()
    assert set(schema["paths"]) == {
        "/health",
        "/anime/{id}",
        "/anime/{id}/episodes",
        "/search",
        "/home",
        "/releases/latest",
    }
    assert schema["paths"]["/health"]["get"]["responses"]["200"]


@pytest.mark.parametrize(
    ("method", "path", "status", "code"),
    [("GET", "/missing", 404, "NOT_FOUND"), ("POST", "/health", 405, "METHOD_NOT_ALLOWED")],
)
def test_framework_errors_use_envelope(
    client: TestClient, method: str, path: str, status: int, code: str
) -> None:
    response = client.request(method, path)
    assert response.status_code == status
    assert response.json()["error"]["code"] == code
    assert response.json()["error"]["requestId"] == response.headers["x-request-id"]
    if status == 405:
        assert "GET" in response.headers["allow"]


@pytest.mark.parametrize(
    ("error_type", "status", "code"),
    [
        (NotFound, 404, "NOT_FOUND"),
        (NetworkError, 502, "NETWORK_ERROR"),
        (ParsingError, 502, "PARSING_ERROR"),
        (ProviderUnavailable, 503, "PROVIDER_UNAVAILABLE"),
        (PlayerUnavailable, 503, "PLAYER_UNAVAILABLE"),
        (UnsupportedOperation, 422, "UNSUPPORTED_OPERATION"),
        (RateLimited, 429, "RATE_LIMITED"),
    ],
)
def test_domain_error_mapping_hides_internal_details(
    app: FastAPI,
    error_type: type[AppError],
    status: int,
    code: str,
    log_output: io.StringIO,
) -> None:
    @app.get("/test-error")
    async def fail() -> None:
        raise error_type("private-token=do-not-leak")

    with TestClient(app) as client:
        response = client.get("/test-error")
    assert response.status_code == status
    assert response.json()["error"]["code"] == code
    assert response.json()["error"]["requestId"] == response.headers["x-request-id"]
    assert "private-token" not in response.text + log_output.getvalue()


def test_rate_limited_preserves_retry_after(app: FastAPI) -> None:
    @app.get("/limited")
    async def limited() -> None:
        raise RateLimited(retry_after=30)

    with TestClient(app) as client:
        response = client.get("/limited")
    assert response.status_code == 429
    assert response.headers["retry-after"] == "30"


def test_request_validation_does_not_echo_input(app: FastAPI) -> None:
    @app.get("/validated")
    async def validated(page: Annotated[int, Query(ge=1)]) -> int:
        return page

    with TestClient(app) as client:
        response = client.get("/validated", params={"page": "secret-invalid-value"})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
    assert "secret-invalid-value" not in response.text


def test_http_exception_does_not_expose_detail(app: FastAPI) -> None:
    @app.get("/http-error")
    async def fail() -> None:
        raise HTTPException(403, "secret-internal-detail")

    with TestClient(app) as client:
        response = client.get("/http-error")
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "HTTP_ERROR"
    assert "secret-internal-detail" not in response.text


def test_unhandled_error_and_lifespan_cleanup(app: FastAPI, log_output: io.StringIO) -> None:
    @app.get("/crash")
    async def crash() -> None:
        raise RuntimeError("private-token=do-not-leak")

    with TestClient(app, raise_server_exceptions=False) as client:
        resources = cast(AppResources, app.state.resources)
        assert not resources.http_client.is_closed
        response = client.get("/crash")
        assert client.get("/health").status_code == 200
    assert resources.http_client.is_closed
    assert not hasattr(app.state, "resources")
    assert response.status_code == 500
    assert response.json()["error"]["code"] == "UNKNOWN_ERROR"
    assert response.json()["error"]["requestId"] == response.headers["x-request-id"]
    assert "private-token" not in response.text + log_output.getvalue()
    records = [json.loads(line) for line in log_output.getvalue().splitlines()]
    assert any(r.get("exception_type") == "RuntimeError" for r in records)
    assert any(r.get("route") == "/crash" and r.get("status") == 500 for r in records)


def test_response_validation_failure_is_an_internal_error(app: FastAPI) -> None:
    @app.get("/bad-response", response_model=HealthResponse)
    async def bad_response() -> dict[str, str]:
        return {"status": "invalid-internal-state"}

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/bad-response")
    assert response.status_code == 500
    assert response.json()["error"]["code"] == "UNKNOWN_ERROR"
    assert "invalid-internal-state" not in response.text


def test_structured_logs_exclude_request_secrets(app: FastAPI, log_output: io.StringIO) -> None:
    with TestClient(app) as client:
        response = client.get(
            "/health?token=query-secret",
            headers={"Authorization": "Bearer header-secret", "Cookie": "session=cookie-secret"},
        )
        client.get("/private-path-secret")
    records = [json.loads(line) for line in log_output.getvalue().splitlines()]
    first = records[0]
    assert first["event"] == "request_completed"
    assert first["request_id"] == response.headers["x-request-id"]
    assert first["route"] == "/health"
    assert first["duration_ms"] >= 0
    for secret in ("query-secret", "header-secret", "cookie-secret", "private-path-secret"):
        assert secret not in log_output.getvalue()
