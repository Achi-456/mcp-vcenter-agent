# Phase 05 - Argo CD GitOps Nerve Centre

Install Argo CD on the utility node and expose it through the existing RKE2 NGINX ingress path at `https://argocd.dclab.local`.

This phase does not add MetalLB. For now, `argocd.dclab.local` should resolve to `172.25.188.89`.

## Targets

```text
Argo CD namespace: argocd
Argo CD host:      argocd.dclab.local
Ingress IP:        172.25.188.89
Chart:             argo/argo-cd 9.5.12
App version:       v3.4.1
Node placement:    role=utility
TLS issuer:        dclab-local-selfsigned
TLS secret:        argocd-tls
```

## Workstation Setup

Use the normal kubeconfig first:

```powershell
$env:Path=[System.Environment]::GetEnvironmentVariable('Path','Machine')+';'+[System.Environment]::GetEnvironmentVariable('Path','User')
$env:KUBECONFIG="$env:USERPROFILE\.kube\agentic-config"
kubectl get nodes
```

If workstation access to `172.25.188.85:6443` hangs or fails, create an SSH tunnel and use a temporary kubeconfig:

```powershell
$sshKey="$env:USERPROFILE\.ssh\hybrid-cloud-idp"
$log=Join-Path $env:TEMP 'agentic-api-tunnel.log'
$args=@('-o','ExitOnForwardFailure=yes','-o','ServerAliveInterval=30','-o','StrictHostKeyChecking=no','-i',$sshKey,'-N','-L','16443:127.0.0.1:6443','root@172.25.188.85')
Start-Process -FilePath 'ssh.exe' -ArgumentList $args -WindowStyle Hidden -PassThru -RedirectStandardError $log

$env:KUBECONFIG=Join-Path $env:TEMP 'agentic-config-tunnel'
(Get-Content "$env:USERPROFILE\.kube\agentic-config") -replace 'https://172\.25\.188\.85:6443','https://127.0.0.1:16443' | Set-Content -LiteralPath $env:KUBECONFIG -Encoding ascii
kubectl get nodes
```

## Preflight

```powershell
kubectl get nodes -l role=utility -o wide
kubectl get ingressclass nginx
kubectl -n kube-system get ds rke2-ingress-nginx-controller -o wide
kubectl get clusterissuer dclab-local-selfsigned

helm repo add argo https://argoproj.github.io/argo-helm
helm repo update
helm search repo argo/argo-cd --version 9.5.12
```

Expected chart:

```text
argo/argo-cd  9.5.12  v3.4.1
```

## Workstation DNS

Run PowerShell as Administrator and make sure this hosts entry exists:

```powershell
Add-Content -Path "$env:SystemRoot\System32\drivers\etc\hosts" -Value "172.25.188.89 argocd.dclab.local"
Select-String -Path "$env:SystemRoot\System32\drivers\etc\hosts" -Pattern "argocd\.dclab\.local"
```

If you cannot edit the hosts file, test with `curl --resolve` in the validation section.

## Create Namespace And TLS Certificate

```powershell
kubectl create namespace argocd --dry-run=client -o yaml | kubectl apply -f -

@'
apiVersion: cert-manager.io/v1
kind: Certificate
metadata:
  name: argocd-tls
  namespace: argocd
spec:
  secretName: argocd-tls
  dnsNames:
    - argocd.dclab.local
  issuerRef:
    name: dclab-local-selfsigned
    kind: ClusterIssuer
'@ | kubectl apply -f -
```

## Install Argo CD

```powershell
$values=Join-Path $env:TEMP 'argocd-values.yaml'

@'
global:
  domain: argocd.dclab.local
  nodeSelector:
    kubernetes.io/os: linux
    role: utility

configs:
  params:
    server.insecure: true

dex:
  enabled: false

server:
  ingress:
    enabled: true
    ingressClassName: nginx
    hostname: argocd.dclab.local
    tls: true
    annotations:
      nginx.ingress.kubernetes.io/backend-protocol: HTTP
    extraTls:
      - hosts:
          - argocd.dclab.local
        secretName: argocd-tls
'@ | Set-Content -LiteralPath $values -Encoding ascii

helm upgrade --install argocd argo/argo-cd `
  --namespace argocd `
  --version 9.5.12 `
  -f $values `
  --wait `
  --timeout 15m
```

## Admin Login

Do not store this password in Git.

```powershell
$ARGOCD_PASSWORD_B64 = kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}"
$ARGOCD_PASSWORD = [System.Text.Encoding]::UTF8.GetString([System.Convert]::FromBase64String($ARGOCD_PASSWORD_B64))
$ARGOCD_PASSWORD
```

Login:

```text
URL:      https://argocd.dclab.local
Username: admin
Password: value from argocd-initial-admin-secret
```

## Create Baseline Namespaces

```powershell
kubectl create namespace agentic-app --dry-run=client -o yaml | kubectl apply -f -
kubectl create namespace agentic-agents --dry-run=client -o yaml | kubectl apply -f -
kubectl create namespace agentic-data --dry-run=client -o yaml | kubectl apply -f -
kubectl create namespace monitoring --dry-run=client -o yaml | kubectl apply -f -
```

## Validation

```powershell
helm ls -n argocd
kubectl -n argocd get pods -o wide
kubectl -n argocd get certificate argocd-tls
kubectl -n argocd get ingress
kubectl get ns agentic-app agentic-agents agentic-data monitoring
kubectl get nodes
kubectl get pods -A --field-selector=status.phase!=Succeeded --no-headers | Select-String -Pattern 'Pending|CrashLoopBackOff|Error|ImagePullBackOff|ErrImagePull|0/'
```

If workstation DNS is configured:

```powershell
curl.exe -k https://argocd.dclab.local/ -I --max-time 20
```

If the hosts file cannot be edited:

```powershell
curl.exe -k --resolve "argocd.dclab.local:443:172.25.188.89" https://argocd.dclab.local/ -I --max-time 20
```

Expected results:

```text
argocd Helm release: deployed, chart argo-cd-9.5.12, app v3.4.1
argocd pods: all Running on agentic-utility-01.dclab.local
argocd-tls certificate: Ready=True
argocd-server ingress: host argocd.dclab.local, ports 80 and 443
curl: HTTP/1.1 200 OK
nodes: all Ready
unhealthy pod scan: no output
```

## Commands Used In This Lab

This run used an SSH API tunnel because direct workstation access to `172.25.188.85:6443` failed, while control-plane `kubectl` over SSH was healthy.

The Windows hosts file already had a stale `argocd.dclab.local` entry pointing to a different IP, but the update was blocked by local Windows permissions. Ingress validation therefore used:

```powershell
curl.exe -k --resolve "argocd.dclab.local:443:172.25.188.89" https://argocd.dclab.local/ -I --max-time 20
```
