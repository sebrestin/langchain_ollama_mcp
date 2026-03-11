# LangChain + Ollama AI Agent with Model Context Protocol (MCP)

A Python-based conversational AI agent that leverages [Ollama](https://ollama.com/) for local LLM inference, [LangChain](https://www.langchain.com/) for agent orchestration, and the **Model Context Protocol (MCP)** for extensible tool usage. The agent acts as an MCP Client, connecting to MCP Servers to execute tools like weather fetching, web search, and date retrieval.

## 🌟 Features

- **LangChain Agent**: Uses `langchain` + `langgraph` to orchestrate the agent loop, tool selection, and response generation.
- **LangChain Ollama Integration**: Connects to a local Ollama instance via `langchain-ollama` (`ChatOllama`).
- **MCP Tool Adapters**: Discovers and binds MCP server tools automatically using `langchain-mcp-adapters` (`MultiServerMCPClient`).
- **Model Context Protocol (MCP)**: Uses a standardized protocol to connect the Agent (Client) with Tools (Server).
- **Interactive Chat Interface**: Conversational agent with streaming responses.
- **Thinking Mode**: Optional reasoning display showing the model's thought process.
- **Weather Data**: Fetch historical weather data using the Open-Meteo API.
- **Web Search**: Search the web and fetch URL content via DuckDuckGo.
- **Docker Support**: Full containerized setup orchestrating Agent, Tools Servers, and Ollama.
- **Dev Container**: VS Code dev container configuration for easy development.

## 🏗️ Project Structure

The project is split into an Agent Client and two MCP Tool Servers:

```
langchain_ollama_mcp/
├── agent/                  # MCP Client — The AI Agent
│   ├── agent.py            # Core Agent class (LangChain-based)
│   ├── main.py             # Entry point: loads MCP tools and starts the agent
│   └── __init__.py
├── search_tools/           # MCP Server for Search Tools
│   ├── main.py             # Entry point (FastMCP, port 8001)
│   └── tools.py            # web_search and fetch_url tool definitions
├── weather_tools/          # MCP Server for Weather Tools
│   ├── main.py             # Entry point (FastMCP, port 8000)
│   └── tools.py            # get_weather and current_date tool definitions
├── mcp_server_config.json  # Configuration for connecting Agent to MCP Servers
├── dockers/
│   ├── Dockerfile          # Shared container image
│   ├── docker-compose.yml  # Production orchestration
│   └── docker-compose.dev.yml  # Development orchestration
└── requirements.txt        # Dependencies
```

## 🚀 Getting Started

### Prerequisites

- Docker and Docker Compose
- NVIDIA GPU with Docker GPU support (recommended)
- Python 3.12+ (if running locally)

### Option 1: Docker (Recommended)

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd langchain_ollama_mcp
   ```

2. **Start the services**:
   This will start the Ollama container, the Weather Tools Server, and the Search Tools Server.
   ```bash
   docker-compose -f dockers/docker-compose.yml up -d
   ```

3. **Pull the required model**:
   ```bash
   docker exec -it langchain_ollama_mcp-ollama-1 ollama pull qwen3
   ```
   *(Note: Container name might vary, check with `docker ps`)*

4. **Run the Agent interactively**:
   ```bash
   docker-compose -f dockers/docker-compose.yml run --rm app python agent/main.py
   ```

### Option 2: Local Development

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Start the MCP Tool Servers**:
   Open two terminal windows/tabs.

   Terminal 1 (Weather Tools — port 8000):
   ```bash
   python weather_tools/main.py
   ```

   Terminal 2 (Search Tools — port 8001):
   ```bash
   python search_tools/main.py
   ```

3. **Configure the Agent**:
   Edit `mcp_server_config.json` to point to your local servers:
   ```json
   {
     "mcpServers": {
       "weather_tools": {
         "transport": "sse",
         "url": "http://localhost:8000/sse"
       },
       "search_tools": {
         "transport": "sse",
         "url": "http://localhost:8001/sse"
       }
     }
   }
   ```

4. **Start the Agent**:
   In a separate terminal:
   ```bash
   python agent/main.py
   ```

## 🏛️ Architecture

The agent startup sequence in `agent/main.py`:

1. Reads `mcp_server_config.json` to locate MCP servers.
2. Creates a `MultiServerMCPClient` (from `langchain-mcp-adapters`) and fetches all available tools.
3. Instantiates `Agent` with a `ChatOllama` model and the discovered tools.
4. `Agent.start()` calls `create_agent` (LangChain/LangGraph) to build the runnable agent graph, then enters the interactive loop.
5. Each user message is appended to the conversation context and streamed through the LangGraph agent, which handles tool calls transparently.

## 🛠️ Available Tools

Tools are served by the MCP Servers and automatically discovered by the agent at startup via `MultiServerMCPClient.get_tools()`.

### Weather Tools (`weather_tools/`, port 8000)
- **`get_weather(lat, lon, start_date, end_date)`**: Fetches historical weather data from the Open-Meteo Archive API.
- **`current_date()`**: Returns the current date.

### Search Tools (`search_tools/`, port 8001)
- **`web_search(query, num_results)`**: Search the web using the DuckDuckGo HTML endpoint (no JS required).
- **`fetch_url(url, max_length)`**: Fetch content from a URL and return clean text (strips scripts and styles).

## 🔧 Customization

### Adding New Tools
1. Define the function in `search_tools/tools.py` or `weather_tools/tools.py` (or create a new MCP server module).
2. Register it in the respective `main.py` with `mcp.add_tool(...)`.
3. Add the new server to `mcp_server_config.json`.
4. Restart the Tools Server. The agent discovers all tools automatically at startup via `MultiServerMCPClient`.

### Changing the Model
Update the `model` argument in `agent/main.py`:
```python
a = agent.Agent(model="llama3.2", thinking=False, tools=available_tools)
```
Any model available in your Ollama instance can be used.

## 📦 Dependencies

| Package | Purpose |
|---|---|
| `langchain` | Agent orchestration and message types |
| `langchain-ollama` | `ChatOllama` LLM integration |
| `langchain-mcp-adapters` | `MultiServerMCPClient` — bridges MCP servers to LangChain tools |
| `langgraph` | Agent execution graph built by `create_agent` |
| `mcp` | Model Context Protocol SDK (used by the tool servers) |
| `pandas`, `openmeteo-requests` | Weather data fetching and processing |
| `beautifulsoup4` | HTML parsing for the `fetch_url` tool |
