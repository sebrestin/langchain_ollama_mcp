from mcp.server.fastmcp import FastMCP

import tools as tools


# Initialize FastMCP server
mcp = FastMCP("timezone-tools-server", host="0.0.0.0", port=8002)


mcp.add_tool(tools.current_time)
mcp.add_tool(tools.current_timezone)
mcp.add_tool(tools.convert_timezone)
mcp.add_tool(tools.timezone_delta)


if __name__ == "__main__":
    # Run the MCP server with SSE transport
    mcp.run(transport='sse')
