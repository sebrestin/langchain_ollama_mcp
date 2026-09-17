# LangChain + Ollama AI Agent with Model Context Protocol (MCP)

A Python-based conversational AI agent that leverages [Ollama](https://ollama.com/) for local LLM inference, [LangChain](https://www.langchain.com/) for agent orchestration, and the **Model Context Protocol (MCP)** for extensible tool usage. The agent acts as an MCP Client, connecting to MCP Servers to execute tools like weather fetching, web search, and date retrieval. It also loads Claude/Codex-style **skills** from a local `skills/` directory, and keeps a long-term **memory** of the user in `memory/AGENTS.md`.

## 🌟 Features

- **LangChain Agent**: Uses `langchain` + `langgraph` to orchestrate the agent loop, tool selection, and response generation.
- **LangChain Ollama Integration**: Connects to a local Ollama instance via `langchain-ollama` (`ChatOllama`).
- **MCP Tool Adapters**: Discovers and binds MCP server tools automatically using `langchain-mcp-adapters` (`MultiServerMCPClient`).
- **Skills**: Claude/Codex-style `SKILL.md` packages discovered from `skills/` and disclosed progressively to the model through LangChain middleware.
- **Long-term Memory**: An `AGENTS.md` file of facts and preferences about the user, added to every prompt and extended by the agent with its `remember` tool.
- **Model Context Protocol (MCP)**: Uses a standardized protocol to connect the Agent (Client) with Tools (Server).
- **Interactive Chat Interface**: Conversational agent with streaming responses.
- **Thinking Mode**: Optional reasoning display showing the model's thought process.
- **LangSmith Runs**: Serve the agent with `langgraph dev`, invoke runs from the command line, and trace model calls, tool calls and skill usage in [LangSmith](https://smith.langchain.com/).
- **Weather Data**: Fetch historical weather data using the Open-Meteo API.
- **Web Search**: Search the web and fetch URL content via DuckDuckGo.
- **Research**: Multi-source web research with cited answers through the `research` skill.
- **Timezones**: Current time, timezone conversion and time differences through the `timezone` skill's deterministic scripts.
- **Docker Support**: Full containerized setup orchestrating Agent, Tools Servers, and Ollama.
- **Dev Container**: VS Code dev container configuration for easy development.

## 🏗️ Project Structure

The project is split into an Agent Client, a `tools/` directory with two MCP Tool Servers and the agent's local tools, a directory of local skills and the agent's memory:

```
langchain_ollama_mcp/
├── agent/                  # MCP Client — The AI Agent
│   ├── agent.py            # Core Agent class (LangChain-based)
│   ├── main.py             # Entry point: builds the agent from MCP tools, skills and memory; chat loop and langgraph dev factory
│   ├── skills_middleware.py  # Skill discovery and the middleware exposing skills to the model
│   ├── memory_middleware.py  # Middleware loading memory/AGENTS.md into the prompt, and the remember tool
│   └── __init__.py
├── tools/                  # Tools: the MCP Tool Servers and the agent's local tools
│   ├── search_tools/       # MCP Server for Search Tools
│   │   ├── main.py         # Entry point (FastMCP, port 8001)
│   │   └── tools.py        # web_search and fetch_url tool definitions
│   ├── weather_tools/      # MCP Server for Weather Tools
│   │   ├── main.py         # Entry point (FastMCP, port 8000)
│   │   └── tools.py        # get_weather and current_date tool definitions
│   └── executables.py      # run_executable: runs allowed executables, such as python, for skills
├── skills/                 # Local skills loaded by the agent
│   ├── timezone/
│   │   ├── SKILL.md        # Frontmatter (name, description) + instructions with script command lines
│   │   └── scripts/        # Deterministic scripts the agent runs
│   └── research/
│       └── SKILL.md        # Research workflow: search the web, read pages, answer with sources
├── memory/
│   └── AGENTS.md           # Long-term memory about the user (git-ignored, created on first use)
├── mcp_server_config.json  # Configuration for connecting Agent to MCP Servers
├── langgraph.json          # langgraph dev configuration: graph factory and .env file
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
   docker-compose -f dockers/docker-compose.yml run --rm app python -m agent.main
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
   python -m tools.weather_tools.main
   ```

   Terminal 2 (Search Tools — port 8001):
   ```bash
   python -m tools.search_tools.main
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
   In a separate terminal, from the repository root:
   ```bash
   python -m agent.main
   ```
   To send questions from the command line and trace them in LangSmith instead, see [Running Through LangSmith](#-running-through-langsmith).

## 🔍 Running Through LangSmith

`langgraph dev` (from `langgraph-cli`) serves the agent through a local LangGraph API server. You start agent runs from the command line with `curl`, and follow each run in [LangSmith](https://smith.langchain.com/), both as a trace and in LangSmith Studio. `langgraph.json` tells the server to build the agent with `make_graph()` from `agent/main.py`. The server calls it for every request, so each run uses the tools the MCP servers offer at that moment.

Run all commands from the repository root, in the dev container or your local environment, with Ollama and the MCP tool servers running (see [Getting Started](#-getting-started)).

> **Note:** With tracing on, prompts, model output and tool results are sent to LangSmith's servers. The model itself still runs locally in Ollama.

### 1. Install the LangGraph CLI

`langgraph-cli[inmem]` is listed in `requirements.txt`. Rebuild the dev container (**Dev Containers: Rebuild Container**) or the Docker image, or install the requirements locally:
```bash
pip install -r requirements.txt
```

If you run `pip install` inside a container built before `~/.local/bin` was added to the image's `PATH`, the shell reports `langgraph: command not found`. pip installed the command into `~/.local/bin`, so add that directory to your `PATH`:
```bash
export PATH="$HOME/.local/bin:$PATH"
```

### 2. Configure LangSmith

Create an API key in LangSmith under **Settings → API Keys**. Then create a `.env` file in the repository root (git ignores it). `langgraph dev` loads it through the `"env"` setting in `langgraph.json`:
```bash
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=<your-api-key>
LANGSMITH_PROJECT=langchain-ollama-mcp
```
- `LANGSMITH_PROJECT` is optional. Without it, traces go to the `default` project.
- If your LangSmith account is hosted in the EU, also set `LANGSMITH_ENDPOINT=https://eu.api.smith.langchain.com`.
- Without a `.env` file the server still starts, but it sends no traces unless these variables are exported in your terminal.

### 3. Start the Server

```bash
langgraph dev
```

It prints three URLs:
- the API: `http://127.0.0.1:2024`
- a LangSmith Studio link, where you can chat with the agent and step through its graph in the browser
- the API reference: `http://127.0.0.1:2024/docs`

Studio opens automatically unless you pass `--no-browser`. The server reloads when you edit the code and stores its threads in `.langgraph_api/`, which git ignores.

With Docker, rebuild the image (`docker-compose -f dockers/docker-compose.yml up -d --build`), then run this step and the next one inside the `app` container. To open a shell there, run `docker-compose -f dockers/docker-compose.yml exec -w /workspaces/langchain_ollama_mcp app bash`. Studio also needs port 2024 to be reachable from your browser. The dev container forwards that port automatically.

### 4. Invoke a Run

In another terminal, ask a single question and wait for the result. `personal_assistant` is the graph name from `langgraph.json`:
```bash
curl -s http://127.0.0.1:2024/runs/wait \
  -H 'Content-Type: application/json' \
  -d '{"assistant_id": "personal_assistant",
       "input": {"messages": [{"role": "user", "content": "What time is it in Tokyo right now?"}]}}'
```

The response holds the agent's final state: every message of the run, including tool calls and their results. To print only the answer, pipe the response into:
```bash
python3 -c 'import json, sys; print(json.load(sys.stdin)["messages"][-1]["content"])'
```

To have a conversation, create a thread and send each message to it. The thread keeps the message history between runs:
```bash
THREAD_ID=$(curl -s -X POST http://127.0.0.1:2024/threads \
  -H 'Content-Type: application/json' -d '{}' \
  | python3 -c 'import json, sys; print(json.load(sys.stdin)["thread_id"])')

curl -s http://127.0.0.1:2024/threads/$THREAD_ID/runs/wait \
  -H 'Content-Type: application/json' \
  -d '{"assistant_id": "personal_assistant",
       "input": {"messages": [{"role": "user", "content": "What is the date today?"}]}}'
```
To send a follow-up, run the second command again with a new `content`.

To see the answer as the model writes it, use the `/runs/stream` endpoint with the same request body plus `"stream_mode": "messages-tuple"`. It sends one server-sent event per generated token.

### 5. View the Traces

Open your project in LangSmith. Each run adds a trace named `personal_assistant`, which you can expand to see each model call, tool call and skill call with its inputs, outputs, token counts and timings. Runs on the same thread carry its `thread_id`, so LangSmith groups them into one conversation. Traces are uploaded in the background and appear a few seconds after the answer.

### Tracing the Interactive Agent

`python -m agent.main` does not read `.env`, but it sends traces as well when the same variables are set in your terminal:
```bash
export LANGSMITH_TRACING=true
export LANGSMITH_API_KEY=<your-api-key>
export LANGSMITH_PROJECT=langchain-ollama-mcp
python -m agent.main
```
With Docker, pass the variables to the container: `docker-compose -f dockers/docker-compose.yml run --rm -e LANGSMITH_TRACING=true -e LANGSMITH_API_KEY="$LANGSMITH_API_KEY" app python -m agent.main`.

## 🏛️ Architecture

`build_agent()` in `agent/main.py` creates the agent:

1. Reads `mcp_server_config.json` to locate MCP servers.
2. Creates a `MultiServerMCPClient` (from `langchain-mcp-adapters`) and fetches the tools of every server.
3. Scans `skills/` for `SKILL.md` files and, if it finds any, adds the [`run_executable`](#running-executables) tool to the fetched tools. It creates a `SkillsMiddleware` for the skills found, and a `MemoryMiddleware` for `memory/AGENTS.md`.
4. Instantiates `Agent` with a `ChatOllama` model, the fetched tools and both middleware. `Agent` calls `create_agent` (LangChain/LangGraph) to build the runnable agent graph.

The agent then runs in one of two ways:

- **Interactive** (`python -m agent.main`): `Agent.start()` enters the chat loop. Each user message is added to the conversation context and streamed through the LangGraph agent, which handles tool calls transparently.
- **LangGraph API** (`langgraph dev`): the server calls `make_graph()` for each request. That function returns the graph from `build_agent()`, and the server runs it, keeps thread state and streams results.

In both modes, the middleware appends the available skills and then the memory to the system prompt before every model call.

## 🛠️ Available Tools

Tools are served by the MCP Servers and discovered by the agent at startup via `MultiServerMCPClient.get_tools()`. The model has all of them from the first message on, whether or not a skill is loaded. Every MCP tool returns its errors, such as invalid arguments or an unreachable server, to the model as the tool result instead of aborting the run.

### Weather Tools (`tools/weather_tools/`, port 8000)
- **`get_weather(lat, lon, start_date, end_date)`**: Fetches historical weather data from the Open-Meteo Archive API.
- **`current_date()`**: Returns the current date.

### Search Tools (`tools/search_tools/`, port 8001)
- **`web_search(query, num_results)`**: Search the web using the DuckDuckGo HTML endpoint (no JS required).
- **`fetch_url(url, max_length)`**: Fetch content from a URL and return clean text (strips scripts and styles).

## 🧩 Skills

Skills package instructions together with the scripts and reference files they need, using the same `SKILL.md` layout as Claude Code and Codex. `SkillsMiddleware` (`agent/skills_middleware.py`) implements the [LangChain skills pattern](https://docs.langchain.com/oss/python/langchain/multi-agent/skills) with progressive disclosure, so a skill costs one line of context until it is needed:

1. **Discover**: At startup `discover_skills()` scans `skills/*/SKILL.md`. Before every model call the middleware appends the `name` and `description` of each skill that is not `hidden` to the system prompt.
2. **Load**: When a request matches a description, the model calls `load_skill`, which returns the instructions of the skill and of the skills it `requires`, and the files bundled with them.
3. **Use**: The model does what the instructions say with the tools it has, as described [below](#tools-in-skills), and reads bundled files with `read_skill_file`.

Skills take priority over tools: the system prompt tells the model to load a matching skill even if one of its tools could handle the request directly.

### Tools in Skills

A skill says what has to be done and never names a tool, neither in its instructions nor in its frontmatter. The research skill says "search the web", not `web_search`, and a skill that needs a script shows the command line a person would type, such as `python scripts/example.py --name value`. The middleware only knows how to load skills and read their files: it gives the model no other tools, and running tools is LangChain's job. The model has every tool registered with the agent and picks the tool for each step from the tools' descriptions. If none of its tools can do a step, the system prompt tells it to say so instead of guessing the result.

For a command, the model works out how to run it the same way it picks a skill for a request, since skills take priority over tools there too:

1. If a skill's description covers running the command, the model loads that skill and follows it. No skill does this yet.
2. Otherwise the model runs the command with its tools. It picks [`run_executable`](#running-executables) from the tool's description, which explains how to turn a command line into a call.

### Running Executables

`run_executable(executable, executable_args, skill_name)`, defined in `tools/executables.py`, runs an executable in the folder of a skill. The tool is generic: it does not know what it runs. Its description tells the model how to turn a command line into a call, and a skill that covers an executable can add what to know about running it, without naming the tool.

- It only runs the executables listed in `EXECUTABLES` in `agent/main.py`, keyed by the name the model passes as `executable`. Out of the box that is `python` (and its alias `python3`), the agent's own interpreter. It only runs `.py` scripts and sets `PYTHONDONTWRITEBYTECODE`, so running scripts does not leave `__pycache__` folders in skills.
- An `Executable` has a `path`, optional `env` variables, and optional `script_suffixes`. With `script_suffixes`, the first argument must be a script that the skill bundles in its `scripts/` folder with one of those suffixes, so an interpreter cannot run code the model wrote, such as `python -c ...`. Executables without `script_suffixes` get their arguments as given, and need `skill_name`.
- It runs with the skill folder as working directory, a 30 second timeout and no shell: `executable_args` are split with `shlex`, so the model cannot chain extra commands. Executables still run with the agent's permissions, so only allow executables and add skills you trust.
- It is bound to the model, so the model can run commands that no skill covers. Its description says how to split a command line into `executable` and `executable_args`, and lists the configured executables and the timeout.

To let skills run another interpreter, add it to `EXECUTABLES`, e.g. `"bash": Executable("/bin/bash", script_suffixes=(".sh",))`. The model can then run `bash scripts/example.sh` from the tool description alone; for more reliable calls, add a skill whose description says it covers `bash` commands and explains what to know about running them.

### Timezone Skill (`skills/timezone/`)

Instead of doing time arithmetic itself, the model runs these scripts with [`run_executable`](#running-executables) and answers from their JSON output:
- **`scripts/current_time.py [--tz ZONE]`**: Current time, weekday, UTC offset and abbreviation, locally or in any IANA timezone.
- **`scripts/convert_timezone.py --time TIME --from ZONE --to ZONE [--days N]`**: Converts a wall-clock time from one timezone to another. `TIME` can be a full date-time or a time of day (today in the source timezone), and `--days 1` moves it to tomorrow.
- **`scripts/timezone_delta.py --time1 TIME --tz1 ZONE --time2 TIME --tz2 ZONE`**: Time difference between two wall-clock times, accounting for daylight saving time.

### Research Skill (`skills/research/`)

For questions that need current information, facts about people or companies, or a given URL, the model plans up to three queries, searches the web, reads the best results and answers with a source URL for each fact. The skill never names the [Search Tools](#search-tools-toolssearch_tools-port-8001): the model picks `web_search` and `fetch_url` for those steps from their descriptions, and if it has no tools to search the web and read pages, the skill tells it to say it cannot research the question. To fit the 8192-token context window, the skill has the model ask for 5 search results and read 4,000 characters of page text instead of the tools' defaults of 10 and 10,000, and read at most three pages per question.

### Writing a Skill

Create a folder under `skills/` containing a `SKILL.md` file:

```
skills/my_skill/
├── SKILL.md            # Required
├── scripts/            # Optional: Python scripts the model can run
│   ├── do_thing.py
│   └── _helpers.py     # Paths starting with "_" or "." are private: not listed, read or run
└── references/         # Optional: files the model can read on demand
    └── guide.md
```

```markdown
---
name: my_skill
description: What the skill does and when to use it. The model decides whether to load the skill from this text alone.
---

# My Skill

Step-by-step instructions for the model. Describe each step as what has to be done, for example
"look up the weather for the city", document scripts as command lines, for example
`python scripts/do_thing.py --input value`, and point to references such as `references/guide.md`.
```

- `description` is required; `name` defaults to the folder name.
- Never name a tool, such as `get_weather` or `run_executable`: say what has to be done, and show scripts as the command line a person would type. The model picks the tools, as described in [Tools in Skills](#tools-in-skills). If a step needs a kind of tool that the agent may not have, such as web search, say what to tell the user in that case.
- `requires` lists the names of skills that are always loaded together with this one, for instructions that several skills share. Skills that require a skill that does not exist are skipped with a warning.
- `hidden: true` leaves a skill out of the system prompt, for skills that are only loaded through `requires`.
- Give a skill a name that differs from the tools it runs: `qwen3` sometimes called a skill named `web-search` instead of its `web_search` tool.
- `SKILL.md` is re-read every time a skill is loaded, so instructions can be edited while the agent runs. New skills are picked up when the interactive agent restarts, and on the next run under `langgraph dev`.
- To load skills from more places, add directories to `SKILL_DIRECTORIES` in `agent/main.py`, e.g. `["skills", "/path/to/shared/skills"]`. Earlier directories win when two skills share a name.

## 🧠 Memory

The agent keeps facts and preferences about the user in `memory/AGENTS.md`, so it knows them in every conversation without being told again. In LangGraph terms this is long-term memory: the message history of a conversation ends with it, while the memory file lasts across conversations, and the agent adds to it itself. `MemoryMiddleware` (`agent/memory_middleware.py`) follows the [Deep Agents memory](https://docs.langchain.com/oss/python/deepagents/overview#context-management) design, but gives the model an append-only tool instead of general file editing:

1. **Load**: Before every model call, the middleware appends the contents of `memory/AGENTS.md` to the system prompt, with instructions on when to save new facts.
2. **Remember**: When the user shares something that will matter later, such as their name, home timezone or formatting preferences, or corrects the agent, the model calls `remember(fact)`. The tool appends the fact to the file as a bullet point.

For example, after "My home timezone is Asia/Tokyo", a later conversation asking "What time is it at home?" runs the timezone skill with `--tz Asia/Tokyo`.

### Editing the Memory

`memory/AGENTS.md` is a markdown file you can edit like any other:

```markdown
<!-- Comments are not sent to the model. -->

- The user's home timezone is Asia/Tokyo.
- The user prefers the 24-hour clock.
```

- The file is re-read before every model call, so edits apply immediately, even while the agent runs. If it does not exist, the first `remember` call creates it.
- `remember` only appends. It skips facts that are already saved and rejects facts longer than 200 characters. To change a fact, the model saves the new version, and the prompt tells it that later entries win. Delete outdated entries by hand.
- The memory is capped at 2,000 characters, about 500 tokens of the 8192-token context window. When it is full, `remember` saves nothing and tells the model to ask you to remove outdated entries.
- The whole file is sent to the model as part of the system prompt, and to LangSmith when tracing is on. Only write what you would put in the system prompt yourself.
- The file holds personal information, so git ignores it. With Docker, the repository is mounted into the containers, so the file stays on the host.
- The file lives in `memory/` rather than at the repository root because coding agents such as Codex read a root `AGENTS.md` as instructions for working on this code. To use another file, change the path passed to `MemoryMiddleware` in `build_agent()`.

## 🔧 Customization

### Adding New Tools
1. Define the function in `tools/search_tools/tools.py` or `tools/weather_tools/tools.py` (or create a new MCP server package under `tools/`, run with `python -m tools.<server>.main` from the repository root).
2. Register it in the respective `main.py` with `mcp.add_tool(...)`.
3. Add the new server to `mcp_server_config.json`.
4. Restart the Tools Server and the agent. The agent discovers the tools automatically at startup via `MultiServerMCPClient`. A skill that needs them describes the task, and the model finds the tools from their descriptions, so give each tool a docstring that says what it does and what its arguments mean.

### Changing the Model
Update the `model` argument in `build_agent()` in `agent/main.py`:
```python
return Agent(model="llama3.2", thinking=False, tools=available_tools, middleware=[skills, memory])
```
Any model available in your Ollama instance can be used.

### Changing the Context Size
The agent asks Ollama for an 8192-token context window instead of Ollama's 4096-token default, which is too small once a skill is loaded and the model is thinking. 8192 is the largest size at which `qwen3` (8B) still fits entirely on an 8 GB GPU. Adjust it for your model and GPU with the `context_size` argument in `build_agent()` in `agent/main.py`:
```python
return Agent(model="qwen3", thinking=True, tools=available_tools, middleware=[skills, memory], context_size=16384)
```
After the agent has answered a question, run `ollama ps`: if the `PROCESSOR` column shows a CPU/GPU split instead of `100% GPU`, the context is too large for your GPU and responses will be much slower.

## 📦 Dependencies

| Package | Purpose |
|---|---|
| `langchain` | Agent orchestration, middleware and message types |
| `langchain-ollama` | `ChatOllama` LLM integration |
| `langchain-mcp-adapters` | `MultiServerMCPClient` — bridges MCP servers to LangChain tools |
| `langgraph` | Agent execution graph built by `create_agent` |
| `langgraph-cli[inmem]` | `langgraph dev`: serves the agent through a local LangGraph API server |
| `langsmith` | Optional tracing of agent runs to LangSmith |
| `mcp` | Model Context Protocol SDK (used by the tool servers) |
| `PyYAML` | Parsing `SKILL.md` frontmatter |
| `pandas`, `openmeteo-requests` | Weather data fetching and processing |
| `beautifulsoup4` | HTML parsing for the `fetch_url` tool |
