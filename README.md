# mcp-vcenter-agent

AI-powered VMware vCenter administration agent with Model Context Protocol (MCP) integration and multi-LLM support for OpenAI, Anthropic, and Gemini.

`mcp-vcenter-agent` is a conversational administration stack for VMware vCenter. It exposes vSphere operations through MCP and pairs them with a multi-provider LLM agent, letting you query inventory, manage VMs, and run common vCenter tasks through natural language. A NiceGUI dashboard provides a chat interface, live inventory tree, model/settings management, and recent task history.

## Features

- MCP server for exposing vCenter tools to MCP-compatible clients.
- Multi-provider LLM agent with Anthropic, OpenAI, Google Gemini, Grok, and Moonshot/Kimi support.
- VMware vCenter automation using `pyVmomi` and `govc`.
- NiceGUI web dashboard with chat, inventory, model settings, and recent tasks.
- FastAPI backend with health checks and REST endpoints.
- Docker Compose deployment with Nginx reverse proxy.
- Safety checks for destructive operations.

## Project Structure

```text
app/
  agent/      Multi-turn agent engine, prompts, safety, and session handling
  llm/        LLM provider adapters and schema utilities
  mcp/        MCP server entry point
  tools/      vCenter, govc, search, and tool registry logic
  ui/         NiceGUI dashboard pages and layout
docker/       Nginx configuration
docs/         Deployment notes
static/       Static dashboard assets
tests/        Tests
```

## Quick Start

1. Clone the repository:

```bash
git clone https://github.com/Achi-456/mcp-vcenter-agent.git
cd mcp-vcenter-agent
```

2. Create your environment file:

```bash
cp .env.example .env
```

3. Edit `.env` and set your vCenter credentials and at least one LLM provider key:

```env
VCENTER_HOST=vcenter.example.com
VCENTER_USER=administrator@vsphere.local
VCENTER_PASSWORD=REPLACE_WITH_YOUR_PASSWORD
ANTHROPIC_API_KEY=REPLACE_WITH_YOUR_KEY
```

4. Start the stack:

```bash
docker compose up --build
```

5. Open the dashboard:

```text
http://localhost/
```

The FastAPI backend is proxied behind Nginx. API documentation is available from the backend at `/docs` when exposed directly.

## Local Development

Create a virtual environment and install dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

On Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Run the FastAPI app locally:

```bash
uvicorn app.main:app --reload --port 8000
```

## MCP Server

Run the MCP server in stdio mode:

```bash
python -m app.mcp.server
```

Example MCP client configuration:

```json
{
  "mcpServers": {
    "vcenter": {
      "command": "python",
      "args": ["-m", "app.mcp.server"],
      "env": {
        "VCENTER_HOST": "vcenter.example.com",
        "VCENTER_USER": "administrator@vsphere.local",
        "VCENTER_PASSWORD": "REPLACE_WITH_YOUR_PASSWORD"
      }
    }
  }
}
```

## Configuration

The main configuration is managed through environment variables. Start from `.env.example` and copy it to `.env`.

Common settings:

- `VCENTER_HOST`, `VCENTER_USER`, `VCENTER_PASSWORD`, `VCENTER_PORT`
- `AGENT_PROVIDER` for selecting the default provider
- `AGENT_MODEL` for selecting a specific model
- `AGENT_MAX_TURNS` and `AGENT_MAX_TOKENS`
- `AGENT_PLANNER`, `AGENT_REFLECTION`, and `AGENT_REVIEWER`
- `AGENT_SESSION_STORE` and `AGENT_SESSION_DB`

## Security Notes

- Do not commit `.env` or real credentials.
- Review destructive actions before approving them.
- Use least-privilege vCenter service accounts where possible.
- Lock down CORS and network exposure before production use.

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.
