"""Code search utilities for the agent."""

from __future__ import annotations

import re
from pathlib import Path

from analyzer.tools.filesystem import _IGNORED_DIRS, _BINARY_EXTENSIONS


def grep_in_repo(
    repo_path: str,
    pattern: str,
    *,
    file_glob: str | None = None,
    max_results: int = 30,
    case_sensitive: bool = False,
) -> str:
    """Search for a regex *pattern* across files in the repository.

    Returns matching lines with file paths and line numbers.
    """
    root = Path(repo_path)
    flags = 0 if case_sensitive else re.IGNORECASE
    try:
        compiled = re.compile(pattern, flags)
    except re.error as exc:
        return f"Invalid regex pattern: {exc}"

    results: list[str] = []
    glob_pattern = file_glob or "**/*"

    for filepath in root.glob(glob_pattern):
        if not filepath.is_file():
            continue
        if any(part in _IGNORED_DIRS for part in filepath.parts):
            continue
        if filepath.suffix.lower() in _BINARY_EXTENSIONS:
            continue

        try:
            text = filepath.read_text(errors="replace")
        except (PermissionError, OSError):
            continue

        rel = str(filepath.relative_to(root))
        for lineno, line in enumerate(text.splitlines(), 1):
            if compiled.search(line):
                results.append(f"{rel}:{lineno}: {line.rstrip()}")
                if len(results) >= max_results:
                    break
        if len(results) >= max_results:
            break

    if not results:
        return f"No matches found for pattern '{pattern}'."

    output = "\n".join(results)
    if len(results) >= max_results:
        output += f"\n\n... [showing first {max_results} results]"
    return output


def find_symbol(repo_path: str, symbol_name: str, max_results: int = 20) -> str:
    """Find definitions of a symbol (class, function, variable) in the codebase.

    Searches for common definition patterns across popular languages.
    """
    # Patterns that indicate a definition rather than a usage
    def_patterns = [
        rf"\bclass\s+{re.escape(symbol_name)}\b",
        rf"\bdef\s+{re.escape(symbol_name)}\b",
        rf"\bfunction\s+{re.escape(symbol_name)}\b",
        rf"\bconst\s+{re.escape(symbol_name)}\b",
        rf"\blet\s+{re.escape(symbol_name)}\b",
        rf"\bvar\s+{re.escape(symbol_name)}\b",
        rf"\binterface\s+{re.escape(symbol_name)}\b",
        rf"\btype\s+{re.escape(symbol_name)}\b",
        rf"\bstruct\s+{re.escape(symbol_name)}\b",
        rf"\benum\s+{re.escape(symbol_name)}\b",
        rf"\bfn\s+{re.escape(symbol_name)}\b",
        rf"\bfunc\s+{re.escape(symbol_name)}\b",
    ]
    combined = "|".join(def_patterns)
    return grep_in_repo(repo_path, combined, max_results=max_results)


def find_references(repo_path: str, symbol_name: str, max_results: int = 30) -> str:
    """Find all references to a symbol in the codebase."""
    return grep_in_repo(
        repo_path,
        rf"\b{re.escape(symbol_name)}\b",
        max_results=max_results,
    )
