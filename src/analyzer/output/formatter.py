"""Output formatting utilities."""

from __future__ import annotations

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

console = Console()


def print_analysis(report: str) -> None:
    """Render the final analysis report using Rich."""
    console.print()
    console.print(Panel(Markdown(report), title="Analysis Report", border_style="green", padding=(1, 2)))
    console.print()


def print_answer(answer: str) -> None:
    """Render an answer to a developer question."""
    console.print()
    console.print(Panel(Markdown(answer), title="Answer", border_style="cyan", padding=(1, 2)))
    console.print()


def print_error(message: str) -> None:
    """Print an error message."""
    console.print(f"\n[bold red]Error:[/bold red] {message}\n")


def print_info(message: str) -> None:
    """Print an informational message."""
    console.print(f"[dim]{message}[/dim]")
