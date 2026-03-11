"""Entry point for the Ollama MCP Agent."""
import asyncio
import json

from langchain_mcp_adapters.client import MultiServerMCPClient

import agent


with open("mcp_server_config.json", "r") as f:
    config = json.load(f)

client = MultiServerMCPClient(config["mcpServers"])
available_tools = asyncio.run(client.get_tools())

a = agent.Agent(model="qwen3", thinking=True, tools=available_tools)
asyncio.run(a.start())
