"""Data models for repository analysis."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class FileInfo:
    """Metadata about a single file."""
    path: str
    extension: str
    size_bytes: int
    language: str | None = None


@dataclass
class ComponentInfo:
    """A discovered architectural component (module, service, package)."""
    name: str
    path: str
    description: str = ""
    files: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)


@dataclass
class RepositoryProfile:
    """Aggregated profile of a repository built during analysis."""
    root_path: str
    name: str = ""
    languages: list[str] = field(default_factory=list)
    frameworks: list[str] = field(default_factory=list)
    total_files: int = 0
    entry_points: list[str] = field(default_factory=list)
    components: list[ComponentInfo] = field(default_factory=list)
    architecture_pattern: str = ""
    has_git: bool = False
    has_tests: bool = False
    has_ci: bool = False
    has_docker: bool = False

    def summary_dict(self) -> dict:
        return {
            "name": self.name,
            "languages": self.languages,
            "frameworks": self.frameworks,
            "total_files": self.total_files,
            "architecture": self.architecture_pattern,
            "entry_points": self.entry_points,
            "components": [c.name for c in self.components],
            "has_git": self.has_git,
            "has_tests": self.has_tests,
            "has_ci": self.has_ci,
            "has_docker": self.has_docker,
        }
