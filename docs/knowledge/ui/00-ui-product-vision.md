# AgenticOps UI Product Vision

Product name: AgenticOps Console

AgenticOps is a professional vCenter-style infrastructure operations console with AI-assisted diagnostics. It should feel like vCenter plus Aria Operations plus an AI Assistant: reliable, calm, structured, and operationally useful.

The preferred first theme is a light enterprise operations theme. Avoid a cyberpunk, flashy, or overly dark visual direction.

The UI should help an operator quickly answer:
- Is the platform healthy?
- What is happening in vCenter?
- What did the agent inspect?
- Which tools are available, blocked, or read-only?
- What evidence supports the final answer?

Primary users:
- vSphere administrators
- platform engineers
- infrastructure operators
- SREs supporting the lab cluster

Product principles:
- Prioritize clarity over visual noise.
- Make safety state visible before tool results.
- Hide raw JSON by default, but make evidence inspectable.
- Keep read-only checks distinct from blocked or approval-required actions.
- Use concise tables and status cards for operational data.
- Keep previous data visible while refreshing when practical.
- Do not show fake success data or blank cards when an endpoint fails.
- Never expose secrets, internal tokens, API keys, or passwords.

Version 1 UI scope:
- Dashboard and system health
- Agent chat with SSE event rendering
- Inventory views for VMs, hosts, and datastores
- Diagnostics pages for pyVmomi, govc, vSphere REST, and safe MCP status tools
- Tool registry browser
- Settings and sessions scaffolds

Version 1 backend capabilities already available:
- pyVmomi read-only inventory and context endpoints
- govc read-only diagnostic endpoints
- vSphere REST read-only diagnostic endpoints
- safe MCP status tools through Agent Engine chat only
- Tool Registry governance metadata
- health and service status endpoints

Out of scope for the first UI rebuild:
- Destructive operation UI
- Approval workflow UI
- Kubernetes CSI/CNS/govmomi workflows
- Frontend direct MCP access
- Secret editing in the browser
- Raw arbitrary MCP execution
- Raw govc command execution
