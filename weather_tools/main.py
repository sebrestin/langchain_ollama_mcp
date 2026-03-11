"""MCP Server for Weather Tools."""
from mcp.server.fastmcp import FastMCP

import tools as tools


# Initialize FastMCP server
mcp = FastMCP("weather-tools-server", host="0.0.0.0", port=8000)


mcp.add_tool(tools.get_weather)
mcp.add_tool(tools.current_date)


if __name__ == "__main__":
    # Run the MCP server with SSE transport
    mcp.run(transport='sse')

