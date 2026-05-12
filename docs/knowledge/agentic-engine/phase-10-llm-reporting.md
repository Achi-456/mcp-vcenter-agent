# Phase 10 - LLM Assisted Troubleshooting Reports

## 1. Objective

Phase 10 improves final answers from shallow tool summaries into infrastructure-engineer style troubleshooting reports.

Current agent behavior is evidence collection plus deterministic formatting. For a prompt like:

```text
anything wrong in vCenter?
```

the current answer may look like:

```text
environment overview ok
datastore health ok
active alarms ok
recent events ok
No action was taken.
```

The target answer should read like an operational report:

```markdown
## Issue Summary

I checked the vCenter environment, datastore health, active alarms, and recent events.

The main concern is storage pressure. The environment has 25 datastores, and 10 are currently in a critical state. There are also 35 active alarms, so the next priority should be to review alarms that are attached to those critical datastores or affected VMs.

## Evidence Collected

| Source | Finding |
|---|---|
| Environment Overview | 292 VMs, 2 hosts, 25 datastores |
| Datastore Health | 10 critical datastores found |
| Active Alarms | 35 active alarms found |
| Recent Events | 50 events reviewed |

## Probable Root Cause

The strongest signal is datastore capacity pressure. This may be caused by VM growth, ISO/log accumulation, old snapshots, backup files, or orphaned VMDKs.

## Confidence Level

Medium - the current evidence shows datastore pressure and alarms, but datastore file inspection and alarm scope review are needed to confirm the root cause.

## Recommended Next Checks

1. Review the top critical datastores.
2. Check related active alarms.
3. Search datastore folders for large `.vmdk`, `.iso`, `.log`, and snapshot delta files when datastore file search is available.
4. Review recent events for affected VMs.

## Suggested Fix

Do not delete files directly. First identify the file owner and confirm whether snapshots, ISO files, or orphaned disks are contributing to usage.

## Risk Level

Read-only investigation completed. Any cleanup or deletion would require approval.

## Approval Required?

No approval was required for this investigation.

## Sources

- vCenter environment overview
- vCenter datastore health
- vCenter active alarms
- vCenter recent events

## Actions Taken

No action was taken.
```

## 2. Design Principle

Phase 10 must not weaken the current safety model.

The LLM may:

- summarize
- reason
- explain
- prioritize
- write reports
- review report quality

The LLM must not:

- execute tools directly
- call raw govc
- call shell
- call pyVmomi directly
- call MCP directly
- bypass ToolRegistry
- bypass PolicyService
- bypass AuditService

Correct flow:

```text
User
  -> deterministic intent/router/safety
  -> existing tool execution
  -> tool results collected
  -> LLM Report Writer
  -> LLM Reviewer
  -> final answer
```

Rejected flow:

```text
User
  -> LLM autonomously chooses and executes arbitrary tools
```

## 3. Scope

### In Scope

- LLM provider abstraction
- OpenAI provider implementation first
- LLM report writer node
- LLM reviewer node
- deterministic fallback
- prompt templates
- structured report output
- secret-based API key configuration
- LLM health/status visibility
- tests

### Out of Scope

- web search
- VMware KB search
- memory/RAG
- pgvector
- autonomous planner
- new infrastructure tools
- datastore file search
- VM creation/cloning
- approval workflow execution
- direct LLM tool execution
- UI redesign

## 4. Recommended Subphases

### Phase 10A - LLM Provider Foundation

Goal: create a safe provider abstraction.

Files likely to create:

```text
apps/engine/app/llm/base.py
apps/engine/app/llm/openai_provider.py
apps/engine/app/llm/prompts.py
apps/engine/app/llm/schemas.py
apps/engine/app/llm/factory.py
```

Engine configuration:

```env
LLM_ENABLED=true|false
LLM_PROVIDER=openai
LLM_MODEL=<model-name>
OPENAI_API_KEY=<from Kubernetes Secret>
LLM_TIMEOUT_SECONDS=30
LLM_MAX_INPUT_CHARS=60000
LLM_TEMPERATURE=0.2
LLM_REPORT_WRITER_ENABLED=true|false
LLM_REVIEWER_ENABLED=true|false
```

Kubernetes Secret:

```text
agentic-llm-provider
  OPENAI_API_KEY=...
```

Rules:

- Do not store raw API keys in Postgres.
- Do not log API keys.
- Do not expose API keys in UI.

### Phase 10B - LLM Report Writer

Goal: use the LLM only after tools have already executed.

Input to LLM:

```json
{
  "user_message": "...",
  "intent": {},
  "safety": {},
  "tool_calls": [],
  "tool_results_summary": [],
  "tool_results_json": {},
  "allowed_actions": "read-only only",
  "report_format": "standard troubleshooting report"
}
```

Output:

```markdown
## Issue Summary
...
## Evidence Collected
...
## Probable Root Cause
...
## Confidence Level
...
## Recommended Next Checks
...
## Suggested Fix
...
## Risk Level
...
## Approval Required?
...
## Sources
...
## Actions Taken
No action was taken.
```

### Phase 10C - LLM Reviewer

Goal: validate the LLM report before sending it to the user.

Reviewer checks:

- Did the report use only provided tool evidence?
- Did it invent values?
- Did it include unsafe instructions?
- Did it include `No action was taken.`?
- Did it clearly mark missing or unavailable data?
- Did it give a confidence level?
- Did it mention approval if suggesting risky fixes?

Reviewer output:

```json
{
  "passed": true,
  "issues": [],
  "safe_to_return": true,
  "fallback_required": false
}
```

If the reviewer fails, use the deterministic fallback report.

### Phase 10D - Deterministic Fallback

LLM generation may fail because:

- no API key
- provider timeout
- provider error
- token/input limit
- reviewer failure

Fallback behavior:

- Use the existing deterministic report formatter.
- Show a clean answer, not an LLM stack trace.
- Do not expose raw exception details or API key errors to the user.

## 5. Updated LangGraph Flow

Current simplified flow:

```text
START
-> intent_router
-> safety_agent
-> route_by_intent
-> vcenter/govc/rest/mcp agent
-> validation_agent
-> report_agent
-> END
```

Phase 10 flow:

```text
START
-> intent_router
-> safety_agent
-> route_by_intent
-> specialist/tool agent
-> validation_agent
-> deterministic_report_agent
-> llm_report_writer_agent
-> llm_reviewer_agent
-> final_response_selector
-> END
```

`final_response_selector` rule:

```text
if LLM enabled and reviewer passed:
    use LLM report
else:
    use deterministic report
```

## 6. Standard Report Format

Every troubleshooting LLM report must follow this exact structure:

```markdown
## Issue Summary

## Evidence Collected

## Probable Root Cause

## Confidence Level

## Recommended Next Checks

## Suggested Fix

## Risk Level

## Approval Required?

## Sources

## Actions Taken
No action was taken.
```

For simple requests like `show tags` or `test MCP`, the LLM may use a shorter format.

Recommended rule:

- Use the full report for troubleshooting, `health_summary`, compare, alarm, datastore, host, VM issue, and similar diagnostic prompts.
- Use a concise answer for simple inventory, list, and info prompts.

## 7. Prompt Design

### Report Writer System Prompt

```text
You are an expert VMware vCenter infrastructure troubleshooting assistant.

You write clear operational reports using only the evidence provided by backend tools.

Rules:
- Use only the provided tool results.
- Do not invent values.
- If data is missing, say it is unavailable.
- Never claim that an action was executed unless tool results show it.
- Do not recommend destructive operations as direct actions.
- If a fix may change infrastructure, state that approval is required.
- Always include "No action was taken." in the Actions Taken section unless an approved write action result is explicitly provided.
- Prefer concise tables for evidence.
- For VMware/vCenter issues, explain likely causes and safe next checks.
- Do not expose secrets, tokens, passwords, API keys, or internal headers.
```

### Report Writer User Prompt Template

```text
User request:
{user_message}

Intent:
{intent_json}

Safety:
{safety_json}

Tool calls:
{tool_calls_json}

Tool results:
{tool_results_json}

Current deterministic answer:
{deterministic_answer}

Write the final answer in this format:
## Issue Summary
## Evidence Collected
## Probable Root Cause
## Confidence Level
## Recommended Next Checks
## Suggested Fix
## Risk Level
## Approval Required?
## Sources
## Actions Taken
```

### Reviewer System Prompt

```text
You are a safety and accuracy reviewer for a VMware infrastructure assistant.

Review the proposed final answer against the provided evidence.

Rules:
- Fail if the answer invents data not present in evidence.
- Fail if it says an action was taken when no approved action result exists.
- Fail if it gives unsafe destructive instructions without approval.
- Fail if it exposes secrets or tokens.
- Fail if "No action was taken." is missing for read-only investigations.
- Pass if the answer is evidence-grounded, safe, and clear.

Reviewer should return JSON only:

{
  "passed": true,
  "safe_to_return": true,
  "issues": [],
  "fallback_required": false
}
```

## 8. AgentState Additions

Extend `AgentState` with:

```python
llm_enabled: bool
llm_provider: str | None
llm_model: str | None
deterministic_answer: str | None
llm_report: str | None
llm_review: dict | None
llm_used: bool
llm_error: str | None
final_answer_source: Literal["llm", "deterministic"]
```

SSE events can stay unchanged for Phase 10 to avoid frontend work.

Recommended mapping:

- `agent_start` can emit `llm_report_writer_agent` when the LLM report writer runs.
- `validation` can include reviewer status when available.
- `final` should contain the selected final answer.

Optional later event types:

- `llm_start`
- `llm_review`

Do not add new SSE event types in Phase 10 unless necessary.

## 9. Configuration and Secrets

Engine environment:

```env
LLM_ENABLED=false
LLM_PROVIDER=openai
LLM_MODEL=gpt-5.4-mini
LLM_TIMEOUT_SECONDS=30
LLM_REPORT_WRITER_ENABLED=true
LLM_REVIEWER_ENABLED=true
OPENAI_API_KEY=<secret>
```

OpenAI SDKs commonly read `OPENAI_API_KEY` from the environment, which fits the Kubernetes Secret pattern.

Kubernetes Secret:

```powershell
kubectl create secret generic agentic-llm-provider `
  -n agentic-agents `
  --from-literal=OPENAI_API_KEY="..."
```

Do not commit secrets.

Agent Engine deployment environment:

```yaml
- name: LLM_ENABLED
  value: "true"
- name: LLM_PROVIDER
  value: "openai"
- name: LLM_MODEL
  value: "gpt-5.4-mini"
- name: OPENAI_API_KEY
  valueFrom:
    secretKeyRef:
      name: agentic-llm-provider
      key: OPENAI_API_KEY
```

Use the model name the account has access to.

## 10. Error Handling

If API key is missing:

- Mark LLM as disabled or unconfigured.
- Use deterministic report.

If timeout occurs:

- Mark LLM report generation as timed out.
- Use deterministic report.

If reviewer fails:

- Use deterministic report.

If LLM returns invalid output:

- Use deterministic report.

Users must not see:

- Python stack traces
- OpenAI API key error details
- raw exceptions

## 11. Audit and Metadata

For Phase 10, store safe metadata in existing run metadata if possible:

```json
{
  "llm_used": true,
  "provider": "openai",
  "model": "configured-model",
  "llm_report_status": "success",
  "reviewer_passed": true,
  "final_answer_source": "llm"
}
```

Do not audit full prompts if they may include sensitive tool data unless a redaction layer is added first.

Safe audit summary:

```json
{
  "llm_used": true,
  "provider": "openai",
  "model": "configured-model",
  "reviewer_passed": true,
  "final_answer_source": "llm"
}
```

## 12. Tests

### Provider Tests

1. LLM disabled returns deterministic fallback.
2. Missing API key disables LLM cleanly.
3. Provider timeout returns deterministic fallback.
4. Provider error returns deterministic fallback.
5. API key is never logged.

### Report Writer Tests

1. Given VM details result, LLM writer is called with summarized evidence.
2. Given `health_summary` result, LLM writer is called after tools complete.
3. LLM output becomes final only if reviewer passes.
4. If reviewer fails, deterministic answer is used.
5. `No action was taken.` is enforced.

### Reviewer Tests

1. Reviewer passes safe grounded answer.
2. Reviewer fails answer with invented action.
3. Reviewer fails answer missing `No action was taken.`
4. Reviewer fails unsafe destructive recommendation.

### Regression Tests

1. Existing deterministic routing still works.
2. Existing pyVmomi prompt still works.
3. Existing govc prompt still works.
4. Existing REST prompt still works.
5. Existing MCP prompt still works.
6. Existing safety block still works.
7. No direct LLM tool execution exists.

## 13. UI Impact

Phase 10 can be mostly engine-only.

The existing frontend should still work because the `final` SSE event still contains a Markdown answer.

Optional UI improvement later:

```text
Answer generated by LLM
Deterministic fallback used
```

This badge is not required for Phase 10.

## 14. Security Boundaries

Strict rules:

- LLM does not execute tools.
- LLM does not choose raw tool arguments for execution in Phase 10.
- LLM only receives already collected evidence.
- Tool execution remains deterministic.
- Safety gate remains before tools.
- Approval workflow is not implemented yet.
- No secrets in prompts if avoidable.
- Raw tokens and passwords must be redacted before sending evidence to LLM.

## 15. Files Likely to Change

Engine:

```text
apps/engine/requirements.txt
apps/engine/app/core/config.py
apps/engine/app/graph/state.py
apps/engine/app/graph/workflow.py
apps/engine/app/graph/reporting.py
apps/engine/app/llm/base.py
apps/engine/app/llm/factory.py
apps/engine/app/llm/openai_provider.py
apps/engine/app/llm/prompts.py
apps/engine/app/llm/schemas.py
apps/engine/tests/*
```

Kubernetes later:

```text
k8s/apps/agentic-agents/configmap.yaml
k8s/apps/agentic-agents/deployment.yaml
```

Kubernetes changes should happen only after local validation.
