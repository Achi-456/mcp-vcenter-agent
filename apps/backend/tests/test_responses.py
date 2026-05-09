from app.core.errors import ErrorCode
from app.core.responses import error_response, success_response


def test_success_response_shape() -> None:
    response = success_response({"status": "ok"}, source="test")

    assert response["ok"] is True
    assert response["data"] == {"status": "ok"}
    assert response["metadata"]["source"] == "test"
    assert response["metadata"]["cached"] is False
    assert response["metadata"]["collected_at"]


def test_error_response_shape() -> None:
    response = error_response(ErrorCode.TOOL_NOT_FOUND, "missing")

    assert response == {
        "ok": False,
        "error_code": "TOOL_NOT_FOUND",
        "message": "missing",
        "details": {},
    }
