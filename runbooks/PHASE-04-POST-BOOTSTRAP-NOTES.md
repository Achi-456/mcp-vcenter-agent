# Phase 04 - Cluster Foundation

Run after Phase 3 passes and all five nodes are `Ready`.

This phase installs foundation components directly with Helm:

```text
Longhorn       namespace: longhorn-system   storage path: /data/longhorn on agentic-db-01
cert-manager   namespace: cert-manager      node placement: role=utility
ClusterIssuer  name: dclab-local-selfsigned
```

Use the Windows kubeconfig copied in Phase 2:

```powershell
$env:KUBECONFIG="$env:USERPROFILE\.kube\agentic-config"
kubectl get nodes -o wide
```

## 1. Install Helm On Workstation

Skip this if `helm version` already works.

```powershell
helm version
```

If Helm is missing, install it with WinGet:

```powershell
winget install Helm.Helm
```

Close and reopen PowerShell, then verify:

```powershell
helm version
```

## 2. Add Helm Repositories

```powershell
$env:KUBECONFIG="$env:USERPROFILE\.kube\agentic-config"

helm repo add longhorn https://charts.longhorn.io
helm repo add jetstack https://charts.jetstack.io
helm repo update
```

## 3. Install Longhorn Prerequisites On All Nodes

Longhorn requires iSCSI support on Kubernetes nodes. Install NFS tools now so RWX volume support is ready later. Install `cryptsetup` as well; it was required by the successful reference deployment.

```powershell
$KEY="$env:USERPROFILE\.ssh\hybrid-cloud-idp"
$NODES="172.25.188.85","172.25.188.86","172.25.188.87","172.25.188.88","172.25.188.89"

foreach ($IP in $NODES) {
  Write-Host "`n=== $IP ==="
ssh -i $KEY root@$IP @'
set -e
dnf install -y iscsi-initiator-utils nfs-utils cryptsetup
systemctl enable --now iscsid
systemctl is-active iscsid
'@
}
```

## 4. Apply Longhorn/RKE2 Firewall And CNI Recovery Rules

These rules are required on this RHEL/firewalld lab. Without them, Longhorn managers and UI can fail DNS/service lookups such as `longhorn-backend` or `10.43.0.10`, and CSI pods can stay unstable.

```powershell
$KEY="$env:USERPROFILE\.ssh\hybrid-cloud-idp"
$NODES="172.25.188.85","172.25.188.86","172.25.188.87","172.25.188.88","172.25.188.89"

foreach ($IP in $NODES) {
  Write-Host "`n=== $IP ==="
  ssh -i $KEY root@$IP @'
set -e
mkdir -p /etc/NetworkManager/conf.d
cat > /etc/NetworkManager/conf.d/rke2-cni.conf <<'EOF'
[keyfile]
unmanaged-devices=interface-name:cali*;interface-name:flannel*;interface-name:vxlan.calico
EOF
systemctl reload NetworkManager || true

firewall-cmd --permanent --zone=trusted --add-source=10.42.0.0/16
firewall-cmd --permanent --zone=trusted --add-source=10.43.0.0/16
firewall-cmd --permanent --zone=trusted --add-interface=flannel.1 || true
firewall-cmd --permanent --add-port=9500-9503/tcp
firewall-cmd --reload
'@
}
```

## 5. Prepare Longhorn Data Path On DB Node

```powershell
$KEY="$env:USERPROFILE\.ssh\hybrid-cloud-idp"

ssh -i $KEY root@172.25.188.88 @'
set -e
findmnt /data
mkdir -p /data/longhorn
chmod 700 /data/longhorn
df -h /data
'@
```

## 6. Label DB Node For Longhorn Default Disk

```powershell
$env:KUBECONFIG="$env:USERPROFILE\.kube\agentic-config"

kubectl label node agentic-db-01.dclab.local node.longhorn.io/create-default-disk=true --overwrite
kubectl get node agentic-db-01.dclab.local --show-labels
```

## 7. Install Longhorn

This keeps Longhorn control components schedulable across the cluster while creating default storage only on the labeled DB node.

```powershell
$env:KUBECONFIG="$env:USERPROFILE\.kube\agentic-config"

kubectl create namespace longhorn-system --dry-run=client -o yaml | kubectl apply -f -
kubectl label namespace longhorn-system `
  pod-security.kubernetes.io/enforce=privileged `
  pod-security.kubernetes.io/audit=privileged `
  pod-security.kubernetes.io/warn=privileged `
  --overwrite

helm upgrade --install longhorn longhorn/longhorn `
  --namespace longhorn-system `
  --set defaultSettings.createDefaultDiskLabeledNodes=true `
  --set defaultSettings.defaultDataPath=/data/longhorn `
  --set defaultSettings.defaultReplicaCount=1 `
  --set persistence.defaultClassReplicaCount=1
```

Watch rollout:

```powershell
$env:KUBECONFIG="$env:USERPROFILE\.kube\agentic-config"
kubectl get pods -n longhorn-system -o wide --watch
```

Press `Ctrl+C` when all Longhorn pods are running.

If Longhorn pods initially show image pull errors or CSI sidecars report missing `/csi/csi.sock`, wait several minutes after image pulls complete. If pods stay unhealthy after the firewall/CNI rules above, recycle only unhealthy Longhorn pods:

```powershell
kubectl -n longhorn-system delete pod <pod-name>
```

## 8. Validate Longhorn

```powershell
$env:KUBECONFIG="$env:USERPROFILE\.kube\agentic-config"

kubectl get pods -n longhorn-system -o wide
kubectl get sc
kubectl -n longhorn-system get settings.longhorn.io default-data-path default-replica-count create-default-disk-labeled-nodes
```

Expected:

```text
Longhorn pods Running
longhorn StorageClass exists
default-data-path is /data/longhorn
default-replica-count is 1
create-default-disk-labeled-nodes is true
```

## 9. Longhorn PVC Smoke Test

```powershell
$env:KUBECONFIG="$env:USERPROFILE\.kube\agentic-config"

kubectl create namespace longhorn-smoke --dry-run=client -o yaml | kubectl apply -f -
@'
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: longhorn-smoke-pvc
  namespace: longhorn-smoke
spec:
  accessModes:
    - ReadWriteOnce
  storageClassName: longhorn
  resources:
    requests:
      storage: 1Gi
'@ | kubectl apply -f -

@'
apiVersion: v1
kind: Pod
metadata:
  name: longhorn-smoke-pod
  namespace: longhorn-smoke
spec:
  restartPolicy: Never
  containers:
    - name: writer
      image: docker.io/library/busybox:1.36.1
      command: ["sh", "-c", "echo longhorn-ok > /data/test.txt && cat /data/test.txt && sleep 20"]
      volumeMounts:
        - name: data
          mountPath: /data
  volumes:
    - name: data
      persistentVolumeClaim:
        claimName: longhorn-smoke-pvc
'@ | kubectl apply -f -

kubectl get pvc,pod -n longhorn-smoke -o wide
kubectl logs -n longhorn-smoke longhorn-smoke-pod
```

Expected:

```text
longhorn-smoke-pvc Bound
longhorn-smoke-pod Running or Completed
longhorn-ok
```

Cleanup:

```powershell
$env:KUBECONFIG="$env:USERPROFILE\.kube\agentic-config"
kubectl delete namespace longhorn-smoke
```

## 10. Install Cert-Manager On Utility Node

```powershell
$env:KUBECONFIG="$env:USERPROFILE\.kube\agentic-config"

helm upgrade --install cert-manager jetstack/cert-manager `
  --namespace cert-manager `
  --create-namespace `
  --set crds.enabled=true `
  --set nodeSelector.role=utility `
  --set nodeSelector."kubernetes\.io/os"=linux `
  --set webhook.nodeSelector.role=utility `
  --set webhook.nodeSelector."kubernetes\.io/os"=linux `
  --set cainjector.nodeSelector.role=utility `
  --set cainjector.nodeSelector."kubernetes\.io/os"=linux `
  --set startupapicheck.nodeSelector.role=utility `
  --set startupapicheck.nodeSelector."kubernetes\.io/os"=linux
```

Watch rollout:

```powershell
$env:KUBECONFIG="$env:USERPROFILE\.kube\agentic-config"
kubectl get pods -n cert-manager -o wide --watch
```

Press `Ctrl+C` when cert-manager pods are running.

## 11. Create Self-Signed ClusterIssuer

```powershell
$env:KUBECONFIG="$env:USERPROFILE\.kube\agentic-config"

@'
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: dclab-local-selfsigned
spec:
  selfSigned: {}
'@ | kubectl apply -f -

kubectl get clusterissuer dclab-local-selfsigned
```

Expected:

```text
dclab-local-selfsigned Ready=True
```

## 12. Cert-Manager Smoke Test

```powershell
$env:KUBECONFIG="$env:USERPROFILE\.kube\agentic-config"

kubectl create namespace cert-smoke --dry-run=client -o yaml | kubectl apply -f -
@'
apiVersion: cert-manager.io/v1
kind: Certificate
metadata:
  name: dclab-smoke-cert
  namespace: cert-smoke
spec:
  secretName: dclab-smoke-tls
  dnsNames:
    - smoke.dclab.local
  issuerRef:
    name: dclab-local-selfsigned
    kind: ClusterIssuer
'@ | kubectl apply -f -

kubectl get certificate -n cert-smoke
kubectl get secret dclab-smoke-tls -n cert-smoke
```

Expected:

```text
dclab-smoke-cert Ready=True
dclab-smoke-tls exists
```

Cleanup:

```powershell
$env:KUBECONFIG="$env:USERPROFILE\.kube\agentic-config"
kubectl delete namespace cert-smoke
```

## 13. Foundation Acceptance Check

```powershell
$env:KUBECONFIG="$env:USERPROFILE\.kube\agentic-config"

kubectl get nodes -o wide
kubectl get pods -n kube-system -o wide
kubectl get pods -n longhorn-system -o wide
kubectl get pods -n cert-manager -o wide
kubectl get sc
kubectl get clusterissuer dclab-local-selfsigned
helm ls -n longhorn-system
helm ls -n cert-manager
```

Expected:

```text
all 5 nodes Ready
kube-system healthy
Longhorn pods Running
cert-manager pods Running on agentic-utility-01
longhorn StorageClass exists
dclab-local-selfsigned Ready=True
Helm releases show deployed
```

## 14. Ten Minute Stability Check

```powershell
$env:KUBECONFIG="$env:USERPROFILE\.kube\agentic-config"

for ($i = 1; $i -le 10; $i++) {
  Write-Host "=== check $i/10 ==="
  kubectl get nodes --no-headers
  kubectl get pods -A --no-headers | Select-String "Pending|CrashLoopBackOff|ImagePullBackOff|Error"
  Start-Sleep -Seconds 60
}
```

Expected:

```text
all nodes stay Ready
no foundation pod remains Pending, CrashLoopBackOff, ImagePullBackOff, or Error
```
