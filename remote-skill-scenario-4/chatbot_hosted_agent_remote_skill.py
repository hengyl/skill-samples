"""
Simple LangGraph Chatbot with Remote Agent Skills from MCP Server
A minimal chatbot using LangGraph that fetches tools from an MCP server.
"""
import logging
import os
import asyncio
from typing import Annotated
from typing_extensions import TypedDict

from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from langchain_openai import AzureChatOpenAI
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from azure.ai.agentserver.langgraph import from_langgraph

from dotenv import load_dotenv
load_dotenv()

logging.basicConfig(level=logging.WARNING, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("mcp_chatbot")
logger.setLevel(logging.INFO)

# --------------------------------------------------------------------------
# 1. Define the state
#    "messages" holds the conversation history.
#    add_messages is a reducer that appends new messages instead of replacing.
# --------------------------------------------------------------------------
class State(TypedDict):
    messages: Annotated[list, add_messages]

# --------------------------------------------------------------------------
# 2. Create the LLM using your Azure AI Foundry project
# --------------------------------------------------------------------------
token_provider = get_bearer_token_provider(
    DefaultAzureCredential(),
    "https://cognitiveservices.azure.com/.default",
)

llm = AzureChatOpenAI(
    azure_deployment=os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o"),
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    azure_ad_token_provider=token_provider,
    api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-12-01-preview"),
)

# --------------------------------------------------------------------------
# 3. Build the graph
# --------------------------------------------------------------------------
def build_graph(tools):
    llm_with_tools = llm.bind_tools(tools)
    
    def chatbot(state: State) -> State:
        response = llm_with_tools.invoke(state["messages"])
        # Log when the LLM decides to call a tool
        if response.tool_calls:
            for tc in response.tool_calls:
                logger.info(f"LLM requesting MCP tool call: {tc['name']}({tc['args']})")
        return {"messages": [response]}
    
    tool_node = ToolNode(tools)
    async def logging_tool_node(state: State) -> State:
        logger.info("Invoking MCP tool(s)...")
        result = await tool_node.ainvoke(state)
        return result
    
    graph_builder = StateGraph(State)
    graph_builder.add_node("chatbot", chatbot)
    graph_builder.add_node("tools", logging_tool_node)
    graph_builder.add_edge(START, "chatbot")
    graph_builder.add_conditional_edges("chatbot", tools_condition)
    graph_builder.add_edge("tools", "chatbot")
    
    return graph_builder.compile()


# --------------------------------------------------------------------------
# 4. Run the chatbot with MCP tools
#    The MultiServerMCPClient fetches tools from the specified MCP server.
#    The MCP server url has a few skills deployed. We can switch to a different url when toolbox is available 
#    as they are both using the same MCP protocol.
# --------------------------------------------------------------------------
async def run():
    print("LangGraph Chatbot\n")

    client = MultiServerMCPClient({
        "math": {
            "url": "https://mcp-skills-server.proudflower-762b7070.westus2.azurecontainerapps.io/mcp",
            "transport": "streamable_http",
        }
    })
    tools = await client.get_tools()
    logger.info(f"Loaded {len(tools)} MCP tool(s): {[t.name for t in tools]}")
    graph = build_graph(tools)
    return graph

if __name__ == "__main__":
    agent_graph = asyncio.run(run())
    adapter = from_langgraph(agent_graph)
    adapter.run()