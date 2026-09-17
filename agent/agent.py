from typing import Any

from langchain_ollama import ChatOllama
from langchain.agents import create_agent
from langchain.messages import HumanMessage, ToolMessage, SystemMessage
from langgraph.graph.state import CompiledStateGraph



class Agent:
    """
    An AI Agent capable of conversing and using tools via the Model Context Protocol (MCP).
    
    This agent uses a local LLM via Ollama and connects to MCP servers to execute tools.
    It supports a thinking mode to display reasoning and manages a conversation history.
    """

    STOP_MARK = "stop"

    def __init__(self, model: str, thinking: bool, tools: list, middleware: list | None = None, context_size: int = 8192):
        """
        Initialize the Agent.

        :param model: The name of the Ollama model to use
        :type model: str
        :param thinking: Whether to enable thinking/reasoning mode
        :type thinking: bool
        :param tools: A list of tool wrappers available to the agent
        :type tools: list
        :param middleware: Agent middleware to apply, e.g. SkillsMiddleware to enable local skills
            or MemoryMiddleware to enable long-term memory
        :type middleware: list | None
        :param context_size: Context window in tokens. Ollama's 4096 default overflows once a skill is
            loaded and the model is thinking; 8192 is the largest size at which qwen3 (8B) still fits
            entirely on an 8 GB GPU
        :type context_size: int
        """
        self._model = ChatOllama(model=model, disable_streaming=False, reasoning=thinking, num_ctx=context_size)
        self._thinking = thinking
        self._tools = tools
        self._middleware = middleware or []
        self._context = list()
        self._agent = create_agent(
            self._model,
              self._tools,
                name="personal_assistant",
                middleware=self._middleware,
                system_prompt=SystemMessage(
                    "You are a helpful assistant that can use tools to answer questions and perform tasks."
                    "Use the tools when necessary to provide accurate and complete responses."
                    "Do not limit your tool usage and use them as much as possible to help answer the user's questions as accurately as possible."
                )
        )

    @property
    def graph(self) -> CompiledStateGraph:
        """
        The LangGraph agent graph, which `langgraph dev` serves through the LangGraph API.
        """
        return self._agent

    async def start(self) -> None:
        """
        Start the interactive agent loop.

        Continuously prompts the user for input and processes requests until the
        stop marker is received.
        """

        while True:
            message = input("What's on your mind? \n")
            if message == self.STOP_MARK:
                break
            self._context = list()
            await self.process_request(message)

    async def process_request(self, message: str) -> Any:
        """
        Process a single user request.

        Sends the message to the LLM, handles tool calls if generated, and manages
        the conversation context.

        :param message: The user's input message
        :type message: str
        :return: The final response object from Ollama
        """
        self._context.append(HumanMessage(message))

        thinking = ""
        content = ""

        done_thinking = False

        response = self._agent.astream(
            {"messages": self._context},
            stream_mode="messages",
        )
            
        async for chunk in response:
            if "reasoning_content" in chunk[0].additional_kwargs:
                thinking += chunk[0].additional_kwargs["reasoning_content"]
                print(chunk[0].additional_kwargs["reasoning_content"], end="", flush=True)
                
            if chunk[0].content and isinstance(chunk[0], ToolMessage):
                print(f"\nTool call generated: {chunk[0].content}\n")
            elif chunk[0].content:
                if not done_thinking:
                    done_thinking = True
                    print("\n")
                content += chunk[0].content
                print(chunk[0].content, end="", flush=True)

        print("\n\n")