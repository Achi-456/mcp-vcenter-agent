# Phase 08 - Code Scaffold, CI, And First Real Images

Scaffold the first real app containers, build and push them to GHCR, then use those images to unblock Phase 07.

This phase has three gates:

```text
Gate A - Repo scaffold and local container tests
Gate B - GitHub Actions builds and pushes GHCR images
Gate C - Execute Phase 07 with real image references
```

Do not start Gate B until Gate A passes locally. Do not start Gate C until all three GHCR images exist.

## Targets

```text
Branch:          main-rke2-mcp
Registry:        ghcr.io/achi-456
Image tag:       0.7.0
FastAPI image:   ghcr.io/achi-456/agentic-fastapi:0.7.0
Next.js image:   ghcr.io/achi-456/agentic-nextjs:0.7.0
MCP image:       ghcr.io/achi-456/agentic-mcp:0.7.0
Namespace:       agentic-app
App node:        agentic-worker-01.dclab.local
```

## Gate A - Local Scaffold Validation

The repo contains:

```text
apps/backend    FastAPI app with /health, /ready, /api/v1/chat/stream-test, /ws
apps/frontend   Next.js standalone app with /api/health and placeholder page
apps/mcp        internal MCP placeholder server with /health
```

Validate frontend dependencies:

```powershell
cd apps/frontend
npm install --package-lock-only --ignore-scripts
npm audit --audit-level=moderate
cd ..\..
```

Expected:

```text
found 0 vulnerabilities
```

Build and test backend:

```powershell
docker build -t agentic-fastapi:local .\apps\backend
docker run --rm -d -p 8000:8000 --name fa `
  -e DB_URL="postgresql://invalid" `
  -e REDIS_URL="redis://invalid" `
  agentic-fastapi:local
Start-Sleep -Seconds 3
curl.exe -s http://localhost:8000/health
docker stop fa
```

Expected:

```json
{"status":"ok"}
```

Build and test frontend:

```powershell
docker build `
  --build-arg NEXT_PUBLIC_API_URL=https://api.dclab.local `
  --build-arg NEXT_PUBLIC_WS_URL=wss://api.dclab.local/ws `
  --build-arg "NEXT_PUBLIC_APP_NAME=vCenter Agentic Ops" `
  -t agentic-nextjs:local .\apps\frontend
docker run --rm -d -p 3000:3000 --name nj agentic-nextjs:local
Start-Sleep -Seconds 5
curl.exe -s http://localhost:3000/api/health
docker stop nj
```

Expected:

```json
{"status":"ok"}
```

Build and test MCP:

```powershell
docker build -t agentic-mcp:local .\apps\mcp
docker run --rm -d -p 8001:8001 --name mcp agentic-mcp:local
Start-Sleep -Seconds 3
curl.exe -s http://localhost:8001/health
docker stop mcp
```

Expected:

```json
{"status":"ok","tools":[],"resources":[],"prompts":[]}
```

## Gate B - GitHub Actions And GHCR

The workflows build on pushes to `main-rke2-mcp` and can also be run manually:

```text
.github/workflows/build-backend.yml
.github/workflows/build-frontend.yml
.github/workflows/build-mcp.yml
```

They use the built-in `GITHUB_TOKEN` with:

```yaml
permissions:
  contents: read
  packages: write
```

After pushing Phase 08, check GitHub Actions:

```text
https://github.com/Achi-456/mcp-vcenter-agent/actions
```

Expected packages:

```text
ghcr.io/achi-456/agentic-fastapi:0.7.0
ghcr.io/achi-456/agentic-nextjs:0.7.0
ghcr.io/achi-456/agentic-mcp:0.7.0
```

## Required User Action - GHCR Visibility

After the first successful workflow push, choose one access model before Phase 07 deploy:

```text
Option A - Make all three GHCR packages public.
Option B - Keep packages private and create an imagePullSecret in agentic-app.
```

Recommended for this lab: make the packages public to avoid image pull secret churn.

If keeping packages private, create a token with package read permission and run:

```powershell
kubectl create secret docker-registry ghcr-pull-secret `
  --namespace agentic-app `
  --docker-server=ghcr.io `
  --docker-username=<your-github-username> `
  --docker-password=<GHCR_TOKEN> `
  --dry-run=client -o yaml | kubectl apply -f -
```

Then add this to every Phase 07 Deployment spec:

```yaml
imagePullSecrets:
  - name: ghcr-pull-secret
```

## Gate C - Execute Phase 07

Once Gate B is green and GHCR visibility is handled, use these image values in Phase 07:

```powershell
$FASTAPI_IMAGE="ghcr.io/achi-456/agentic-fastapi:0.7.0"
$NEXTJS_IMAGE="ghcr.io/achi-456/agentic-nextjs:0.7.0"
$MCP_IMAGE="ghcr.io/achi-456/agentic-mcp:0.7.0"
```

Then execute `PHASE-07-APP-LAYER.md` from section 1 onward.

If direct Kubernetes API access still hangs, use the SSH tunnel fallback from Phase 07.

## Gate C Test Plan

Image pull:

```powershell
kubectl -n agentic-app get pods -o wide
```

Expected:

```text
fastapi, nextjs, and mcp-server Running on agentic-worker-01.dclab.local
No ErrImagePull or ImagePullBackOff
```

FastAPI:

```powershell
curl.exe -k --resolve "api.dclab.local:443:172.25.188.89" https://api.dclab.local/health
curl.exe -k --resolve "api.dclab.local:443:172.25.188.89" https://api.dclab.local/ready
```

Expected:

```json
{"status":"ok"}
{"status":"ready","db":"ok","redis":"ok"}
```

Next.js:

```powershell
curl.exe -k --resolve "app.dclab.local:443:172.25.188.89" https://app.dclab.local/api/health
```

Expected:

```json
{"status":"ok"}
```

MCP:

```powershell
kubectl run mcp-check --namespace agentic-app --image=curlimages/curl --rm -it --restart=Never -- `
  curl -s http://mcp-server.agentic-app.svc.cluster.local:8001/health
```

Expected:

```json
{"status":"ok","tools":[],"resources":[],"prompts":[]}
```

Stability:

```powershell
kubectl get nodes
kubectl get pods -A --field-selector=status.phase!=Succeeded --no-headers | Select-String -Pattern 'Pending|CrashLoopBackOff|Error|ImagePullBackOff|ErrImagePull|0/'
```

Expected:

```text
all nodes Ready
unhealthy pod scan has no output
```

## Troubleshooting

```text
GitHub Actions cannot push package:
  Confirm workflow permissions include packages: write.
  Confirm repository Actions settings allow GitHub Actions to create packages.

ImagePullBackOff:
  Make GHCR package public or create ghcr-pull-secret and add imagePullSecrets.

Frontend points to wrong API URL:
  Rebuild image. NEXT_PUBLIC_* values are baked at build time.

FastAPI /ready returns degraded:
  Confirm Phase 06 postgres and redis pods are Running.
  Confirm agentic-app-secrets DB_URL and REDIS_URL are correct.

Local Docker build fails:
  Fix locally first. Do not debug CI before Gate A passes.
```

## Commands Used In This Lab

Frontend dependency audit was fixed by pinning:

```text
next 15.5.16
postcss 8.5.10
npm overrides.postcss 8.5.10
```

This clears current `npm audit --audit-level=moderate` for the frontend scaffold.

MCP dependency resolution required a newer FastAPI pin than the backend because:

```text
mcp 1.0.0 requires starlette >=0.39
fastapi 0.115.0 requires starlette <0.39
```

The MCP scaffold therefore uses:

```text
fastapi 0.136.1
```
