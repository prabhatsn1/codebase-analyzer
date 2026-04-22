"""LLM client abstraction — supports OpenAI, Azure OpenAI, and HuggingFace."""

from __future__ import annotations

import json
from typing import Any

from openai import AzureOpenAI, OpenAI

from analyzer.config import Config

# ---------------------------------------------------------------------------
# Tool definitions (OpenAI function-calling schema)
# ---------------------------------------------------------------------------

TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "list_directory",
            "description": "List the contents of a directory. Directories end with '/'.",
            "parameters": {
                "type": "object",
                "properties": {
                    "relative_dir": {
                        "type": "string",
                        "description": "Directory path relative to the repo root. Use '.' for root.",
                    }
                },
                "required": ["relative_dir"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_directory_tree",
            "description": "Get a visual tree of the repository structure up to a certain depth.",
            "parameters": {
                "type": "object",
                "properties": {
                    "max_depth": {
                        "type": "integer",
                        "description": "Maximum depth to traverse (default: 3).",
                    }
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read the contents of a file. Returns up to 500 lines.",
            "parameters": {
                "type": "object",
                "properties": {
                    "relative_path": {
                        "type": "string",
                        "description": "File path relative to the repo root.",
                    },
                    "max_lines": {
                        "type": "integer",
                        "description": "Maximum lines to read (default: 500).",
                    },
                },
                "required": ["relative_path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "find_files",
            "description": "Find files matching a glob pattern. Example: '**/*.py', 'src/**/*.ts'.",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {
                        "type": "string",
                        "description": "Glob pattern to match files.",
                    }
                },
                "required": ["pattern"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_file_summary",
            "description": "Get a summary of file counts by extension in the repository.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "find_high_signal_files",
            "description": "Identify important files (README, configs, entry points) in the repository.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "analyze_file_structure",
            "description": (
                "Parse a source file and extract structural information "
                "(classes, functions, imports, types). Supports Python, JS/TS, Java, Go, Rust."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "relative_path": {
                        "type": "string",
                        "description": "File path relative to the repo root.",
                    }
                },
                "required": ["relative_path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "grep_search",
            "description": "Search for a regex pattern across files in the repository. Returns matching lines with paths and line numbers.",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {
                        "type": "string",
                        "description": "Regex pattern to search for.",
                    },
                    "file_glob": {
                        "type": "string",
                        "description": "Optional glob to restrict search to certain files.",
                    },
                    "case_sensitive": {
                        "type": "boolean",
                        "description": "Whether the search is case-sensitive (default: false).",
                    },
                },
                "required": ["pattern"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "find_symbol",
            "description": "Find definitions of a symbol (class, function, variable) across the codebase.",
            "parameters": {
                "type": "object",
                "properties": {
                    "symbol_name": {
                        "type": "string",
                        "description": "Name of the symbol to find.",
                    }
                },
                "required": ["symbol_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "find_references",
            "description": "Find all references to a symbol in the codebase.",
            "parameters": {
                "type": "object",
                "properties": {
                    "symbol_name": {
                        "type": "string",
                        "description": "Name of the symbol to search for.",
                    }
                },
                "required": ["symbol_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_git_summary",
            "description": "Get a high-level Git summary: branches, recent commits, contributors.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_recent_commits",
            "description": "Get the most recent Git commits.",
            "parameters": {
                "type": "object",
                "properties": {
                    "count": {
                        "type": "integer",
                        "description": "Number of commits to show (default: 15).",
                    }
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_commit_details",
            "description": "Get details of a specific Git commit, including changed files.",
            "parameters": {
                "type": "object",
                "properties": {
                    "commit_hash": {
                        "type": "string",
                        "description": "The commit hash to inspect.",
                    }
                },
                "required": ["commit_hash"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_most_changed_files",
            "description": "Identify files with the most commits (change hotspots).",
            "parameters": {
                "type": "object",
                "properties": {
                    "count": {
                        "type": "integer",
                        "description": "Number of files to return (default: 20).",
                    }
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_file_history",
            "description": "Get the Git commit history for a specific file.",
            "parameters": {
                "type": "object",
                "properties": {
                    "relative_path": {
                        "type": "string",
                        "description": "File path relative to the repo root.",
                    },
                    "count": {
                        "type": "integer",
                        "description": "Number of commits to show (default: 10).",
                    },
                },
                "required": ["relative_path"],
            },
        },
    },
]


class LLMClient:
    """Thin wrapper around the OpenAI-compatible chat-completions API.

    Supports three providers:
    - openai      — OpenAI API
    - azure       — Azure OpenAI Service
    - huggingface — HuggingFace Inference API (OpenAI-compatible endpoint)
    """

    def __init__(self, config: Config):
        self.model = config.model
        self.max_tokens = config.max_tokens
        self.provider = config.provider

        if config.provider == "azure":
            self.client: OpenAI = AzureOpenAI(
                api_key=config.api_key,
                azure_endpoint=config.azure_endpoint,
                api_version=config.azure_api_version,
            )
        elif config.provider == "huggingface":
            self.client = OpenAI(
                base_url=config.hf_base_url,
                api_key=config.api_key,
            )
        else:  # openai (default)
            self.client = OpenAI(api_key=config.api_key)

    def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
    ) -> Any:
        """Send a chat completion request and return the response message."""
        kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "max_tokens": self.max_tokens,
            "temperature": 0.1,
        }
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"

        response = self.client.chat.completions.create(**kwargs)
        return response.choices[0].message

    def parse_tool_calls(self, message: Any) -> list[dict[str, Any]]:
        """Extract tool calls from a response message."""
        if not message.tool_calls:
            return []
        calls = []
        for tc in message.tool_calls:
            try:
                args = json.loads(tc.function.arguments)
            except json.JSONDecodeError:
                args = {}
            calls.append({
                "id": tc.id,
                "name": tc.function.name,
                "arguments": args,
            })
        return calls
