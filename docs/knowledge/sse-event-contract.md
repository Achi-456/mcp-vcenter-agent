# SSE Event Contract

Frontend, FastAPI, and Agent Engine must agree on these events before chat
implementation proceeds.

## Transport

Endpoint:

```text
POST /api/v1/chat/stream
```

Headers:

```text
Content-Type: text/event-stream
Cache-Control: no-cache
X-Accel-Buffering: no
```

Each event is sent as:

```text
data: {"type":"event_name", ...}

```

## Event Types

```text
start
intent
safety_check
plan
agent_start
tool_call
tool_result
finding
validation
final
error
done
```

## Event Shapes

### start

```json
{
  "type": "start",
  "session_id": "uuid",
  "run_id": "uuid"
}
```

### intent

```json
{
  "type": "intent",
  "intent": "host_details",
  "confidence": 0.91
}
```

### safety_check

```json
{
  "type": "safety_check",
  "risk_level": "read_only",
  "allowed": true
}
```

### plan

```json
{
  "type": "plan",
  "steps": [
    {
      "id": "step-1",
      "tool": "get_host_details",
      "reason": "User asked for ESXi host details"
    }
  ]
}
```

### agent_start

```json
{
  "type": "agent_start",
  "agent": "vcenter_inventory_agent"
}
```

### tool_call

```json
{
  "type": "tool_call",
  "tool": "get_host_details",
  "risk_level": "read_only",
  "input_summary": "host_name=esxi01.dclab.com"
}
```

### tool_result

```json
{
  "type": "tool_result",
  "tool": "get_host_details",
  "ok": true,
  "output_summary": "Host found and details collected"
}
```

### finding

```json
{
  "type": "finding",
  "severity": "info",
  "message": "Host is connected and not in maintenance mode"
}
```

### validation

```json
{
  "type": "validation",
  "status": "passed",
  "message": "Response matches requested object type"
}
```

### final

```json
{
  "type": "final",
  "content": "Final assistant answer"
}
```

### error

```json
{
  "type": "error",
  "error_code": "HOST_NOT_FOUND",
  "message": "No ESXi host named esxi01.dclab.com was found."
}
```

### done

```json
{
  "type": "done"
}
```

## Rules

- Always emit `start` first.
- Always emit `done` last unless the connection is interrupted.
- Runtime failures after stream start must emit `error` then `done`.
- Do not include secret values in any event.
- Tool inputs must be summaries, not raw secret-bearing payloads.

