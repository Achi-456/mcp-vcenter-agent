# Phase 9 UI/UX Clean Rebuild Implementation Plan

Do not build the full UI in one task.

Keep it under one major phase:

```text
Phase 9 - UI/UX Clean Rebuild
```

Split implementation:

- Phase 9A - UI foundation
- Phase 9B - Chat UI
- Phase 9C - Dashboard + Health
- Phase 9D - Inventory
- Phase 9E - Diagnostics + Tools
- Phase 9F - Settings + Sessions

## Why Split It

A single huge UI implementation is likely to cause:
- broken routing
- bad SSE parser assumptions
- wrong API assumptions
- large TypeScript error sets
- inconsistent components
- too many pages half working
- difficult debugging

Every subphase must end with:
- `npm run build` passed
- frontend container build passed
- UI screenshot reviewed
- no backend/engine/MCP/database changes

## Phase 9A - Design System + Layout Shell

Build:
- Sidebar
- Topbar
- Page shell
- API client
- Basic routing
- Reusable cards and badges
- Page placeholders

Do not implement full chat yet.

## Phase 9B - AI Assistant

Build:
- SSE parser
- Chat layout
- Event cards
- Final Markdown answer
- Prompt suggestions
- Expandable input
- Session header

## Phase 9C - Dashboard + Health

Build:
- Dashboard metrics
- Health cards
- Auto-refresh
- Last updated
- Keep old data during refresh

## Phase 9D - Inventory

Build:
- VM table
- Host table
- Datastore table
- Search/filter/sort
- Details drawer

## Phase 9E - Diagnostics + Tools

Build:
- pyVmomi diagnostics
- govc diagnostics
- vSphere REST diagnostics
- MCP diagnostics
- Tool registry table

## Phase 9F - Settings + Sessions

Build:
- vCenter status
- Test/reconnect
- LLM provider status
- MCP status
- Sessions list

## Phase 9A Prompt

```text
Implement Phase 9A - AgenticOps UI Foundation.

Frontend only.

Do not modify:
- apps/backend
- apps/engine
- apps/mcp
- k8s
- database migrations

Read:
- docs/knowledge/ui/01-design-system.md
- docs/knowledge/ui/02-api-contracts.md
- current apps/frontend

Use this color palette:
- #1B3B6F primary navy
- #2F6690 secondary steel blue
- #A3CEF1 info blue
- #F6E4C8 warm beige
- #FFF8EE warm off-white

Goal:
Create a professional infrastructure operations console UI foundation.

Implement:
1. App shell:
   - left sidebar
   - top status bar
   - main content area
   - responsive behavior

2. Navigation:
   - Dashboard
   - AI Assistant
   - Inventory
   - Diagnostics
   - Tools
   - System Health
   - Settings
   - Sessions

3. Shared API client:
   - use NEXT_PUBLIC_API_BASE_URL
   - handle standard success/error envelopes
   - clean error handling

4. Shared components:
   - StatusBadge
   - RiskBadge
   - ToolBadge
   - MetricCard
   - HealthCard
   - EmptyState
   - ErrorState
   - LoadingState
   - RefreshButton
   - PageHeader

5. Page scaffolds:
   - dashboard
   - chat
   - inventory
   - diagnostics
   - tools
   - health
   - settings
   - sessions

6. Wire minimally:
   - System Health page to GET /api/v1/health/services
   - Tools page to GET /api/v1/tools
   - Dashboard to GET /api/v1/health/services

Rules:
- Do not implement full chat SSE yet.
- Do not implement full inventory tables yet.
- Do not expose secrets.
- Do not show raw JSON by default.
- Add empty/error/loading states.
- Keep old data visible while refreshing if simple.
- Do not break build.

Validation:
- npm run lint if configured
- npm run build
- docker build frontend if configured

After coding, return:
1. Files changed
2. Files created
3. Components created
4. Pages created
5. Endpoints wired
6. Build/test results
7. Remaining risks
```
