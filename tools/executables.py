"""The tool that runs the command lines shown by skills.

Skills say what has to be done and never name a tool: they show their scripts as plain command lines,
such as ``python scripts/example.py --name value``. The ``run_executable`` tool created here is bound to
the model, and its description says how to turn such a command line into a call, so the model picks it
from that description. A skill that covers running a kind of command can add what to know about it, and
does not name this tool either.
It only runs the executables it is configured with, such as a Python interpreter, in the directory of a
skill.
"""
import os
import re
import shlex
import subprocess
from collections.abc import Mapping
from dataclasses import dataclass, field

from langchain.tools import BaseTool, ToolException, tool

from agent.skills_middleware import Skill, find_bundled_file, get_skill, truncate


SCRIPTS_DIR = "scripts"
TIMEOUT_SECONDS = 30
# An argument that is only pipes, command separators or redirections, such as `|`, `&&` or `>`
SHELL_OPERATOR = re.compile(r"[|&;<>]+")


@dataclass(frozen=True)
class Executable:
    """An executable that skills can run."""

    path: str
    # Suffixes of the scripts the executable runs, such as (".py",) for an interpreter. When set, the first argument
    # must be a script bundled with the skill, so the executable cannot run code the model wrote, e.g. `python -c`
    script_suffixes: tuple[str, ...] = ()
    # Environment variables for the executable, on top of the agent's
    env: Mapping[str, str] = field(default_factory=dict)


def create_executable_tool(skills: dict[str, Skill], executables: dict[str, Executable]) -> BaseTool:
    """
    Create the ``run_executable`` tool, which runs the given executables for the given skills.

    An executable runs in a subprocess whose working directory is the skill directory, without a
    shell and with a timeout. Only the given executables can be run. An executable that runs scripts
    only runs the scripts in a skill's ``scripts/`` directory, and not private ones such as
    ``scripts/_common.py``.

    :param skills: The skills to run executables for, keyed by name, as returned by ``discover_skills``
    :type skills: dict[str, Skill]
    :param executables: The executables that can be run, keyed by the name skills give them, e.g. "python"
    :type executables: dict[str, Executable]
    :return: The tool. When an executable cannot be run or fails, it returns the error to the model as an error
        ``ToolMessage``
    :rtype: BaseTool
    """
    @tool(parse_docstring=True)
    def run_executable(executable: str, executable_args: str = "", skill_name: str = "") -> str:
        """Run a command line from the instructions of a loaded skill and return what it printed.

        Whenever skill instructions show a command such as `python scripts/example.py --name value`, run it with this tool and answer from its output: never work out the output yourself. Split the command line in two: executable is its first word and executable_args is everything after it, with the example values replaced by the values for the request. So `python scripts/example.py --name value` from the example skill becomes run_executable(executable="python", executable_args="scripts/example.py --name value", skill_name="example").

        Each call runs exactly one command, without a shell: never put a command inside the arguments of another with $(...) or backticks, and never use pipes (|), ; or && or redirections (>). When a command needs a value that another command prints, run that command first in its own call, then copy the value from its output into the arguments of the next call.

        A command that fails returns its exit code and error message: fix the arguments and run it again.

        Args:
            executable: First word of the command line, e.g. "python".
            executable_args: Everything after the first word, as one string, e.g. "scripts/example.py --name value". Quote values that contain spaces, e.g. --city "New York".
            skill_name: Name of the skill whose instructions show the command, e.g. "example".
        """
        if executable not in executables:
            names = ", ".join(executables) or "none"
            raise ToolException(f"Unknown executable '{executable}'. Available executables: {names}.")
        config = executables[executable]
        try:
            argv = shlex.split(executable_args)
        except ValueError as e:
            raise ToolException(f"Could not parse executable_args {executable_args!r}: {e}") from e
        command = shlex.join([executable, *argv])
        # Without a shell such syntax would reach the executable verbatim, and its error would not say what went wrong
        shell_syntax = next((arg for arg in argv if "$(" in arg or "`" in arg or SHELL_OPERATOR.fullmatch(arg)), None)
        if shell_syntax is not None:
            raise ToolException(
                f"executable_args contain shell syntax ({shell_syntax!r}), but each call runs exactly one command "
                "without a shell, so $(...), backticks, pipes, ;, && and redirections do not work. Run each command "
                "in its own call, then copy the values you need from its output into the arguments of the next call."
            )

        if config.script_suffixes:
            if not argv:
                raise ToolException(
                    f"'{executable}' runs scripts: executable_args must start with the path of a script bundled "
                    f'with the skill, e.g. "{SCRIPTS_DIR}/example{config.script_suffixes[0]}".'
                )
            skill, script = find_bundled_file(skills, skill_name, argv[0])
            if not script.is_relative_to(skill.directory / SCRIPTS_DIR) or script.suffix not in config.script_suffixes:
                raise ToolException(
                    f"'{argv[0]}' is not a script '{executable}' can run: scripts must live in {SCRIPTS_DIR}/ "
                    f"and end in {', '.join(config.script_suffixes)}."
                )
            argv[0] = str(script)
        elif skill_name:
            skill = get_skill(skills, skill_name)
        else:
            raise ToolException(f"Pass skill_name: '{executable}' runs in the directory of the skill that describes it.")

        try:
            # No shell: arguments reach the executable verbatim and cannot run other commands
            result = subprocess.run(
                [config.path, *argv],
                cwd=skill.directory,
                env={**os.environ, **config.env},
                capture_output=True,
                text=True,
                timeout=TIMEOUT_SECONDS,
            )
        except subprocess.TimeoutExpired as e:
            raise ToolException(f"'{command}' timed out after {TIMEOUT_SECONDS} seconds.") from e
        except OSError as e:
            raise ToolException(f"Could not run '{executable}': {e}") from e

        output = truncate("\n".join(stream.strip() for stream in (result.stdout, result.stderr) if stream.strip()))
        if result.returncode != 0:
            raise ToolException(f"'{command}' failed with exit code {result.returncode}:\n{output}")
        return output or "(no output)"

    # A docstring cannot hold the configuration, and the model needs it to tell which commands it can run
    run_executable.description += (
        f" Commands are stopped after {TIMEOUT_SECONDS} seconds. Available executables: {', '.join(executables) or 'none'}."
    )
    # Return ToolException messages to the model, so it can fix the command, instead of aborting the agent run
    run_executable.handle_tool_error = True
    return run_executable
