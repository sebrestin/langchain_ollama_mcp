"""Long-term memory for the agent, kept in an AGENTS.md file.

The memory file is added to the system prompt before every model call, so the agent knows what it
learned about the user in earlier conversations. The agent adds facts with the ``remember`` tool,
and the user can edit the file by hand at any time: it is re-read before every model call. HTML
comments are not sent to the model, so the file can hold notes for the people editing it.
"""
import asyncio
import re
import threading
from collections.abc import Awaitable, Callable
from pathlib import Path

from langchain.agents.middleware import AgentMiddleware, ModelRequest, ModelResponse
from langchain.messages import SystemMessage
from langchain.tools import BaseTool, ToolException, tool


# Keeps the memory to about 500 tokens of the agent's 8192-token context window
MAX_MEMORY_CHARS = 2_000
MAX_FACT_CHARS = 200

COMMENT_PATTERN = re.compile(r"<!--.*?-->", re.DOTALL)

TEMPLATE = """<!--
Long-term memory of the personal assistant, loaded by agent/memory_middleware.py.
Everything in this file except comments like this one is added to the system prompt before every
model call. The assistant appends facts with its remember tool; edit or delete entries freely.
-->
"""

# `langgraph dev` creates a middleware for every request, so the lock is shared by all instances
_write_lock = threading.Lock()


def strip_comments(text: str) -> str:
    """Return the memory as the model sees it: the text without HTML comments."""
    return COMMENT_PATTERN.sub("", text).strip()


class MemoryMiddleware(AgentMiddleware):
    """
    Agent middleware that gives the model a long-term memory stored in an AGENTS.md file.

    Appends the contents of the file to the system prompt and registers the ``remember`` tool,
    which appends a fact to the file.
    """

    def __init__(self, path: str):
        """
        Set up the memory. No file is read here: the memory is loaded before every model call.

        :param path: Path of the memory file. The first fact remembered creates it if it is missing
        :type path: str
        """
        self.path = Path(path)
        self.tools = self._create_tools()

    def load(self) -> str:
        """
        Read the memory, as the model sees it.

        :return: The memory without comments, or an empty string if there is no memory file
        :rtype: str
        """
        try:
            return strip_comments(self._read())
        except OSError as e:
            print(f"Could not read memory file {self.path}: {e}")
            return ""

    def save(self, fact: str) -> str:
        """
        Append a fact to the memory file.

        :param fact: One short sentence about the user
        :type fact: str
        :return: A confirmation for the model
        :rtype: str
        :raises ToolException: If the fact is empty or too long, the memory is full or the file cannot be written
        """
        fact = " ".join(fact.split())
        if not fact:
            raise ToolException("The fact is empty. Pass one short sentence about the user.")
        if len(fact) > MAX_FACT_CHARS:
            raise ToolException(
                f"The fact is {len(fact)} characters long. Shorten it to one sentence of at most {MAX_FACT_CHARS} characters."
            )
        entry = f"- {fact}"

        with _write_lock:
            try:
                text = self._read()
                memory = strip_comments(text)
                if entry.lower() in (line.strip().lower() for line in memory.splitlines()):
                    return f"Already in memory: {fact}"
                if len(memory) + len(entry) + 1 > MAX_MEMORY_CHARS:
                    raise ToolException(
                        f"Memory is full, so nothing was saved. Tell the user to remove outdated entries from {self.path}."
                    )

                # Start a new file with the template, and never append to the end of an unterminated line
                prefix = f"{TEMPLATE}\n" if not text.strip() else "" if text.endswith("\n") else "\n"
                self.path.parent.mkdir(parents=True, exist_ok=True)
                with self.path.open("a", encoding="utf-8") as file:
                    file.write(f"{prefix}{entry}\n")
            except OSError as e:
                raise ToolException(f"Could not save to memory: {e}") from e
        return f"Saved to memory: {fact}"

    def wrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], ModelResponse],
    ) -> ModelResponse:
        """Inject the memory into the system prompt."""
        return handler(self._with_memory_prompt(request, self.load()))

    async def awrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], Awaitable[ModelResponse]],
    ) -> ModelResponse:
        """Inject the memory into the system prompt."""
        # Reading a file on the event loop is a blocking call, which `langgraph dev` rejects
        memory = await asyncio.to_thread(self.load)
        return await handler(self._with_memory_prompt(request, memory))

    def _read(self) -> str:
        try:
            return self.path.read_text(encoding="utf-8", errors="replace")
        except FileNotFoundError:
            return ""

    def _with_memory_prompt(self, request: ModelRequest, memory: str) -> ModelRequest:
        if len(memory) > MAX_MEMORY_CHARS:
            memory = f"{memory[:MAX_MEMORY_CHARS]}\n... [memory truncated]"
        prompt = (
            "## Memory\n\n"
            "Below is your long-term memory: facts and preferences about the user, saved in earlier "
            "conversations. Apply them without being asked, unless the user says otherwise now. When two "
            "entries disagree, the later one wins.\n\n"
            f"<memory>\n{memory or '(empty)'}\n</memory>\n\n"
            "When the user tells you something about themselves that will still matter in future "
            "conversations, such as their name, where they live, their home timezone or how they like "
            "their answers, or corrects you in a way that should last, call the remember tool with one "
            "short sentence about the user. To change a saved fact, remember the new version. Do not save "
            "one-off requests, tool results or anything already in your memory."
        )
        blocks = list(request.system_message.content_blocks) if request.system_message else []
        system_message = SystemMessage(content=[*blocks, {"type": "text", "text": prompt}])
        return request.override(system_message=system_message)

    def _create_tools(self) -> list[BaseTool]:
        @tool(parse_docstring=True)
        def remember(fact: str) -> str:
            """Save a fact about the user to your long-term memory, so you still know it in future conversations.

            Args:
                fact: One short sentence about the user, starting with "The user".
            """
            return self.save(fact)

        # Return ToolException messages to the model instead of aborting the agent run
        remember.handle_tool_error = True
        return [remember]
