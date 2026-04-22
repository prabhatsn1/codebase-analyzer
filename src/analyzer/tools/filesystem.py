"""File system exploration tools for the agent."""

from __future__ import annotations

import os
from pathlib import Path

# Directories / patterns that are almost never useful to explore
_IGNORED_DIRS = {
    ".git", "__pycache__", "node_modules", ".venv", "venv", ".tox",
    ".mypy_cache", ".pytest_cache", ".ruff_cache", "dist", "build",
    ".eggs", ".next", ".nuxt", "target", "bin", "obj", ".idea",
    ".vscode", ".vs", "coverage", ".angular", ".cache",
}

_BINARY_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".ico", ".svg", ".webp",
    ".woff", ".woff2", ".ttf", ".eot", ".otf",
    ".zip", ".tar", ".gz", ".bz2", ".7z", ".rar",
    ".pdf", ".doc", ".docx", ".xls", ".xlsx",
    ".exe", ".dll", ".so", ".dylib", ".o", ".a",
    ".pyc", ".pyo", ".class", ".jar", ".war",
    ".mp3", ".mp4", ".avi", ".mov", ".wav",
    ".sqlite", ".db", ".lock",
}

# High-signal files that the agent should inspect first
HIGH_SIGNAL_FILES = [
    "README.md", "README.rst", "README.txt", "README",
    "pyproject.toml", "setup.py", "setup.cfg",
    "package.json", "tsconfig.json",
    "Cargo.toml", "go.mod", "pom.xml", "build.gradle", "build.gradle.kts",
    "Makefile", "CMakeLists.txt",
    "Dockerfile", "docker-compose.yml", "docker-compose.yaml",
    ".env.example", ".env.sample",
    "requirements.txt", "Pipfile", "Gemfile", "composer.json",
    "manage.py", "app.py", "main.py", "index.ts", "index.js",
    "settings.py", "config.py", "config.ts", "config.js",
]


def list_directory(repo_path: str, relative_dir: str = ".") -> str:
    """List the contents of a directory with type indicators.

    Returns a formatted string with one entry per line.
    Directories end with '/'.
    """
    target = Path(repo_path) / relative_dir
    if not target.is_dir():
        return f"Error: '{relative_dir}' is not a directory."

    entries: list[str] = []
    try:
        for item in sorted(target.iterdir()):
            name = item.name
            if name in _IGNORED_DIRS:
                continue
            if item.is_dir():
                entries.append(f"{name}/")
            else:
                entries.append(name)
    except PermissionError:
        return f"Error: Permission denied for '{relative_dir}'."

    if not entries:
        return "(empty directory)"
    return "\n".join(entries)


def get_directory_tree(repo_path: str, max_depth: int = 3) -> str:
    """Build a visual tree of the repository up to *max_depth* levels.

    Ignores common non-essential directories and binary files.
    """
    root = Path(repo_path)
    lines: list[str] = [root.name + "/"]

    def _walk(directory: Path, prefix: str, depth: int) -> None:
        if depth > max_depth:
            return
        try:
            children = sorted(directory.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
        except PermissionError:
            return

        visible = [c for c in children if c.name not in _IGNORED_DIRS]
        for i, child in enumerate(visible):
            is_last = i == len(visible) - 1
            connector = "└── " if is_last else "├── "
            if child.is_dir():
                lines.append(f"{prefix}{connector}{child.name}/")
                extension = "    " if is_last else "│   "
                _walk(child, prefix + extension, depth + 1)
            else:
                lines.append(f"{prefix}{connector}{child.name}")

    _walk(root, "", 1)
    return "\n".join(lines)


def read_file(repo_path: str, relative_path: str, max_lines: int = 500) -> str:
    """Read a file and return its contents, capped at *max_lines*.

    Returns an error string for binary or unreadable files.
    """
    file_path = Path(repo_path) / relative_path
    if not file_path.is_file():
        return f"Error: '{relative_path}' is not a file or does not exist."

    if file_path.suffix.lower() in _BINARY_EXTENSIONS:
        return f"[Binary file: {relative_path} ({file_path.stat().st_size:,} bytes)]"

    try:
        text = file_path.read_text(errors="replace")
    except PermissionError:
        return f"Error: Permission denied for '{relative_path}'."

    lines = text.splitlines(keepends=True)
    if len(lines) > max_lines:
        truncated = "".join(lines[:max_lines])
        return truncated + f"\n\n... [truncated — showing {max_lines}/{len(lines)} lines]"
    return text


def find_files(repo_path: str, pattern: str, max_results: int = 50) -> str:
    """Find files matching a glob *pattern* relative to the repo root.

    Example patterns: '**/*.py', 'src/**/*.ts', '**/test_*.py'.
    """
    root = Path(repo_path)
    matches: list[str] = []
    for path in root.glob(pattern):
        if any(part in _IGNORED_DIRS for part in path.parts):
            continue
        if path.is_file():
            matches.append(str(path.relative_to(root)))
            if len(matches) >= max_results:
                break
    if not matches:
        return f"No files found matching '{pattern}'."
    result = "\n".join(sorted(matches))
    if len(matches) >= max_results:
        result += f"\n\n... [showing first {max_results} results]"
    return result


def get_file_summary(repo_path: str) -> str:
    """Return a summary of file counts by extension in the repository."""
    root = Path(repo_path)
    ext_counts: dict[str, int] = {}
    total = 0
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in _IGNORED_DIRS]
        for fname in filenames:
            ext = Path(fname).suffix.lower() or "(no extension)"
            ext_counts[ext] = ext_counts.get(ext, 0) + 1
            total += 1

    sorted_exts = sorted(ext_counts.items(), key=lambda x: -x[1])
    lines = [f"Total files: {total}", ""]
    for ext, count in sorted_exts[:30]:
        lines.append(f"  {ext:20s} {count:>5d}")
    if len(sorted_exts) > 30:
        lines.append(f"  ... and {len(sorted_exts) - 30} more extensions")
    return "\n".join(lines)


def find_high_signal_files(repo_path: str) -> str:
    """Identify high-signal files present in the repository root."""
    root = Path(repo_path)
    found: list[str] = []
    for name in HIGH_SIGNAL_FILES:
        if (root / name).is_file():
            found.append(name)
    # Also check for common entry-point patterns in subdirectories
    for pattern in ["**/main.*", "**/app.*", "**/index.*", "**/server.*"]:
        for path in root.glob(pattern):
            if any(part in _IGNORED_DIRS for part in path.parts):
                continue
            rel = str(path.relative_to(root))
            if rel not in found and path.is_file():
                found.append(rel)
    if not found:
        return "No high-signal files found."
    return "\n".join(found)
