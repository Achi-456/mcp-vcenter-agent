# Phase 12 - Agent Engine Skeleton On Worker-02

## Summary

Deploy a minimal LangGraph agent engine into `agentic-agents` on
`agentic-worker-02.dclab.local`. This phase proves the internal path:

```text
Browser
  -> FastAPI POST /api/v1/agent/run
  -> agent-engine.agentic-agents.svc.cluster.local:8080
  -> LangGraph graph.astream()
  -> Postgres checkpointer
  -> Redis cache
  -> SSE back through FastAPI
```

No LLM calls, vCenter tools, MCP tool calls, KEDA, new ingress, DNS, or TLS are
introduced in this phase.

## Versions

The original draft pins did not resolve on Python 3.12. These pins were
validated with `pip install --dry-run` in `python:3.12-slim`:

```text
langgraph==0.2.74
langchain-core==0.3.81
langgraph-checkpoint-postgres==2.0.0
psycopg[binary]==3.2.1
pydantic==2.7.4
```

`langchain-core==0.3.81` is the minimum 0.x-line patch for
CVE-2025-68664; do not lower it when refreshing dependency pins.

`AsyncPostgresSaver.from_conn_string()` is used as a long-lived async context
manager. The package creates its psycopg connection with `autocommit=True`, so
`setup()` can create checkpoint tables safely.

## What Gets Added

```text
apps/engine/                         Python FastAPI + LangGraph service
.github/workflows/build-engine.yml   GHCR build and manifest tag update
k8s/apps/agentic-agents/             GitOps manifests for engine workload
k8s/argocd/agentic-agents-application.yaml
```

FastAPI in `apps/backend` gets a stable public proxy:

```text
POST /api/v1/agent/run
GET  /api/v1/agent/sessions/{session_id}
```

The public FastAPI API remains stable so Phase 13 can replace the direct proxy
with a Redis queue and KEDA workers without changing the browser contract.

## Secret Creation

Secrets are manual and not committed.

```powershell
$PG_APP_PW = kubectl -n agentic-data get secret agentic-postgres-auth `
  -o jsonpath="{.data.app-password}" | `
  % { [System.Text.Encoding]::UTF8.GetString([System.Convert]::FromBase64String($_)) }

$REDIS_PW = kubectl -n agentic-data get secret agentic-redis-auth `
  -o jsonpath="{.data.redis-password}" | `
  % { [System.Text.Encoding]::UTF8.GetString([System.Convert]::FromBase64String($_)) }

kubectl create secret generic agentic-engine-secrets `
  --namespace agentic-agents `
  --from-literal=DB_URL="postgresql+asyncpg://agentic_app:${PG_APP_PW}@postgres.agentic-data.svc.cluster.local:5432/agentic" `
  --from-literal=REDIS_URL="redis://:${REDIS_PW}@redis-master.agentic-data.svc.cluster.local:6379" `
  --dry-run=client -o yaml | kubectl apply -f -
```

Confirm the app user can create checkpoint tables before deployment:

```powershell
kubectl -n agentic-data exec postgres-0 -- env PGPASSWORD=$PG_APP_PW `
  psql -U agentic_app -d agentic -v ON_ERROR_STOP=1 `
  -c "BEGIN; CREATE TABLE phase12_priv_check(id integer); DROP TABLE phase12_priv_check; ROLLBACK;"
```

## Local Validation

```powershell
docker version

docker build -t agentic-engine:local apps/engine

docker run --rm -d `
  --name agentic-engine-local `
  -p 8080:8080 `
  agentic-engine:local

Start-Sleep 5
curl.exe -s http://localhost:8080/health
# Expected: {"status":"ok"}

docker stop agentic-engine-local

docker build -t agentic-fastapi:phase12 apps/backend
```

`/ready` is expected to be degraded locally unless real `DB_URL` and
`REDIS_URL` are supplied.

## GitOps Deployment

Push the code first and wait for GitHub Actions to publish:

```text
ghcr.io/achi-456/agentic-engine:0.12.0
ghcr.io/achi-456/agentic-engine:<commit-sha>
```

Then create the secret and apply only the Argo CD Application:

```powershell
kubectl apply -f k8s/argocd/agentic-agents-application.yaml
```

Check sync status:

```powershell
kubectl -n argocd get applications.argoproj.io agentic-agents
kubectl -n agentic-agents get pods -o wide
```

## Test Plan

### Placement

```powershell
kubectl -n agentic-agents get pods -o wide
# Expected: agent-engine pod Running on agentic-worker-02.dclab.local
```

### Internal Health

```powershell
kubectl run engine-health --image=curlimages/curl --rm -it --restart=Never -- `
  curl -s http://agent-engine.agentic-agents.svc.cluster.local:8080/health

kubectl run engine-ready --image=curlimages/curl --rm -it --restart=Never -- `
  curl -s http://agent-engine.agentic-agents.svc.cluster.local:8080/ready
```

Expected readiness:

```json
{"status":"ready","db":"ok","redis":"ok","langgraph":"ok"}
```

### SSE Through FastAPI

```powershell
curl.exe -k -N `
  -H "Content-Type: application/json" `
  -H "Accept: text/event-stream" `
  -d '{"message":"hello agent skeleton"}' `
  https://api.dclab.local/api/v1/agent/run
```

Expected incremental events:

```text
data: {"type":"session","session_id":"..."}
data: {"type":"node","node":"load_context","output":{...}}
data: {"type":"node","node":"echo_node","output":{...}}
data: {"type":"done"}
```

### Redis Cache

```powershell
$body = '{"session_id":"test-session-001","message":"hello cache"}'

curl.exe -k -N -H "Content-Type: application/json" `
  -H "Accept: text/event-stream" `
  -d $body https://api.dclab.local/api/v1/agent/run

curl.exe -k -N -H "Content-Type: application/json" `
  -H "Accept: text/event-stream" `
  -d $body https://api.dclab.local/api/v1/agent/run
```

Expected: the second run includes `[CACHED]`.

### Checkpoint State

```powershell
curl.exe -k https://api.dclab.local/api/v1/agent/sessions/test-session-001
```

Expected: `found` is `true` and `values` contains the latest graph state.

Optional SQL check:

```powershell
kubectl -n agentic-data exec postgres-0 -- env PGPASSWORD=$PG_APP_PW `
  psql -U agentic_app -d agentic `
  -c "SELECT thread_id, checkpoint_id FROM checkpoints WHERE thread_id='test-session-001' LIMIT 5;"
```

### Stability

```powershell
kubectl get nodes
kubectl get pods -A | Select-String -Pattern "Pending|CrashLoopBackOff|ErrImagePull|ImagePullBackOff|\bError\b"
kubectl -n argocd get applications.argoproj.io agentic-app agentic-agents
```

Expected: all five nodes are Ready, no unhealthy pods, and both Argo CD
Applications are Synced/Healthy.

## Troubleshooting

| Symptom | First check |
|---|---|
| `ImagePullBackOff` | Confirm GHCR package is public or add `imagePullSecret` before changing manifests |
| `/ready` shows DB error | Check `agentic-engine-secrets` DB URL and `agentic_app` privileges |
| `/ready` shows Redis error | Check Redis password and service `redis-master.agentic-data.svc.cluster.local` |
| `/ready` shows LangGraph error | `kubectl -n agentic-agents logs deploy/agent-engine` |
| SSE buffers | Confirm FastAPI ingress still has buffering disabled and proxy response has `X-Accel-Buffering: no` |
| HPA targets `<unknown>` | Check `rke2-metrics-server` in `kube-system` |

## Assumptions

- KEDA is deferred to Phase 13.
- HPA min replica count remains `1` because Phase 12 uses direct SSE proxying.
- `agentic_app` owns LangGraph checkpoint tables created by `setup()`.
- Secrets stay manual until Sealed Secrets or External Secrets is introduced.
- Argo CD manages manifests; manual `kubectl apply` is only for secrets and the initial Application.
