"""
Simple LangGraph Chatbot with Agent Skills (Azure AI Foundry OpenAI).

Implements the Agent Skills spec (https://agentskills.io) with progressive disclosure:
  1. Discovery  — Load only name + description from SKILL.md frontmatter at startup
  2. Activation — LLM calls activate_skill tool when a task matches a skill
  3. Execution  — Full SKILL.md body is loaded, LLM follows the instructions
"""

import os
import re
import logging
import yaml
from pathlib import Path
from dotenv import load_dotenv
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from langchain_openai import AzureChatOpenAI
from langchain_core.tools import tool
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode
from typing import Annotated
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages
from azure.ai.agentserver.langgraph import from_langgraph

# Load environment variables from .env file
load_dotenv()

logging.basicConfig(level=logging.WARNING, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

SKILLS_DIR = Path(__file__).parent / "skills"


# ============================================================
# 1. SKILL DISCOVERY — Parse only frontmatter (name + description)
# ============================================================

def discover_skills(skills_dir: Path) -> dict:
    """Scan skills/ folder and extract only the YAML frontmatter from each SKILL.md.
    Returns a dict: { skill_name: { "description": ..., "path": ... } }
    """
    catalog = {}
    if not skills_dir.exists():
        return catalog

    for skill_file in skills_dir.rglob("SKILL.md"):
        content = skill_file.read_text(encoding="utf-8")
        # Parse YAML frontmatter between --- markers
        match = re.match(r"^---\s*\n(.*?)\n---", content, re.DOTALL)
        if not match:
            continue
        frontmatter = yaml.safe_load(match.group(1))
        name = frontmatter.get("name", skill_file.parent.name)
        catalog[name] = {
            "description": frontmatter.get("description", ""),
            "path": str(skill_file),
        }
    return catalog


# Load skill catalog at startup (frontmatter only — lightweight!)
skill_catalog = discover_skills(SKILLS_DIR)


# ============================================================
# 2. SKILL ACTIVATION TOOL — LLM calls this to load full content
# ============================================================

@tool
def activate_skill(skill_name: str) -> str:
    """Activate a skill by name to get its full instructions.
    Call this when the user's request matches a skill from the catalog."""
    if skill_name not in skill_catalog:
        logger.warning("Skill '%s' not found. Available: %s", skill_name, list(skill_catalog.keys()))
        return f"Skill '{skill_name}' not found. Available: {list(skill_catalog.keys())}"

    logger.info("Activating skill '%s'", skill_name)
    skill_path = skill_catalog[skill_name]["path"]
    full_content = Path(skill_path).read_text(encoding="utf-8")
    logger.info("Loaded %d chars from %s", len(full_content), skill_path)
    return f"[Skill '{skill_name}' activated. Follow these instructions:]\n\n{full_content}"


tools = [activate_skill]


# ============================================================
# 3. BUILD THE SYSTEM PROMPT — Only includes skill catalog (names + descriptions)
# ============================================================

def build_system_prompt(catalog: dict) -> str:
    if not catalog:
        return "You are a helpful assistant."

    skill_list = "\n".join(
        f"  - {name}: {info['description']}" for name, info in catalog.items()
    )
    return (
        "You are a helpful assistant with access to skills.\n\n"
        "Available skills (call activate_skill to load full instructions before using one):\n"
        f"{skill_list}\n\n"
        "When a user's request matches a skill, call activate_skill with the skill name "
        "to load its full instructions, then follow them. "
        "For general questions, respond directly without activating any skill."
    )


SYSTEM_PROMPT = build_system_prompt(skill_catalog)


# ============================================================
# 4. STATE + MODEL
# ============================================================

class State(TypedDict):
    messages: Annotated[list, add_messages]


credential = DefaultAzureCredential()
token_provider = get_bearer_token_provider(credential, "https://cognitiveservices.azure.com/.default")

llm = AzureChatOpenAI(
    azure_deployment=os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o"),
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    azure_ad_token_provider=token_provider,
    api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-12-01-preview"),
)

# Bind the activate_skill tool to the LLM
llm_with_tools = llm.bind_tools(tools)


# ============================================================
# 5. GRAPH NODES
# ============================================================

def chatbot(state: State):
    """Call the LLM with the skill catalog in the system prompt."""
    system_message = {"role": "system", "content": SYSTEM_PROMPT}
    response = llm_with_tools.invoke([system_message] + state["messages"])
    return {"messages": [response]}


def should_continue(state: State):
    """If the LLM called a tool, route to the tool node; otherwise end."""
    last_message = state["messages"][-1]
    if last_message.tool_calls:
        return "tools"
    return END


# ============================================================
# 6. BUILD THE GRAPH
# ============================================================
#
#   START → chatbot → (tool call?) → tools → chatbot → ... → END
#                   └─ (no tool)  → END

def build_graph():
    graph_builder = StateGraph(State)
    graph_builder.add_node("chatbot", chatbot)
    graph_builder.add_node("tools", ToolNode(tools))

    graph_builder.add_edge(START, "chatbot")
    graph_builder.add_conditional_edges("chatbot", should_continue, ["tools", END])
    graph_builder.add_edge("tools", "chatbot")

    graph = graph_builder.compile()
    return graph

# ============================================================
# 7. RUN THE CHATBOT LOOP
# ============================================================
if __name__ == "__main__":
    agent_graph = build_graph()
    adapter = from_langgraph(agent_graph)
    adapter.run()
