# Phase 11 - Permanent Kubectl Access Via Auto-Starting SSH Tunnel

## Summary

Make workstation `kubectl` access permanent by running a hidden SSH tunnel at
Windows login. The tunnel forwards local API traffic from `127.0.0.1:6443` to
the RKE2 API server at `172.25.188.85:6443` through SSH to
`agentic-cp-01.dclab.local`.

No cluster-side networking changes are required.

```text
kubectl
  -> kubeconfig server https://127.0.0.1:6443
  -> local SSH tunnel
  -> root@172.25.188.85
  -> 172.25.188.85:6443 RKE2 API
```

## Current Lab Defaults

```text
Control plane:      agentic-cp-01.dclab.local
Control plane IP:   172.25.188.85
SSH alias:          agentic-cp
SSH user:           root
SSH identity:       C:\Users\achinthah\.ssh\hybrid-cloud-idp
Kubeconfig:         C:\Users\achinthah\.kube\agentic-config
Local tunnel port:  127.0.0.1:6443
```

The API server certificate includes `127.0.0.1` in its SAN list, so changing
kubeconfig to localhost does not break TLS validation.

## Preflight

Run from Windows PowerShell:

```powershell
ssh -o BatchMode=yes agentic-cp hostname
# Expected: agentic-cp-01.dclab.local

Test-NetConnection -ComputerName 127.0.0.1 -Port 6443
# Expected before install: TcpTestSucceeded: False

Get-ScheduledTask -TaskPath "\agentic\" -TaskName "agentic-kubectl-tunnel" -ErrorAction SilentlyContinue
# Expected before install: no output

Select-String -Path "$env:USERPROFILE\.kube\agentic-config" -Pattern "server:"
# Expected before install: server: https://172.25.188.85:6443
```

Stop if SSH prompts for a password or passphrase. The tunnel must be able to
start unattended at login.

## SSH Config

Keep this block in `C:\Users\achinthah\.ssh\config`:

```sshconfig
Host agentic-cp
  HostName 172.25.188.85
  User root
  IdentityFile C:/Users/achinthah/.ssh/hybrid-cloud-idp
  IdentitiesOnly yes
  ServerAliveInterval 30
  ServerAliveCountMax 3
  ExitOnForwardFailure yes
  StrictHostKeyChecking no
```

Validate:

```powershell
ssh -o BatchMode=yes agentic-cp hostname
```

## Manual Tunnel Test

Test the tunnel with a temporary kubeconfig before changing the real config:

```powershell
$testConfig = "$env:USERPROFILE\.kube\agentic-config.phase11-test"
Copy-Item "$env:USERPROFILE\.kube\agentic-config" $testConfig -Force

(Get-Content $testConfig) `
  -replace 'server: https://172\.25\.188\.85:6443', 'server: https://127.0.0.1:6443' |
  Set-Content $testConfig

$tunnel = Start-Process ssh `
  -ArgumentList @("-N", "-L", "6443:172.25.188.85:6443", "agentic-cp") `
  -WindowStyle Hidden `
  -PassThru

Start-Sleep 3
Test-NetConnection -ComputerName 127.0.0.1 -Port 6443
kubectl --kubeconfig $testConfig get nodes -o wide

Stop-Process -Id $tunnel.Id -Force
Remove-Item $testConfig -Force
```

Expected result: all five RKE2 nodes are `Ready`.

## Persistent Tunnel Script

Create `C:\Users\achinthah\scripts\agentic-kubectl-tunnel.ps1`:

```powershell
$scriptPath = "$env:USERPROFILE\scripts\agentic-kubectl-tunnel.ps1"
$logPath = "$env:USERPROFILE\scripts\agentic-kubectl-tunnel.log"

New-Item -ItemType Directory -Force -Path "$env:USERPROFILE\scripts" | Out-Null

@"
# agentic-kubectl-tunnel.ps1
# Keeps the local kubectl API tunnel alive for the agentic RKE2 cluster.

`$LogPath = "$logPath"
`$SshPath = "`$env:WINDIR\System32\OpenSSH\ssh.exe"

`$sshArgs = @(
  "-N",
  "-o", "ServerAliveInterval=30",
  "-o", "ServerAliveCountMax=3",
  "-o", "ExitOnForwardFailure=yes",
  "-L", "6443:172.25.188.85:6443",
  "agentic-cp"
)

while (`$true) {
  Add-Content -Path `$LogPath -Value "`$(Get-Date -Format o) starting tunnel"
  & `$SshPath @sshArgs >> `$LogPath 2>&1
  Add-Content -Path `$LogPath -Value "`$(Get-Date -Format o) tunnel exited with code `$LASTEXITCODE; restarting in 5s"
  Start-Sleep -Seconds 5
}
"@ | Set-Content -Path $scriptPath -Encoding ascii

if (-not (Test-Path $logPath)) {
  New-Item -ItemType File -Path $logPath | Out-Null
}
```

The script restarts only the SSH tunnel process. If SSH exits because of sleep,
network loss, or keepalive failure, the loop starts it again after five seconds.

## Update Kubeconfig

Back up and change the kubeconfig server to localhost:

```powershell
$configPath = "$env:USERPROFILE\.kube\agentic-config"
Copy-Item $configPath "$configPath.phase11.bak" -Force

(Get-Content $configPath) `
  -replace 'server: https://172\.25\.188\.85:6443', 'server: https://127.0.0.1:6443' |
  Set-Content $configPath

Select-String -Path $configPath -Pattern "server:"
# Expected: server: https://127.0.0.1:6443
```

Set `KUBECONFIG` permanently for the current Windows user:

```powershell
[System.Environment]::SetEnvironmentVariable(
  "KUBECONFIG",
  "$env:USERPROFILE\.kube\agentic-config",
  "User"
)

$env:KUBECONFIG = "$env:USERPROFILE\.kube\agentic-config"
```

New terminal windows should inherit this value. Existing terminals may need
`$env:KUBECONFIG` set manually until they are restarted.

## Default Kubeconfig Fallback

Some already-open terminals may not inherit the new user `KUBECONFIG`
environment variable. In that case, plain `kubectl` falls back to
`C:\Users\achinthah\.kube\config` and may use an old AKS context instead.

To make plain `kubectl` work even when `KUBECONFIG` is missing from the current
process, add an explicit `agentic-rke2` context to the default kubeconfig and
make it current:

```powershell
$agentic = "$env:USERPROFILE\.kube\agentic-config"
$default = "$env:USERPROFILE\.kube\config"
$backup = "$default.phase11-before-agentic-default.bak"
Copy-Item $default $backup -Force

$ca = kubectl --kubeconfig $agentic config view --raw -o jsonpath='{.clusters[0].cluster.certificate-authority-data}'
$cert = kubectl --kubeconfig $agentic config view --raw -o jsonpath='{.users[0].user.client-certificate-data}'
$key = kubectl --kubeconfig $agentic config view --raw -o jsonpath='{.users[0].user.client-key-data}'

kubectl --kubeconfig $default config set-cluster agentic-rke2 --server='https://127.0.0.1:6443'
kubectl --kubeconfig $default config set clusters.agentic-rke2.certificate-authority-data $ca
kubectl --kubeconfig $default config set-credentials agentic-rke2
kubectl --kubeconfig $default config set users.agentic-rke2.client-certificate-data $cert
kubectl --kubeconfig $default config set users.agentic-rke2.client-key-data $key
kubectl --kubeconfig $default config set-context agentic-rke2 --cluster=agentic-rke2 --user=agentic-rke2
kubectl --kubeconfig $default config use-context agentic-rke2

kubectl config current-context
# Expected: agentic-rke2
```

This preserves existing AKS and Docker Desktop contexts in the default config;
it only adds/selects the local RKE2 context.

## Preferred Autostart: Task Scheduler

Register a per-user logon task:

```powershell
$scriptPath = "$env:USERPROFILE\scripts\agentic-kubectl-tunnel.ps1"

$action = New-ScheduledTaskAction `
  -Execute "powershell.exe" `
  -Argument "-NoProfile -ExecutionPolicy Bypass -NonInteractive -WindowStyle Hidden -File `"$scriptPath`""

$trigger = New-ScheduledTaskTrigger -AtLogOn

$settings = New-ScheduledTaskSettingsSet `
  -ExecutionTimeLimit (New-TimeSpan -Hours 0) `
  -RestartCount 99 `
  -RestartInterval (New-TimeSpan -Minutes 1) `
  -StartWhenAvailable `
  -MultipleInstances IgnoreNew

$principal = New-ScheduledTaskPrincipal `
  -UserId "$env:USERDOMAIN\$env:USERNAME" `
  -LogonType Interactive `
  -RunLevel Limited

Register-ScheduledTask `
  -TaskName "agentic-kubectl-tunnel" `
  -TaskPath "\agentic\" `
  -Action $action `
  -Trigger $trigger `
  -Settings $settings `
  -Principal $principal `
  -Description "SSH tunnel for kubectl access to agentic RKE2 cluster"

Start-ScheduledTask -TaskPath "\agentic\" -TaskName "agentic-kubectl-tunnel"
```

Validate:

```powershell
Get-ScheduledTask -TaskPath "\agentic\" -TaskName "agentic-kubectl-tunnel" |
  Select-Object TaskName, State
```

## Fallback Autostart: HKCU Run Key

On this workstation, Task Scheduler registration may fail with:

```text
Access is denied.
```

If that happens, use the per-user Windows startup registry key instead. This
does not require administrator rights:

```powershell
$scriptPath = "$env:USERPROFILE\scripts\agentic-kubectl-tunnel.ps1"
$runPath = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run"
$runName = "agentic-kubectl-tunnel"
$runValue = "powershell.exe -NoProfile -ExecutionPolicy Bypass -NonInteractive -WindowStyle Hidden -File `"$scriptPath`""

New-ItemProperty -Path $runPath -Name $runName -Value $runValue -PropertyType String -Force | Out-Null

Start-Process powershell.exe `
  -ArgumentList "-NoProfile -ExecutionPolicy Bypass -NonInteractive -WindowStyle Hidden -File `"$scriptPath`"" `
  -WindowStyle Hidden
```

Validate the fallback:

```powershell
Get-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run" `
  -Name "agentic-kubectl-tunnel" |
  Select-Object -ExpandProperty "agentic-kubectl-tunnel"

Get-CimInstance Win32_Process -Filter "Name='powershell.exe'" |
  Where-Object { $_.CommandLine -match 'agentic-kubectl-tunnel.ps1' }
```

## Test Plan

### Tunnel Listening

```powershell
Test-NetConnection -ComputerName 127.0.0.1 -Port 6443
# Expected: TcpTestSucceeded: True
```

### Kubectl

```powershell
kubectl --kubeconfig "$env:USERPROFILE\.kube\agentic-config" get nodes -o wide
kubectl --kubeconfig "$env:USERPROFILE\.kube\agentic-config" -n agentic-app get pods
kubectl --kubeconfig "$env:USERPROFILE\.kube\agentic-config" -n argocd get applications.argoproj.io agentic-app
```

Expected:

```text
All five nodes Ready.
fastapi, nextjs, and mcp-server Running.
agentic-app Synced and Healthy.
```

### Restart Behavior

Kill only the SSH child process and confirm the PowerShell loop restarts it:

```powershell
Get-CimInstance Win32_Process -Filter "Name='ssh.exe'" |
  Where-Object { $_.CommandLine -match '6443:172.25.188.85:6443' } |
  ForEach-Object { Stop-Process -Id $_.ProcessId -Force }

Start-Sleep 15
Test-NetConnection -ComputerName 127.0.0.1 -Port 6443
kubectl --kubeconfig "$env:USERPROFILE\.kube\agentic-config" get nodes
```

Expected: the port returns and `kubectl` works.

### Fresh Terminal

Open a new PowerShell window:

```powershell
kubectl get nodes
```

Expected: all five nodes are `Ready` without manually setting `KUBECONFIG`.

### Login/Reboot

After logoff/login or reboot:

```powershell
Test-NetConnection -ComputerName 127.0.0.1 -Port 6443
kubectl get nodes
```

Expected: the startup entry launches the tunnel automatically.

## Managing The Tunnel

### Task Scheduler Mode

```powershell
Start-ScheduledTask -TaskPath "\agentic\" -TaskName "agentic-kubectl-tunnel"
Stop-ScheduledTask -TaskPath "\agentic\" -TaskName "agentic-kubectl-tunnel"
Unregister-ScheduledTask -TaskPath "\agentic\" -TaskName "agentic-kubectl-tunnel" -Confirm:$false
```

### HKCU Run Fallback Mode

```powershell
# Stop current script and SSH tunnel processes.
Get-CimInstance Win32_Process -Filter "Name='powershell.exe'" |
  Where-Object { $_.CommandLine -match 'agentic-kubectl-tunnel.ps1' } |
  ForEach-Object { Stop-Process -Id $_.ProcessId -Force }

Get-CimInstance Win32_Process -Filter "Name='ssh.exe'" |
  Where-Object { $_.CommandLine -match '6443:172.25.188.85:6443' } |
  ForEach-Object { Stop-Process -Id $_.ProcessId -Force }

# Remove login autostart.
Remove-ItemProperty `
  -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run" `
  -Name "agentic-kubectl-tunnel" `
  -ErrorAction SilentlyContinue
```

### Logs

```powershell
Get-Content "$env:USERPROFILE\scripts\agentic-kubectl-tunnel.log" -Tail 50
```

## Rollback

Restore the kubeconfig and remove persistent startup:

```powershell
Copy-Item "$env:USERPROFILE\.kube\agentic-config.phase11.bak" `
  "$env:USERPROFILE\.kube\agentic-config" `
  -Force

Copy-Item "$env:USERPROFILE\.kube\config.phase11-before-agentic-default.bak" `
  "$env:USERPROFILE\.kube\config" `
  -Force

[System.Environment]::SetEnvironmentVariable("KUBECONFIG", $null, "User")

Stop-ScheduledTask -TaskPath "\agentic\" -TaskName "agentic-kubectl-tunnel" -ErrorAction SilentlyContinue
Unregister-ScheduledTask -TaskPath "\agentic\" -TaskName "agentic-kubectl-tunnel" -Confirm:$false -ErrorAction SilentlyContinue

Remove-ItemProperty `
  -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run" `
  -Name "agentic-kubectl-tunnel" `
  -ErrorAction SilentlyContinue

Get-CimInstance Win32_Process -Filter "Name='powershell.exe'" |
  Where-Object { $_.CommandLine -match 'agentic-kubectl-tunnel.ps1' } |
  ForEach-Object { Stop-Process -Id $_.ProcessId -Force }

Get-CimInstance Win32_Process -Filter "Name='ssh.exe'" |
  Where-Object { $_.CommandLine -match '6443:172.25.188.85:6443' } |
  ForEach-Object { Stop-Process -Id $_.ProcessId -Force }
```

## Notes

- This phase intentionally does not change cluster API server routing,
  firewalls, RKE2 config, MetalLB, ingress, or DNS.
- `ServerAliveInterval 30` and `ServerAliveCountMax 3` cause SSH to detect a
  dead connection in about 90 seconds.
- After sleep/wake, wait 15-30 seconds before retrying `kubectl` if the first
  command gets `connection refused`.
- If another process binds `127.0.0.1:6443`, the tunnel fails fast and records
  the bind error in `agentic-kubectl-tunnel.log`.
