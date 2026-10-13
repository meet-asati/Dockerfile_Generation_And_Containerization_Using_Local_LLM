from fastapi.testclient import TestClient

from sample_api.main import app


client = TestClient(app)


def test_health_check() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_welcome_endpoint() -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert response.json()["service"] == "sample-python-api"
