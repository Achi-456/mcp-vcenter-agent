# Phase 03 - Join RKE2 Agent Nodes

Run after Phase 2 is healthy. This joins all four non-control-plane nodes:

```text
agentic-worker-01.dclab.local   172.25.188.86   role=app-worker
agentic-worker-02.dclab.local   172.25.188.87   role=app-worker
agentic-db-01.dclab.local       172.25.188.88   role=data
agentic-utility-01.dclab.local  172.25.188.89   role=utility
```

RKE2 version is pinned to match the control plane:

```text
v1.35.3+rke2r3
```

## 1. Preflight From Control Plane

```powershell
$KEY="$env:USERPROFILE\.ssh\hybrid-cloud-idp"

ssh -i $KEY root@172.25.188.85 @'
systemctl is-active rke2-server
kubectl get nodes -o wide
test -s /var/lib/rancher/rke2/server/node-token && echo TOKEN_OK || echo TOKEN_MISSING
ss -lntp | egrep ':6443|:9345'
'@
```

Expected:

```text
active
agentic-cp-01.dclab.local Ready
TOKEN_OK
API listens on 6443
RKE2 supervisor listens on 9345
```

## 2. Preflight On Joining Nodes

```powershell
$KEY="$env:USERPROFILE\.ssh\hybrid-cloud-idp"
$JOIN_NODES="172.25.188.86","172.25.188.87","172.25.188.88","172.25.188.89"

foreach ($IP in $JOIN_NODES) {
  Write-Host "`n=== $IP ==="
  ssh -i $KEY -o ConnectTimeout=8 root@$IP @'
hostname -f
ip -4 addr show ens192 | grep -o "172.25.188.[0-9]*/[0-9]*" || true
stat -fc %T /sys/fs/cgroup
timeout 5 bash -lc '</dev/tcp/172.25.188.85/9345' && echo CP_9345_OK || echo CP_9345_FAIL
timeout 5 bash -lc '</dev/tcp/172.25.188.85/6443' && echo CP_6443_OK || echo CP_6443_FAIL
swapon --show
firewall-cmd --list-ports
'@
}
```

Expected for every joining node:

```text
cgroup2fs
CP_9345_OK
CP_6443_OK
no swap output
6443/tcp 9345/tcp 10250/tcp 8472/udp
```

Stop if any node cannot reach `172.25.188.85` on `9345` or `6443`.

## 3. Join Agent Nodes With Labels

This pulls the join token from the control plane without pasting it into the runbook.

```powershell
$KEY="$env:USERPROFILE\.ssh\hybrid-cloud-idp"
$TOKEN=(ssh -i $KEY root@172.25.188.85 "cat /var/lib/rancher/rke2/server/node-token").Trim()

$JOIN_TARGETS = @(
  @{ IP = "172.25.188.86"; Label = "role=app-worker" },
  @{ IP = "172.25.188.87"; Label = "role=app-worker" },
  @{ IP = "172.25.188.88"; Label = "role=data" },
  @{ IP = "172.25.188.89"; Label = "role=utility" }
)

foreach ($NODE in $JOIN_TARGETS) {
  $IP=$NODE.IP
  $LABEL=$NODE.Label
  Write-Host "`n=== Joining $IP with $LABEL ==="
  ssh -i $KEY root@$IP @"
set -e
mkdir -p /etc/rancher/rke2
cat > /etc/rancher/rke2/config.yaml <<EOF
server: https://172.25.188.85:9345
token: $TOKEN
node-label:
  - "$LABEL"
EOF
curl -sfL https://get.rke2.io | INSTALL_RKE2_TYPE="agent" INSTALL_RKE2_VERSION="v1.35.3+rke2r3" sh -
systemctl enable --now rke2-agent
"@
}
```

## 4. Watch All Nodes Join

```powershell
$KEY="$env:USERPROFILE\.ssh\hybrid-cloud-idp"
ssh -i $KEY root@172.25.188.85 "watch -n 5 kubectl get nodes -o wide"
```

Press `Ctrl+C` after all five nodes are `Ready`.

## 5. Validate Labels And System Pods

```powershell
$KEY="$env:USERPROFILE\.ssh\hybrid-cloud-idp"

ssh -i $KEY root@172.25.188.85 @'
kubectl get nodes -o wide
kubectl get nodes -l role=app-worker -o name
kubectl get nodes -l role=data -o name
kubectl get nodes -l role=utility -o name
kubectl get pods -n kube-system -o wide
'@
```

Expected:

```text
5 nodes Ready
agentic-worker-01 and agentic-worker-02 selected by role=app-worker
agentic-db-01 selected by role=data
agentic-utility-01 selected by role=utility
no kube-system pod in Pending or CrashLoopBackOff
```

## 6. Reapply Control Plane Taint

Apply this only after all five nodes are `Ready` and `kube-system` is healthy.

```powershell
$KEY="$env:USERPROFILE\.ssh\hybrid-cloud-idp"

ssh -i $KEY root@172.25.188.85 @'
kubectl taint node agentic-cp-01.dclab.local CriticalAddonsOnly=true:NoExecute --overwrite
kubectl describe node agentic-cp-01.dclab.local | grep -i taints
'@
```

Rollback command if any system pod becomes stuck:

```powershell
$KEY="$env:USERPROFILE\.ssh\hybrid-cloud-idp"
ssh -i $KEY root@172.25.188.85 "kubectl taint node agentic-cp-01.dclab.local CriticalAddonsOnly=true:NoExecute-"
```

## 7. Ten Minute Stability Check

```powershell
$KEY="$env:USERPROFILE\.ssh\hybrid-cloud-idp"

ssh -i $KEY root@172.25.188.85 @'
for i in {1..10}; do
  echo "=== check $i/10 ==="
  kubectl get nodes --no-headers
  kubectl get pods -n kube-system --no-headers | egrep 'Pending|CrashLoopBackOff|ImagePullBackOff|Error' || true
  sleep 60
done
'@
```

Expected:

```text
all five nodes stay Ready
no kube-system pod remains Pending, CrashLoopBackOff, ImagePullBackOff, or Error
```

## 8. Agent Service Check

```powershell
$KEY="$env:USERPROFILE\.ssh\hybrid-cloud-idp"
$JOIN_NODES="172.25.188.86","172.25.188.87","172.25.188.88","172.25.188.89"

foreach ($IP in $JOIN_NODES) {
  Write-Host "`n=== $IP ==="
  ssh -i $KEY root@$IP "systemctl is-active rke2-agent; journalctl -u rke2-agent -n 30 --no-pager"
}
```
