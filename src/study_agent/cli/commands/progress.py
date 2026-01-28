"""Progress command for viewing learning progress.

学習進捗状況を確認するコマンドを提供する。
トピック別の習熟度、正答率、弱点トピックなどを表示する。

Example:
    $ study-agent progress
    $ study-agent progress --doc abc123
    $ study-agent progress --weak
"""

from __future__ import annotations

import asyncio

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from study_agent.cli.utils import (
    get_container,
    handle_errors,
    get_progress_bar,
    truncate_text,
)

console = Console()


@handle_errors
def progress_command(
    document: str | None = typer.Option(
        None, "--doc", "-d", help="Document ID to filter by"
    ),
    weak: bool = typer.Option(False, "--weak", "-w", help="Show weak topics only"),
    detailed: bool = typer.Option(False, "--detailed", help="Show detailed statistics"),
) -> None:
    """View your learning progress.

    Displays your progress across topics including mastery levels,
    accuracy rates, and study counts.

    Examples:
        study-agent progress              # Overall progress
        study-agent progress --weak       # Show weak topics
        study-agent progress --detailed   # Detailed stats
    """

    async def _progress() -> None:
        async with get_container() as container:
            # ドキュメント一覧を取得
            documents = await container.document_service.list_documents()

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
                return

            for doc in documents:
                # ドキュメントの進捗サマリーを取得
                summary = await container.progress_service.get_document_summary(doc.id)

                if summary is None:
                    console.print(f"[dim]No progress data for {doc.title}[/dim]")
                    continue

                # ヘッダーを表示
                console.print()
                title = f"📚 {doc.title}"
                if weak:
                    title += " - Weak Topics"

                console.print(
                    Panel(
                        f"[bold]{title}[/bold]\n\n"
                        f"Progress: {summary.studied_topics}/{summary.total_topics} topics studied\n"
                        f"Mastered: {summary.mastered_topics} topics\n"
                        f"Average Mastery: {summary.average_mastery:.0f}%",
                        border_style="blue",
                    )
                )

                # トピック別の進捗を取得
                if weak:
                    # 弱点トピックのみ
                    if not summary.weak_topics:
                        console.print("[green]No weak topics! 🎉[/green]")
                        continue
                    progress_records = await container.progress_service.get_weak_topics(
                        doc.id
                    )
                else:
                    progress_records = (
                        await container.progress_service.get_all_progress(doc.id)
                    )

                if not progress_records:
                    console.print("[dim]Start studying to track your progress![/dim]")
                    continue

                # テーブルを作成
                table = Table(show_header=True, header_style="bold")
                table.add_column("Topic", style="cyan", min_width=30)
                table.add_column("Mastery", justify="center", min_width=15)
                table.add_column("Accuracy", justify="right")
                table.add_column("Studies", justify="right")

                if detailed:
                    table.add_column("Correct", justify="right")
                    table.add_column("Total", justify="right")
                    table.add_column("Last Studied", justify="right")

                for record in progress_records:
                    # トピック名を取得
                    topic_name = (
                        record.topic.title
                        if hasattr(record, "topic")
                        else record.topic_id[:20]
                    )
                    topic_name = truncate_text(topic_name, 35)

                    # 習熟度バー
                    mastery_level = (
                        record.progress.mastery_level
                        if hasattr(record, "progress")
                        else record.mastery_level
                    )
                    mastery_bar = get_progress_bar(mastery_level)
                    mastery_str = f"{mastery_level:.0f}% {mastery_bar}"

                    # 正答率
                    total = (
                        record.progress.total_count
                        if hasattr(record, "progress")
                        else record.total_count
                    )
                    correct = (
                        record.progress.correct_count
                        if hasattr(record, "progress")
                        else record.correct_count
                    )
                    accuracy = (correct / total * 100) if total > 0 else 0
                    accuracy_str = f"{accuracy:.0f}%" if total > 0 else "-"

                    # 学習回数
                    study_count = (
                        record.progress.study_count
                        if hasattr(record, "progress")
                        else record.study_count
                    )

                    if detailed:
                        last_studied = (
                            record.progress.last_studied_at
                            if hasattr(record, "progress")
                            else record.last_studied_at
                        )
                        last_str = (
                            last_studied.strftime("%m/%d") if last_studied else "-"
                        )
                        table.add_row(
                            topic_name,
                            mastery_str,
                            accuracy_str,
                            str(study_count),
                            str(correct),
                            str(total),
                            last_str,
                        )
                    else:
                        table.add_row(
                            topic_name,
                            mastery_str,
                            accuracy_str,
                            str(study_count),
                        )

                console.print(table)

                # 推薦トピック
                if not weak:
                    recommendation = (
                        await container.progress_service.get_recommended_topic(doc.id)
                    )
                    if recommendation:
                        console.print()
                        console.print(
                            f"[bold yellow]💡 Recommended:[/bold yellow] {recommendation.topic.title}"
                        )
                        console.print(f"   [dim]{recommendation.reason}[/dim]")

    asyncio.run(_progress())


@handle_errors
def stats_command() -> None:
    """Show overall learning statistics."""

    async def _stats() -> None:
        async with get_container() as container:
            documents = await container.document_service.list_documents()

            if not documents:
                console.print("[dim]No documents loaded.[/dim]")
                return

            total_topics = 0
            total_studied = 0
            total_mastered = 0
            total_quizzes = 0
            total_correct = 0

            for doc in documents:
                summary = await container.progress_service.get_document_summary(doc.id)
                if summary:
                    total_topics += summary.total_topics
                    total_studied += summary.studied_topics
                    total_mastered += summary.mastered_topics

                # クイズ統計
                quiz_stats = await container.progress_service.get_quiz_stats(doc.id)
                if quiz_stats:
                    total_quizzes += quiz_stats.get("total", 0)
                    total_correct += quiz_stats.get("correct", 0)

            # 統計を表示
            console.print()
            console.print("[bold]📊 Learning Statistics[/bold]")
            console.print("─" * 40)
            console.print(f"Documents:     {len(documents)}")
            console.print(f"Topics:        {total_studied}/{total_topics} studied")
            console.print(f"Mastered:      {total_mastered} topics")
            if total_quizzes > 0:
                accuracy = (total_correct / total_quizzes) * 100
                console.print(
                    f"Quiz Accuracy: {total_correct}/{total_quizzes} ({accuracy:.0f}%)"
                )

    asyncio.run(_stats())
