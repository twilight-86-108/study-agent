"""Topics command for listing document topics.

読み込まれたドキュメントのトピック（章・セクション）を
ツリー形式で表示するコマンドを提供する。

Example:
    $ study-agent topics
    $ study-agent topics --doc abc123
"""

from __future__ import annotations

import asyncio

import typer
from rich.console import Console
from rich.tree import Tree

from study_agent.cli.utils import get_container, handle_errors

console = Console()


@handle_errors
def topics_command(
    document: str | None = typer.Option(
        None, "--doc", "-d", help="Document ID to filter by"
    ),
    show_ids: bool = typer.Option(False, "--ids", help="Show topic IDs"),
) -> None:
    """List topics from loaded documents.

    Displays the hierarchical structure of chapters and topics
    from your loaded documents in a tree format.
    """

    async def _topics() -> None:
        async with get_container() as container:
            # ドキュメント一覧を取得
            documents = await container.document_service.list_documents()

            # 特定のドキュメントにフィルタ
            if document:
                documents = [
                    d
                    for d in documents
                    if d.id == document or d.id.startswith(document)
                ]
                if not documents:
                    console.print(f"[red]Error:[/red] Document not found: {document}")
                    raise typer.Exit(1)

            if not documents:
                console.print("[dim]No documents loaded.[/dim]")
                console.print(
                    "Use [bold]study-agent load file <path>[/bold] to load a document."
                )
                return

            # 各ドキュメントのトピックをツリー表示
            for doc in documents:
                tree = Tree(
                    f"[bold blue]{doc.title}[/bold blue] [dim]({doc.id[:8]}...)[/dim]"
                )

                # チャプターとトピックを取得
                chapters = await container.document_service.get_chapters(doc.id)
                topics = await container.document_service.get_topics(doc.id)

                if chapters:
                    # チャプターごとにトピックをグループ化
                    chapter_topics = {c.id: [] for c in chapters}
                    orphan_topics = []

                    for topic in topics:
                        if topic.chapter_id and topic.chapter_id in chapter_topics:
                            chapter_topics[topic.chapter_id].append(topic)
                        else:
                            orphan_topics.append(topic)

                    # チャプターを追加
                    for chapter in sorted(chapters, key=lambda c: c.order_index):
                        chapter_label = f"[cyan]{chapter.title}[/cyan]"
                        if chapter.page_start:
                            chapter_label += f" [dim](p.{chapter.page_start})[/dim]"
                        if show_ids:
                            chapter_label += f" [dim]{chapter.id[:8]}[/dim]"

                        chapter_branch = tree.add(chapter_label)

                        # チャプター内のトピックを追加
                        for topic in sorted(
                            chapter_topics.get(chapter.id, []),
                            key=lambda t: t.order_index,
                        ):
                            topic_label = topic.title
                            if show_ids:
                                topic_label += f" [dim]{topic.id[:8]}[/dim]"
                            chapter_branch.add(topic_label)

                    # 孤立したトピック（チャプターに属さない）
                    if orphan_topics:
                        other_branch = tree.add("[dim]Other Topics[/dim]")
                        for topic in sorted(orphan_topics, key=lambda t: t.order_index):
                            topic_label = topic.title
                            if show_ids:
                                topic_label += f" [dim]{topic.id[:8]}[/dim]"
                            other_branch.add(topic_label)

                elif topics:
                    # チャプターがない場合はトピックを直接表示
                    for topic in sorted(topics, key=lambda t: t.order_index):
                        topic_label = topic.title
                        if show_ids:
                            topic_label += f" [dim]{topic.id[:8]}[/dim]"
                        tree.add(topic_label)
                else:
                    tree.add("[dim]No topics found[/dim]")

                console.print(tree)
                console.print()

    asyncio.run(_topics())
