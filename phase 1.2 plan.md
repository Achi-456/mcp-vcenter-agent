Below is a **full detailed Phase 1.2 plan** for your project.

```text
Phase 1.2 Goal:
Build secure credential and connection management from the dashboard,
so vCenter and LLM credentials can be entered, tested, saved, checked,
and deleted through the UI without exposing secrets back to the browser.
```

---

# Phase 1.2 — Settings & Credentials Backend Wiring

## 1. What Phase 1.2 must deliver

At the end of Phase 1.2, your dashboard should support this flow:

```text
User opens Settings page
        ↓
User enters vCenter credentials
        ↓
Clicks Test Connection
        ↓
FastAPI validates the credentials by connecting to vCenter
        ↓
User clicks Save
        ↓
FastAPI stores credentials as Kubernetes Secret
        ↓
Dashboard shows safe status only
        ↓
Inventory and Agent Engine can use those credentials later
```

Same concept for LLM provider:

```text
User enters LLM provider settings
        ↓
Clicks Test LLM
        ↓
FastAPI sends small test request to model provider
        ↓
User clicks Save
        ↓
FastAPI stores API key as Kubernetes Secret
        ↓
Dashboard shows provider/model/configured status only
```

---

# 2. Phase 1.2 scope

## In scope

```text
✅ FastAPI connections router
✅ vCenter credential test endpoint
✅ vCenter credential save endpoint
✅ vCenter credential status endpoint
✅ vCenter credential delete endpoint
✅ LLM credential test endpoint
✅ LLM credential save endpoint
✅ LLM credential status endpoint
✅ LLM credential delete endpoint
✅ Kubernetes Secret storage service
✅ RBAC for FastAPI service account
✅ Frontend Settings page wiring
✅ Safe status display
✅ Error handling
✅ Toast notifications
✅ Form validation
✅ Audit-friendly response messages
```

## Out of scope for Phase 1.2

```text
❌ Real inventory table data
❌ Full LangGraph agent tool calling
❌ VM power operations
❌ Snapshot operations
❌ Migration operations
❌ Approval workflow
❌ Vault integration
❌ External Secrets Operator
❌ Multi-tenant credential management
```

Those come later.

---

# 3. Recommended endpoint design

Use a new FastAPI router:

```text
apps/api/app/routers/connections.py
```

Base path:

```text
/api/v1/connections
```

## vCenter endpoints

```http
POST   /api/v1/connections/vcenter/test
POST   /api/v1/connections/vcenter
GET    /api/v1/connections/vcenter/status
DELETE /api/v1/connections/vcenter
```

## LLM endpoints

```http
POST   /api/v1/connections/llm/test
POST   /api/v1/connections/llm
GET    /api/v1/connections/llm/status
DELETE /api/v1/connections/llm
```

## Keep this separation

```text
/settings
    Used for normal non-secret settings

/connections
    Used for credentials, API keys, connection testing, and secret status
```

This keeps your backend clean.

---

# 4. Backend file structure

Add these files:

```text
apps/api/app/
├── routers/
│   └── connections.py
│
├── schemas/
│   └── connections.py
│
├── services/
│   ├── k8s_secret_store.py
│   ├── vcenter_connection_service.py
│   └── llm_connection_service.py
│
├── core/
│   └── security.py
│
└── main.py
```

Expected purpose:

```text
connections.py
    FastAPI routes

schemas/connections.py
    Pydantic request/response models

k8s_secret_store.py
    Create, update, read metadata, and delete Kubernetes Secrets

vcenter_connection_service.py
    Test vCenter connection

llm_connection_service.py
    Test LLM provider connection

security.py
    Helpers for masking usernames, safe response handling, validation
```

---

# 5. Kubernetes Secret names

Use predictable names:

```text
agentic-vcenter-default
agentic-llm-provider-default
```

Namespace:

```text
agentic-app
```

or whatever your actual app namespace is. Keep one consistent namespace in manifests and docs.

---

# 6. vCenter Secret format

Secret name:

```text
agentic-vcenter-default
```

Secret keys:

```text
VCENTER_NAME
VCENTER_URL
VCENTER_USERNAME
VCENTER_PASSWORD
VCENTER_VERIFY_SSL
VCENTER_CREATED_AT
VCENTER_UPDATED_AT
VCENTER_LAST_TEST_STATUS
VCENTER_LAST_TESTED_AT
```

Example logical values:

```text
VCENTER_NAME=dclab-vcenter
VCENTER_URL=https://vcenter.dclab.local
VCENTER_USERNAME=administrator@vsphere.local
VCENTER_PASSWORD=********
VCENTER_VERIFY_SSL=false
VCENTER_CREATED_AT=2026-05-07T10:00:00Z
VCENTER_UPDATED_AT=2026-05-07T10:20:00Z
VCENTER_LAST_TEST_STATUS=success
VCENTER_LAST_TESTED_AT=2026-05-07T10:19:30Z
```

Important: the actual Secret stores the password, but the API never returns it.

---

# 7. LLM Secret format

Secret name:

```text
agentic-llm-provider-default
```

Secret keys:

```text
LLM_PROVIDER
LLM_BASE_URL
LLM_MODEL
LLM_API_KEY
LLM_CREATED_AT
LLM_UPDATED_AT
LLM_LAST_TEST_STATUS
LLM_LAST_TESTED_AT
```

Example:

```text
LLM_PROVIDER=openrouter
LLM_BASE_URL=https://openrouter.ai/api/v1
LLM_MODEL=anthropic/claude-sonnet-4.5
LLM_API_KEY=********
LLM_CREATED_AT=2026-05-07T10:00:00Z
LLM_UPDATED_AT=2026-05-07T10:15:00Z
LLM_LAST_TEST_STATUS=success
LLM_LAST_TESTED_AT=2026-05-07T10:14:20Z
```

---

# 8. Request and response models

## vCenter test request

```json
{
  "name": "dclab-vcenter",
  "vcenter_url": "https://vcenter.dclab.local",
  "username": "administrator@vsphere.local",
  "password": "secret-password",
  "verify_ssl": false
}
```

## vCenter test success response

```json
{
  "ok": true,
  "status": "success",
  "message": "Connected to vCenter successfully.",
  "details": {
    "vcenter_url": "https://vcenter.dclab.local",
    "username_hint": "administrator@vsphere.local",
    "server_time": "2026-05-07T10:30:00Z"
  }
}
```

## vCenter test failure response

```json
{
  "ok": false,
  "status": "failed",
  "message": "Unable to connect to vCenter.",
  "error_code": "VCENTER_AUTH_FAILED"
}
```

Do not return raw exception details to frontend.

---

## vCenter save request

Same as test request:

```json
{
  "name": "dclab-vcenter",
  "vcenter_url": "https://vcenter.dclab.local",
  "username": "administrator@vsphere.local",
  "password": "secret-password",
  "verify_ssl": false
}
```

## vCenter save response

```json
{
  "ok": true,
  "status": "saved",
  "message": "vCenter credentials saved securely.",
  "connection": {
    "configured": true,
    "name": "dclab-vcenter",
    "vcenter_url": "https://vcenter.dclab.local",
    "username_hint": "administrator@vsphere.local",
    "verify_ssl": false,
    "last_test_status": "success",
    "last_tested_at": "2026-05-07T10:30:00Z"
  }
}
```

---

## vCenter status response

```json
{
  "configured": true,
  "name": "dclab-vcenter",
  "vcenter_url": "https://vcenter.dclab.local",
  "username_hint": "administrator@vsphere.local",
  "verify_ssl": false,
  "password_set": true,
  "last_test_status": "success",
  "last_tested_at": "2026-05-07T10:30:00Z"
}
```

Allowed:

```text
configured
name
url
username hint
verify_ssl
password_set true/false
last_test_status
last_tested_at
```

Not allowed:

```text
password
full token
private key
raw secret value
```

---

## LLM test request

```json
{
  "provider": "openrouter",
  "base_url": "https://openrouter.ai/api/v1",
  "model": "anthropic/claude-sonnet-4.5",
  "api_key": "secret-api-key"
}
```

## LLM status response

```json
{
  "configured": true,
  "provider": "openrouter",
  "base_url": "https://openrouter.ai/api/v1",
  "model": "anthropic/claude-sonnet-4.5",
  "api_key_set": true,
  "last_test_status": "success",
  "last_tested_at": "2026-05-07T10:30:00Z"
}
```

---

# 9. Pydantic schema plan

Create:

```text
apps/api/app/schemas/connections.py
```

Models:

```text
VCenterConnectionRequest
VCenterConnectionStatus
VCenterTestResponse
VCenterSaveResponse

LLMConnectionRequest
LLMConnectionStatus
LLMTestResponse
LLMSaveResponse

ConnectionDeleteResponse
```

Validation rules:

```text
vCenter URL must start with https:// or http://
Username cannot be empty
Password minimum length maybe 1 for lab, 8 for production
verify_ssl must be boolean

Provider must be one of:
- openai
- openrouter
- azure-openai
- local

Base URL must be valid URL
Model cannot be empty
API key cannot be empty unless provider=local
```

For your lab, allow:

```text
verify_ssl=false
```

Because self-signed certificates are common in vSphere labs.

---

# 10. Kubernetes Secret service plan

Create:

```text
apps/api/app/services/k8s_secret_store.py
```

Functions needed:

```text
create_or_update_secret(name, data, labels)
get_secret(name)
get_secret_status(name)
delete_secret(name)
secret_exists(name)
```

Behavior:

```text
If running inside Kubernetes:
    use in-cluster config

If running locally:
    use local kubeconfig if available
```

Labels to apply:

```yaml
app.kubernetes.io/name: agentic-ops
app.kubernetes.io/component: credentials
agentic.io/managed-by: fastapi
agentic.io/secret-type: vcenter
```

For LLM secret:

```yaml
agentic.io/secret-type: llm
```

Important:

```text
Never log Secret values.
Never print request body with passwords.
Never return Secret data directly.
```

---

# 11. FastAPI service account RBAC

Your FastAPI pod needs permission to manage only these two secrets.

Create or update:

```text
k8s/apps/agentic-app/api/rbac.yaml
```

Recommended resources:

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: agentic-api
  namespace: agentic-app
```

Role:

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: agentic-api-secret-manager
  namespace: agentic-app
rules:
  - apiGroups: [""]
    resources: ["secrets"]
    resourceNames:
      - agentic-vcenter-default
      - agentic-llm-provider-default
    verbs: ["get", "create", "update", "patch", "delete"]
```

RoleBinding:

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: agentic-api-secret-manager
  namespace: agentic-app
subjects:
  - kind: ServiceAccount
    name: agentic-api
    namespace: agentic-app
roleRef:
  kind: Role
  name: agentic-api-secret-manager
  apiGroup: rbac.authorization.k8s.io
```

Then make sure FastAPI deployment uses:

```yaml
serviceAccountName: agentic-api
```

Important note: Kubernetes RBAC `create` with `resourceNames` can be tricky because creation does not always know the resource name before admission. If this causes issues, use:

```yaml
verbs: ["get", "list", "create", "update", "patch", "delete"]
```

but keep the namespace limited and add app-level validation to only allow those two names.

---

# 12. Backend route behavior

## POST `/api/v1/connections/vcenter/test`

Steps:

```text
1. Receive vCenter credentials
2. Validate URL, username, password
3. Try connecting to vCenter
4. Return success/failure
5. Do not save secret
```

Use this button for dashboard:

```text
Test Connection
```

---

## POST `/api/v1/connections/vcenter`

Steps:

```text
1. Receive vCenter credentials
2. Validate input
3. Optionally test connection before saving
4. Store as Kubernetes Secret
5. Return safe status
```

Recommended behavior:

```text
Always test before saving.
If test fails, do not save unless request includes force_save=true.
```

For Phase 1.2, keep it simple:

```text
No force_save.
Test must pass before save.
```

---

## GET `/api/v1/connections/vcenter/status`

Steps:

```text
1. Check if secret exists
2. If no secret, return configured=false
3. If secret exists, read safe metadata
4. Return URL, username_hint, verify_ssl, password_set, last_test_status
5. Never return password
```

---

## DELETE `/api/v1/connections/vcenter`

Steps:

```text
1. Delete Kubernetes Secret
2. Return ok=true
3. Frontend updates status to not configured
```

---

## LLM route behavior

Same pattern:

```text
POST /llm/test
    Test provider using supplied API key

POST /llm
    Test and save as Kubernetes Secret

GET /llm/status
    Return safe metadata only

DELETE /llm
    Delete secret
```

---

# 13. vCenter connection test details

Use `pyVmomi` in FastAPI.

Install dependency if not already available:

```bash
pip install pyvmomi
```

Or add to your API dependency file:

```text
pyvmomi
```

Connection logic:

```text
Input:
    vcenter_url
    username
    password
    verify_ssl

Process:
    Parse hostname from URL
    Create SSL context
    Connect to vCenter
    Read service instance content
    Disconnect

Success means:
    Authentication works
    Network path works
    Certificate mode works
```

Common error mapping:

```text
Invalid credentials
    VCENTER_AUTH_FAILED

Cannot resolve hostname
    VCENTER_DNS_FAILED

Connection refused / timeout
    VCENTER_UNREACHABLE

SSL certificate error
    VCENTER_SSL_ERROR

Unknown pyVmomi error
    VCENTER_UNKNOWN_ERROR
```

Return friendly messages, not raw stack traces.

---

# 14. LLM connection test details

For Phase 1.2, support these provider types:

```text
openai
openrouter
local
```

Recommended test behavior:

```text
openai:
    GET /models or small chat completion

openrouter:
    GET /models or small chat completion

local:
    GET /health or /v1/models depending on your local endpoint
```

For simplicity, use a small test prompt:

```text
Reply with only: ok
```

Timeout:

```text
10 seconds
```

Do not send long prompts.

Do not log API key.

---

# 15. Frontend changes needed

Current Settings page already exists. Now update it to use the new connections endpoints.

Frontend files to update:

```text
apps/frontend/lib/api.ts
apps/frontend/app/settings/page.tsx
```

Optional new files:

```text
apps/frontend/lib/types.ts
apps/frontend/lib/validators.ts
apps/frontend/components/settings/vcenter-credentials-card.tsx
apps/frontend/components/settings/llm-credentials-card.tsx
apps/frontend/hooks/use-connection-status.ts
```

---

# 16. Frontend API client functions

In:

```text
apps/frontend/lib/api.ts
```

Add:

```text
testVCenterConnection(payload)
saveVCenterConnection(payload)
getVCenterConnectionStatus()
deleteVCenterConnection()

testLLMConnection(payload)
saveLLMConnection(payload)
getLLMConnectionStatus()
deleteLLMConnection()
```

Use endpoints:

```text
POST /api/v1/connections/vcenter/test
POST /api/v1/connections/vcenter
GET  /api/v1/connections/vcenter/status
DELETE /api/v1/connections/vcenter

POST /api/v1/connections/llm/test
POST /api/v1/connections/llm
GET  /api/v1/connections/llm/status
DELETE /api/v1/connections/llm
```

---

# 17. Settings page UI design

Settings page should have these cards:

```text
vCenter Connection
LLM Provider
Connection Status
Danger Zone
```

## vCenter card fields

```text
Connection Name
vCenter URL
Username
Password
Verify SSL switch
```

Buttons:

```text
Test Connection
Save Credentials
Delete Credentials
```

Status display:

```text
Configured: Yes/No
URL: https://vcenter.dclab.local
Username: administrator@vsphere.local
Password: Saved / Not saved
Last Test: Success / Failed / Never
Last Tested At: timestamp
```

---

## LLM card fields

```text
Provider
Base URL
Model
API Key
```

Provider dropdown:

```text
OpenAI
OpenRouter
Local
```

Buttons:

```text
Test LLM
Save Credentials
Delete Credentials
```

Status display:

```text
Configured: Yes/No
Provider: openrouter
Model: anthropic/claude-sonnet-4.5
API Key: Saved / Not saved
Last Test: Success / Failed / Never
```

---

# 18. Form validation rules

Use:

```text
react-hook-form
zod
```

vCenter validation:

```text
name: required, min 2 chars
vcenter_url: required, valid URL
username: required
password: required when saving new credential
verify_ssl: boolean
```

LLM validation:

```text
provider: required
base_url: required unless local default
model: required
api_key: required unless provider=local
```

UX rule:

```text
When status already configured, password field should be empty.
Placeholder: "Enter new password to replace existing credential"
```

Do not prefill password.

---

# 19. Safe credential UX

Important behavior:

```text
When loading settings page:
    Fetch status only.
    Do not fetch secret values.
    Do not fill password or API key fields.

When saving:
    Send current typed password/API key.
    Clear password field after successful save.

When testing:
    Use typed values from form.
    Do not persist unless user clicks Save.

When deleting:
    Show confirmation dialog.
```

Display examples:

```text
Password: Configured
API Key: Configured
```

Never display:

```text
Password: my-secret-password
API Key: sk-...
```

---

# 20. Error handling plan

Backend should return consistent error shape:

```json
{
  "ok": false,
  "status": "failed",
  "message": "Unable to connect to vCenter.",
  "error_code": "VCENTER_AUTH_FAILED"
}
```

Frontend should show:

```text
Toast:
    vCenter connection failed

Card:
    Unable to connect to vCenter.
    Reason: Authentication failed.
```

Do not show stack traces in UI.

Backend logs can include:

```text
request_id
connection type
error code
safe message
```

Backend logs must not include:

```text
password
api_key
authorization header
full request body
```

---

# 21. Observability and logging

Add basic logs:

```text
vCenter test started
vCenter test success
vCenter test failed with error_code
vCenter secret saved
vCenter secret deleted

LLM test started
LLM test success
LLM test failed with error_code
LLM secret saved
LLM secret deleted
```

Include request ID if you already have one.

Example safe log:

```text
INFO vcenter_test_success url=https://vcenter.dclab.local username_hint=administrator@vsphere.local
```

Bad log:

```text
ERROR password=MyPassword123
```

Never do that.

---

# 22. Security checklist

Phase 1.2 must follow these rules:

```text
✅ Secrets never stored in frontend
✅ Secrets never stored in localStorage
✅ Secrets never stored in NEXT_PUBLIC env vars
✅ Secrets never returned from FastAPI
✅ Secrets never printed in logs
✅ Password fields never prefilled
✅ API keys never prefilled
✅ Kubernetes Secrets are namespace-scoped
✅ FastAPI service account has limited RBAC
✅ Delete credential action requires confirmation
✅ Connection tests have timeout
✅ Failed test does not save credentials
```

Optional but recommended:

```text
✅ Add rate limit for test endpoints later
✅ Add audit event table later
✅ Add user authentication later
```

---

# 23. Kubernetes deployment changes

FastAPI deployment must use the correct ServiceAccount:

```yaml
spec:
  template:
    spec:
      serviceAccountName: agentic-api
```

Also confirm namespace:

```bash
kubectl get deploy -n agentic-app
kubectl get sa -n agentic-app
kubectl get role -n agentic-app
kubectl get rolebinding -n agentic-app
```

After deploying RBAC:

```bash
kubectl auth can-i get secret/agentic-vcenter-default \
  --as=system:serviceaccount:agentic-app:agentic-api \
  -n agentic-app
```

Expected:

```text
yes
```

Also check create/update/delete:

```bash
kubectl auth can-i create secrets \
  --as=system:serviceaccount:agentic-app:agentic-api \
  -n agentic-app

kubectl auth can-i patch secret/agentic-vcenter-default \
  --as=system:serviceaccount:agentic-app:agentic-api \
  -n agentic-app

kubectl auth can-i delete secret/agentic-vcenter-default \
  --as=system:serviceaccount:agentic-app:agentic-api \
  -n agentic-app
```

---

# 24. GitOps manifests needed

Add or update:

```text
k8s/apps/agentic-app/api/
├── serviceaccount.yaml
├── rbac.yaml
├── deployment.yaml
└── kustomization.yaml
```

Make sure `kustomization.yaml` includes:

```yaml
resources:
  - serviceaccount.yaml
  - rbac.yaml
  - deployment.yaml
```

If you already have these files, update them instead of creating duplicates.

---

# 25. CI/CD checks

Before merge:

```bash
cd apps/api
pytest
```

```bash
cd apps/frontend
npm run lint
npm run build
```

If using Docker:

```bash
docker build -t agentic-api:test apps/api
docker build -t agentic-frontend:test apps/frontend
```

After GitOps sync:

```bash
kubectl get pods -n agentic-app
kubectl logs deploy/agentic-api -n agentic-app --tail=100
kubectl get secrets -n agentic-app | grep agentic
```

Do not print secret values.

---

# 26. Manual test flow

## Test 1 — vCenter status before save

Open:

```text
Settings → vCenter
```

Expected:

```text
Configured: No
Password: Not saved
Last test: Never
```

API:

```bash
curl https://api.dclab.local/api/v1/connections/vcenter/status
```

Expected:

```json
{
  "configured": false
}
```

---

## Test 2 — wrong vCenter password

Enter wrong password.

Click:

```text
Test Connection
```

Expected:

```text
Connection failed
Credentials not saved
```

Check:

```bash
kubectl get secret agentic-vcenter-default -n agentic-app
```

Expected:

```text
NotFound
```

---

## Test 3 — correct vCenter credentials

Enter correct credentials.

Click:

```text
Test Connection
```

Expected:

```text
Connection successful
```

Click:

```text
Save Credentials
```

Expected:

```text
Credentials saved securely
```

Check secret exists:

```bash
kubectl get secret agentic-vcenter-default -n agentic-app
```

Expected:

```text
agentic-vcenter-default   Opaque
```

---

## Test 4 — reload settings page

Refresh browser.

Expected:

```text
Configured: Yes
URL visible
Username hint visible
Password field empty
Password status: Saved
```

Password value should not appear.

---

## Test 5 — delete credentials

Click:

```text
Delete Credentials
```

Confirm.

Expected:

```text
Credentials deleted
Configured: No
```

Kubernetes:

```bash
kubectl get secret agentic-vcenter-default -n agentic-app
```

Expected:

```text
NotFound
```

---

## Test 6 — LLM provider

Enter:

```text
Provider: OpenRouter
Base URL: https://openrouter.ai/api/v1
Model: your selected model
API Key: your key
```

Click:

```text
Test LLM
```

Expected:

```text
LLM connection successful
```

Click:

```text
Save Credentials
```

Expected:

```text
LLM credentials saved securely
```

Check:

```bash
kubectl get secret agentic-llm-provider-default -n agentic-app
```

---

# 27. Backend unit tests

Add tests for:

```text
schemas validation
safe username masking
secret create/update
secret status response excludes password
vCenter test success mocked
vCenter test auth failure mocked
LLM test success mocked
LLM test failure mocked
delete secret
```

Important test:

```text
Assert password not in response JSON.
Assert api_key not in response JSON.
```

---

# 28. Frontend tests or checks

At minimum:

```text
Settings page renders
vCenter form validates required fields
Test Connection button calls correct endpoint
Save button calls correct endpoint
Status card does not display secret values
Delete button shows confirmation
```

If no frontend test framework yet, manual testing is okay for this phase.

---

# 29. Recommended implementation order

Do not build everything randomly. Use this order.

## Step 1 — Backend schemas

```text
Create Pydantic request and response models.
```

Done when:

```text
FastAPI can import schemas with no error.
```

---

## Step 2 — Kubernetes Secret service

```text
Create k8s_secret_store.py.
```

Done when:

```text
Can create/update/get/delete a test secret from FastAPI environment.
```

---

## Step 3 — RBAC manifests

```text
Create ServiceAccount, Role, RoleBinding.
Update FastAPI deployment serviceAccountName.
```

Done when:

```text
kubectl auth can-i checks pass.
```

---

## Step 4 — vCenter test service

```text
Create vcenter_connection_service.py using pyVmomi.
```

Done when:

```text
POST /vcenter/test succeeds with real credentials.
```

---

## Step 5 — vCenter router

```text
Add test, save, status, delete endpoints.
```

Done when:

```text
Dashboard or curl can test/save/status/delete vCenter credentials.
```

---

## Step 6 — LLM test service

```text
Create llm_connection_service.py.
```

Done when:

```text
POST /llm/test succeeds with valid API key.
```

---

## Step 7 — LLM router

```text
Add test, save, status, delete endpoints.
```

Done when:

```text
Can save/status/delete LLM provider secret.
```

---

## Step 8 — Frontend API client

```text
Update apps/frontend/lib/api.ts.
```

Done when:

```text
All connection functions exist and are typed.
```

---

## Step 9 — Frontend Settings page wiring

```text
Wire forms to real endpoints.
```

Done when:

```text
Settings page can test/save/delete credentials.
```

---

## Step 10 — Final security review

```text
Check browser devtools response.
Check FastAPI logs.
Check Kubernetes secrets.
```

Done when:

```text
No secret value appears in frontend, logs, or response body.
```

---

# 30. Phase 1.2 acceptance checklist

Use this as the final checklist:

```text
[ ] /api/v1/connections/vcenter/test works
[ ] /api/v1/connections/vcenter saves only after successful test
[ ] /api/v1/connections/vcenter/status returns safe metadata only
[ ] /api/v1/connections/vcenter delete works
[ ] /api/v1/connections/llm/test works
[ ] /api/v1/connections/llm saves only after successful test
[ ] /api/v1/connections/llm/status returns safe metadata only
[ ] /api/v1/connections/llm delete works
[ ] Kubernetes Secrets are created in correct namespace
[ ] FastAPI service account has correct RBAC
[ ] Frontend Settings page uses real endpoints
[ ] Password field is never prefilled
[ ] API key field is never prefilled
[ ] Secret values never appear in API responses
[ ] Secret values never appear in logs
[ ] Wrong credentials fail safely
[ ] Correct credentials save successfully
[ ] Delete requires confirmation
[ ] CI/CD builds frontend and backend
[ ] Argo CD sync deploys successfully
```

---

# 31. Best Codex / Cursor prompt for Phase 1.2

Use this prompt directly:

```text
You are working inside my existing vCenter Agentic Ops Platform project.

Current state:
- RKE2 Kubernetes cluster is working.
- CI/CD and Argo CD GitOps are working.
- Frontend app path is apps/frontend.
- Frontend hostname is infra-agent-console.dclab.local.
- FastAPI API hostname is https://api.dclab.local.
- Ingress uses nginx, not Traefik.
- Phase 1.1 dashboard shell is complete.
- Do not rename apps/frontend.
- Do not change the main architecture.
- Do not replace FastAPI, Next.js, LangGraph, Redis, Postgres, or Kubernetes.

Implement Phase 1.2: Settings & Credentials Backend Wiring.

Goal:
Allow credentials to be entered from the dashboard, tested by FastAPI, saved securely as Kubernetes Secrets, checked by safe status endpoints, and deleted from the dashboard.

Backend requirements:
1. Add FastAPI router: /api/v1/connections.
2. Add vCenter endpoints:
   - POST /api/v1/connections/vcenter/test
   - POST /api/v1/connections/vcenter
   - GET /api/v1/connections/vcenter/status
   - DELETE /api/v1/connections/vcenter
3. Add LLM endpoints:
   - POST /api/v1/connections/llm/test
   - POST /api/v1/connections/llm
   - GET /api/v1/connections/llm/status
   - DELETE /api/v1/connections/llm
4. Create Pydantic schemas for all request and response models.
5. Create Kubernetes Secret storage service.
6. Store vCenter credentials in secret:
   - agentic-vcenter-default
   - keys: VCENTER_NAME, VCENTER_URL, VCENTER_USERNAME, VCENTER_PASSWORD, VCENTER_VERIFY_SSL, VCENTER_CREATED_AT, VCENTER_UPDATED_AT, VCENTER_LAST_TEST_STATUS, VCENTER_LAST_TESTED_AT
7. Store LLM credentials in secret:
   - agentic-llm-provider-default
   - keys: LLM_PROVIDER, LLM_BASE_URL, LLM_MODEL, LLM_API_KEY, LLM_CREATED_AT, LLM_UPDATED_AT, LLM_LAST_TEST_STATUS, LLM_LAST_TESTED_AT
8. Use pyVmomi to test vCenter connectivity.
9. Support verify_ssl=false for lab/self-signed vCenter.
10. Test credentials before saving. If test fails, do not save.
11. Never return password or API key in any API response.
12. Never log password or API key.
13. Return only safe status metadata.
14. Add friendly error codes:
   - VCENTER_AUTH_FAILED
   - VCENTER_DNS_FAILED
   - VCENTER_UNREACHABLE
   - VCENTER_SSL_ERROR
   - VCENTER_UNKNOWN_ERROR
   - LLM_AUTH_FAILED
   - LLM_UNREACHABLE
   - LLM_MODEL_NOT_FOUND
   - LLM_UNKNOWN_ERROR
15. Add Kubernetes manifests:
   - serviceaccount.yaml
   - rbac.yaml
   - update deployment.yaml with serviceAccountName
16. Limit RBAC to the app namespace and secret management only.

Frontend requirements:
1. Update apps/frontend/lib/api.ts with typed functions:
   - testVCenterConnection
   - saveVCenterConnection
   - getVCenterConnectionStatus
   - deleteVCenterConnection
   - testLLMConnection
   - saveLLMConnection
   - getLLMConnectionStatus
   - deleteLLMConnection
2. Update Settings page to call the real /api/v1/connections endpoints.
3. Password and API key fields must never be prefilled.
4. After successful save, clear the password/API key field.
5. Show safe status:
   - configured true/false
   - URL
   - username_hint
   - provider
   - model
   - password_set/api_key_set
   - last_test_status
   - last_tested_at
6. Add loading states, success toasts, error cards, and delete confirmation dialog.
7. Do not store credentials in localStorage, sessionStorage, cookies, or frontend env variables.

Validation:
1. Run backend tests if available.
2. Run frontend lint/build.
3. Make sure no response contains password or API key.
4. Make sure Kubernetes Secret is created after save.
5. Make sure deleting from dashboard removes the Kubernetes Secret.

Expected result:
A secure Settings & Credentials workflow where users can enter, test, save, view safe status, and delete vCenter/LLM credentials through the dashboard.
```

---

# 32. Best final direction

For your project, Phase 1.2 should not be rushed. This is the security foundation for the whole platform.

Build in this order:

```text
1. vCenter test endpoint
2. Kubernetes Secret save/status/delete
3. Frontend vCenter Settings wiring
4. LLM test endpoint
5. LLM Secret save/status/delete
6. Frontend LLM Settings wiring
7. Final security review
```

After this is done, your next phase becomes very clear:

```text
Phase 1.3:
Use saved vCenter credentials to show real VM, host, datastore, and network inventory.
```
