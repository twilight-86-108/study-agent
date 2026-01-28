"""Chat command for interactive mode.

インタラクティブな対話モードでAI学習アシスタントと
会話しながら学習を進めるコマンドを提供する。

Example:
    $ study-agent chat
    $ study-agent chat --doc abc123
"""

from __future__ import annotations

import asyncio

import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt

from study_agent.cli.utils import get_container, handle_errors
from study_agent.domain import SessionMode

console = Console()


WELCOME_MESSAGE = """[bold]StudyAgent 対話モード[/bold]

学習アシスタントと会話しながら学習を進められます。

[cyan]使い方:[/cyan]
• 「〜について教えて」「〜を説明して」で概念の説明を取得
• 「クイズ」「問題を出して」でクイズに挑戦
• 「進捗」「学習状況」で進捗を確認
• 「次へ」「おすすめ」で次のトピックを提案
• 「ヘルプ」でこのメッセージを再表示
• 「exit」「終了」で対話モードを終了

[dim]Ctrl+C でもいつでも終了できます[/dim]"""


HELP_MESSAGE = """[bold]コマンド一覧:[/bold]

[cyan]学習:[/cyan]
  〜について教えて    トピックの説明を取得
  〜とは            用語の定義を取得
  〜と〜の違い       概念を比較

[cyan]クイズ:[/cyan]
  クイズ / 問題      クイズに挑戦
  〜のクイズ         特定トピックのクイズ

[cyan]ナビゲーション:[/cyan]
  次へ / next        次のトピックへ
  おすすめ           学習を提案

[cyan]確認:[/cyan]
  進捗 / progress    学習進捗を確認
  トピック一覧       トピックを表示

[cyan]その他:[/cyan]
  ヘルプ / help      このメッセージを表示
  exit / 終了        対話モードを終了"""


@handle_errors
def chat_command(
    document: str | None = typer.Option(None, "--doc", "-d", help="Document ID to use"),
) -> None:
    """Start interactive chat mode.

    Enter an interactive session where you can chat with the AI
    learning assistant, ask questions, take quizzes, and track
    your progress.

    Examples:
        study-agent chat
        study-agent chat --doc abc123
    """

    async def _chat() -> None:
        async with get_container() as container:
            # ドキュメント確認
            if document:
                doc = await container.document_service.get_document(document)
                if not doc:
                    console.print(f"[red]Error:[/red] Document not found: {document}")
                    raise typer.Exit(1)
                console.print(f"[dim]Using document: {doc.title}[/dim]")

            # セッションを開始
            session = await container.session_service.start_session(
                document_id=document,
                mode=SessionMode.LEARNING,
            )

            # ウェルカムメッセージを表示
            console.print()
            console.print(Panel(WELCOME_MESSAGE, border_style="blue"))
            console.print()

            current_quiz = None

            while True:
                try:
                    # ユーザー入力を取得
                    user_input = Prompt.ask("[bold cyan]You[/bold cyan]")
                    user_input = user_input.strip()

                    if not user_input:
                        continue

                    # 終了コマンド
                    if user_input.lower() in ["exit", "quit", "終了", "おわり", "bye"]:
                        await container.session_service.end_session(session.id)
                        console.print(
                            "\n[dim]学習お疲れさまでした！またお会いしましょう 👋[/dim]"
                        )
                        break

                    # ヘルプコマンド
                    if user_input.lower() in ["help", "ヘルプ", "?"]:
                        console.print(Panel(HELP_MESSAGE, border_style="cyan"))
                        continue

                    # クリアコマンド
                    if user_input.lower() in ["clear", "cls"]:
                        console.clear()
                        continue

                    # 入力を処理
                    state = await container.orchestrator.process(
                        user_query=user_input,
                        session_id=session.id,
                        document_id=document,
                    )

                    # クイズ状態を更新
                    if state.get("quiz"):
                        current_quiz = state.get("quiz")
                    elif state.get("evaluation"):
                        # 評価後はクイズをクリア
                        current_quiz = None

                    # 応答を表示
                    response = state.get("response", "")
                    if response:
                        console.print()
                        console.print("[bold green]Assistant[/bold green]")
                        console.print(Markdown(response))
                        console.print()
                    else:
                        console.print("\n[dim]（応答を生成できませんでした）[/dim]\n")

                except KeyboardInterrupt:
                    # Ctrl+C で終了
                    await container.session_service.end_session(session.id)
                    console.print("\n\n[dim]セッションを終了しました。[/dim]")
                    break

                except Exception as e:
                    console.print(f"\n[red]Error:[/red] {e}\n")
                    continue

    asyncio.run(_chat())


@handle_errors
def quick_chat_command(
    query: str = typer.Argument(..., help="Question to ask"),
    document: str | None = typer.Option(None, "--doc", "-d", help="Document ID to use"),
) -> None:
    """Ask a quick question without entering interactive mode."""

    async def _quick() -> None:
        async with get_container() as container:
            state = await container.orchestrator.process(
                user_query=query,
                session_id="cli-quick",
                document_id=document,
            )

            response = state.get("response", "")
            if response:
                console.print()
                console.print(Markdown(response))
            else:
                console.print("[yellow]No response generated.[/yellow]")

    asyncio.run(_quick())
