# Phase 07 - App Layer

Deploy FastAPI, Next.js, and an internal MCP server into `agentic-app` on `agentic-worker-01.dclab.local`.

This phase uses direct `kubectl apply`. Argo CD adoption is deferred until a Git repository URL and credentials are defined.

Do not execute the deployment section until the image placeholders are replaced with real image references.

## Targets

```text
Namespace:        agentic-app
Node placement:   agentic-worker-01.dclab.local / role=app-worker
FastAPI host:     api.dclab.local
Next.js host:     app.dclab.local
Ingress IP:       172.25.188.89
MCP access:       internal ClusterIP only
FastAPI service:  fastapi.agentic-app.svc.cluster.local:8000
Next.js service:  nextjs.agentic-app.svc.cluster.local:3000
MCP service:      mcp-server.agentic-app.svc.cluster.local:8001
```

## 1. Workstation Setup

Use the normal kubeconfig first:

```powershell
$env:Path=[System.Environment]::GetEnvironmentVariable('Path','Machine')+';'+[System.Environment]::GetEnvironmentVariable('Path','User')
$env:KUBECONFIG="$env:USERPROFILE\.kube\agentic-config"
kubectl get nodes --request-timeout=15s
```

If workstation access to `172.25.188.85:6443` hangs or fails, use the SSH API tunnel fallback:

```powershell
$sshKey="$env:USERPROFILE\.ssh\hybrid-cloud-idp"
$log=Join-Path $env:TEMP 'agentic-api-tunnel-phase7.log'
$args=@('-o','ExitOnForwardFailure=yes','-o','ServerAliveInterval=30','-o','StrictHostKeyChecking=no','-i',$sshKey,'-N','-L','16443:127.0.0.1:6443','root@172.25.188.85')
Start-Process -FilePath 'ssh.exe' -ArgumentList $args -WindowStyle Hidden -PassThru -RedirectStandardError $log

$env:KUBECONFIG=Join-Path $env:TEMP 'agentic-config-tunnel'
(Get-Content "$env:USERPROFILE\.kube\agentic-config") -replace 'https://172\.25\.188\.85:6443','https://127.0.0.1:16443' | Set-Content -LiteralPath $env:KUBECONFIG -Encoding ascii
kubectl get nodes --request-timeout=20s
```

## 2. Image Variables And Stop Gate

Replace these placeholders with real image references before deploying.

```powershell
$FASTAPI_IMAGE="ghcr.io/<your-org>/agentic-fastapi:0.7.0"
$NEXTJS_IMAGE="ghcr.io/<your-org>/agentic-nextjs:0.7.0"
$MCP_IMAGE="ghcr.io/<your-org>/agentic-mcp:0.7.0"

if (($FASTAPI_IMAGE + $NEXTJS_IMAGE + $MCP_IMAGE) -match '<your-org>') {
  throw "STOP: replace image placeholders before Phase 07 deployment."
}
```

If the registry is private, create an image pull secret before applying Deployments:

```powershell
kubectl create secret docker-registry ghcr-pull `
  --namespace agentic-app `
  --docker-server=ghcr.io `
  --docker-username="<github-user>" `
  --docker-password="<github-token>" `
  --docker-email="<email>" `
  --dry-run=client -o yaml | kubectl apply -f -
```

If images are public, do not add `imagePullSecrets` to the Deployments.

## 3. Preflight

```powershell
kubectl get ns agentic-app
kubectl get nodes -l role=app-worker -o wide
kubectl describe node agentic-worker-01.dclab.local | Select-String "Labels","Taints","Unschedulable"
kubectl get ingressclass nginx
kubectl get clusterissuer dclab-local-selfsigned
kubectl -n agentic-data get pod postgres-0 redis-master-0 -o wide
kubectl -n agentic-data get svc postgres redis-master
```

Confirm cluster DNS and TCP connectivity to Phase 06 services:

```powershell
kubectl run db-test `
  --namespace agentic-app `
  --image=busybox:1.36.1 `
  --rm -it `
  --restart=Never `
  -- sh -c "nc -zv postgres.agentic-data.svc.cluster.local 5432 && nc -zv redis-master.agentic-data.svc.cluster.local 6379"
```

Expected:

```text
agentic-app exists
agentic-worker-01 is Ready, role=app-worker, and schedulable
postgres and redis services accept TCP connections
nginx ingress class exists
dclab-local-selfsigned is Ready
```

## 4. Workstation Hosts Entries

Run PowerShell as Administrator:

```powershell
Add-Content -Path "$env:SystemRoot\System32\drivers\etc\hosts" -Value "172.25.188.89 app.dclab.local"
Add-Content -Path "$env:SystemRoot\System32\drivers\etc\hosts" -Value "172.25.188.89 api.dclab.local"
Select-String -Path "$env:SystemRoot\System32\drivers\etc\hosts" -Pattern "app\.dclab\.local|api\.dclab\.local"
```

If hosts file edits are blocked, use `curl --resolve` during validation:

```powershell
curl.exe -k --resolve "api.dclab.local:443:172.25.188.89" https://api.dclab.local/health
curl.exe -k --resolve "app.dclab.local:443:172.25.188.89" https://app.dclab.local/
```

## 5. Create Runtime Config

Next.js `NEXT_PUBLIC_*` values must also exist at image build time. Runtime ConfigMap values alone do not rewrite a prebuilt Next.js browser bundle.

```powershell
@'
apiVersion: v1
kind: ConfigMap
metadata:
  name: agentic-app-config
  namespace: agentic-app
data:
  APP_ENV: "production"
  LOG_LEVEL: "INFO"
  DEFAULT_MODEL: "claude-sonnet-4-20250514"
  FALLBACK_MODEL: "gpt-4o"
  VCENTER_PORT: "443"
  VCENTER_IGNORE_SSL: "false"
  AGENT_MAX_TURNS: "20"
  AGENT_SUMMARIZE_EVERY: "5"
  AGENT_TOOL_TIMEOUT_READ: "30"
  AGENT_TOOL_TIMEOUT_MUTATE: "300"
  AGENT_MAX_PARALLEL_TOOLS: "3"
  CONTEXT_MAX_TOKENS: "150000"
  CONTEXT_RESERVE_OUTPUT: "0.10"
  LANGSMITH_PROJECT: "vcenter-agent"
  OTEL_EXPORTER_OTLP_ENDPOINT: "http://otel-collector.monitoring.svc.cluster.local:4317"
  MCP_SERVER_URL: "http://mcp-server.agentic-app.svc.cluster.local:8001"
  NEXT_PUBLIC_API_URL: "https://api.dclab.local"
  NEXT_PUBLIC_WS_URL: "wss://api.dclab.local/ws"
  NEXT_PUBLIC_APP_NAME: "vCenter Agentic Ops"
'@ | kubectl apply -f -
```

## 6. Create Runtime Secrets

Set local PowerShell variables first. Do not write secret values into tracked files.

```powershell
$ANTHROPIC_API_KEY=""
$OPENAI_API_KEY=""
$GOOGLE_API_KEY=""
$LANGSMITH_API_KEY=""
$VCENTER_HOST="<vcenter-fqdn-or-ip>"
$VCENTER_USER="<vcenter-user>"
$VCENTER_PASSWORD="<vcenter-password>"
$SECRET_KEY=(New-Guid).Guid

if ($VCENTER_HOST -match '^<|>$' -or $VCENTER_USER -match '^<|>$' -or $VCENTER_PASSWORD -match '^<|>$') {
  throw "STOP: set real vCenter connection values before creating agentic-app-secrets."
}
```

Retrieve Phase 06 passwords and create URLs:

```powershell
$PG_APP_PW = kubectl -n agentic-data get secret agentic-postgres-auth -o jsonpath="{.data.app-password}" | % { [System.Text.Encoding]::UTF8.GetString([System.Convert]::FromBase64String($_)) }
$REDIS_PW = kubectl -n agentic-data get secret agentic-redis-auth -o jsonpath="{.data.redis-password}" | % { [System.Text.Encoding]::UTF8.GetString([System.Convert]::FromBase64String($_)) }

$DB_URL="postgresql+asyncpg://agentic_app:$PG_APP_PW@postgres.agentic-data.svc.cluster.local:5432/agentic"
$REDIS_URL="redis://:$REDIS_PW@redis-master.agentic-data.svc.cluster.local:6379"
```

Create the secret:

```powershell
kubectl create secret generic agentic-app-secrets `
  --namespace agentic-app `
  --from-literal=ANTHROPIC_API_KEY="$ANTHROPIC_API_KEY" `
  --from-literal=OPENAI_API_KEY="$OPENAI_API_KEY" `
  --from-literal=GOOGLE_API_KEY="$GOOGLE_API_KEY" `
  --from-literal=LANGSMITH_API_KEY="$LANGSMITH_API_KEY" `
  --from-literal=VCENTER_HOST="$VCENTER_HOST" `
  --from-literal=VCENTER_USER="$VCENTER_USER" `
  --from-literal=VCENTER_PASSWORD="$VCENTER_PASSWORD" `
  --from-literal=SECRET_KEY="$SECRET_KEY" `
  --from-literal=DB_URL="$DB_URL" `
  --from-literal=REDIS_URL="$REDIS_URL" `
  --dry-run=client -o yaml | kubectl apply -f -
```

## 7. Create TLS Certificates

```powershell
@'
apiVersion: cert-manager.io/v1
kind: Certificate
metadata:
  name: app-tls
  namespace: agentic-app
spec:
  secretName: app-tls
  dnsNames:
    - app.dclab.local
  issuerRef:
    name: dclab-local-selfsigned
    kind: ClusterIssuer
---
apiVersion: cert-manager.io/v1
kind: Certificate
metadata:
  name: api-tls
  namespace: agentic-app
spec:
  secretName: api-tls
  dnsNames:
    - api.dclab.local
  issuerRef:
    name: dclab-local-selfsigned
    kind: ClusterIssuer
'@ | kubectl apply -f -
```

Wait until both are ready:

```powershell
kubectl -n agentic-app wait certificate/app-tls --for=condition=Ready --timeout=3m
kubectl -n agentic-app wait certificate/api-tls --for=condition=Ready --timeout=3m
kubectl -n agentic-app get certificate app-tls api-tls
```

## 8. Deploy FastAPI

```powershell
@"
apiVersion: apps/v1
kind: Deployment
metadata:
  name: fastapi
  namespace: agentic-app
  labels:
    app: fastapi
    phase: "07"
spec:
  replicas: 1
  selector:
    matchLabels:
      app: fastapi
  template:
    metadata:
      labels:
        app: fastapi
    spec:
      nodeSelector:
        role: app-worker
        kubernetes.io/hostname: agentic-worker-01.dclab.local
      containers:
        - name: fastapi
          image: $FASTAPI_IMAGE
          ports:
            - containerPort: 8000
              name: http
          envFrom:
            - secretRef:
                name: agentic-app-secrets
            - configMapRef:
                name: agentic-app-config
          resources:
            requests:
              cpu: 250m
              memory: 256Mi
            limits:
              cpu: "1"
              memory: 2Gi
          livenessProbe:
            httpGet:
              path: /health
              port: 8000
            initialDelaySeconds: 15
            periodSeconds: 20
            failureThreshold: 3
          readinessProbe:
            httpGet:
              path: /ready
              port: 8000
            initialDelaySeconds: 10
            periodSeconds: 10
            failureThreshold: 3
---
apiVersion: v1
kind: Service
metadata:
  name: fastapi
  namespace: agentic-app
spec:
  type: ClusterIP
  selector:
    app: fastapi
  ports:
    - name: http
      port: 8000
      targetPort: 8000
---
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: fastapi
  namespace: agentic-app
  annotations:
    nginx.ingress.kubernetes.io/proxy-buffering: "off"
    nginx.ingress.kubernetes.io/proxy-request-buffering: "off"
    nginx.ingress.kubernetes.io/proxy-read-timeout: "3600"
    nginx.ingress.kubernetes.io/proxy-send-timeout: "3600"
    nginx.ingress.kubernetes.io/proxy-http-version: "1.1"
spec:
  ingressClassName: nginx
  tls:
    - hosts:
        - api.dclab.local
      secretName: api-tls
  rules:
    - host: api.dclab.local
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: fastapi
                port:
                  number: 8000
"@ | kubectl apply -f -
```

## 9. Deploy Next.js

```powershell
@"
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nextjs
  namespace: agentic-app
  labels:
    app: nextjs
    phase: "07"
spec:
  replicas: 1
  selector:
    matchLabels:
      app: nextjs
  template:
    metadata:
      labels:
        app: nextjs
    spec:
      nodeSelector:
        role: app-worker
        kubernetes.io/hostname: agentic-worker-01.dclab.local
      containers:
        - name: nextjs
          image: $NEXTJS_IMAGE
          ports:
            - containerPort: 3000
              name: http
          env:
            - name: NEXT_PUBLIC_API_URL
              valueFrom:
                configMapKeyRef:
                  name: agentic-app-config
                  key: NEXT_PUBLIC_API_URL
            - name: NEXT_PUBLIC_WS_URL
              valueFrom:
                configMapKeyRef:
                  name: agentic-app-config
                  key: NEXT_PUBLIC_WS_URL
            - name: NEXT_PUBLIC_APP_NAME
              valueFrom:
                configMapKeyRef:
                  name: agentic-app-config
                  key: NEXT_PUBLIC_APP_NAME
          resources:
            requests:
              cpu: 250m
              memory: 256Mi
            limits:
              cpu: "1"
              memory: 1Gi
          livenessProbe:
            httpGet:
              path: /api/health
              port: 3000
            initialDelaySeconds: 20
            periodSeconds: 20
            failureThreshold: 3
          readinessProbe:
            httpGet:
              path: /api/health
              port: 3000
            initialDelaySeconds: 15
            periodSeconds: 10
            failureThreshold: 3
---
apiVersion: v1
kind: Service
metadata:
  name: nextjs
  namespace: agentic-app
spec:
  type: ClusterIP
  selector:
    app: nextjs
  ports:
    - name: http
      port: 3000
      targetPort: 3000
---
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: nextjs
  namespace: agentic-app
  annotations:
    nginx.ingress.kubernetes.io/proxy-read-timeout: "60"
    nginx.ingress.kubernetes.io/proxy-send-timeout: "60"
spec:
  ingressClassName: nginx
  tls:
    - hosts:
        - app.dclab.local
      secretName: app-tls
  rules:
    - host: app.dclab.local
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: nextjs
                port:
                  number: 3000
"@ | kubectl apply -f -
```

## 10. Deploy Internal MCP Server

```powershell
@"
apiVersion: apps/v1
kind: Deployment
metadata:
  name: mcp-server
  namespace: agentic-app
  labels:
    app: mcp-server
    phase: "07"
spec:
  replicas: 1
  selector:
    matchLabels:
      app: mcp-server
  template:
    metadata:
      labels:
        app: mcp-server
    spec:
      nodeSelector:
        role: app-worker
        kubernetes.io/hostname: agentic-worker-01.dclab.local
      containers:
        - name: mcp-server
          image: $MCP_IMAGE
          ports:
            - containerPort: 8001
              name: http
          envFrom:
            - secretRef:
                name: agentic-app-secrets
            - configMapRef:
                name: agentic-app-config
          resources:
            requests:
              cpu: 100m
              memory: 128Mi
            limits:
              cpu: 500m
              memory: 512Mi
          livenessProbe:
            httpGet:
              path: /health
              port: 8001
            initialDelaySeconds: 10
            periodSeconds: 20
            failureThreshold: 3
          readinessProbe:
            httpGet:
              path: /health
              port: 8001
            initialDelaySeconds: 5
            periodSeconds: 10
            failureThreshold: 3
---
apiVersion: v1
kind: Service
metadata:
  name: mcp-server
  namespace: agentic-app
spec:
  type: ClusterIP
  selector:
    app: mcp-server
  ports:
    - name: http
      port: 8001
      targetPort: 8001
"@ | kubectl apply -f -
```

## 11. Wait For Rollouts

```powershell
kubectl -n agentic-app rollout status deployment/fastapi --timeout=10m
kubectl -n agentic-app rollout status deployment/nextjs --timeout=10m
kubectl -n agentic-app rollout status deployment/mcp-server --timeout=10m
kubectl -n agentic-app get pods -o wide
```

Expected:

```text
fastapi, nextjs, and mcp-server pods Running on agentic-worker-01.dclab.local
```

## 12. Validate FastAPI

If hosts entries are configured:

```powershell
curl.exe -k https://api.dclab.local/health
curl.exe -k https://api.dclab.local/ready
curl.exe -k -N -H "Accept: text/event-stream" https://api.dclab.local/api/v1/chat/stream-test
```

If hosts entries are blocked:

```powershell
curl.exe -k --resolve "api.dclab.local:443:172.25.188.89" https://api.dclab.local/health
curl.exe -k --resolve "api.dclab.local:443:172.25.188.89" https://api.dclab.local/ready
curl.exe -k -N --resolve "api.dclab.local:443:172.25.188.89" -H "Accept: text/event-stream" https://api.dclab.local/api/v1/chat/stream-test
```

Open:

```text
https://api.dclab.local/docs
```

Expected:

```text
/health returns healthy status
/ready confirms db and redis are ok
/docs loads Swagger UI
SSE events arrive incrementally
```

## 13. Validate Next.js

```powershell
curl.exe -k --resolve "app.dclab.local:443:172.25.188.89" https://app.dclab.local/
curl.exe -k --resolve "app.dclab.local:443:172.25.188.89" https://app.dclab.local/api/health
```

Open:

```text
https://app.dclab.local
```

Expected:

```text
UI loads
/api/health returns healthy status
browser network calls target https://api.dclab.local
```

## 14. Validate MCP Internal Access

```powershell
kubectl run mcp-test `
  --namespace agentic-app `
  --image=curlimages/curl `
  --rm -it `
  --restart=Never `
  -- curl -s http://mcp-server.agentic-app.svc.cluster.local:8001/health
```

Expected:

```text
healthy status from MCP server
no mcp.dclab.local ingress exists
```

## 15. Validate Dependency Access From FastAPI Pod

```powershell
$POD = kubectl -n agentic-app get pod -l app=fastapi -o jsonpath="{.items[0].metadata.name}"

kubectl -n agentic-app exec $POD -- python -c "import asyncio, asyncpg, os; async def t():`n    conn = await asyncpg.connect(os.environ['DB_URL'].replace('+asyncpg',''))`n    print(await conn.fetchval('SELECT version()'))`n    await conn.close()`nasyncio.run(t())"

kubectl -n agentic-app exec $POD -- python -c "import redis, os; r = redis.from_url(os.environ['REDIS_URL']); r.set('phase7', 'smoke-ok'); print(r.get('phase7'))"
```

Expected:

```text
PostgreSQL 16.x version string
b'smoke-ok'
```

## 16. Final Stability Check

```powershell
kubectl -n agentic-app get deploy,svc,ingress,certificate,pods -o wide
kubectl get nodes
kubectl get pods -A --field-selector=status.phase!=Succeeded --no-headers | Select-String -Pattern 'Pending|CrashLoopBackOff|Error|ImagePullBackOff|ErrImagePull|0/'
```

Expected:

```text
all app Deployments Available
all five nodes Ready
unhealthy pod scan has no output
```

## Troubleshooting

```text
Pod Pending:
  kubectl describe pod <name> -n agentic-app
  Check nodeSelector, taints, and resource requests.

Pod CrashLoopBackOff:
  kubectl logs <name> -n agentic-app --previous
  Check missing secret/config env vars.

ImagePullBackOff:
  Confirm image variables are real registry paths.
  If private, create imagePullSecret and add it to Deployment specs.

SSE stream buffered:
  Confirm FastAPI ingress has proxy-buffering off and proxy-request-buffering off.

Next.js browser calls wrong API:
  Rebuild image with NEXT_PUBLIC_API_URL and NEXT_PUBLIC_WS_URL set at build time.

Certificate not Ready:
  kubectl describe certificate api-tls -n agentic-app
  kubectl get clusterissuer dclab-local-selfsigned

Rollout hangs:
  kubectl -n agentic-app get events --sort-by=.lastTimestamp
```

## Commands Used In This Lab

Phase 07 was not deployed during runbook creation because image references are still placeholders:

```text
ghcr.io/<your-org>/agentic-fastapi:0.7.0
ghcr.io/<your-org>/agentic-nextjs:0.7.0
ghcr.io/<your-org>/agentic-mcp:0.7.0
```

Replace them with real image references before executing sections 5 through 16.
