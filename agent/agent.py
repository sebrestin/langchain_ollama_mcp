from typing import Any

from langchain_ollama import ChatOllama
from langchain.agents import create_agent
from langchain.messages import HumanMessage, ToolMessage



class Agent:
    """
    An AI Agent capable of conversing and using tools via the Model Context Protocol (MCP).
    
    This agent uses a local LLM via Ollama and connects to MCP servers to execute tools.
    It supports a thinking mode to display reasoning and manages a conversation history.
    """

    STOP_MARK = "stop"

    def __init__(self, model: str, thinking: bool, tools: list):
        """
        Initialize the Agent.

        :param model: The name of the Ollama model to use
        :type model: str
        :param thinking: Whether to enable thinking/reasoning mode
        :type thinking: bool
        :param tools: A list of tool wrappers available to the agent
        :type tools: list
        """
        self._model = ChatOllama(model=model, disable_streaming=False, reasoning=thinking)
        self._thinking = thinking
        self._tools = tools
        self._context = list()
        self._agent = None
    
    async def start(self) -> None:
        """
        Start the interactive agent loop.

        Continuously prompts the user for input and processes requests until the
        stop marker is received.
        """

        self._agent = create_agent(self._model, self._tools)

        while True:
            message = input("What's on your mind? \n")
            if message == self.STOP_MARK:
                break
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