# Phase 00 - Inventory And Access

Use this before any RKE2 work. Commands are written for Windows PowerShell.

## Local SSH Key

```powershell
$KEY="$env:USERPROFILE\.ssh\hybrid-cloud-idp"
Test-Path $KEY
```

## Node Inventory

| Role | Hostname | FQDN | IP |
| --- | --- | --- | --- |
| Control plane | agentic-cp-01 | agentic-cp-01.dclab.local | 172.25.188.85 |
| Worker | agentic-worker-01 | agentic-worker-01.dclab.local | 172.25.188.86 |
| Worker | agentic-worker-02 | agentic-worker-02.dclab.local | 172.25.188.87 |
| Database | agentic-db-01 | agentic-db-01.dclab.local | 172.25.188.88 |
| Utility | agentic-utility-01 | agentic-utility-01.dclab.local | 172.25.188.89 |

Network defaults:

```text
Gateway: 172.25.188.1
DNS:     172.25.188.20
Domain:  dclab.local
NIC:     ens192
```

## SSH Check

```powershell
$KEY="$env:USERPROFILE\.ssh\hybrid-cloud-idp"
$NODES="172.25.188.85","172.25.188.86","172.25.188.87","172.25.188.88","172.25.188.89"

foreach ($IP in $NODES) {
  Write-Host "`n=== $IP ==="
  ssh -i $KEY -o StrictHostKeyChecking=no -o ConnectTimeout=8 root@$IP "hostname -f; ip -4 addr show ens192 | grep -o '172.25.188.[0-9]*/[0-9]*' || true"
}
```

All five nodes should answer before Phase 1.

