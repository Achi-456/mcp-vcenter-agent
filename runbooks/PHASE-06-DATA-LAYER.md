# Phase 06 - Data Layer

Deploy PostgreSQL with pgvector and Redis into `agentic-data` on `agentic-db-01.dclab.local`.

This phase uses direct `kubectl` and Helm from the workstation. Argo CD adoption is deferred until a Git repository URL and credentials are defined.

## Targets

```text
Namespace:          agentic-data
Node placement:     role=data
DB node:            agentic-db-01.dclab.local / 172.25.188.88
StorageClass:       longhorn
Longhorn replicas:  1
PostgreSQL image:   pgvector/pgvector:0.8.2-pg16
PostgreSQL service: postgres.agentic-data.svc.cluster.local:5432
PostgreSQL DB/user: agentic / agentic_app
Redis chart:        bitnami/redis 24.1.2
Redis app version:  8.4.0
Redis service:      redis-master.agentic-data.svc.cluster.local:6379
```

## 1. Workstation Setup

Use the normal kubeconfig first:

```powershell
$env:Path=[System.Environment]::GetEnvironmentVariable('Path','Machine')+';'+[System.Environment]::GetEnvironmentVariable('Path','User')
$env:KUBECONFIG="$env:USERPROFILE\.kube\agentic-config"
kubectl get nodes --request-timeout=15s
helm version --short
```

If workstation access to `172.25.188.85:6443` hangs or fails, use the Phase 5 SSH tunnel fallback:

```powershell
$sshKey="$env:USERPROFILE\.ssh\hybrid-cloud-idp"
$log=Join-Path $env:TEMP 'agentic-api-tunnel-phase6.log'
$args=@('-o','ExitOnForwardFailure=yes','-o','ServerAliveInterval=30','-o','StrictHostKeyChecking=no','-i',$sshKey,'-N','-L','16443:127.0.0.1:6443','root@172.25.188.85')
Start-Process -FilePath 'ssh.exe' -ArgumentList $args -WindowStyle Hidden -PassThru -RedirectStandardError $log

$env:KUBECONFIG=Join-Path $env:TEMP 'agentic-config-tunnel'
(Get-Content "$env:USERPROFILE\.kube\agentic-config") -replace 'https://172\.25\.188\.85:6443','https://127.0.0.1:16443' | Set-Content -LiteralPath $env:KUBECONFIG -Encoding ascii
kubectl get nodes --request-timeout=20s
```

## 2. Preflight

```powershell
kubectl get ns agentic-data
kubectl get node agentic-db-01.dclab.local --show-labels
kubectl get storageclass
kubectl get storageclass longhorn -o yaml
kubectl -n longhorn-system get settings.longhorn.io default-replica-count default-data-path
kubectl -n longhorn-system get volumes.longhorn.io
```

Expected:

```text
agentic-data exists
agentic-db-01.dclab.local is Ready and has role=data
longhorn is marked default
longhorn StorageClass has numberOfReplicas: "1"
default-data-path is /data/longhorn
```

Confirm the DB node data disk:

```powershell
$KEY="$env:USERPROFILE\.ssh\hybrid-cloud-idp"
ssh -i $KEY root@172.25.188.88 "findmnt /data; df -h /data; ls -ld /data /data/longhorn"
```

Expected:

```text
/data is /dev/sdb1 xfs
/data has the 300 GB disk mounted
/data/longhorn exists
```

## 3. Add Bitnami Helm Repo

```powershell
helm repo add bitnami https://charts.bitnami.com/bitnami --force-update
helm repo update
helm search repo bitnami/redis --version 24.1.2
```

Expected:

```text
bitnami/redis  24.1.2  8.4.0
```

## 4. Create Secrets

Do not store these passwords in Git.

```powershell
function New-SecretValue {
  $bytes = New-Object byte[] 24
  [System.Security.Cryptography.RandomNumberGenerator]::Fill($bytes)
  [Convert]::ToBase64String($bytes).TrimEnd('=').Replace('+','-').Replace('/','_')
}

$postgresPassword = New-SecretValue
$appPassword = New-SecretValue
$redisPassword = New-SecretValue

kubectl create secret generic agentic-postgres-auth `
  -n agentic-data `
  --from-literal=postgres-password=$postgresPassword `
  --from-literal=app-password=$appPassword `
  --dry-run=client -o yaml | kubectl apply -f -

kubectl create secret generic agentic-redis-auth `
  -n agentic-data `
  --from-literal=redis-password=$redisPassword `
  --dry-run=client -o yaml | kubectl apply -f -
```

Retrieve later if needed:

```powershell
$POSTGRES_PASSWORD_B64 = kubectl -n agentic-data get secret agentic-postgres-auth -o jsonpath="{.data.postgres-password}"
$POSTGRES_PASSWORD = [System.Text.Encoding]::UTF8.GetString([System.Convert]::FromBase64String($POSTGRES_PASSWORD_B64))

$REDIS_PASSWORD_B64 = kubectl -n agentic-data get secret agentic-redis-auth -o jsonpath="{.data.redis-password}"
$REDIS_PASSWORD = [System.Text.Encoding]::UTF8.GetString([System.Convert]::FromBase64String($REDIS_PASSWORD_B64))
```

## 5. Deploy PostgreSQL + pgvector

PostgreSQL must not mount the Longhorn volume root directly because the filesystem contains `lost+found`. Set `PGDATA` to a subdirectory under the mount.

```powershell
@'
apiVersion: v1
kind: ConfigMap
metadata:
  name: postgres-init
  namespace: agentic-data
data:
  01-agentic.sh: |
    #!/bin/bash
    set -euo pipefail
    psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname postgres <<-EOSQL
      DO
      \$\$
      BEGIN
        IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'agentic_app') THEN
          CREATE ROLE agentic_app LOGIN PASSWORD '${APP_PASSWORD}';
        ELSE
          ALTER ROLE agentic_app LOGIN PASSWORD '${APP_PASSWORD}';
        END IF;
      END
      \$\$;

      SELECT 'CREATE DATABASE agentic OWNER agentic_app'
      WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'agentic')\gexec
    EOSQL

    psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname agentic <<-EOSQL
      CREATE EXTENSION IF NOT EXISTS vector;
      GRANT ALL PRIVILEGES ON DATABASE agentic TO agentic_app;
      GRANT ALL ON SCHEMA public TO agentic_app;
      ALTER SCHEMA public OWNER TO agentic_app;
    EOSQL
---
apiVersion: v1
kind: Service
metadata:
  name: postgres
  namespace: agentic-data
spec:
  type: ClusterIP
  selector:
    app.kubernetes.io/name: postgres
  ports:
    - name: postgresql
      port: 5432
      targetPort: 5432
---
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: postgres
  namespace: agentic-data
spec:
  serviceName: postgres
  replicas: 1
  selector:
    matchLabels:
      app.kubernetes.io/name: postgres
  template:
    metadata:
      labels:
        app.kubernetes.io/name: postgres
    spec:
      nodeSelector:
        role: data
        kubernetes.io/os: linux
      securityContext:
        fsGroup: 999
      containers:
        - name: postgres
          image: pgvector/pgvector:0.8.2-pg16
          imagePullPolicy: IfNotPresent
          ports:
            - name: postgresql
              containerPort: 5432
          env:
            - name: POSTGRES_DB
              value: agentic
            - name: POSTGRES_USER
              value: postgres
            - name: POSTGRES_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: agentic-postgres-auth
                  key: postgres-password
            - name: APP_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: agentic-postgres-auth
                  key: app-password
            - name: PGDATA
              value: /var/lib/postgresql/data/pgdata
          readinessProbe:
            exec:
              command:
                - sh
                - -c
                - pg_isready -U postgres -d agentic
            initialDelaySeconds: 10
            periodSeconds: 10
            timeoutSeconds: 5
            failureThreshold: 6
          livenessProbe:
            exec:
              command:
                - sh
                - -c
                - pg_isready -U postgres -d agentic
            initialDelaySeconds: 30
            periodSeconds: 20
            timeoutSeconds: 5
            failureThreshold: 6
          resources:
            requests:
              cpu: 250m
              memory: 1Gi
            limits:
              memory: 4Gi
          volumeMounts:
            - name: data
              mountPath: /var/lib/postgresql/data
            - name: postgres-init
              mountPath: /docker-entrypoint-initdb.d
              readOnly: true
      volumes:
        - name: postgres-init
          configMap:
            name: postgres-init
            defaultMode: 0755
  volumeClaimTemplates:
    - metadata:
        name: data
      spec:
        accessModes:
          - ReadWriteOnce
        storageClassName: longhorn
        resources:
          requests:
            storage: 50Gi
'@ | kubectl apply -f -
```

Wait for PostgreSQL:

```powershell
kubectl -n agentic-data rollout status statefulset/postgres --timeout=10m
kubectl -n agentic-data get pod postgres-0 -o wide
```

If it fails or hangs:

```powershell
kubectl -n agentic-data logs postgres-0 --previous
kubectl -n agentic-data logs postgres-0 --tail=100
```

## 6. Install Redis

```powershell
$values=Join-Path $env:TEMP 'redis-agentic-values.yaml'

@'
architecture: standalone

auth:
  enabled: true
  existingSecret: agentic-redis-auth
  existingSecretPasswordKey: redis-password

master:
  nodeSelector:
    kubernetes.io/os: linux
    role: data
  persistence:
    enabled: true
    storageClass: longhorn
    size: 10Gi
  resources:
    requests:
      cpu: 100m
      memory: 512Mi
    limits:
      memory: 2Gi

replica:
  replicaCount: 0

metrics:
  enabled: false
'@ | Set-Content -LiteralPath $values -Encoding ascii

helm upgrade --install redis bitnami/redis `
  --namespace agentic-data `
  --version 24.1.2 `
  -f $values `
  --wait `
  --timeout 15m
```

If Helm times out and the release is stuck in `pending-install`, uninstall before retrying:

```powershell
helm uninstall redis -n agentic-data
```

The Bitnami Redis `24.1.2` chart currently defaults to `registry-1.docker.io/bitnami/redis:latest`. This lab run keeps the chart pinned and records the warning. For stricter production-style repeatability, replace it later with an approved pinned Redis image from a private or enterprise catalog.

## 7. Validate PostgreSQL

```powershell
$POSTGRES_PASSWORD_B64 = kubectl -n agentic-data get secret agentic-postgres-auth -o jsonpath="{.data.postgres-password}"
$POSTGRES_PASSWORD = [System.Text.Encoding]::UTF8.GetString([System.Convert]::FromBase64String($POSTGRES_PASSWORD_B64))

kubectl -n agentic-data exec postgres-0 -- env PGPASSWORD=$POSTGRES_PASSWORD psql -U postgres -d agentic -c "SELECT version();"
kubectl -n agentic-data exec postgres-0 -- env PGPASSWORD=$POSTGRES_PASSWORD psql -U postgres -d agentic -c "SELECT current_database();"
kubectl -n agentic-data exec postgres-0 -- env PGPASSWORD=$POSTGRES_PASSWORD psql -U postgres -d agentic -c "SELECT extname FROM pg_extension WHERE extname='vector';"
kubectl -n agentic-data exec postgres-0 -- env PGPASSWORD=$POSTGRES_PASSWORD psql -U postgres -d agentic -c "CREATE TABLE IF NOT EXISTS phase6_vector_smoke (id bigserial PRIMARY KEY, embedding vector(3)); TRUNCATE phase6_vector_smoke; INSERT INTO phase6_vector_smoke (embedding) VALUES ('[1,2,3]'), ('[1,1,1]'); SELECT id FROM phase6_vector_smoke ORDER BY embedding <-> '[1,2,2]' LIMIT 1;"
```

Expected:

```text
current_database = agentic
extname = vector
nearest-neighbor query returns one row
```

## 8. Validate Redis

```powershell
$REDIS_PASSWORD_B64 = kubectl -n agentic-data get secret agentic-redis-auth -o jsonpath="{.data.redis-password}"
$REDIS_PASSWORD = [System.Text.Encoding]::UTF8.GetString([System.Convert]::FromBase64String($REDIS_PASSWORD_B64))

kubectl -n agentic-data exec redis-master-0 -- env REDISCLI_AUTH=$REDIS_PASSWORD redis-cli ping
kubectl -n agentic-data exec redis-master-0 -- env REDISCLI_AUTH=$REDIS_PASSWORD redis-cli set phase6 smoke-ok
kubectl -n agentic-data exec redis-master-0 -- env REDISCLI_AUTH=$REDIS_PASSWORD redis-cli get phase6
```

Expected:

```text
PONG
OK
smoke-ok
```

## 9. Final Validation

```powershell
kubectl -n agentic-data get pods -o wide
kubectl -n agentic-data get pvc -o wide
helm ls -n agentic-data
kubectl get storageclass
kubectl -n longhorn-system get volumes.longhorn.io
kubectl get nodes
kubectl get pods -A --field-selector=status.phase!=Succeeded --no-headers | Select-String -Pattern 'Pending|CrashLoopBackOff|Error|ImagePullBackOff|ErrImagePull|0/'
```

Expected:

```text
postgres-0 Running on agentic-db-01.dclab.local
redis-master-0 Running on agentic-db-01.dclab.local
data-postgres-0 Bound with longhorn
redis-data-redis-master-0 Bound with longhorn
Longhorn PostgreSQL and Redis volumes attached and healthy on agentic-db-01
all nodes Ready
unhealthy pod scan has no output
```

## Commands Used In This Lab

During implementation, direct workstation access to `172.25.188.85:6443` still hung, so the SSH API tunnel was used.

PostgreSQL initially failed because the official PostgreSQL image will not initialize directly into a mounted filesystem root containing `lost+found`. The fixed manifest sets:

```text
PGDATA=/var/lib/postgresql/data/pgdata
```

The pgvector functional smoke test returned one row from a nearest-neighbor query, and Redis returned:

```text
PONG
OK
smoke-ok
```
