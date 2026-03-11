from mcp.server.fastmcp import FastMCP

import tools as tools


# Initialize FastMCP server
mcp = FastMCP("search-tools-server", host="0.0.0.0", port=8001)


mcp.add_tool(tools.web_search)
mcp.add_tool(tools.fetch_url)


if __name__ == "__main__":
    # Run the MCP server with SSE transport
    mcp.run(transport='sse')
