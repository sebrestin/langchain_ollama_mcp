"""Claude/Codex-style skills for the agent.

A skill is a directory containing a ``SKILL.md`` file: YAML frontmatter with a ``name`` and a
``description``, followed by markdown instructions. Files bundled next to it, such as scripts or
reference documents, are available to the agent as well. The instructions say what has to be
done, such as searching the web or running ``python scripts/example.py``, and never name a tool:
the agent picks the tool for each step from the tools' descriptions, and tells the user when none
of its tools can do a step.

A skill can build on other skills by listing their names under ``requires`` in its frontmatter:
loading the skill loads the skills it requires too, so instructions that several skills share are
written once.

Skills are disclosed progressively: only the name and description of each skill go into the
system prompt, and the agent loads instructions and reads bundled files on demand through the
tools registered by ``SkillsMiddleware``. The middleware neither adds tools to the model nor runs
them: the model has the tools registered with the agent, and LangChain runs them. Skills take
priority over tools: the agent loads a matching skill before it uses any tool directly. That holds
for the steps of a skill too: before running a command that a skill shows, the agent loads the
skill that covers running it, if there is one, and otherwise runs the command with a tool, picked
by the tool's own description.
"""
import asyncio
import re
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from pathlib import Path

import yaml
from langchain.agents.middleware import AgentMiddleware, ModelRequest, ModelResponse, ToolCallRequest
from langchain.messages import SystemMessage, ToolMessage
from langchain.tools import BaseTool, ToolException, tool
from langgraph.types import Command


SKILL_FILE = "SKILL.md"
MAX_OUTPUT_CHARS = 20_000

FRONTMATTER_PATTERN = re.compile(r"\A---[ \t]*\r?\n(.*?)\r?\n---[ \t]*(?:\r?\n|\Z)", re.DOTALL)


@dataclass(frozen=True)
class Skill:
    """A skill discovered on disk."""

    name: str
    description: str
    directory: Path
    # Names of the skills that are loaded together with this one
    requires: tuple[str, ...] = ()
    # Hidden skills are not listed in the system prompt: they are only loaded as a requirement of other skills
    hidden: bool = False

    def instructions(self) -> str:
        """Return the markdown body of the skill's SKILL.md.

        The file is read on every call so edits are picked up without restarting the agent.
        """
        _, body = parse_skill_file((self.directory / SKILL_FILE).read_text(encoding="utf-8"))
        return body.strip()

    def bundled_files(self) -> list[str]:
        """Return the paths, relative to the skill directory, of the files bundled with the skill.

        SKILL.md itself is excluded, as is any path with a component starting with ``_`` or ``.``
        (helper modules, caches, hidden files): those are private to the skill.
        """
        files = []
        for path in self.directory.rglob("*"):
            relative = path.relative_to(self.directory)
            private = any(part.startswith(("_", ".")) for part in relative.parts)
            if path.is_file() and not private and relative != Path(SKILL_FILE):
                files.append(relative.as_posix())
        return sorted(files)

    def resolve(self, relative_path: str) -> Path | None:
        """Return the absolute path of a bundled file, or None if the skill does not list it.

        Checking against the listed files also rejects paths that escape the skill directory.
        """
        path = (self.directory / relative_path).resolve()
        if path.is_relative_to(self.directory) and path.relative_to(self.directory).as_posix() in self.bundled_files():
            return path
        return None


def parse_skill_file(text: str) -> tuple[dict, str]:
    """
    Split the contents of a SKILL.md file into its YAML frontmatter and markdown body.

    :param text: Contents of a SKILL.md file
    :type text: str
    :return: The frontmatter as a dict (empty if there is none) and the markdown body
    :rtype: tuple[dict, str]
    """
    match = FRONTMATTER_PATTERN.match(text)
    if not match:
        return {}, text
    metadata = yaml.safe_load(match.group(1)) or {}
    if not isinstance(metadata, dict):
        raise ValueError("frontmatter must be a YAML mapping")
    return metadata, text[match.end():]


def read_skill(skill_file: Path) -> Skill:
    """
    Create a skill from the frontmatter of its SKILL.md file.

    :param skill_file: Path of the SKILL.md file
    :type skill_file: Path
    :return: The skill
    :rtype: Skill
    :raises ValueError: If the frontmatter is invalid
    """
    metadata, _ = parse_skill_file(skill_file.read_text(encoding="utf-8"))
    description = " ".join(str(metadata.get("description") or "").split())
    if not description:
        raise ValueError("missing 'description' in frontmatter")

    name = str(metadata.get("name") or skill_file.parent.name)
    # A single required skill may be given as a plain name
    requires = metadata.get("requires") or []
    if isinstance(requires, str):
        requires = [requires]
    if not isinstance(requires, list) or not all(isinstance(required, str) for required in requires):
        raise ValueError("'requires' in frontmatter must be a list of skill names")
    return Skill(name, description, skill_file.parent.resolve(), tuple(requires), metadata.get("hidden") is True)


def discover_skills(directories: list[str]) -> dict[str, Skill]:
    """
    Find the skills defined as ``<directory>/<skill>/SKILL.md`` in each of the given directories.

    Invalid skills, and skills that require a skill that is not available, are skipped with a
    warning. When two skills share a name the first one found wins, so earlier directories take
    precedence.

    :param directories: Directories to scan for skills, in order of precedence
    :type directories: list[str]
    :return: The discovered skills, keyed by name
    :rtype: dict[str, Skill]
    """
    skills = {}
    for directory in directories:
        for skill_file in sorted(Path(directory).glob(f"*/{SKILL_FILE}")):
            try:
                skill = read_skill(skill_file)
            except (OSError, ValueError, yaml.YAMLError) as e:
                print(f"Skipping skill {skill_file}: {e}")
                continue

            if skill.name in skills:
                print(f"Skipping skill {skill_file}: skill '{skill.name}' is already defined in {skills[skill.name].directory}")
            else:
                skills[skill.name] = skill

    # Skipping a skill can leave the skills that require it incomplete, so repeat until none is missing a requirement
    while incomplete := [skill for skill in skills.values() if not skills.keys() >= set(skill.requires)]:
        for skill in incomplete:
            missing = ", ".join(name for name in skill.requires if name not in skills)
            print(f"Skipping skill {skill.directory / SKILL_FILE}: it requires skills that are not available: {missing}")
            del skills[skill.name]
    return skills


def get_skill(skills: dict[str, Skill], name: str) -> Skill:
    """
    Return the skill with the given name.

    :param skills: The available skills, keyed by name
    :type skills: dict[str, Skill]
    :param name: Name of the skill
    :type name: str
    :return: The skill
    :rtype: Skill
    :raises ToolException: If there is no such skill, with a message for the model
    """
    if name not in skills:
        listed = ", ".join(skill.name for skill in skills.values() if not skill.hidden)
        raise ToolException(f"Unknown skill '{name}'. Available skills: {listed}.")
    return skills[name]


def find_bundled_file(skills: dict[str, Skill], skill_name: str, relative_path: str) -> tuple[Skill, Path]:
    """
    Find a file bundled with a skill.

    :param skills: The available skills, keyed by name
    :type skills: dict[str, Skill]
    :param skill_name: Name of the skill that bundles the file. If empty, every skill is searched
    :type skill_name: str
    :param relative_path: Path of the file relative to the skill directory
    :type relative_path: str
    :return: The skill that bundles the file and the file's absolute path
    :rtype: tuple[Skill, Path]
    :raises ToolException: If no file, or more than one, matches, with a message for the model
    """
    # Models often drop skill_name once a skill is loaded, so without it look the path up in every skill
    candidates = [get_skill(skills, skill_name)] if skill_name else list(skills.values())
    matches = [(skill, path) for skill in candidates if (path := skill.resolve(relative_path))]
    if len(matches) == 1:
        return matches[0]
    if matches:
        names = ", ".join(skill.name for skill, _ in matches)
        raise ToolException(f"Several skills have a file '{relative_path}' ({names}). Pass skill_name to pick one.")
    if skill_name:
        files = ", ".join(candidates[0].bundled_files()) or "none"
        raise ToolException(f"Skill '{skill_name}' has no file '{relative_path}'. Bundled files: {files}.")
    raise ToolException(f"No skill has a file '{relative_path}'. Call load_skill to see the files of a skill.")


def truncate(text: str) -> str:
    """Cap tool output so a single call cannot flood the model's context."""
    if len(text) <= MAX_OUTPUT_CHARS:
        return text
    return f"{text[:MAX_OUTPUT_CHARS]}\n... [truncated {len(text) - MAX_OUTPUT_CHARS} characters]"


class SkillsMiddleware(AgentMiddleware):
    """
    Agent middleware that gives the model access to local skills.

    Appends the name and description of every skill that is not hidden to the system prompt and
    registers the ``load_skill`` and ``read_skill_file`` tools. It adds no other tools: skills say
    what to do, and the model does it with the tools registered with the agent.
    """

    def __init__(self, skills: dict[str, Skill]):
        """
        Set up the skills available to the agent.

        :param skills: The skills, keyed by name, as returned by ``discover_skills``
        :type skills: dict[str, Skill]
        """
        self.skills = skills
        self.tools = self._create_tools() if self.skills else []
        # Spell out the load_skill call for each skill: small models otherwise try to call skill names as tools
        listing = "\n".join(
            f'- {skill.name}: {skill.description} To use it, call load_skill(skill_name="{skill.name}").'
            for skill in self.skills.values()
            if not skill.hidden
        )
        self._prompt = listing and (
            "## Skills\n\n"
            "A skill packages the instructions, and any deterministic scripts, for one kind of task, and is "
            "more reliable than your own knowledge. Skills are not tools and cannot be called directly: whenever "
            "a request is covered by the description of a skill, first call the load_skill tool with the "
            "skill's name, then follow the instructions it returns. Skills take priority over tools: load the "
            "matching skill even if one of your tools could handle the request directly. Never answer such a "
            "request from memory or by calculating the result yourself. The same priority holds inside a skill: "
            "when its instructions tell you to run a script or command, first load the skill whose description "
            "covers running it, unless you already have, and only if there is none run it with your tools. "
            "A skill says what to do, not which tool to use: pick the tool for each step from the descriptions of "
            "your tools. If none of your tools can do a step, tell the user instead of guessing the result.\n\n"
            f"Available skills:\n{listing}"
        )

    def wrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], ModelResponse],
    ) -> ModelResponse:
        """Inject the available skills into the system prompt."""
        return handler(self._with_prompt(request))

    async def awrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], Awaitable[ModelResponse]],
    ) -> ModelResponse:
        """Inject the available skills into the system prompt."""
        return await handler(self._with_prompt(request))

    def _with_prompt(self, request: ModelRequest) -> ModelRequest:
        if not self._prompt:
            return request
        blocks = list(request.system_message.content_blocks) if request.system_message else []
        return request.override(system_message=SystemMessage(content=[*blocks, {"type": "text", "text": self._prompt}]))

    def wrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], ToolMessage | Command],
    ) -> ToolMessage | Command:
        """Tell the model how to load a skill that it called as a tool."""
        redirect = self._redirect_skill_call(request)
        return redirect if redirect is not None else handler(request)

    async def awrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], Awaitable[ToolMessage | Command]],
    ) -> ToolMessage | Command:
        """Tell the model how to load a skill that it called as a tool."""
        redirect = self._redirect_skill_call(request)
        return redirect if redirect is not None else await handler(request)

    def _redirect_skill_call(self, request: ToolCallRequest) -> ToolMessage | None:
        """Tell the model how to load a skill it called as a tool.

        Small models call skills as tools, and LangChain's invalid tool message would not tell them what to do.
        """
        name = request.tool_call["name"]
        if request.tool is not None or name not in self.skills:
            return None
        message = (
            f"'{name}' is a skill, not a tool. Call load_skill(skill_name=\"{name}\") if you have not yet, "
            "then follow the instructions it returns."
        )
        return ToolMessage(message, name=name, tool_call_id=request.tool_call["id"], status="error")

    def _with_requirements(self, skill: Skill) -> list[Skill]:
        """Return the skills that the skill requires, directly or indirectly, followed by the skill itself."""
        ordered = []
        visited = set()

        def visit(current: Skill) -> None:
            # Visited skills are skipped, so every skill is listed once and cyclic requirements terminate
            if current.name in visited:
                return
            visited.add(current.name)
            for name in current.requires:
                visit(self.skills[name])
            ordered.append(current)

        visit(skill)
        return ordered

    @staticmethod
    def _describe(skill: Skill, loaded_skills: list[Skill]) -> str:
        """Return what load_skill tells the model: the instructions and bundled files of the loaded skills.

        :raises ToolException: If the SKILL.md of a loaded skill cannot be read
        """
        sections = []
        # Required skills come first, so the model knows what they provide when it reads the skill that uses them
        for loaded in loaded_skills:
            heading = f"# Skill: {loaded.name}"
            if loaded is not skill:
                heading += f" (required by {skill.name})"
            try:
                sections += [heading, loaded.instructions()]
            except (OSError, ValueError, yaml.YAMLError) as e:
                raise ToolException(f"Could not load skill '{loaded.name}': {e}") from e

            files = loaded.bundled_files()
            if files:
                sections.append(
                    f"## Files bundled with {loaded.name}\n\n"
                    + "\n".join(f"- {file}" for file in files)
                    + "\n\nUse them as the instructions above describe. Skills take priority over tools here too: "
                    "before running a script, call load_skill for the skill whose description covers running it, "
                    "unless you already have, and only if no skill covers it run the script with your tools. "
                    "Only read a file when the instructions tell you to, by calling "
                    f'read_skill_file(skill_name="{loaded.name}", path="<file>").'
                )
        return "\n\n".join(sections)

    def _create_tools(self) -> list[BaseTool]:
        @tool(parse_docstring=True)
        async def load_skill(skill_name: str) -> str:
            """Load the full instructions of a skill, and of the skills it requires, and list the files bundled with them.

            Args:
                skill_name: Name of the skill, as listed under "Available skills".
            """
            skill = get_skill(self.skills, skill_name)
            # Reading the skill files must not block the event loop that `langgraph dev` runs this on
            return await asyncio.to_thread(self._describe, skill, self._with_requirements(skill))

        @tool(parse_docstring=True)
        def read_skill_file(path: str, skill_name: str = "") -> str:
            """Read a file bundled with a skill, such as a reference document mentioned in its instructions.

            Args:
                path: Path of the file relative to the skill directory, e.g. "references/guide.md".
                skill_name: Name of the skill that bundles the file. Can be omitted when only one skill has this path.
            """
            _, file = find_bundled_file(self.skills, skill_name, path)
            try:
                return truncate(file.read_text(encoding="utf-8", errors="replace"))
            except OSError as e:
                raise ToolException(f"Could not read '{path}': {e}") from e

        tools = [load_skill, read_skill_file]
        for skill_tool in tools:
            # Return ToolException messages to the model instead of aborting the agent run
            skill_tool.handle_tool_error = True
        return tools
