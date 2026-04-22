"""Core agent loop — orchestrates LLM reasoning with tool execution."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

from analyzer.config import Config
from analyzer.llm.client import LLMClient, TOOL_DEFINITIONS
from analyzer.llm.prompts import SYSTEM_PROMPT, INITIAL_ANALYSIS_PROMPT, make_question_prompt
from analyzer.tools import filesystem, ast_parser, git_tools, search

console = Console()


class ToolExecutor:
    """Dispatches tool calls from the LLM to the actual tool implementations."""

    def __init__(self, repo_path: str):
        self.repo_path = repo_path

    def execute(self, tool_name: str, arguments: dict[str, Any]) -> str:
        """Execute a tool and return its string output."""
        try:
            return self._dispatch(tool_name, arguments)
        except Exception as exc:
            return f"Tool error ({tool_name}): {exc}"

    def _dispatch(self, name: str, args: dict[str, Any]) -> str:
        match name:
            # --- Filesystem tools ---
            case "list_directory":
                return filesystem.list_directory(self.repo_path, args.get("relative_dir", "."))
            case "get_directory_tree":
                return filesystem.get_directory_tree(self.repo_path, args.get("max_depth", 3))
            case "read_file":
                return filesystem.read_file(
                    self.repo_path, args["relative_path"], args.get("max_lines", 500)
                )
            case "find_files":
                return filesystem.find_files(self.repo_path, args["pattern"])
            case "get_file_summary":
                return filesystem.get_file_summary(self.repo_path)
            case "find_high_signal_files":
                return filesystem.find_high_signal_files(self.repo_path)

            # --- AST / structure tools ---
            case "analyze_file_structure":
                source = filesystem.read_file(self.repo_path, args["relative_path"])
                if source.startswith("Error:") or source.startswith("[Binary"):
                    return source
                return ast_parser.analyze_file_structure(source, args["relative_path"])

            # --- Search tools ---
            case "grep_search":
                return search.grep_in_repo(
                    self.repo_path,
                    args["pattern"],
                    file_glob=args.get("file_glob"),
                    case_sensitive=args.get("case_sensitive", False),
                )
            case "find_symbol":
                return search.find_symbol(self.repo_path, args["symbol_name"])
            case "find_references":
                return search.find_references(self.repo_path, args["symbol_name"])

            # --- Git tools ---
            case "get_git_summary":
                return git_tools.get_git_summary(self.repo_path)
            case "get_recent_commits":
                return git_tools.get_recent_commits(self.repo_path, args.get("count", 15))
            case "get_commit_details":
                return git_tools.get_commit_details(self.repo_path, args["commit_hash"])
            case "get_most_changed_files":
                return git_tools.get_most_changed_files(self.repo_path, args.get("count", 20))
            case "get_file_history":
                return git_tools.get_file_history(
                    self.repo_path, args["relative_path"], args.get("count", 10)
                )

            case _:
                return f"Unknown tool: {name}"


class Agent:
    """The agentic codebase analyzer.

    Runs an iterative loop:
      1. Send messages (including tool definitions) to the LLM.
      2. If the LLM requests tool calls, execute them and feed results back.
      3. Repeat until the LLM produces a final text response or the
         iteration limit is reached.
    """

    def __init__(self, repo_path: str, config: Config):
        self.repo_path = str(Path(repo_path).resolve())
        self.config = config
        self.llm = LLMClient(config)
        self.executor = ToolExecutor(self.repo_path)
        self.messages: list[dict[str, Any]] = [
            {"role": "system", "content": SYSTEM_PROMPT},
        ]
        self._iteration = 0

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def analyze(self) -> str:
        """Run a full repository analysis and return the final report."""
        repo_name = Path(self.repo_path).name
        console.print(
            Panel(f"Analyzing repository: [bold]{repo_name}[/bold]\n{self.repo_path}",
                  title="Codebase Analyzer", border_style="blue")
        )
        prompt = (
            f"The repository is located at: {self.repo_path}\n\n"
            f"{INITIAL_ANALYSIS_PROMPT}"
        )
        return self._run(prompt)

    def ask(self, question: str) -> str:
        """Answer a developer question about the repository."""
        prompt = (
            f"The repository is located at: {self.repo_path}\n\n"
            f"{make_question_prompt(question)}"
        )
        return self._run(prompt)

    # ------------------------------------------------------------------
    # Agent loop
    # ------------------------------------------------------------------

    def _run(self, user_prompt: str) -> str:
        """Execute the agent loop for a given user prompt."""
        self.messages.append({"role": "user", "content": user_prompt})
        self._iteration = 0

        while self._iteration < self.config.max_agent_iterations:
            self._iteration += 1
            console.print(
                f"  [dim]Agent iteration {self._iteration}/{self.config.max_agent_iterations}[/dim]"
            )

            response = self.llm.chat(self.messages, tools=TOOL_DEFINITIONS)

            # Check for tool calls
            tool_calls = self.llm.parse_tool_calls(response)

            if not tool_calls:
                # The LLM produced a final answer
                final = response.content or ""
                self.messages.append({"role": "assistant", "content": final})
                return final

            # The LLM wants to call tools — execute them
            # First, append the assistant message with tool calls
            self.messages.append({
                "role": "assistant",
                "content": response.content,
                "tool_calls": [
                    {
                        "id": tc["id"],
                        "type": "function",
                        "function": {
                            "name": tc["name"],
                            "arguments": _serialize_args(tc["arguments"]),
                        },
                    }
                    for tc in tool_calls
                ],
            })

            for tc in tool_calls:
                console.print(f"    [cyan]→ {tc['name']}[/cyan]({_brief_args(tc['arguments'])})")
                result = self.executor.execute(tc["name"], tc["arguments"])
                self.messages.append({
                    "role": "tool",
                    "tool_call_id": tc["id"],
                    "content": result,
                })

        return (
            "⚠ Reached the maximum number of agent iterations "
            f"({self.config.max_agent_iterations}). "
            "The analysis may be incomplete. Try asking a more specific question."
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _serialize_args(args: dict) -> str:
    import json
    return json.dumps(args)


def _brief_args(args: dict) -> str:
    """Create a short string representation of tool arguments for logging."""
    parts = []
    for k, v in args.items():
        val = str(v)
        if len(val) > 60:
            val = val[:57] + "..."
        parts.append(f"{k}={val}")
    return ", ".join(parts)
