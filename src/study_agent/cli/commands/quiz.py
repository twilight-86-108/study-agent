"""Quiz command for testing knowledge.

トピックに関するクイズを生成し、ユーザーの回答を評価する
インタラクティブなクイズ機能を提供する。

Example:
    $ study-agent quiz
    $ study-agent quiz "Amazon EC2" --count 5
    $ study-agent quiz --type open --difficulty hard
"""

from __future__ import annotations

import asyncio

import typer
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.markdown import Markdown

from study_agent.cli.utils import get_container, handle_errors
from study_agent.domain import QuizType, Difficulty

console = Console()


@handle_errors
def quiz_command(
    topic: str | None = typer.Argument(None, help="Topic to quiz on (optional)"),
    document: str | None = typer.Option(None, "--doc", "-d", help="Document ID to use"),
    count: int = typer.Option(
        1, "--count", "-n", min=1, max=10, help="Number of questions"
    ),
    quiz_type: str = typer.Option(
        "choice", "--type", "-t", help="Quiz type: choice, tf (true/false), open"
    ),
    difficulty: str = typer.Option(
        "medium", "--difficulty", help="Difficulty: easy, medium, hard"
    ),
) -> None:
    """Take a quiz to test your knowledge.

    Generates quiz questions based on your loaded documents
    and evaluates your answers with feedback.

    Examples:
        study-agent quiz                    # Random quiz
        study-agent quiz "EC2" -n 5        # 5 questions about EC2
        study-agent quiz --type tf          # True/False questions
    """
    # クイズタイプを解析
    type_map = {
        "choice": "選択式",
        "multiple": "選択式",
        "tf": "○×",
        "truefalse": "○×",
        "true_false": "○×",
        "open": "記述式",
        "free": "記述式",
    }
    quiz_type_label = type_map.get(quiz_type.lower(), "選択式")

    # 難易度を解析
    diff_map = {
        "easy": "簡単",
        "medium": "",
        "hard": "難しい",
    }
    difficulty_label = diff_map.get(difficulty.lower(), "")

    async def _quiz() -> None:
        async with get_container() as container:
            score_total = 0
            correct_count = 0
            current_quiz = None

            for i in range(count):
                # 問題番号を表示
                if count > 1:
                    console.print(
                        f"\n[bold cyan]━━━ Question {i+1}/{count} ━━━[/bold cyan]"
                    )
                else:
                    console.print()

                # クイズ生成クエリを構築
                query_parts = []
                if topic:
                    query_parts.append(f"{topic}について")
                if difficulty_label:
                    query_parts.append(f"{difficulty_label}")
                query_parts.append(f"{quiz_type_label}クイズを出して")
                query = "".join(query_parts)

                # クイズを生成
                state = await container.orchestrator.process(
                    user_query=query,
                    session_id="cli-quiz",
                    document_id=document,
                )

                current_quiz = state.get("quiz")
                response = state.get("response", "")

                if not response:
                    console.print("[yellow]Could not generate quiz.[/yellow]")
                    console.print("Try loading a document first.")
                    return

                # 問題を表示
                panel = Panel(
                    response,
                    title="[bold yellow]📝 問題[/bold yellow]",
                    border_style="yellow",
                    padding=(1, 2),
                )
                console.print(panel)

                # 回答を取得
                console.print()
                answer = Prompt.ask("[bold]あなたの回答[/bold]")

                if not answer.strip():
                    console.print("[dim]Skipped.[/dim]")
                    continue

                # 回答を評価
                eval_state = await container.orchestrator.process(
                    user_query=answer,
                    session_id="cli-quiz",
                    document_id=document,
                )

                # クイズがアクティブな場合は評価結果を取得
                evaluation = eval_state.get("evaluation")
                feedback = eval_state.get("response", "")

                # 結果を表示
                console.print()
                if evaluation and evaluation.get("is_correct"):
                    correct_count += 1
                    score_total += evaluation.get("score", 100)
                    console.print("[bold green]✓ 正解！[/bold green]")
                else:
                    score = evaluation.get("score", 0) if evaluation else 0
                    score_total += score
                    if score > 0:
                        console.print(f"[yellow]△ 部分点: {score}点[/yellow]")
                    else:
                        console.print("[bold red]✗ 不正解[/bold red]")

                # フィードバックを表示
                if feedback:
                    console.print()
                    console.print(Markdown(feedback))

            # 最終スコアを表示（複数問の場合）
            if count > 1:
                console.print()
                console.print("[bold cyan]━━━ 結果 ━━━[/bold cyan]")
                accuracy = (correct_count / count) * 100
                avg_score = score_total / count

                if accuracy >= 80:
                    style = "green"
                    emoji = "🎉"
                elif accuracy >= 60:
                    style = "yellow"
                    emoji = "👍"
                else:
                    style = "red"
                    emoji = "📚"

                console.print(
                    f"{emoji} 正答率: [{style}]{correct_count}/{count} ({accuracy:.0f}%)[/{style}]"
                )
                console.print(f"   平均スコア: {avg_score:.0f}点")

    asyncio.run(_quiz())


@handle_errors
def quick_quiz_command(
    document: str | None = typer.Option(None, "--doc", "-d", help="Document ID to use"),
) -> None:
    """Take a quick single-question quiz."""
    # quiz_commandを1問で呼び出し
    quiz_command(
        topic=None, document=document, count=1, quiz_type="choice", difficulty="medium"
    )
