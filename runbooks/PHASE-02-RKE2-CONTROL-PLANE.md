# Phase 02 - RKE2 Control Plane Bootstrap

Run only after Phase 1 passes on all five nodes.

Target:

```text
agentic-cp-01.dclab.local
172.25.188.85
```

## 1. Create RKE2 Server Config

Do not use the `CriticalAddonsOnly=true:NoExecute` taint during single-node bootstrap. It blocked RKE2 system pods in this lab. Reapply a scheduling strategy later after workers join.

```powershell
$KEY="$env:USERPROFILE\.ssh\hybrid-cloud-idp"

ssh -i $KEY root@172.25.188.85 @'
mkdir -p /etc/rancher/rke2
cat > /etc/rancher/rke2/config.yaml <<'EOF'
write-kubeconfig-mode: "0644"
tls-san:
  - "172.25.188.85"
  - "agentic-cp-01"
  - "agentic-cp-01.dclab.local"
EOF
'@
```

## 2. Install RKE2 Server

This lab used `v1.35.3+rke2r3`. Pinning avoids accidentally taking a newer broken build.

```powershell
$KEY="$env:USERPROFILE\.ssh\hybrid-cloud-idp"

ssh -i $KEY root@172.25.188.85 @'
set -e
curl -sfL https://get.rke2.io | INSTALL_RKE2_VERSION="v1.35.3+rke2r3" sh -
systemctl enable rke2-server
systemctl start rke2-server
'@
```

Watch startup:

```powershell
$KEY="$env:USERPROFILE\.ssh\hybrid-cloud-idp"
ssh -i $KEY root@172.25.188.85 "journalctl -u rke2-server -f"
```

Press `Ctrl+C` after the API is up.

## 3. Configure Kubectl On Control Plane

```powershell
$KEY="$env:USERPROFILE\.ssh\hybrid-cloud-idp"

ssh -i $KEY root@172.25.188.85 @'
set -e
mkdir -p /root/.kube
cp /etc/rancher/rke2/rke2.yaml /root/.kube/config
sed -i 's/127.0.0.1/172.25.188.85/g' /root/.kube/config
ln -sf /var/lib/rancher/rke2/bin/kubectl /usr/local/bin/kubectl
'@
```

## 4. Copy Kubeconfig To Windows

```powershell
$KEY="$env:USERPROFILE\.ssh\hybrid-cloud-idp"
mkdir -Force "$env:USERPROFILE\.kube"
scp -i $KEY root@172.25.188.85:/root/.kube/config "$env:USERPROFILE\.kube\agentic-config"
```

Test from Windows:

```powershell
$env:KUBECONFIG="$env:USERPROFILE\.kube\agentic-config"
kubectl get nodes -o wide
```

## 5. Capture Join Token For Phase 3

Do not paste the token into chat or documents. Read it from the control plane when needed.

```powershell
$KEY="$env:USERPROFILE\.ssh\hybrid-cloud-idp"
ssh -i $KEY root@172.25.188.85 "cat /var/lib/rancher/rke2/server/node-token"
```

## 6. Phase 2 Acceptance Check

```powershell
$KEY="$env:USERPROFILE\.ssh\hybrid-cloud-idp"

ssh -i $KEY root@172.25.188.85 @'
systemctl is-active rke2-server
kubectl get nodes -o wide
kubectl get pods -n kube-system -o wide
kubectl cluster-info
ss -lntp | egrep ':6443|:9345'
'@
```

Expected:

```text
rke2-server is active
agentic-cp-01.dclab.local is Ready
all kube-system pods are Running or Completed
API listens on 6443
RKE2 supervisor listens on 9345
```

