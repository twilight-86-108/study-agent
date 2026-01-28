"""Load command for importing documents.

ドキュメントファイル（PDF、Markdown、テキスト）を読み込み、
学習システムに取り込むコマンドを提供する。

Example:
    $ study-agent load file syllabus.pdf
    $ study-agent load file notes.md --title "Study Notes"
    $ study-agent load list
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from study_agent.cli.utils import get_container, format_file_size, handle_errors
from study_agent.core.constants import SUPPORTED_FORMATS

console = Console()
app = typer.Typer(help="Document loading commands")


@app.command(name="file")
@handle_errors
def load_file(
    file_path: str = typer.Argument(..., help="Path to document file"),
    title: str | None = typer.Option(
        None, "--title", "-t", help="Custom document title"
    ),
) -> None:
    """Load a document file (PDF, Markdown, or text).

    Supports the following file formats:
    - PDF (.pdf)
    - Markdown (.md, .markdown)
    - Plain text (.txt)
    """
    path = Path(file_path)

    # ファイル存在チェック
    if not path.exists():
        console.print(f"[red]Error:[/red] File not found: {file_path}")
        raise typer.Exit(1)

    # ファイル形式チェック
    suffix = path.suffix.lower().lstrip(".")
    if suffix not in SUPPORTED_FORMATS:
        console.print(
            f"[red]Error:[/red] Unsupported file format: {suffix}\n"
            f"Supported formats: {', '.join(SUPPORTED_FORMATS)}"
        )
        raise typer.Exit(1)

    async def _load() -> None:
        async with get_container() as container:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                task = progress.add_task("Loading document...", total=None)

                try:
                    result = await container.document_service.load_document(
                        file_path=str(path.absolute()),
                        title=title,
                    )

                    progress.update(task, description="Processing complete!")

                except Exception as e:
                    progress.stop()
                    console.print(f"[red]Error loading document:[/red] {e}")
                    raise typer.Exit(1)

            # 成功メッセージを表示
            console.print()
            console.print(
                f"[green]✓[/green] Loaded: [bold]{result.document.title}[/bold]"
            )
            console.print(f"  ID: {result.document.id}")
            console.print(f"  Type: {result.document.file_type.value}")
            console.print(f"  Size: {format_file_size(result.document.file_size)}")
            if result.document.total_pages:
                console.print(f"  Pages: {result.document.total_pages}")
            console.print(f"  Chunks: {result.chunk_count}")

            if result.chapters:
                console.print(f"  Chapters: {len(result.chapters)}")
            if result.topics:
                console.print(f"  Topics: {len(result.topics)}")

    asyncio.run(_load())


@app.command(name="list")
@handle_errors
def list_documents() -> None:
    """List all loaded documents."""

    async def _list() -> None:
        async with get_container() as container:
            documents = await container.document_service.list_documents()

            if not documents:
                console.print("[dim]No documents loaded.[/dim]")
                console.print(
                    "Use [bold]study-agent load file <path>[/bold] to load a document."
                )
                return

            # テーブルを作成
            table = Table(title="Loaded Documents")
            table.add_column("ID", style="cyan", no_wrap=True)
            table.add_column("Title", style="bold")
            table.add_column("Type", style="dim")
            table.add_column("Size", justify="right")
            table.add_column("Pages", justify="right")

            for doc in documents:
                table.add_row(
                    doc.id[:8] + "...",
                    doc.title[:40] + ("..." if len(doc.title) > 40 else ""),
                    doc.file_type.value,
                    format_file_size(doc.file_size),
                    str(doc.total_pages) if doc.total_pages else "-",
                )

            console.print(table)

    asyncio.run(_list())


@app.command(name="delete")
@handle_errors
def delete_document(
    document_id: str = typer.Argument(..., help="Document ID to delete"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
) -> None:
    """Delete a loaded document."""

    async def _delete() -> None:
        async with get_container() as container:
            # ドキュメントを確認
            doc = await container.document_service.get_document(document_id)
            if not doc:
                console.print(f"[red]Error:[/red] Document not found: {document_id}")
                raise typer.Exit(1)

            # 確認
            if not force:
                from rich.prompt import Confirm

                if not Confirm.ask(f"Delete document '[bold]{doc.title}[/bold]'?"):
                    console.print("[dim]Cancelled.[/dim]")
                    return

            # 削除実行
            await container.document_service.delete_document(document_id)
            console.print(f"[green]✓[/green] Deleted: {doc.title}")

    asyncio.run(_delete())


@app.command(name="info")
@handle_errors
def document_info(
    document_id: str = typer.Argument(..., help="Document ID"),
) -> None:
    """Show detailed information about a document."""

    async def _info() -> None:
        async with get_container() as container:
            doc = await container.document_service.get_document(document_id)
            if not doc:
                console.print(f"[red]Error:[/red] Document not found: {document_id}")
                raise typer.Exit(1)

            # 詳細情報を表示
            console.print(f"\n[bold]{doc.title}[/bold]")
            console.print(f"{'─' * 50}")
            console.print(f"ID:         {doc.id}")
            console.print(f"File Path:  {doc.file_path}")
            console.print(f"File Type:  {doc.file_type.value}")
            console.print(f"File Size:  {format_file_size(doc.file_size)}")
            if doc.total_pages:
                console.print(f"Pages:      {doc.total_pages}")
            console.print(f"Created:    {doc.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
            console.print(f"Updated:    {doc.updated_at.strftime('%Y-%m-%d %H:%M:%S')}")

            # トピック一覧を取得
            topics = await container.document_service.get_topics(document_id)
            if topics:
                console.print(f"\n[bold]Topics ({len(topics)}):[/bold]")
                for i, topic in enumerate(topics[:10], 1):
                    console.print(f"  {i}. {topic.title}")
                if len(topics) > 10:
                    console.print(f"  ... and {len(topics) - 10} more")

    asyncio.run(_info())
