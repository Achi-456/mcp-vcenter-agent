from fastapi.testclient import TestClient

from app.api.main import app


def test_raw_govc_command_endpoint_does_not_exist() -> None:
    response = TestClient(app).post("/api/v1/govc/command", json={"command": "about"})

    assert response.status_code == 404


def test_rest_write_endpoints_do_not_exist() -> None:
    client = TestClient(app)

    assert client.post("/api/v1/vsphere-rest/tags").status_code == 405
    assert client.delete("/api/v1/vsphere-rest/tags/tag-1").status_code == 404
