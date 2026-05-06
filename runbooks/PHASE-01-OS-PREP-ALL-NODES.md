# Phase 01 - OS Prep On All Nodes

Run this after all five nodes answer SSH on their intended IPs.

## 1. Set Hostnames

Run each command from Windows PowerShell.

```powershell
$KEY="$env:USERPROFILE\.ssh\hybrid-cloud-idp"

ssh -i $KEY root@172.25.188.85 "hostnamectl set-hostname agentic-cp-01.dclab.local"
ssh -i $KEY root@172.25.188.86 "hostnamectl set-hostname agentic-worker-01.dclab.local"
ssh -i $KEY root@172.25.188.87 "hostnamectl set-hostname agentic-worker-02.dclab.local"
ssh -i $KEY root@172.25.188.88 "hostnamectl set-hostname agentic-db-01.dclab.local"
ssh -i $KEY root@172.25.188.89 "hostnamectl set-hostname agentic-utility-01.dclab.local"
```

## 2. Mount RHEL ISO Repo On Every Node

Use this if `dnf repolist` has no working repositories. It assumes the RHEL ISO is attached as `/dev/sr0`.

```powershell
$KEY="$env:USERPROFILE\.ssh\hybrid-cloud-idp"
$NODES="172.25.188.85","172.25.188.86","172.25.188.87","172.25.188.88","172.25.188.89"

foreach ($IP in $NODES) {
  Write-Host "`n=== $IP ==="
  ssh -i $KEY root@$IP @'
mkdir -p /mnt/rhel-iso
mountpoint -q /mnt/rhel-iso || mount /dev/sr0 /mnt/rhel-iso
grep -q '/mnt/rhel-iso' /etc/fstab || echo '/dev/sr0 /mnt/rhel-iso iso9660 ro,defaults,nofail 0 0' >> /etc/fstab
cat > /etc/yum.repos.d/rhel8-iso.repo <<'EOF'
[rhel8-baseos]
name=RHEL 8 BaseOS ISO
baseurl=file:///mnt/rhel-iso/BaseOS
enabled=1
gpgcheck=0

[rhel8-appstream]
name=RHEL 8 AppStream ISO
baseurl=file:///mnt/rhel-iso/AppStream
enabled=1
gpgcheck=0
EOF
dnf clean all
dnf makecache
'@
}
```

## 3. Apply Common OS Prep

```powershell
$KEY="$env:USERPROFILE\.ssh\hybrid-cloud-idp"
$NODES="172.25.188.85","172.25.188.86","172.25.188.87","172.25.188.88","172.25.188.89"

foreach ($IP in $NODES) {
  Write-Host "`n=== $IP ==="
  ssh -i $KEY root@$IP @'
set -e

dnf install -y chrony firewalld
systemctl enable --now chronyd firewalld
timedatectl set-ntp true

swapoff -a || true
sed -i.bak '/[[:space:]]swap[[:space:]]/d' /etc/fstab

cat > /etc/modules-load.d/rke2.conf <<'EOF'
overlay
br_netfilter
EOF
modprobe overlay
modprobe br_netfilter

cat > /etc/sysctl.d/99-rke2.conf <<'EOF'
net.bridge.bridge-nf-call-iptables = 1
net.bridge.bridge-nf-call-ip6tables = 1
net.ipv4.ip_forward = 1
EOF
sysctl --system

cat > /etc/hosts <<'EOF'
127.0.0.1 localhost localhost.localdomain
::1 localhost localhost.localdomain
172.25.188.85 agentic-cp-01.dclab.local agentic-cp-01
172.25.188.86 agentic-worker-01.dclab.local agentic-worker-01
172.25.188.87 agentic-worker-02.dclab.local agentic-worker-02
172.25.188.88 agentic-db-01.dclab.local agentic-db-01
172.25.188.89 agentic-utility-01.dclab.local agentic-utility-01
EOF

firewall-cmd --permanent --add-port=6443/tcp
firewall-cmd --permanent --add-port=9345/tcp
firewall-cmd --permanent --add-port=10250/tcp
firewall-cmd --permanent --add-port=8472/udp
firewall-cmd --reload
'@
}
```

## 4. Protect RKE2 CNI From NetworkManager

Run this before or after RKE2 install. It prevents NetworkManager from taking over Canal/Calico/Flannel interfaces.

```powershell
$KEY="$env:USERPROFILE\.ssh\hybrid-cloud-idp"
$NODES="172.25.188.85","172.25.188.86","172.25.188.87","172.25.188.88","172.25.188.89"

foreach ($IP in $NODES) {
  Write-Host "`n=== $IP ==="
  ssh -i $KEY root@$IP @'
mkdir -p /etc/NetworkManager/conf.d
cat > /etc/NetworkManager/conf.d/rke2-cni.conf <<'EOF'
[keyfile]
unmanaged-devices=interface-name:cali*;interface-name:flannel*;interface-name:vxlan.calico
EOF
systemctl reload NetworkManager || true
'@
}
```

## 5. Open Etcd Ports On Control Plane Only

```powershell
$KEY="$env:USERPROFILE\.ssh\hybrid-cloud-idp"
ssh -i $KEY root@172.25.188.85 "firewall-cmd --permanent --add-port=2379-2380/tcp && firewall-cmd --reload"
```

## 6. Enable Cgroup V2 On Every Node

RKE2 `v1.35.x` requires cgroup v2. Reboot is required.

```powershell
$KEY="$env:USERPROFILE\.ssh\hybrid-cloud-idp"
$NODES="172.25.188.85","172.25.188.86","172.25.188.87","172.25.188.88","172.25.188.89"

foreach ($IP in $NODES) {
  Write-Host "`n=== $IP ==="
  ssh -i $KEY root@$IP "grubby --update-kernel=ALL --args='systemd.unified_cgroup_hierarchy=1 cgroup_no_v1=all'; reboot"
}
```

Wait 2 to 5 minutes, then verify:

```powershell
$KEY="$env:USERPROFILE\.ssh\hybrid-cloud-idp"
$NODES="172.25.188.85","172.25.188.86","172.25.188.87","172.25.188.88","172.25.188.89"

foreach ($IP in $NODES) {
  Write-Host "`n=== $IP ==="
  ssh -i $KEY -o ConnectTimeout=8 root@$IP "hostname -f; stat -fc %T /sys/fs/cgroup"
}
```

Expected cgroup output:

```text
cgroup2fs
```

## 7. Prepare `/data` On DB Node Only

Stop if `/dev/sdb` is not the dedicated 300 GB data disk.

```powershell
$KEY="$env:USERPROFILE\.ssh\hybrid-cloud-idp"

ssh -i $KEY root@172.25.188.88 @'
set -e

lsblk -o NAME,SIZE,TYPE,MOUNTPOINT,FSTYPE
test -b /dev/sdb
if findmnt /dev/sdb >/dev/null 2>&1; then
  echo "STOP: /dev/sdb is already mounted"
  exit 1
fi

parted -s /dev/sdb mklabel gpt
parted -s /dev/sdb mkpart primary xfs 0% 100%
partprobe /dev/sdb
mkfs.xfs -f /dev/sdb1
mkdir -p /data
UUID=$(blkid -s UUID -o value /dev/sdb1)
grep -q "$UUID" /etc/fstab || echo "UUID=$UUID /data xfs defaults 0 0" >> /etc/fstab
mount -a
df -h /data
'@
```

## 8. Phase 1 Acceptance Check

```powershell
$KEY="$env:USERPROFILE\.ssh\hybrid-cloud-idp"
$NODES="172.25.188.85","172.25.188.86","172.25.188.87","172.25.188.88","172.25.188.89"

foreach ($IP in $NODES) {
  Write-Host "`n=== $IP ==="
  ssh -i $KEY root@$IP "hostname -f; ip route | grep default; grep -E 'nameserver|search' /etc/resolv.conf; swapon --show; lsmod | egrep 'overlay|br_netfilter'; sysctl net.ipv4.ip_forward; firewall-cmd --list-ports"
}

ssh -i $KEY root@172.25.188.88 "df -h /data; findmnt /data"
```
