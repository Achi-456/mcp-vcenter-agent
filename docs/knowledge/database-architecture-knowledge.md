# AgenticOps Database Architecture Knowledge

## Purpose

This document is for the `knowledge/` folder. It explains how AgenticOps should use databases and storage inside the Kubernetes/RKE2 cluster.

The platform needs durable state, fast cache, audit history, session memory, LangGraph checkpoints, and future job queue support.

Recommended core design:

```text
Postgres = durable platform state
Redis    = short-lived cache and temporary run state
Kubernetes Secrets = sensitive credentials
Object Storage later = large reports and evidence bundles
```

---

# 1. Main Database Principle

Do **not** store actual vCenter passwords or LLM API keys directly in Postgres.

Use this split:

```text
Postgres:
- metadata
- references
- sessions
- checkpoints
- audit logs
- tool runs
- reports
- approvals

Kubernetes Secrets:
- vCenter password
- LLM API keys
- Redis password
- Postgres password
- external service tokens
```

Correct example:

```text
Postgres:
connection_profiles.secret_name = agentic-vcenter-default

Kubernetes Secret:
agentic-vcenter-default contains VCENTER_USERNAME and VCENTER_PASSWORD
```

Wrong example:

```text
Postgres:
connection_profiles.password = actual-vcenter-password
```

---

# 2. Database Roles

## 2.1 Postgres

Postgres has three primary responsibilities:

```text
1. Platform metadata and settings
2. LangGraph checkpoints and agent state
3. Audit logs and operational history
```

Additional responsibilities:

```text
4. Chat sessions
5. Tool call history
6. Reports metadata/content
7. Approval requests later
8. Connection profile metadata
9. LLM provider metadata
```

## 2.2 Redis

Redis has two primary responsibilities:

```text
1. Tool result cache
2. Future lightweight queue / KEDA scaling trigger
```

Additional responsibilities:

```text
3. Temporary run state
4. SSE/session temporary state
5. Rate limiting later
6. Short-lived provider model cache
```

## 2.3 Kubernetes Secrets

Kubernetes Secrets store all sensitive credentials:

```text
- vCenter credentials
- LLM provider API keys
- database passwords
- Redis password
- external API tokens
```

## 2.4 Object Storage Later

Use object storage later for large artifacts:

```text
- CSI VA reports
- inventory CSV exports
- evidence bundles
- long logs
- screenshots
- generated documents
```

Possible options:

```text
- MinIO
- S3
- NFS-backed object storage
```

---

# 3. Recommended Architecture

```text
Next.js Frontend
   ↓
FastAPI Backend
   ↓
Postgres
   ├── connection metadata
   ├── chat sessions
   ├── LangGraph checkpoints
   ├── audit logs
   ├── tool calls
   ├── reports
   └── approval requests

FastAPI Backend
   ↓
Kubernetes Secrets
   ├── vCenter credentials
   ├── LLM API keys
   ├── DB password
   └── Redis password

FastAPI / Agent Engine
   ↓
Redis
   ├── tool result cache
   ├── temporary run state
   ├── SSE/session cache
   └── future queue backend

Future:
FastAPI / Agent Engine
   ↓
Object Storage
   ├── report files
   ├── evidence JSON
   └── exported CSVs
```

---

# 4. Postgres Schema Plan

## 4.1 `connection_profiles`

Stores metadata for vCenter and LLM connections.

Do not store secrets directly.

```sql
CREATE TABLE connection_profiles (
    id UUID PRIMARY KEY,
    name TEXT NOT NULL,
    connection_type TEXT NOT NULL, -- vcenter, llm, redis, postgres, mcp
    provider TEXT,                 -- gemini, openai, anthropic, xai, moonshot
    url TEXT,
    username_hint TEXT,
    secret_name TEXT NOT NULL,
    verify_ssl BOOLEAN DEFAULT TRUE,
    status TEXT DEFAULT 'unknown',
    last_test_status TEXT,
    last_tested_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);
```

Example rows:

```text
vCenter:
name = default-vcenter
connection_type = vcenter
url = https://core-infra-vc01.dclab.com
username_hint = administrator@vsphere.local
secret_name = agentic-vcenter-default

Gemini:
connection_type = llm
provider = gemini
secret_name = agentic-llm-gemini
```

---

## 4.2 `chat_sessions`

Stores assistant sessions.

```sql
CREATE TABLE chat_sessions (
    id UUID PRIMARY KEY,
    title TEXT,
    provider TEXT,
    model TEXT,
    status TEXT DEFAULT 'active',
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);
```

---

## 4.3 `chat_messages`

Stores user and assistant messages.

```sql
CREATE TABLE chat_messages (
    id UUID PRIMARY KEY,
    session_id UUID REFERENCES chat_sessions(id) ON DELETE CASCADE,
    role TEXT NOT NULL, -- user, assistant, system, tool
    content TEXT NOT NULL,
    metadata_json JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT now()
);
```

---

## 4.4 `langgraph_checkpoints`

Use the official LangGraph Postgres checkpointer schema if available.

If a custom schema is needed:

```sql
CREATE TABLE langgraph_checkpoints (
    thread_id TEXT NOT NULL,
    checkpoint_id TEXT NOT NULL,
    parent_checkpoint_id TEXT,
    checkpoint JSONB NOT NULL,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT now(),
    PRIMARY KEY (thread_id, checkpoint_id)
);
```

Purpose:

```text
- preserve agent state
- survive pod restarts
- resume long-running tasks
- support multi-step workflows
```

---

## 4.5 `agent_runs`

Stores one execution/run of an agent workflow.

```sql
CREATE TABLE agent_runs (
    id UUID PRIMARY KEY,
    session_id UUID REFERENCES chat_sessions(id) ON DELETE SET NULL,
    user_message TEXT,
    task_type TEXT,
    domain TEXT,
    risk_level TEXT,
    status TEXT, -- running, completed, failed, blocked
    started_at TIMESTAMPTZ DEFAULT now(),
    completed_at TIMESTAMPTZ,
    error_code TEXT,
    summary TEXT,
    metadata_json JSONB DEFAULT '{}'
);
```

---

## 4.6 `tool_calls`

Stores every tool call from every agent run.

```sql
CREATE TABLE tool_calls (
    id UUID PRIMARY KEY,
    run_id UUID REFERENCES agent_runs(id) ON DELETE CASCADE,
    tool_name TEXT NOT NULL,
    agent_name TEXT,
    backend TEXT, -- pyvmomi, govc, govmomi, k8s, rest, mcp
    risk_level TEXT,
    status TEXT, -- success, error, blocked, timeout
    input_summary TEXT,
    output_summary TEXT,
    error_code TEXT,
    duration_ms INTEGER,
    started_at TIMESTAMPTZ DEFAULT now(),
    completed_at TIMESTAMPTZ,
    metadata_json JSONB DEFAULT '{}'
);
```

Important:

```text
Do not store full secret-bearing inputs.
Store summaries only.
```

---

## 4.7 `audit_events`

Stores security/audit history.

```sql
CREATE TABLE audit_events (
    id UUID PRIMARY KEY,
    actor TEXT,
    event_type TEXT NOT NULL,
    resource_type TEXT,
    resource_name TEXT,
    tool_name TEXT,
    risk_level TEXT,
    status TEXT,
    created_at TIMESTAMPTZ DEFAULT now(),
    metadata_json JSONB DEFAULT '{}'
);
```

Example event types:

```text
TOOL_CALLED
TOOL_BLOCKED
VCENTER_TESTED
SECRET_UPDATED
LLM_PROVIDER_CONNECTED
HIGH_RISK_ACTION_BLOCKED
APPROVAL_REQUEST_CREATED
APPROVAL_GRANTED
APPROVAL_REJECTED
REPORT_GENERATED
```

---

## 4.8 `reports`

Stores generated report metadata and optionally Markdown content.

```sql
CREATE TABLE reports (
    id UUID PRIMARY KEY,
    run_id UUID REFERENCES agent_runs(id) ON DELETE SET NULL,
    report_type TEXT NOT NULL, -- csi_va, vcenter_health, rke2_health
    title TEXT,
    status TEXT,
    content_markdown TEXT,
    object_uri TEXT,
    created_at TIMESTAMPTZ DEFAULT now(),
    metadata_json JSONB DEFAULT '{}'
);
```

If reports become large:

```text
Store content in MinIO/S3.
Keep only object_uri in Postgres.
```

---

## 4.9 `approval_requests`

For future high-risk action workflow.

```sql
CREATE TABLE approval_requests (
    id UUID PRIMARY KEY,
    run_id UUID REFERENCES agent_runs(id) ON DELETE SET NULL,
    tool_name TEXT NOT NULL,
    requested_action TEXT NOT NULL,
    risk_level TEXT NOT NULL,
    status TEXT DEFAULT 'pending', -- pending, approved, rejected, expired, cancelled
    requested_by TEXT,
    approved_by TEXT,
    reason TEXT,
    created_at TIMESTAMPTZ DEFAULT now(),
    decided_at TIMESTAMPTZ,
    metadata_json JSONB DEFAULT '{}'
);
```

Current phase:

```text
Create table now or later.
Do not execute risky actions yet.
```

---

## 4.10 `tool_registry_snapshots`

Optional table for tracking tool registry versions.

```sql
CREATE TABLE tool_registry_snapshots (
    id UUID PRIMARY KEY,
    version TEXT NOT NULL,
    tools_json JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now()
);
```

Useful for audit:

```text
Which tools existed when this agent run happened?
Was a tool enabled or disabled at that time?
```

---

# 5. Redis Key Design

## 5.1 Tool Result Cache

Key pattern:

```text
toolcache:{tool_name}:{hash_of_input}
```

Examples:

```text
toolcache:get_host_details:esxi01-dclab-com
toolcache:get_vm_details:roshellevm02
toolcache:list_vms:default
toolcache:get_datastore_health:default
toolcache:get_csi_va_check:default
```

Recommended values:

```json
{
  "ok": true,
  "data": {},
  "metadata": {
    "source": "pyvmomi",
    "cached_at": "2026-05-10T10:00:00Z"
  }
}
```

---

## 5.2 TTL Plan

```text
VM details: 60s
Host details: 60s
Inventory list: 60–120s
Datastore health: 60s
Recent events: 30s
CSI VA check: 120s
LLM model list: 10m
Health status: 15–30s
```

---

## 5.3 No-Cache Rules

Never cache:

```text
auth failures
permission errors
NotAuthenticated
VCENTER_SESSION_EXPIRED
VCENTER_AUTH_FAILED
VCENTER_SSL_ERROR
TOOL_POLICY_BLOCKED
TOOL_REQUIRES_APPROVAL
destructive tool responses
approval decisions without TTL
```

If a cached value contains an auth/session error:

```text
1. Delete the cache key.
2. Reconnect/retry once.
3. If retry fails, return clean error.
```

---

## 5.4 Temporary Run State

Key patterns:

```text
run:{run_id}:status
run:{run_id}:events
run:{run_id}:latest
session:{session_id}:active_run
```

Use for:

```text
- streaming state
- active run lookup
- resumable UI status
- short-lived SSE buffer
```

TTL:

```text
15 minutes to 2 hours depending on use case.
```

---

## 5.5 Future Queue Keys

For lightweight queue or KEDA later:

```text
queue:agent-runs
queue:reports
queue:security-scans
queue:csi-va-checks
```

Redis is okay for first queue implementation.

For heavier workloads, consider:

```text
NATS JetStream
RabbitMQ
Temporal
Argo Workflows
Kubernetes Jobs
```

---

# 6. Kubernetes Secrets Plan

## 6.1 vCenter Secret

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: agentic-vcenter-default
  namespace: agentic-app
type: Opaque
stringData:
  VCENTER_URL: "https://core-infra-vc01.dclab.com"
  VCENTER_USERNAME: "administrator@vsphere.local"
  VCENTER_PASSWORD: "REDACTED"
  VCENTER_VERIFY_SSL: "false"
```

## 6.2 LLM Provider Secrets

```text
agentic-llm-gemini
agentic-llm-openai
agentic-llm-anthropic
agentic-llm-xai
agentic-llm-moonshot
```

Example:

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: agentic-llm-gemini
  namespace: agentic-app
type: Opaque
stringData:
  PROVIDER: "gemini"
  API_KEY: "REDACTED"
  BASE_URL: ""
  DEFAULT_MODEL: "gemini-2.5-flash"
```

## 6.3 Database Secrets

```text
agentic-postgres-secret
agentic-redis-secret
```

---

# 7. Alternatives

## 7.1 Keep Postgres + Redis

Recommended now.

Pros:

```text
simple
well understood
works well with FastAPI
works with LangGraph checkpointing
good for audit/reporting
easy in Kubernetes
```

Cons:

```text
must manage backups
must protect secrets
must tune Redis memory/TTL
```

---

## 7.2 Kubernetes Secrets + ConfigMaps only

For very small setup:

```text
Kubernetes Secrets = credentials
ConfigMaps = non-sensitive settings
Postgres = only sessions/audit/checkpoints
```

This is okay, but UI-driven settings become harder to query/history.

---

## 7.3 Vault / External Secrets

For enterprise-grade deployments:

```text
HashiCorp Vault
External Secrets Operator
AWS Secrets Manager
Azure Key Vault
GCP Secret Manager
```

Recommended later if customer-facing.

Pattern:

```text
Postgres stores secret_ref.
External secret store holds actual secret.
Kubernetes Secret is synced or mounted.
```

---

## 7.4 NATS / RabbitMQ Instead of Redis Queue

Redis is fine for lightweight queue.

For heavier jobs:

```text
NATS JetStream = fast, cloud-native, good event streaming
RabbitMQ = mature task queue
Kafka = large-scale event streaming
Temporal = durable workflow orchestration
Argo Workflows = Kubernetes-native long job execution
```

Recommendation:

```text
Start with Redis queue.
Move to NATS/RabbitMQ if queue reliability becomes important.
Use Temporal if workflows become very long and business-critical.
Use Kubernetes Jobs for heavy security scans.
```

---

## 7.5 Object Storage for Reports

Use later when reports become large.

Options:

```text
MinIO
S3
NFS-backed object storage
```

Pattern:

```text
Postgres:
report_id, title, object_uri, metadata

Object storage:
reports/csi-va/<run_id>/report.md
reports/csi-va/<run_id>/evidence.json
```

---

# 8. Kubernetes Deployment Notes

## 8.1 Postgres

Use:

```text
StatefulSet or Helm chart
PersistentVolumeClaim
Secret for password
Service ClusterIP
Backup plan
```

Minimum lab sizing:

```text
CPU: 500m–1
Memory: 1Gi–2Gi
Storage: 20Gi–50Gi
```

Production/customer sizing depends on audit/session volume.

---

## 8.2 Redis

Use:

```text
Deployment or StatefulSet
PVC optional
Secret for password
Service ClusterIP
memory limit
eviction policy
```

Minimum lab sizing:

```text
CPU: 250m–500m
Memory: 512Mi–1Gi
```

Redis should have explicit TTL use. Avoid unlimited cache growth.

---

## 8.3 Readiness/Liveness

FastAPI readiness should check:

```text
app started
Postgres reachable
Redis optional/reachable
tool registry loaded
```

Do not make vCenter required for FastAPI readiness.

Correct:

```text
vCenter status appears in System Health page.
FastAPI still runs if vCenter is down.
```

Wrong:

```text
FastAPI pod not ready because vCenter is unreachable.
```

---

# 9. Backup and Retention

## Postgres Backup

Back up:

```text
chat sessions
audit logs
reports metadata
approval history
connection metadata
checkpoints if needed
```

Retention:

```text
audit logs: 90 days or more
chat sessions: configurable
tool calls: 30–90 days
reports: long-term if useful
checkpoints: can be pruned
```

## Redis Backup

Usually not required for cache.

If using Redis queue:

```text
consider persistence or move queue to RabbitMQ/NATS/Temporal
```

---

# 10. Security Rules

```text
1. Do not store actual secrets in Postgres.
2. Do not return secrets from API.
3. Do not log secrets.
4. Audit secret updates without storing secret values.
5. Encrypt backups.
6. Restrict database network access with NetworkPolicy.
7. Use service accounts with least privilege.
8. Use read-only DB users for analytics/reporting if needed.
```

---

# 11. Implementation Roadmap

## DB-1 — Deploy Postgres + Redis

```text
Create Helm/manifests.
Create secrets.
Create services.
Verify FastAPI can connect.
```

## DB-2 — Create Core Tables

```text
connection_profiles
chat_sessions
chat_messages
agent_runs
tool_calls
audit_events
reports
```

## DB-3 — Secret Reference Model

```text
Move actual credentials to Kubernetes Secrets.
Store only secret_name/metadata in Postgres.
```

## DB-4 — LangGraph Checkpointing

```text
Use LangGraph Postgres checkpointer if possible.
Create langgraph checkpoint schema.
Verify state survives Agent Engine pod restart.
```

## DB-5 — Redis Cache

```text
Implement cache_service.
Add TTL.
Add refresh=true cache bypass.
Add no-cache rules for auth/tool failures.
```

## DB-6 — Audit Logging

```text
Audit tool calls.
Audit blocked actions.
Audit credential updates.
Audit provider connections.
```

## DB-7 — Reports and Evidence

```text
Store report metadata in Postgres.
Store Markdown in Postgres first.
Move large evidence to MinIO later.
```

## DB-8 — Future Approval Workflow

```text
Create approval_requests table.
Block risky tools until approval is implemented.
```

---

# 12. Codex Implementation Prompt

Use this prompt with Codex.

```text
You are working on the AgenticOps vCenter Agentic Ops Platform.

Implement the database architecture based on this knowledge document.

Core rules:
1. Postgres stores durable metadata, sessions, checkpoints, audit logs, tool calls, reports, and approval requests.
2. Redis stores short-lived tool result cache, temporary run state, and future queue state.
3. Kubernetes Secrets store actual vCenter credentials and LLM API keys.
4. Do not store actual passwords or API keys in Postgres.
5. Postgres should store only secret_name/secret_ref and metadata.
6. Do not return secrets from APIs.
7. Do not log secrets.
8. Do not cache auth failures or NotAuthenticated errors.
9. Do not make vCenter required for FastAPI readiness.

Create or update:
- DB connection layer
- SQLAlchemy models or equivalent ORM models
- Alembic migrations if used
- repositories for sessions, audit, reports, tool calls, approvals
- Redis cache service
- Secret reference model
- health checks for Postgres and Redis
- audit logging for tool calls and blocked actions

Tables:
- connection_profiles
- chat_sessions
- chat_messages
- agent_runs
- tool_calls
- audit_events
- reports
- approval_requests
- langgraph_checkpoints if not using official LangGraph checkpointer schema
- tool_registry_snapshots optional

Redis:
- toolcache:{tool}:{hash}
- run:{run_id}:status
- run:{run_id}:events
- session:{session_id}:active_run
- future queue keys

Validation:
1. FastAPI can connect to Postgres.
2. FastAPI can connect to Redis.
3. vCenter credentials stay in Kubernetes Secret.
4. connection_profiles stores secret_name only.
5. Tool calls are recorded.
6. Audit events are recorded.
7. Redis cache respects TTL.
8. Auth failures are not cached.
9. LangGraph checkpoint survives pod restart if implemented.
```

---

# 13. Final Recommendation

Use this design:

```text
Postgres:
- durable platform memory
- settings metadata
- LangGraph checkpoints
- sessions
- tool history
- audit
- reports
- approvals

Redis:
- short-lived tool cache
- temporary run state
- future lightweight queue

Kubernetes Secrets:
- all sensitive credentials

Object Storage later:
- large reports and evidence bundles
```

This is the safest and cleanest design for the AgenticOps platform.
