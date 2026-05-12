# AgenticOps Chat SSE Events

The frontend consumes Server-Sent Events from:

- `POST /api/v1/chat/stream`
- `POST /api/v1/agent/run`

The stream currently sends `data:` frames containing JSON objects with a `type` field.

Supported event types:
- `start`
- `intent`
- `safety_check`
- `agent_start`
- `tool_call`
- `tool_result`
- `validation`
- `final`
- `error`
- `done`

Rendering guidance:
- Show `final` as the assistant answer.
- Show `tool_call` and `tool_result` as collapsible evidence cards.
- Show `safety_check.allowed=false` as a blocked-action state.
- Show `error` as a non-destructive failure message.
- Do not show raw JSON by default.
- Provide a "View raw" affordance for debugging.
- Always preserve the final "No action was taken." text when present.

The frontend must not infer success if the backend returns `ok=false`.
