# LangGraph Chatbot with Remote Agent Skills (MCP Server)

A minimal chatbot built with [LangGraph](https://langchain-ai.github.io/langgraph/) that fetches and invokes tools from a remote MCP (Model Context Protocol) server, served as a hosted agent via the Azure AI Agent Server.

## Overview

This sample demonstrates:

- Connecting to a **remote MCP server** to dynamically discover and use tools (skills)
- Building a **LangGraph** agent graph with tool-calling capabilities
- Using **Azure OpenAI** (GPT-4o) as the underlying LLM with Azure AD authentication
- Exposing the agent as an HTTP endpoint using `azure-ai-agentserver-langgraph`

## Architecture

```
User ──► Agent Server (localhost:8088) ──► LangGraph ──► Azure OpenAI (GPT-4o)
                                                │
                                                ▼
                                         Remote MCP Server
                                        (streamable_http)
```

## Prerequisites

- Python 3.10+
- An Azure OpenAI deployment (GPT-4o recommended)
- Azure credentials configured for `DefaultAzureCredential` (e.g. `az login`)

## Setup

1. **Create and activate a virtual environment:**

   ```bash
   python -m venv .venv
   # Windows
   .venv\Scripts\Activate.ps1
   # Linux/macOS
   source .venv/bin/activate
   ```

2. **Install dependencies:**

   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment variables:**

   Create a `.env` file in the project root:

   ```env
   AZURE_OPENAI_ENDPOINT=https://<your-resource>.openai.azure.com/
   AZURE_OPENAI_DEPLOYMENT=gpt-4o
   AZURE_OPENAI_API_VERSION=2024-12-01-preview
   ```

## Running

Start the agent server:

```bash
python chatbot_hosted_agent_remote_skill.py
```

The server starts on `http://localhost:8088` by default.

## Testing

Send a request to the agent:

```powershell
curl -X POST http://localhost:8088/responses `
  -H "Content-Type: application/json" `
  -d '{
    "agent": {
      "name": "local_agent",
      "type": "agent_reference"
    },
    "stream": false,
    "input": "Hi my name is John. Greet me in Spanish"
  }'
```

## How It Works

1. **MCP Tool Discovery** — On startup, `MultiServerMCPClient` connects to the remote MCP server and fetches available tools.
2. **Graph Construction** — A LangGraph `StateGraph` is built with a chatbot node (LLM) and a tools node, connected with conditional edges so the LLM can decide when to call tools.
3. **Agent Server** — The compiled graph is wrapped with `from_langgraph()` and served as an HTTP endpoint that accepts the OpenAI-compatible `/responses` API format.

## Dependencies

| Package | Purpose |
|---|---|
| `langgraph` | Agent graph orchestration |
| `langchain-openai` | Azure OpenAI LLM integration |
| `langchain-mcp-adapters` | MCP client for remote tool discovery |
| `azure-ai-agentserver-langgraph` | Serve the LangGraph agent as an HTTP endpoint |
| `azure-identity` | Azure AD authentication |
| `python-dotenv` | Load environment variables from `.env` |
