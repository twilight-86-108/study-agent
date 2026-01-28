"""Explain command for concept explanations.

トピックや概念についてAIによる説明を取得するコマンドを提供する。
RAG検索を使用してドキュメントのコンテキストを活用した説明を生成する。

Example:
    $ study-agent explain "Amazon EC2"
    $ study-agent explain "機械学習の基礎" --doc abc123
    $ study-agent explain "AとBの違い" --compare
"""

from __future__ import annotations

import asyncio

import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from study_agent.cli.utils import get_container, handle_errors

console = Console()


@handle_errors
def explain_command(
    topic: str = typer.Argument(..., help="Topic or concept to explain"),
    document: str | None = typer.Option(
        None, "--doc", "-d", help="Document ID to use for context"
    ),
    difficulty: int = typer.Option(
        3,
        "--level",
        "-l",
        min=1,
        max=5,
        help="Explanation difficulty level (1=beginner, 5=expert)",
    ),
    compare: bool = typer.Option(
        False, "--compare", "-c", help="Compare two concepts (use 'A vs B' format)"
    ),
    brief: bool = typer.Option(False, "--brief", "-b", help="Get a brief explanation"),
) -> None:
    """Get an AI-powered explanation of a topic or concept.

    Uses RAG (Retrieval Augmented Generation) to provide explanations
    grounded in your loaded documents.

    Examples:
        study-agent explain "Amazon EC2"
        study-agent explain "機械学習" --level 1
        study-agent explain "TCP vs UDP" --compare
    """

    async def _explain() -> None:
        async with get_container() as container:
            # クエリを構築
            if (
                compare
                or " vs " in topic.lower()
                or "と" in topic
                and "の違い" in topic
            ):
                query = f"{topic}を比較して説明してください"
            elif brief:
                query = f"{topic}を簡潔に説明してください"
            else:
                query = f"{topic}について説明してください"

            # 難易度の説明を追加
            difficulty_labels = {
                1: "初心者向けに",
                2: "基礎レベルで",
                3: "",
                4: "詳しく",
                5: "専門的に",
            }
            if difficulty != 3:
                query = f"{difficulty_labels[difficulty]}{query}"

            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
                transient=True,
            ) as progress:
                progress.add_task("Generating explanation...", total=None)

                # オーケストレータで処理
                state = await container.orchestrator.process(
                    user_query=query,
                    session_id="cli-explain",
                    document_id=document,
                )

            # 応答を取得
            response = state.get("response", "")
            if not response:
                console.print("[yellow]No explanation generated.[/yellow]")
                console.print(
                    "Try loading a document first with [bold]study-agent load file[/bold]"
                )
                return

            # ソースチャンクがあれば表示
            source_chunks = state.get("source_chunks", [])

            # パネルで表示
            panel = Panel(
                Markdown(response),
                title=f"[bold]{topic}[/bold]",
                subtitle=(
                    f"[dim]difficulty: {difficulty}/5[/dim]"
                    if difficulty != 3
                    else None
                ),
                border_style="blue",
                padding=(1, 2),
            )
            console.print(panel)

            # ソース情報
            if source_chunks:
                console.print(
                    f"\n[dim]Based on {len(source_chunks)} relevant sections from your documents.[/dim]"
                )

    asyncio.run(_explain())


@handle_errors
def term_command(
    term: str = typer.Argument(..., help="Term to define"),
    document: str | None = typer.Option(
        None, "--doc", "-d", help="Document ID to use for context"
    ),
) -> None:
    """Get a definition of a term.

    Provides a concise definition of a technical term or concept.
    """

    async def _term() -> None:
        async with get_container() as container:
            query = f"「{term}」という用語を定義してください"

            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
                transient=True,
            ) as progress:
                progress.add_task("Looking up term...", total=None)

                state = await container.orchestrator.process(
                    user_query=query,
                    session_id="cli-term",
                    document_id=document,
                )

            response = state.get("response", "")
            if not response:
                console.print(f"[yellow]No definition found for '{term}'.[/yellow]")
                return

            panel = Panel(
                Markdown(response),
                title=f"[bold]{term}[/bold]",
                border_style="green",
                padding=(1, 2),
            )
            console.print(panel)

    asyncio.run(_term())
