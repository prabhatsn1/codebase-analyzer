"""Git metadata extraction tools."""

from __future__ import annotations

import subprocess
from pathlib import Path


def _run_git(repo_path: str, *args: str) -> str:
    """Run a git command and return stdout, or an error string."""
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            return f"Git error: {result.stderr.strip()}"
        return result.stdout.strip()
    except FileNotFoundError:
        return "Error: git is not installed or not on PATH."
    except subprocess.TimeoutExpired:
        return "Error: git command timed out."


def is_git_repo(repo_path: str) -> bool:
    """Check whether the path is inside a Git repository."""
    return (Path(repo_path) / ".git").is_dir()


def get_recent_commits(repo_path: str, count: int = 15) -> str:
    """Return the most recent commits (one-line format)."""
    return _run_git(
        repo_path,
        "log",
        f"-{count}",
        "--oneline",
        "--no-decorate",
    )


def get_commit_details(repo_path: str, commit_hash: str) -> str:
    """Return details of a specific commit including changed files."""
    return _run_git(
        repo_path,
        "show",
        "--stat",
        "--format=Commit: %H%nAuthor: %an <%ae>%nDate:   %ai%n%n%s%n%n%b",
        commit_hash,
    )


def get_branch_info(repo_path: str) -> str:
    """Return the current branch and list of local branches."""
    current = _run_git(repo_path, "branch", "--show-current")
    branches = _run_git(repo_path, "branch", "--list")
    return f"Current branch: {current}\n\nBranches:\n{branches}"


def get_most_changed_files(repo_path: str, count: int = 20) -> str:
    """Identify the files with the most commits (hotspots)."""
    output = _run_git(
        repo_path,
        "log",
        "--all",
        "--name-only",
        "--pretty=format:",
    )
    if output.startswith("Error") or output.startswith("Git error"):
        return output

    file_counts: dict[str, int] = {}
    for line in output.splitlines():
        line = line.strip()
        if line:
            file_counts[line] = file_counts.get(line, 0) + 1

    sorted_files = sorted(file_counts.items(), key=lambda x: -x[1])[:count]
    if not sorted_files:
        return "No file change history found."

    lines = ["Most frequently changed files:"]
    for fname, cnt in sorted_files:
        lines.append(f"  {cnt:>4d} changes  {fname}")
    return "\n".join(lines)


def get_contributors(repo_path: str) -> str:
    """List contributors sorted by number of commits."""
    return _run_git(repo_path, "shortlog", "-sn", "--all", "--no-merges")


def get_file_history(repo_path: str, relative_path: str, count: int = 10) -> str:
    """Return the commit history for a specific file."""
    return _run_git(
        repo_path,
        "log",
        f"-{count}",
        "--oneline",
        "--follow",
        "--",
        relative_path,
    )


def get_git_summary(repo_path: str) -> str:
    """Return a high-level Git summary of the repository."""
    if not is_git_repo(repo_path):
        return "This directory is not a Git repository."

    parts: list[str] = []

    branch = get_branch_info(repo_path)
    parts.append(branch)

    commits = get_recent_commits(repo_path, 10)
    parts.append(f"\nRecent commits:\n{commits}")

    contributors = get_contributors(repo_path)
    if contributors and not contributors.startswith("Error"):
        parts.append(f"\nContributors:\n{contributors}")

    return "\n".join(parts)
