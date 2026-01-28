"""CLI module for StudyAgent.

Typer/Richを使用したコマンドラインインターフェースを提供する。

Example:
    >>> from study_agent.cli import cli_main
    >>> cli_main()
"""

from study_agent.cli.app import app, cli_main

__all__ = ["app", "cli_main"]
