# Phase 09 - GitOps Adoption For agentic-app

This phase moves `agentic-app` workloads from manual `kubectl apply` to Argo CD management.

Argo CD watches:

```text
Repo:   https://github.com/Achi-456/mcp-vcenter-agent.git
Branch: main-rke2-mcp
Path:   k8s/apps/agentic-app
```

Secrets are intentionally not stored in Git. The existing `agentic-app-secrets` Secret remains manually managed until a later Sealed Secrets or External Secrets phase.

## Preconditions

Run from Windows PowerShell:

```powershell
$env:KUBECONFIG="$env:USERPROFILE\.kube\agentic-config"
kubectl get nodes
kubectl -n agentic-app get deploy,svc,ingress,certificate,configmap
kubectl -n argocd get pods
kubectl get clusterissuer dclab-local-selfsigned
```

Expected:

```text
All five nodes Ready.
fastapi, nextjs, and mcp-server deployments are Available.
Argo CD pods are Running.
dclab-local-selfsigned exists and is Ready.
```

If workstation API access hangs, run the checks from `agentic-cp-01`:

```powershell
ssh -i "$env:USERPROFILE\.ssh\hybrid-cloud-idp" root@172.25.188.85
kubectl get nodes
```

## GitOps Resources In This Repo

The watched app path is:

```text
k8s/apps/agentic-app
```

It contains:

```text
namespace.yaml
configmap.yaml
certificates.yaml
fastapi/deployment.yaml
fastapi/service.yaml
fastapi/ingress.yaml
nextjs/deployment.yaml
nextjs/service.yaml
nextjs/ingress.yaml
mcp/deployment.yaml
mcp/service.yaml
```

The Argo CD Application is:

```text
k8s/argocd/agentic-app-application.yaml
```

It starts with:

```text
prune: false
selfHeal: true
```

`prune: false` is intentional. Do not enable pruning until Git is confirmed as the complete source of truth for every `agentic-app` resource.

## Apply Argo CD Application

Apply the Application only once:

```powershell
kubectl apply -f k8s/argocd/agentic-app-application.yaml
```

Or from the control plane:

```powershell
scp -i "$env:USERPROFILE\.ssh\hybrid-cloud-idp" k8s/argocd/agentic-app-application.yaml root@172.25.188.85:/root/agentic-app-application.yaml
ssh -i "$env:USERPROFILE\.ssh\hybrid-cloud-idp" root@172.25.188.85 "kubectl apply -f /root/agentic-app-application.yaml"
```

Validate:

```powershell
kubectl -n argocd get applications.argoproj.io agentic-app
kubectl -n argocd describe applications.argoproj.io agentic-app
```

Expected:

```text
Sync Status: Synced
Health Status: Healthy
```

If the status is `OutOfSync`, inspect the diff in the Argo CD UI before syncing. Update the repo manifests to match the live cluster unless the drift is intentional.

## CI/CD Image Update Flow

Each build workflow now:

1. Builds and pushes the `0.7.0` image tag.
2. Pushes the same image with the full commit SHA tag.
3. Updates the matching Deployment manifest to the SHA tag.
4. Commits the manifest update back to `main-rke2-mcp`.
5. Argo CD detects the Git change and syncs the app.

Workflow permissions must allow GitHub Actions to write to the branch:

```text
GitHub repo -> Settings -> Actions -> General -> Workflow permissions -> Read and write permissions
```

## Live CD Validation

Make a small visible frontend change, commit, and push:

```powershell
git add apps/frontend/app/page.tsx
git commit -m "test: phase 09 gitops validation change"
git push origin main-rke2-mcp
```

Watch:

```text
GitHub Actions -> Build Next.js
```

Then check that the workflow committed a new SHA image tag into:

```text
k8s/apps/agentic-app/nextjs/deployment.yaml
```

Argo CD should sync automatically within its polling window.

Validate app health:

```powershell
curl.exe -k https://api.dclab.local/health
curl.exe -k https://api.dclab.local/ready
curl.exe -k https://app.dclab.local/api/health
```

Validate MCP internally:

```powershell
kubectl run mcp-check --image=curlimages/curl --rm -it --restart=Never -- `
  curl -s http://mcp-server.agentic-app.svc.cluster.local:8001/health
```

Expected:

```json
{"status":"ok","tools":[],"resources":[],"prompts":[]}
```

## Stability Checks

```powershell
kubectl get nodes
kubectl -n agentic-app get pods -o wide
kubectl get pods -A --field-selector=status.phase!=Succeeded
```

Expected:

```text
All five nodes Ready.
fastapi, nextjs, and mcp-server Running on agentic-worker-01.dclab.local.
No Pending, CrashLoopBackOff, ErrImagePull, ImagePullBackOff, or Error pods.
```

## Troubleshooting

If Argo CD cannot read the repo:

```text
The repo is expected to be public. If it becomes private, add a read-only HTTPS token or SSH deploy key to Argo CD.
```

If a workflow fails to push the manifest update:

```text
Check GitHub Actions workflow permissions. It must be Read and write permissions.
```

If an app pod hits `ImagePullBackOff`:

```text
Confirm the SHA image tag exists in GHCR and the package is public, or add an imagePullSecret.
```

If Argo CD wants to delete resources:

```text
Stop. Confirm prune is still false, then add any missing live resource to Git before enabling prune in a later phase.
```
