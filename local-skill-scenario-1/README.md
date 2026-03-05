# LangGraph Chatbot with Agent Skills

A simple chatbot using [LangGraph](https://langchain-ai.github.io/langgraph/) and Azure AI Foundry OpenAI that implements the [Agent Skills](https://agentskills.io) open standard. It shows how skills can be integrated today using existing Foundry capabilities — no new platform features required.

## How It Works

The chatbot implements **progressive disclosure** as defined by the Agent Skills spec:

1. **Discovery** — At startup, only the `name` and `description` are read from each `SKILL.md` frontmatter (lightweight, ~100 tokens per skill).
2. **Activation** — When the user's request matches a skill, the LLM calls the `activate_skill` tool to load the full instructions.
3. **Execution** — The LLM follows the loaded skill instructions to respond.

For general questions that don't match any skill, the LLM responds directly without activating anything.

## Project Structure

```
├── chatbot_hosted_agent.py  # Hosted agent version (HTTP server)
├── skills/
│   └── greet/
│       └── SKILL.md        # Example skill: greet users by name in different languages
├── requirements.txt
├── .env
└── README.md
```

## Setup

1. **Install dependencies:**

   ```bash
   pip install -r requirements.txt
   ```

2. **Configure `.env`** with your Azure AI Foundry endpoint:

   ```
   AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
   AZURE_OPENAI_DEPLOYMENT=gpt-4o
   AZURE_OPENAI_API_VERSION=2024-12-01-preview
   ```

3. **Authenticate** via Azure CLI (no API key needed):

   ```bash
   az login
   ```

## Usage

### Hosted Agent (HTTP Server)

```bash
python chatbot_hosted_agent.py
```

Then send requests:

```bash
curl -X POST http://localhost:8088/responses \
  -H "Content-Type: application/json" \
  -d '{
    "agent": { "name": "local_agent", "type": "agent_reference" },
    "stream": false,
    "input": "Hi my name is John. Greet me in Spanish"
  }'
```

## Adding Skills

Create a new folder under `skills/` with a `SKILL.md` file. Skills are auto-discovered at startup.

```
skills/
└── my-new-skill/
    └── SKILL.md
```

See the [Agent Skills specification](https://agentskills.io/specification) for the full format.
