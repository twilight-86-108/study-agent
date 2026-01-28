"""CLI application entry point.

Typerを使用したCLIアプリケーションのメインエントリーポイント。
すべてのサブコマンドを登録し、アプリケーションを起動する。

Example:
    $ study-agent --help
    $ study-agent --version
    $ study-agent load file document.pdf
    $ study-agent explain "EC2"
    $ study-agent chat
"""

from __future__ import annotations

import typer
from rich.console import Console
from rich.panel import Panel

from study_agent.core.constants import APP_NAME, APP_VERSION
from study_agent.cli.commands import load, topics, explain, quiz, progress, chat

console = Console()

# メインアプリケーション
app = typer.Typer(
    name=APP_NAME.lower().replace(" ", "-"),
    help=f"{APP_NAME} - AI-Powered Learning Assistant",
    add_completion=False,
    no_args_is_help=False,
    rich_markup_mode="rich",
)

# サブコマンドを登録
app.add_typer(load.app, name="load", help="Load documents")
app.command(name="topics")(topics.topics_command)
app.command(name="explain")(explain.explain_command)
app.command(name="term")(explain.term_command)
app.command(name="quiz")(quiz.quiz_command)
app.command(name="progress")(progress.progress_command)
app.command(name="stats")(progress.stats_command)
app.command(name="chat")(chat.chat_command)
app.command(name="ask")(chat.quick_chat_command)


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    version: bool = typer.Option(
        False, "--version", "-v", help="Show version and exit"
    ),
) -> None:
    """StudyAgent - AI-Powered Learning Assistant.

    An intelligent study companion that helps you learn from documents,
    take quizzes, and track your progress.

    \b
    Quick Start:
      1. Load a document: study-agent load file document.pdf
      2. Explore topics:  study-agent topics
      3. Start learning:  study-agent chat

    \b
    Commands:
      load      Load and manage documents
      topics    List topics from documents
      explain   Get explanations of concepts
      term      Look up term definitions
      quiz      Take quizzes to test knowledge
      progress  View learning progress
      chat      Interactive chat mode
      ask       Quick question (non-interactive)

    Use [command] --help for more information about a command.
    """
    if version:
        console.print(f"[bold]{APP_NAME}[/bold] v{APP_VERSION}")
        raise typer.Exit()

    if ctx.invoked_subcommand is None:
        # コマンドが指定されていない場合はウェルカムメッセージを表示
        _show_welcome()


def _show_welcome() -> None:
    """ウェルカムメッセージを表示."""
    welcome_text = f"""[bold blue]{APP_NAME}[/bold blue] v{APP_VERSION}

AI-Powered Learning Assistant

[cyan]Getting Started:[/cyan]
  [bold]study-agent load file[/bold] <path>    Load a document
  [bold]study-agent topics[/bold]              List available topics
  [bold]study-agent chat[/bold]                Start interactive mode
  [bold]study-agent --help[/bold]              Show all commands

[dim]For detailed help on any command, use:[/dim]
  study-agent <command> --help"""

    console.print(
        Panel(
            welcome_text,
            border_style="blue",
            padding=(1, 2),
        )
    )


def cli_main() -> None:
    """CLIのメインエントリーポイント."""
    try:
        app()
    except KeyboardInterrupt:
        console.print("\n[dim]Operation cancelled.[/dim]")
        raise typer.Exit(130)
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


if __name__ == "__main__":
    cli_main()
