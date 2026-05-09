# AgenticOps Agentic Flow Knowledge Note

## Purpose

This document is for the `knowledge/` folder so Codex can understand the intended agentic architecture for the vCenter Agentic Ops Platform.

The goal is to build a structured Agent Engine that can safely handle a large toolset:

- pyVmomi tools
- govc read-only tools
- govmomi CNS/CSI tools
- vSphere REST API tools
- Kubernetes/RKE2 tools
- CSI VA check tools
- monitoring tools
- GitOps tools
- security/VA tools
- documentation/RAG tools

The key idea is:

```text
Use LangGraph for orchestration and control flow.
Use LangChain for LLM, prompt, tool, parser, and RAG building blocks.
Use MCP to expose external tool servers.
Use FastAPI as the backend/API gateway.
Use Next.js as the frontend UI.
```

---

# 1. Core Design Principle

Do **not** build one chatbot with 100 tools exposed directly to one LLM.

That creates tool confusion, wrong routing, and unsafe decisions.

Bad pattern:

```text
User prompt
  ↓
Single LLM agent
  ↓
All tools available
  ↓
Wrong tool selection / unsafe action risk
```

Correct pattern:

```text
User prompt
  ↓
Intent Router
  ↓
Safety Gate
  ↓
Supervisor / Planner
  ↓
Specialist Agents with small toolsets
  ↓
Correlation Agent
  ↓
Validation Agent
  ↓
Report Agent
  ↓
Final answer + visible tool trace
```

The LLM should not directly see every tool. The supervisor should select the correct specialist agent. Each specialist agent should only see its own relevant tool group.

---

# 2. LangGraph and LangChain Roles

## LangGraph

LangGraph is the **control-flow engine**.

Use LangGraph for:

```text
- multi-step workflows
- multi-agent routing
- safety gates
- retries
- validation steps
- checkpointing
- long-running tasks
- deterministic task execution
- state management
- specialist agent orchestration
```

LangGraph should decide:

```text
What step runs next?
Which agent should run?
Should the workflow continue or stop?
Did the safety check pass?
Did validation pass?
Should we retry a failed tool?
```

## LangChain

LangChain is the **LLM/tool utility layer**.

Use LangChain for:

```text
- LLM provider wrappers
- prompt templates
- tool definitions
- structured output parsers
- retrievers / RAG
- embeddings
- document loaders
- report generation chains
- validation chains
```

LangChain should help each LangGraph node do its task.

Example:

```text
LangGraph node: intent_router
  uses LangChain prompt + structured output parser

LangGraph node: report_agent
  uses LangChain prompt template + selected LLM provider
```

## Relationship

```text
LangGraph = engine brain / traffic controller
LangChain = LLM, prompt, parser, RAG, and tool utility layer
MCP = external tool exposure layer
FastAPI = platform API gateway
Next.js = UI
```

---

# 3. Recommended High-Level Architecture

```text
User
 ↓
Next.js AI Assistant Panel
 ↓
FastAPI /api/v1/chat/stream
 ↓
Agent Engine
 ↓
LangGraph Workflow
 ↓
Specialist Agents
 ↓
Tool Registry / MCP / Backend APIs
 ↓
pyVmomi / govc / govmomi / vSphere REST / Kubernetes API
 ↓
Tool Results
 ↓
Correlation + Validation + Report
 ↓
SSE Events back to UI
```

---

# 4. AgenticOps Agent Groups

The Agent Engine should use specialist agents.

## 4.1 Intent Router

First node in the graph.

Responsibilities:

```text
Detect domain:
- vCenter
- Kubernetes
- CSI
- GitOps
- Monitoring
- Security
- Documentation / RAG
- General

Detect object type:
- VM
- ESXi host
- datastore
- cluster
- network
- PVC
- PV
- StorageClass
- pod
- ArgoCD app

Detect task type:
- get details
- list
- health check
- validation assessment
- troubleshoot
- report generation
- risky operation
```

Example output:

```json
{
  "domain": "vcenter",
  "object_type": "host",
  "task_type": "get_details",
  "entity": "esxi01.dclab.com",
  "risk_level": "read_only"
}
```

This prevents mistakes such as routing `esxi01.dclab.com` to `get_vm_details`.

---

## 4.2 Safety Agent

Runs before any infrastructure tool.

Risk levels:

```text
read_only
low_risk
approval_required
destructive
```

Examples:

```text
show VM details            → read_only
list datastores            → read_only
run CSI VA check           → read_only
power on VM                → approval_required
delete VM                  → destructive
enter maintenance mode     → approval_required
delete CNS volume          → destructive
```

Current phase rule:

```text
Only read_only tools execute automatically.
All approval_required and destructive tools must be blocked.
```

---

## 4.3 Planner Agent

Creates an execution plan.

For example, for CSI VA Check:

```text
1. Check CSI pods
2. Check CSIDriver objects
3. Check StorageClasses
4. Check PVCs
5. Check PVs
6. Check VolumeAttachments
7. Check datastore health
8. Check storage alarms/events
9. Correlate findings
10. Generate report
```

The planner should emit a `plan` SSE event so the UI can show a PlanCard.

---

## 4.4 vCenter pyVmomi Agent

Primary vCenter inventory and monitoring agent.

Tools:

```text
list_vms
get_vm_details
list_hosts
get_host_details
list_clusters
list_datastores
get_datastore_health
list_networks
get_active_alarms
get_recent_events
get_rke2_vms
```

Use this agent for normal vCenter facts.

---

## 4.5 govc Diagnostic Agent

Read-only fallback/debug agent.

Tools:

```text
govc_about
govc_vm_info
govc_host_info
govc_datastore_info
govc_events
govc_volume_ls
```

Use only when:

```text
- pyVmomi output is incomplete
- CNS/volume investigation is needed
- debug verification is requested
```

Important:

```text
Do not expose raw free-form govc_command.
Only expose whitelisted read-only govc tools.
```

---

## 4.6 govmomi CNS Agent

Go-based specialist for CNS/CSI.

Tools:

```text
govmomi_list_cns_volumes
govmomi_get_cns_volume_details
govmomi_map_pv_to_cns_volume
govmomi_map_cns_volume_to_datastore
govmomi_list_storage_policies
govmomi_validate_storage_policy_mapping
```

Use this agent for CSI VA Check and CNS/PBM mapping.

---

## 4.7 vSphere REST Agent

REST/Automation API specialist.

Tools:

```text
vsphere_rest_list_tags
vsphere_rest_find_objects_by_tag
vsphere_rest_list_content_libraries
vsphere_rest_list_recent_tasks
vsphere_rest_get_appliance_health
```

Use this for:

```text
- tags
- categories
- content libraries
- templates
- recent tasks
- vCenter appliance health
```

---

## 4.8 Kubernetes CSI Agent

Kubernetes-side storage specialist.

Tools:

```text
list_csi_pods
check_csi_pods_health
list_storage_classes
list_pvcs
find_pending_pvcs
list_pvs
list_volume_attachments
find_stuck_volume_attachments
get_k8s_storage_events
```

Use this for:

```text
Run CSI VA check
Check PVC health
Check vSphere CSI health
Check Kubernetes storage
```

---

## 4.9 Monitoring Agent

Observability/evidence agent.

Tools:

```text
get_active_alarms
get_recent_events
query_prometheus_metric
get_loki_logs
get_storage_related_events
```

Use this agent to find supporting evidence.

---

## 4.10 Correlation Agent

Combines tool results into meaningful findings.

Example correlation:

```text
PVC pending
+ StorageClass uses vSphere CSI
+ datastore above 95%
+ storage alarm exists
= likely datastore capacity pressure
```

This agent should mostly analyze collected data. It should not call many tools.

---

## 4.11 Validation Agent

Checks completeness before final answer.

For CSI VA Check, verify:

```text
CSI pods checked?
StorageClasses checked?
PVC/PV checked?
VolumeAttachments checked?
Datastores checked?
Alarms/events checked?
Findings generated?
No destructive action executed?
```

If incomplete, mark the assessment as incomplete instead of pretending it is complete.

---

## 4.12 Report Agent

Generates final answer.

Report format:

```text
Summary
Overall Status
Evidence
Findings
Recommended Next Steps
Open Questions
No action was taken
```

---

# 5. Recommended LangGraph Workflows

## 5.1 General Chat Workflow

Use this for simple questions.

```text
START
 ↓
intent_router
 ↓
safety_agent
 ↓
route_by_task_type
 ↓
specialist_agent
 ↓
validation_agent
 ↓
report_agent
 ↓
END
```

Example:

```text
User: get details for esxi01.dclab.com

intent_router:
  domain = vcenter
  object_type = host
  task_type = get_details
  entity = esxi01.dclab.com

safety_agent:
  read_only allowed

vcenter_pyvmomi_agent:
  get_host_details

validation_agent:
  confirms real host result

report_agent:
  final host details answer
```

---

## 5.2 Long Assessment Workflow

Use this for critical/long tasks such as CSI VA Check.

```text
START
 ↓
intent_router
 ↓
safety_agent
 ↓
planner_agent
 ↓
parallel_collection
   ├── kubernetes_csi_agent
   ├── vcenter_pyvmomi_agent
   ├── govmomi_cns_agent
   └── monitoring_agent
 ↓
correlation_agent
 ↓
validation_agent
 ↓
report_agent
 ↓
END
```

This should be mostly deterministic.

Do not use fully free-form agent discussion for critical infrastructure checks.

---

## 5.3 Debug/Fallback Workflow

Use when the user asks to verify, or when the primary tool fails.

```text
START
 ↓
intent_router
 ↓
safety_agent
 ↓
primary_tool_agent
 ↓
if incomplete/failure:
      govc_diagnostic_agent
 ↓
compare_results
 ↓
report_agent
 ↓
END
```

Example:

```text
get details for esxi01.dclab.com
```

Primary:

```text
pyVmomi get_host_details
```

Fallback:

```text
govc_host_info
```

Final answer:

```text
Primary pyVmomi failed, govc fallback succeeded.
```

---

## 5.4 Future Approval Workflow

For risky operations later.

```text
START
 ↓
intent_router
 ↓
safety_agent
 ↓
if approval_required:
      approval_gate
 ↓
if approved:
      execute_action
 ↓
audit_report
 ↓
END
```

Current phase:

```text
All write/destructive tools are blocked.
```

---

# 6. Tool Registry Design

Use a central registry, but expose tools by scope.

Example ToolSpec:

```json
{
  "name": "get_host_details",
  "display_name": "Get Host Details",
  "backend": "pyvmomi",
  "agent": "vcenter_pyvmomi_agent",
  "category": "Inventory",
  "risk_level": "read_only",
  "enabled": true,
  "implemented": true,
  "requires_approval": false,
  "input_schema": {
    "host_name": "string"
  }
}
```

Risk levels:

```text
read_only
low_risk
approval_required
destructive
```

Registry helper functions:

```text
get_tools_for_agent("vcenter_pyvmomi_agent")
get_tools_by_risk("read_only")
get_tools_by_domain("csi")
get_enabled_tools()
```

Important:

```text
The supervisor should never pass all tools to one LLM.
```

---

# 7. Tool Routing Design

## Domain routing

```text
vCenter prompt       → vCenter pyVmomi Agent
ESXi host prompt     → vCenter pyVmomi Agent
CSI/PVC/PV prompt    → Kubernetes CSI Agent
CNS volume prompt    → govmomi CNS Agent
Datastore prompt     → Storage/vCenter Agent
Tag/template prompt  → vSphere REST Agent
Debug fallback       → govc Diagnostic Agent
```

## Object routing examples

```text
esxi01.dclab.com
  → object_type = host
  → get_host_details

roshellevm02
  → object_type = vm
  → get_vm_details

pvc-abc123
  → object_type = pvc
  → get_pvc_details

datastore01
  → object_type = datastore
  → get_datastore_details
```

---

# 8. Graph State Design

The graph state should include all important data.

```python
class AgentState(TypedDict):
    session_id: str
    run_id: str
    user_message: str

    domain: str
    task_type: str
    object_type: str | None
    entity: str | None
    risk_level: str
    allowed: bool

    plan: list[dict]
    selected_agents: list[str]

    tool_events: list[dict]
    pyvmomi_results: dict
    govc_results: dict
    govmomi_results: dict
    rest_results: dict
    k8s_results: dict
    monitoring_results: dict

    findings: list[dict]
    validation: dict
    final_answer: str
    errors: list[dict]
```

This makes the task auditable, resumable, and easier to debug.

---

# 9. SSE Events for UI

The UI should show every important step.

Recommended event types:

```text
start
intent
safety_check
plan
agent_start
tool_call
tool_result
finding
agent_done
validation
final
error
done
```

Example:

```text
event: intent
data: {"domain":"csi","task_type":"va_check","risk_level":"read_only"}

event: agent_start
data: {"agent":"kubernetes_csi_agent"}

event: tool_call
data: {"agent":"kubernetes_csi_agent","tool":"find_pending_pvcs"}

event: tool_result
data: {"tool":"find_pending_pvcs","summary":"2 pending PVCs found"}

event: finding
data: {"severity":"warning","title":"Pending PVCs detected"}

event: final
data: {"content":"CSI VA Check Summary..."}

event: done
data: {}
```

---

# 10. Execution Modes

## Quick Mode

For simple questions.

Example:

```text
get details for esxi01.dclab.com
```

Flow:

```text
intent → safety → vCenter Agent → validation → report
```

## Assessment Mode

For long checks.

Example:

```text
Run CSI VA check
```

Flow:

```text
intent → safety → planner → multiple agents → correlation → validation → report
```

## Debug Mode

For verification/fallback.

Example:

```text
verify with govc
```

Flow:

```text
primary pyVmomi result → govc diagnostic agent → compare → report
```

## Future Approval Mode

For risky operations.

Example:

```text
power on VM
```

Flow:

```text
intent → safety → approval gate → human approval → execute → audit report
```

Current phase:

```text
Block all write operations.
```

---

# 11. Recommended Folder Structure

```text
apps/engine/app/
├── graph/
│   ├── state.py
│   ├── router.py
│   ├── workflow.py
│   ├── csi_va_workflow.py
│   └── events.py
│
├── chains/
│   ├── intent_chain.py
│   ├── planner_chain.py
│   ├── report_chain.py
│   └── validation_chain.py
│
├── agents/
│   ├── intent_router.py
│   ├── safety_agent.py
│   ├── planner_agent.py
│   ├── vcenter_pyvmomi_agent.py
│   ├── govc_diagnostic_agent.py
│   ├── govmomi_cns_agent.py
│   ├── vsphere_rest_agent.py
│   ├── kubernetes_csi_agent.py
│   ├── monitoring_agent.py
│   ├── correlation_agent.py
│   ├── validation_agent.py
│   └── report_agent.py
│
├── tools/
│   ├── registry.py
│   ├── schemas.py
│   ├── pyvmomi_tools.py
│   ├── govc_tools.py
│   ├── govmomi_tools.py
│   ├── vsphere_rest_tools.py
│   ├── k8s_tools.py
│   └── monitoring_tools.py
│
├── policies/
│   ├── risk_policy.py
│   ├── approval_policy.py
│   └── tool_policy.py
│
└── memory/
    ├── checkpoints.py
    ├── redis_cache.py
    └── session_store.py
```

---

# 12. Recommended Build Order

Do not implement everything at once.

```text
Step 1 — Tool registry v2
Add backend, agent, risk, category, schemas.

Step 2 — Intent router v2
Domain + object + task classification.

Step 3 — Safety gate
Block all non-read-only tools.

Step 4 — Specialist agents
Start with:
- vCenter pyVmomi Agent
- Kubernetes CSI Agent
- govc Diagnostic Agent

Step 5 — CSI VA workflow
Use deterministic graph.

Step 6 — Correlation + validation
Make reports trustworthy.

Step 7 — govmomi CNS Agent
Add CNS volume mapping.

Step 8 — vSphere REST Agent
Add tags/content library/tasks.
```

---

# 13. Critical Design Rules

```text
1. Never expose all tools to one LLM.
2. Always classify domain/object/task first.
3. Always run safety before tools.
4. Use deterministic workflows for long tasks.
5. Use specialist agents with small toolsets.
6. Use validation before final answer.
7. Keep tool traces visible.
8. Do not cache failed auth/tool errors.
9. Never show fake success tables.
10. Keep write/destructive tools disabled until approval workflow.
```

---

# 14. Architecture Summary

Recommended architecture name:

```text
AgenticOps Tool-Orchestrated Infrastructure Engine
```

Core pattern:

```text
Supervisor-Routed Specialist Agents with Deterministic Assessment Workflows
```

Meaning:

```text
Chat for interaction
LangGraph for control
LangChain for prompts/tools/parsers/RAG
MCP for tool exposure
FastAPI for backend APIs
pyVmomi/govc/govmomi/vSphere REST/Kubernetes APIs for real infrastructure tools
Validation/report agents for trust
```

---

# 15. Codex Implementation Prompt

Use this prompt with Codex when implementing the architecture.

```text
You are working on the AgenticOps vCenter Agentic Ops Platform.

Create the next version of the Agent Engine based on this knowledge document.

Core architecture:
- LangGraph is the orchestration/control-flow layer.
- LangChain is the LLM/prompt/tool/parser/RAG utility layer.
- MCP exposes external tool servers.
- FastAPI is the backend/API gateway.
- Next.js is the frontend.

Do not expose all tools to one LLM.

Implement a supervisor-routed specialist-agent architecture:
1. Intent Router
2. Safety Agent
3. Planner Agent
4. vCenter pyVmomi Agent
5. govc Diagnostic Agent
6. govmomi CNS Agent
7. vSphere REST Agent
8. Kubernetes CSI Agent
9. Monitoring Agent
10. Correlation Agent
11. Validation Agent
12. Report Agent

Start with:
- Tool registry v2
- Intent router v2
- Safety gate
- vCenter pyVmomi Agent
- Kubernetes CSI Agent
- govc Diagnostic Agent
- deterministic CSI VA workflow

Requirements:
- Only read_only tools execute automatically.
- approval_required and destructive tools must be blocked.
- Use specialist toolsets.
- Emit SSE events for intent, safety_check, plan, agent_start, tool_call, tool_result, finding, validation, final, error, done.
- Use validation before final answer.
- Never show fake success tables.
- Do not cache failed auth/tool errors.

Folder structure:
apps/engine/app/graph/
apps/engine/app/chains/
apps/engine/app/agents/
apps/engine/app/tools/
apps/engine/app/policies/
apps/engine/app/memory/

Expected first workflows:
1. General vCenter details workflow
2. CSI VA Check workflow
3. govc fallback/debug workflow
```
