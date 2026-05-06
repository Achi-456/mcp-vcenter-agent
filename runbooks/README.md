# RKE2 Lab Runbooks

These files are written for manual copy/paste execution from Windows PowerShell.

Run order:

1. [Phase 00 - Inventory And Access](PHASE-00-INVENTORY-AND-ACCESS.md)
2. [Phase 01 - OS Prep On All Nodes](PHASE-01-OS-PREP-ALL-NODES.md)
3. [Phase 02 - RKE2 Control Plane Bootstrap](PHASE-02-RKE2-CONTROL-PLANE.md)
4. [Phase 03 - Join RKE2 Agent Nodes](PHASE-03-ADD-WORKERS.md)
5. [Phase 04 - Cluster Foundation](PHASE-04-POST-BOOTSTRAP-NOTES.md)
6. [Phase 05 - Argo CD GitOps Nerve Centre](PHASE-05-ARGOCD-GITOPS.md)
7. [Phase 06 - Data Layer](PHASE-06-DATA-LAYER.md)
8. [Phase 07 - App Layer](PHASE-07-APP-LAYER.md)
9. [Phase 08 - Code Scaffold, CI, And First Real Images](PHASE-08-CODE-SCAFFOLD-CI.md)
10. [Phase 09 - GitOps Adoption](PHASE-09-GITOPS-ADOPTION.md)

Lab defaults:

```text
Domain:  dclab.local
Gateway: 172.25.188.1
DNS:     172.25.188.20
SSH key: C:\Users\achinthah\.ssh\hybrid-cloud-idp
RKE2:    v1.35.3+rke2r3
```
