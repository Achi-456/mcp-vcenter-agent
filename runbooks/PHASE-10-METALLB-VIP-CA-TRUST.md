# Phase 10 - MetalLB VIP, Hostname Rename, And CA Trust

This phase gives the lab a stable ingress VIP and trusted local CA.

Final public hostnames:

```text
infra-agent-console.dclab.local -> 172.25.188.84
api.dclab.local                 -> 172.25.188.84
argocd-agent.dclab.local        -> 172.25.188.84
```

Retired hostnames:

```text
app.dclab.local
argocd.dclab.local
```

## Preconditions

From Windows PowerShell:

```powershell
Resolve-DnsName infra-agent-console.dclab.local
Resolve-DnsName api.dclab.local
Resolve-DnsName argocd-agent.dclab.local
```

Expected: all three resolve to `172.25.188.84`.

From `agentic-cp-01`:

```powershell
ssh -i "$env:USERPROFILE\.ssh\hybrid-cloud-idp" root@172.25.188.85
ping -c 2 -W 1 172.25.188.84 || true
ip neigh show | grep 172.25.188.84 || true
```

Expected: no ping replies and no reachable neighbor entry. Stop if another host already owns the VIP.

## Install MetalLB

Install Helm on the control plane if missing:

```bash
if ! command -v helm >/dev/null 2>&1; then
  curl -fsSL https://get.helm.sh/helm-v3.18.6-linux-amd64.tar.gz -o /tmp/helm.tar.gz
  tar -C /tmp -xzf /tmp/helm.tar.gz
  install -m 0755 /tmp/linux-amd64/helm /usr/local/bin/helm
  rm -rf /tmp/helm.tar.gz /tmp/linux-amd64
fi
helm version
```

Install MetalLB:

```bash
kubectl create namespace metallb-system --dry-run=client -o yaml | kubectl apply -f -
helm repo add metallb https://metallb.github.io/metallb
helm repo update
helm upgrade --install metallb metallb/metallb \
  --namespace metallb-system \
  --version 0.14.9 \
  --wait \
  --timeout 5m
```

Apply the pool and LoadBalancer Service:

```bash
kubectl apply -f k8s/infra/metallb/dclab-pool.yaml
kubectl apply -f k8s/infra/ingress/rke2-ingress-nginx-controller-lb.yaml
kubectl -n kube-system get svc rke2-ingress-nginx-controller-lb -w
```

Expected: `EXTERNAL-IP` becomes `172.25.188.84`.

## Create dclab CA Issuer

```bash
kubectl apply -f k8s/infra/cert-manager/dclab-local-ca.yaml
kubectl -n cert-manager wait --for=condition=Ready certificate/dclab-local-ca --timeout=180s
kubectl get clusterissuer dclab-local-ca
```

Expected: `ClusterIssuer/dclab-local-ca` is Ready.

## Rename App Host Through GitOps

Commit and push the changed app manifests:

```powershell
git add k8s/apps/agentic-app k8s/infra runbooks/PHASE-10-METALLB-VIP-CA-TRUST.md runbooks/README.md
git commit -m "Add Phase 10 MetalLB VIP and CA trust"
git push origin main-rke2-mcp
```

Refresh Argo CD:

```bash
kubectl -n argocd annotate applications.argoproj.io agentic-app \
  argocd.argoproj.io/refresh=hard --overwrite
kubectl -n argocd get applications.argoproj.io agentic-app
```

Expected: `agentic-app` returns `Synced` and `Healthy`.

## Rename Argo CD Host

Patch Argo CD direct resources:

```bash
kubectl -n argocd patch configmap argocd-cm \
  --type=merge \
  -p '{"data":{"url":"https://argocd-agent.dclab.local"}}'

kubectl -n argocd patch certificate argocd-tls \
  --type=merge \
  -p '{"spec":{"dnsNames":["argocd-agent.dclab.local"],"issuerRef":{"name":"dclab-local-ca","kind":"ClusterIssuer"}}}'

kubectl -n argocd patch ingress argocd-server \
  --type=json \
  -p='[
    {"op":"replace","path":"/spec/rules/0/host","value":"argocd-agent.dclab.local"},
    {"op":"replace","path":"/spec/tls/0/hosts/0","value":"argocd-agent.dclab.local"},
    {"op":"replace","path":"/spec/tls/1/hosts/0","value":"argocd-agent.dclab.local"},
    {"op":"replace","path":"/spec/tls/1/secretName","value":"argocd-tls"}
  ]'

kubectl -n argocd wait --for=condition=Ready certificate/argocd-tls --timeout=180s
```

## Export And Trust CA

Export from the cluster:

```powershell
kubectl -n cert-manager get secret dclab-local-ca `
  -o jsonpath="{.data['tls\.crt']}" | `
  % { [System.Convert]::FromBase64String($_) } | `
  Set-Content -Encoding Byte dclab-local-ca.crt

certutil -dump dclab-local-ca.crt
```

Install into Windows Trusted Root store from elevated PowerShell:

```powershell
Import-Certificate -FilePath dclab-local-ca.crt -CertStoreLocation Cert:\LocalMachine\Root
```

Restart browsers after installing the CA.

## Validation

MetalLB and ingress:

```powershell
kubectl -n metallb-system get pods -o wide
kubectl -n kube-system get svc rke2-ingress-nginx-controller-lb
Test-NetConnection 172.25.188.84 -Port 443
```

HTTPS with the new hostnames:

```powershell
curl.exe https://api.dclab.local/health
curl.exe https://infra-agent-console.dclab.local/api/health
curl.exe https://argocd-agent.dclab.local
```

Expected: no `-k` is needed after the CA is trusted.

Cluster stability:

```powershell
kubectl get nodes
kubectl get pods -A --field-selector=status.phase!=Succeeded
```

Expected: all nodes Ready and no `Pending`, `CrashLoopBackOff`, `ErrImagePull`, `ImagePullBackOff`, or `Error` pods.

## Rollback

If VIP routing fails, keep the existing ingress hostPort path working by removing only the LoadBalancer Service:

```bash
kubectl -n kube-system delete svc rke2-ingress-nginx-controller-lb
```

If the new CA causes certificate problems, patch certificates back to `dclab-local-selfsigned` temporarily, then investigate issuer status:

```bash
kubectl get clusterissuer
kubectl -n cert-manager describe certificate dclab-local-ca
kubectl -n agentic-app describe certificate app-tls api-tls
kubectl -n argocd describe certificate argocd-tls
```
