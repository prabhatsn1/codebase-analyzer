"""CLI entry point for the Codebase Analyzer."""

from __future__ import annotations

import sys
from pathlib import Path

import click

from analyzer.config import Config
from analyzer.output.formatter import print_analysis, print_answer, print_error, print_info


@click.group()
@click.version_option(version="0.1.0")
def cli() -> None:
    """Codebase Analyzer — an agentic AI that understands any repository."""


@cli.command()
@click.argument("repo_path", type=click.Path(exists=True, file_okay=False))
@click.option("--model", default=None, help="Model name/deployment to use.")
@click.option(
    "--provider",
    default=None,
    type=click.Choice(["openai", "azure", "huggingface"], case_sensitive=False),
    help="LLM provider (default: openai, or LLM_PROVIDER env var).",
)
@click.option("--env-file", default=None, help="Path to .env file with API keys.")
def analyze(repo_path: str, model: str | None, provider: str | None, env_file: str | None) -> None:
    """Perform a full analysis of a repository.

    REPO_PATH is the path to the repository to analyze.
    """
    try:
        config = Config.from_env(env_file, provider=provider)
    except ValueError as exc:
        print_error(str(exc))
        sys.exit(1)

    if model:
        config.model = model

    # Lazy import to keep CLI startup fast
    from analyzer.agent import Agent

    agent = Agent(repo_path, config)
    report = agent.analyze()
    print_analysis(report)


@cli.command()
@click.argument("repo_path", type=click.Path(exists=True, file_okay=False))
@click.argument("question")
@click.option("--model", default=None, help="Model name/deployment to use.")
@click.option(
    "--provider",
    default=None,
    type=click.Choice(["openai", "azure", "huggingface"], case_sensitive=False),
    help="LLM provider (default: openai, or LLM_PROVIDER env var).",
)
@click.option("--env-file", default=None, help="Path to .env file with API keys.")
def ask(repo_path: str, question: str, model: str | None, provider: str | None, env_file: str | None) -> None:
    """Ask a question about a repository.

    REPO_PATH is the path to the repository.
    QUESTION is the developer question to answer.
    """
    try:
        config = Config.from_env(env_file, provider=provider)
    except ValueError as exc:
        print_error(str(exc))
        sys.exit(1)

    if model:
        config.model = model

    from analyzer.agent import Agent

    agent = Agent(repo_path, config)
    answer = agent.ask(question)
    print_answer(answer)


@cli.command()
@click.argument("repo_path", type=click.Path(exists=True, file_okay=False))
@click.option(
    "--provider",
    default=None,
    type=click.Choice(["openai", "azure", "huggingface"], case_sensitive=False),
    help="LLM provider (default: openai, or LLM_PROVIDER env var).",
)
@click.option("--env-file", default=None, help="Path to .env file with API keys.")
def chat(repo_path: str, provider: str | None, env_file: str | None) -> None:
    """Start an interactive chat session about a repository.

    REPO_PATH is the path to the repository.
    """
    try:
        config = Config.from_env(env_file, provider=provider)
    except ValueError as exc:
        print_error(str(exc))
        sys.exit(1)

    from analyzer.agent import Agent

    agent = Agent(repo_path, config)

    # First, run the initial analysis
    print_info("Running initial analysis...")
    report = agent.analyze()
    print_analysis(report)

    # Then enter interactive Q&A loop
    print_info("You can now ask questions about the repository. Type 'quit' or 'exit' to stop.\n")
    while True:
        try:
            question = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not question:
            continue
        if question.lower() in ("quit", "exit", "q"):
            break

        answer = agent.ask(question)
        print_answer(answer)

    print_info("Session ended.")


if __name__ == "__main__":
    cli()
