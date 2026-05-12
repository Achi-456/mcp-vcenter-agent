# Phase 1 - FastAPI Foundation Pack

## Status

Implementation started in the current branch.

## Delivered In This Phase

- Modular FastAPI router structure.
- Common response envelope helpers.
- Canonical error codes.
- SQLAlchemy async model layer.
- Alembic migration scaffold.
- Kubernetes migration Job manifest.
- Redis cache service abstraction.
- Kubernetes SecretStore abstraction.
- Metadata-only tool registry.
- PolicyService.
- AuditService and audit repository.
- Foundation tests for response, cache, registry, policy, and audit redaction.

## Leftovers Before Calling Phase 1 Complete

- Run `alembic upgrade head` against the real `agentic` Postgres database.
- Confirm all Phase 1 tables exist in Postgres.
- Confirm existing LangGraph checkpoint tables are untouched.
- Run the Kubernetes migration Job through Argo CD or manual test apply.
- Confirm `DB_URL` and `REDIS_URL` are present in `agentic-app-secrets`.
- Confirm `/api/v1/health/services` reports Postgres and Redis as `ok` in cluster.
- Confirm `/api/v1/connections/vcenter/status` can see `agentic-vcenter-default` in cluster.
- Decide whether `agentic-vcenter-default` or `agentic-app-secrets` is the long-term vCenter secret source.
- Add integration tests for API routes once a test DB strategy is chosen.
- Keep `/api/v1/tools` metadata-only; do not add execution until Phase 3.

## Known Risks

- The migration Job uses the FastAPI image and must be kept in sync with deployment image tags.
- Argo CD Jobs are immutable unless hook delete policy works as expected.
- Local Windows has no `python` or `py` launcher available, so validation currently depends on Docker.
- Tool registry read-only placeholders are marked `implemented=false`; this is correct until real vCenter tools are added.
- `SecretStore.write()` exists as an abstraction but no public endpoint should expose raw secret writes in Phase 1.

## Acceptance Criteria

- Backend Docker build passes.
- Unit tests pass.
- Existing chat endpoints still stream SSE.
- Health endpoints work with missing dependencies and degrade cleanly.
- Cluster migration creates the expected tables.
- No raw passwords or API keys are committed or returned by API responses.

