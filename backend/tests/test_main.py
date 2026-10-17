from fastapi.testclient import TestClient

from app.main import app

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
