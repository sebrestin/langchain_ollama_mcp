"""Entry point for the Ollama MCP Agent.

Run ``python -m agent.main`` from the repository root to chat with the agent in the terminal, or
``langgraph dev`` to serve it through the LangGraph API, which calls ``make_graph`` (see langgraph.json).
"""
import asyncio
import json
import sys

from langchain.tools import BaseTool, ToolException
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.interceptors import MCPToolCallRequest
from langgraph.graph.state import CompiledStateGraph

from agent.agent import Agent
from agent.memory_middleware import MemoryMiddleware
from agent.skills_middleware import SkillsMiddleware, discover_skills
from tools.executables import Executable, create_executable_tool


# Directories to load skills from, in order of precedence
SKILL_DIRECTORIES = ["skills"]

# The executables that the command lines in skills can start, keyed by the command's first word.
# The Python scripts bundled with skills run with the agent's interpreter
PYTHON = Executable(sys.executable, script_suffixes=(".py",), env={"PYTHONDONTWRITEBYTECODE": "1"})
EXECUTABLES = {"python": PYTHON, "python3": PYTHON}

with open("mcp_server_config.json", "r") as f:
    config = json.load(f)


async def logging_interceptor(
    request: MCPToolCallRequest,
    handler,
):
    """Log tool calls before and after execution."""
    print(f"Calling tool: {request.name} with args: {request.args}")
    result = await handler(request)
    print(f"Tool {request.name} returned: {result}")
    return result


def describe_error(error: BaseException) -> str:
    """Describe an exception, including the errors an exception group wraps, such as MCP connection failures."""
    if isinstance(error, BaseExceptionGroup):
        return "; ".join(describe_error(inner) for inner in error.exceptions)
    return str(error) or type(error).__name__


async def error_interceptor(
    request: MCPToolCallRequest,
    handler,
):
    """Report failures to reach the MCP server as tool errors, which the model sees, e.g. a dropped connection."""
    try:
        return await handler(request)
    except ToolException:
        raise
    except Exception as e:
        raise ToolException(f"Tool '{request.name}' failed: {describe_error(e)}") from e


async def get_tools(client: MultiServerMCPClient) -> list[BaseTool]:
    """Load the tools of all MCP servers."""
    tools = await client.get_tools()
    for tool in tools:
        # Return tool errors, such as an MCP server rejecting the arguments, to the model instead of aborting the run
        tool.handle_tool_error = True
    return tools


async def build_agent() -> Agent:
    """Create the agent with the tools of the MCP servers, the local skills and long-term memory."""
    client = MultiServerMCPClient(config["mcpServers"], tool_interceptors=[error_interceptor, logging_interceptor])
    available_tools = await get_tools(client)

    # Discovering skills reads from disk, which must not block the event loop that `langgraph dev` runs this on
    skills = await asyncio.to_thread(discover_skills, SKILL_DIRECTORIES)
    if skills:
        # Skills show commands without naming a tool. The tool's description tells the model how to run them,
        # unless a skill that covers the executable does
        available_tools.append(create_executable_tool(skills, EXECUTABLES))

    # Skills never name tools: the model does what a skill says with the tools it has
    skills_middleware = SkillsMiddleware(skills)
    memory = MemoryMiddleware("memory/AGENTS.md")

    # Middleware add their prompts in list order. Memory goes last because it changes as the agent learns
    return Agent(model="qwen3", thinking=True, tools=available_tools, middleware=[skills_middleware, memory])


async def make_graph() -> CompiledStateGraph:
    """Graph factory for `langgraph dev`, called for every request so MCP tools are always current."""
    return (await build_agent()).graph


if __name__ == "__main__":
    a = asyncio.run(build_agent())
    asyncio.run(a.start())
