# Phase 1.2 — Settings & Credentials Backend Wiring

> **Branch**: `main-rke2-mcp` | **Commit**: `7994bff` | **Date**: 2026-05-07

---

## What Phase 1.2 Delivers

```
User opens Settings page
  → Enters vCenter/LLM credentials
  → Clicks Test Connection → FastAPI validates via pyVmomi/httpx
  → Clicks Save → FastAPI stores as Kubernetes Secret
  → Dashboard shows safe status only (no passwords exposed)
  → Inventory/Agent can use stored credentials later
```

---

## Backend — New Files

```
apps/backend/
├── app/api/
│   ├── routes/connections.py          # vCenter + LLM endpoints (8 routes)
│   └── schemas/
│       └── connections.py             # Pydantic models (13 classes)
├── app/services/
│   ├── k8s_secret_store.py            # K8s Secret CRUD + masking helpers
│   ├── vcenter_connection_service.py  # pyVmomi connection test
│   └── llm_connection_service.py      # OpenAI/OpenRouter httpx test
└── app/core/
    └── __init__.py
```

## Backend — API Endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/api/v1/connections/vcenter/test` | Test vCenter connection |
| POST | `/api/v1/connections/vcenter` | Test + save vCenter credentials |
| GET | `/api/v1/connections/vcenter/status` | Safe status (no password) |
| DELETE | `/api/v1/connections/vcenter` | Delete vCenter secret |
| POST | `/api/v1/connections/llm/test` | Test LLM connection |
| POST | `/api/v1/connections/llm` | Test + save LLM credentials |
| GET | `/api/v1/connections/llm/status` | Safe status (no API key) |
| DELETE | `/api/v1/connections/llm` | Delete LLM secret |

## Backend — Security

| Rule | Status |
|---|---|
| Passwords never returned in API responses | Verified |
| API keys never returned in API responses | Verified |
| Test must pass before save | Enforced |
| Password fields never logged | Enforced |
| Error codes are user-friendly (not stack traces) | Enforced |
| Secrets stored as K8s Secrets | Enforced |
| Namespace-scoped RBAC | Enforced |

## Backend — Error Codes

```text
VCENTER_AUTH_FAILED     → "Authentication failed. Check username and password."
VCENTER_DNS_FAILED      → "Cannot resolve hostname. Check the vCenter URL."
VCENTER_UNREACHABLE     → "Could not reach vCenter. Check network connectivity."
VCENTER_SSL_ERROR       → "SSL certificate error. Try enabling 'Ignore SSL'."
VCENTER_UNKNOWN_ERROR   → "An unknown error occurred connecting to vCenter."
LLM_AUTH_FAILED         → "Invalid API key. Check your credentials."
LLM_MODEL_NOT_FOUND     → "Model not found or not available."
LLM_UNREACHABLE         → "Could not reach the LLM provider. Check URL."
LLM_UNKNOWN_ERROR       → "An unknown error occurred testing LLM."
```

## Kubernetes — RBAC

```yaml
# k8s/apps/agentic-app/fastapi/
├── serviceaccount.yaml    # agentic-api SA
├── rbac.yaml              # Role + RoleBinding for secret management
└── deployment.yaml        # Updated: serviceAccountName: agentic-api
```

**SA**: `agentic-api` | **Role**: `agentic-api-secret-manager`  
**Permissions**: get, create, update, patch, delete secrets in `agentic-app` namespace

## Kubernetes — Secrets

```text
agentic-vcenter-default
  keys: VCENTER_NAME, VCENTER_URL, VCENTER_USERNAME, VCENTER_PASSWORD,
        VCENTER_VERIFY_SSL, VCENTER_CREATED_AT, VCENTER_UPDATED_AT,
        VCENTER_LAST_TEST_STATUS, VCENTER_LAST_TESTED_AT

agentic-llm-provider-default
  keys: LLM_PROVIDER, LLM_BASE_URL, LLM_MODEL, LLM_API_KEY,
        LLM_CREATED_AT, LLM_UPDATED_AT,
        LLM_LAST_TEST_STATUS, LLM_LAST_TESTED_AT
```

## Frontend — Settings Page

- vCenter card: Connection Name, URL, Username, Password (masked), SSL toggle
- LLM card: Provider, Base URL, Model, API Key (masked)
- Test Connection → success/failure toast
- Save Credentials → stores via K8s Secret
- Delete Credentials → confirmation dialog → removes secret
- Status display: configured badge, URL, username hint, password_set, last test
- Passwords/keys never prefilled, never returned in responses

## Frontend — API Client Additions

```typescript
// lib/api.ts
testVCenterConnection(payload)   → POST /api/v1/connections/vcenter/test
saveVCenterConnection(payload)   → POST /api/v1/connections/vcenter
getVCenterConnectionStatus()     → GET /api/v1/connections/vcenter/status
deleteVCenterConnection()        → DELETE /api/v1/connections/vcenter
testLLMConnection(payload)       → POST /api/v1/connections/llm/test
saveLLMConnection(payload)       → POST /api/v1/connections/llm
getLLMConnectionStatus()         → GET /api/v1/connections/llm/status
deleteLLMConnection()            → DELETE /api/v1/connections/llm
```

## Build Fixes

| Issue | Fix |
|---|---|
| CI used `NEXT_PUBLIC_API_URL` but code used `NEXT_PUBLIC_API_BASE_URL` | Added both to CI + Dockerfile |
| FastAPI deployment used `default` SA | Added `serviceAccountName: agentic-api` |
| Backend missing `kubernetes` and `pyvmomi` | Added to requirements.txt |
| CORS origin wrong | Updated to `https://infra-agent-console.dclab.local` |

## Verification

```bash
kubectl auth can-i get secret/agentic-vcenter-default \
  --as=system:serviceaccount:agentic-app:agentic-api -n agentic-app
# Expected: yes

kubectl get sa agentic-api -n agentic-app
# Expected: agentic-api

kubectl get role,rolebinding -n agentic-app | grep agentic-api
# Expected: agentic-api-secret-manager
```
