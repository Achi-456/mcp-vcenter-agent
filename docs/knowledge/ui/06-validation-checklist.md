# AgenticOps UI Validation Checklist

Run after each frontend phase:

- `npm run build`
- `npm run lint` if configured and compatible with the installed Next.js version
- Docker build for `apps/frontend` if required for deploy
- screenshot desktop layout
- screenshot mobile layout

Manual checks:
- Dashboard renders at `/`
- Chat page renders at `/chat`
- Health page handles loading, error, and success states
- Tools page handles loading, error, and success states
- Navigation works on desktop and mobile
- Text remains readable on the warm off-white background
- Status badges include text labels, not only color
- No secrets are displayed
- Raw JSON is hidden by default

Regression checks:
- Do not change backend, engine, MCP, k8s, or DB migrations for UI-only phases unless explicitly requested.
- Do not add frontend direct MCP calls.
- Do not expose internal tool tokens or secret names beyond non-sensitive references.
- no public arbitrary MCP execution path in frontend code
- no raw govc command UI
- no destructive operation controls in Version 1 UI
