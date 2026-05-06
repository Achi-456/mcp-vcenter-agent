# Project Knowledge Summary

## Resources
| VM Name              | FQDN                             |      Example IP |        Gateway |             DNS |
| -------------------- | -------------------------------- | --------------: | -------------: | --------------: |
| agentic-cp-01        | agentic-cp-01.dclab.local        | 172.25.188.85 | 172.25.188.1 | 172.25.188.20 |
| agentic-worker-01    | agentic-worker-01.dclab.local    | 172.25.188.86 | 172.25.188.1 | 172.25.188.20 |
| agentic-worker-02    | agentic-worker-02.dclab.local    | 172.25.188.87 | 172.25.188.1 | 172.25.188.20 |
| agentic-db-01        | agentic-db-01.dclab.local        | 172.25.188.88 | 172.25.188.1 | 172.25.188.20 |
| agentic-utility-01   | agentic-utility-01.dclab.local   | 172.25.188.89 | 172.25.188.1 | 172.25.188.20 |

## Repository Purpose
This project is a Docker Compose based stack that serves a web UI/API through Nginx and a backend service (`vcenter-api`).

## Runtime Shape
- `docker compose up --build -d` is the primary startup path.
- `docker compose ps` is used to verify running services.
- `http://localhost/api/status` is the fastest health check endpoint.

## Request Routing
- `docker/nginx.conf` routes `/api/*` traffic to the backend (`vcenter-api`).
- `http://localhost/` serves the frontend entrypoint.

## Practical Verification Flow
1. Build and start with Docker Compose.
2. Confirm container status with `docker compose ps`.
3. Check backend health with:
   - `curl.exe -s http://localhost/api/status`
4. Inspect targeted service logs if health check fails.

## Notes
This branch intentionally contains only this knowledge summary file.
