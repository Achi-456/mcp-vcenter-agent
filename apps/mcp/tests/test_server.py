import inspect
from datetime import datetime

from fastapi.testclient import TestClient

import server
from server import app


client = TestClient(app)


def test_tools_returns_only_safe_tools() -> None:
    response = client.get("/tools")

    assert response.status_code == 200
    tools = response.json()["tools"]
    assert {tool["name"] for tool in tools} == {"server_info", "server_time", "echo_text"}
    assert all(tool["risk_level"] == "read_only" for tool in tools)


def test_server_info_call_succeeds() -> None:
    response = client.post("/tools/server_info/call", json={})

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["server"] == "default"
    assert payload["mode"] == "safe"
    assert payload["safe_execution"] is True


def test_server_time_call_succeeds() -> None:
    response = client.post("/tools/server_time/call", json={})

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert datetime.fromisoformat(payload["utc"].replace("Z", "+00:00"))


def test_echo_text_call_succeeds() -> None:
    response = client.post("/tools/echo_text/call", json={"text": "hello"})

    assert response.status_code == 200
    assert response.json() == {"ok": True, "text": "hello", "length": 5}


def test_echo_text_rejects_too_long_text() -> None:
    response = client.post("/tools/echo_text/call", json={"text": "x" * 513})

    assert response.status_code == 400
    payload = response.json()
    assert payload["ok"] is False
    assert payload["error_code"] == "MCP_TOOL_INVALID_INPUT"


def test_unknown_tool_call_fails_cleanly() -> None:
    response = client.post("/tools/unknown/call", json={})

    assert response.status_code == 404
    payload = response.json()
    assert payload["ok"] is False
    assert payload["error_code"] == "MCP_TOOL_NOT_FOUND"


def test_unsafe_tool_name_fails_cleanly() -> None:
    response = client.post("/tools/shell_exec/call", json={})

    assert response.status_code == 403
    payload = response.json()
    assert payload["ok"] is False
    assert payload["error_code"] == "MCP_TOOL_BLOCKED"


def test_no_runtime_shell_file_or_network_imports() -> None:
    source = inspect.getsource(server)

    forbidden = ("subprocess", "shell=True", "os.system", "pathlib", "httpx", "requests", "aiohttp")
    assert all(marker not in source for marker in forbidden)
