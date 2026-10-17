import asyncio
import json

from fastapi.testclient import TestClient
from starlette.requests import Request

from app.main import app, sqlite_error_handler, unexpected_error_handler

client = TestClient(app)


def test_infrastructure_health_endpoint() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "skillscope-api",
        "version": "0.1.0",
    }


def test_api_health_contract() -> None:
    response = client.get("/api/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["service"] == "skillscope-api"
    assert body["version"] == "0.1.0"
    assert body["environment"] in {"development", "test", "production"}


def test_system_persistence_reports_schema_without_exposing_absolute_path() -> None:
    response = client.get("/api/system/persistence")
    assert response.status_code == 200, response.text
    assert response.headers.get("X-Request-ID")
    serialized = json.dumps(response.json())
    assert "/mnt/data/SkillScope/data/skillscope.db" not in serialized
    assert "persistent_store" in response.json()


def _request_with_id(request_id: str = "stage16-safe-error-test") -> Request:
    request = Request({
        "type": "http", "http_version": "1.1", "method": "GET", "scheme": "http",
        "path": "/test/internal", "raw_path": b"/test/internal", "query_string": b"",
        "headers": [], "server": ("testserver", 80), "client": ("testclient", 123),
        "root_path": "",
    })
    request.state.request_id = request_id
    return request


def test_unexpected_error_response_redacts_internal_exception_details() -> None:
    request = _request_with_id()
    response = asyncio.run(unexpected_error_handler(request, RuntimeError("private /srv/app/secret.db token=abc")))
    body = json.loads(response.body)
    assert response.status_code == 500
    assert body["request_id"] == "stage16-safe-error-test"
    assert "secret.db" not in response.body.decode()
    assert "token=abc" not in response.body.decode()
    assert response.headers["X-Request-ID"] == "stage16-safe-error-test"


def test_sqlite_error_response_is_retryable_and_redacts_driver_details() -> None:
    request = _request_with_id("stage16-storage-error-test")
    response = asyncio.run(sqlite_error_handler(request, __import__("sqlite3").OperationalError("locked at /private/path.db")))
    body = json.loads(response.body)
    assert response.status_code == 503
    assert body["request_id"] == "stage16-storage-error-test"
    assert "private/path.db" not in response.body.decode()
    assert response.headers["X-Request-ID"] == "stage16-storage-error-test"


def test_cors_allows_vite_development_origin() -> None:
    response = client.options(
        "/api/health",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:5173"
