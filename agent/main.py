"""Entry point for the Ollama MCP Agent."""
import asyncio
import json

from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.interceptors import MCPToolCallRequest

import agent


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

client = MultiServerMCPClient(config["mcpServers"], tool_interceptors=[logging_interceptor])
available_tools = asyncio.run(client.get_tools())

a = agent.Agent(model="qwen3", thinking=True, tools=available_tools)
asyncio.run(a.start())
