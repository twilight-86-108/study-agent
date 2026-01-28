"""CLI utility functions.

CLIコマンドで共通して使用するユーティリティ関数を提供する。
"""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from functools import wraps
from typing import AsyncGenerator, Callable, TypeVar, Any

from rich.console import Console

from study_agent.infrastructure.config import AppConfig, load_config
from study_agent.container import Container

console = Console()

T = TypeVar("T")


@asynccontextmanager
async def get_container(
    config: AppConfig | None = None,
    use_mock: bool = True,
) -> AsyncGenerator[Container, None]:
    """初期化されたコンテナを取得.

    Args:
        config: アプリケーション設定（Noneの場合はデフォルト設定を使用）
        use_mock: モック実装を使用するかどうか

    Yields:
        初期化されたコンテナ

    Example:
        >>> async with get_container() as container:
        ...     docs = await container.document_service.list_documents()
    """
    if config is None:
        config = load_config()

    container = await Container.create(config, use_mock=use_mock)
    try:
        yield container
    finally:
        await container.close()


def run_async(func: Callable[..., Any]) -> Callable[..., Any]:
    """非同期関数を同期的に実行するデコレータ.

    Typerコマンド内で非同期関数を簡単に実行するために使用。

    Args:
        func: 非同期関数

    Returns:
        同期関数ラッパー

    Example:
        >>> @run_async
        ... async def my_command():
        ...     async with get_container() as container:
        ...         # 非同期処理
        ...         pass
    """

    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        return asyncio.run(func(*args, **kwargs))

    return wrapper


def handle_errors(func: Callable[..., T]) -> Callable[..., T | None]:
    """エラーハンドリングデコレータ.

    CLIコマンドのエラーをキャッチして適切に表示する。

    Args:
        func: 対象関数

    Returns:
        エラーハンドリング付き関数
    """

    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> T | None:
        try:
            return func(*args, **kwargs)
        except KeyboardInterrupt:
            console.print("\n[yellow]Operation cancelled.[/yellow]")
            return None
        except Exception as e:
            console.print(f"[red]Error:[/red] {e}")
            return None

    return wrapper


def format_file_size(size_bytes: int) -> str:
    """ファイルサイズを人間が読みやすい形式に変換.

    Args:
        size_bytes: バイト単位のサイズ

    Returns:
        フォーマットされたサイズ文字列
    """
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


def truncate_text(text: str, max_length: int = 50) -> str:
    """テキストを指定された長さに切り詰める.

    Args:
        text: 対象テキスト
        max_length: 最大長

    Returns:
        切り詰められたテキスト
    """
    if len(text) <= max_length:
        return text
    return text[: max_length - 3] + "..."


def get_progress_bar(level: float, width: int = 10) -> str:
    """進捗バーを生成.

    Args:
        level: 進捗レベル（0.0-1.0または0-100）
        width: バーの幅

    Returns:
        進捗バー文字列
    """
    # 0-100スケールを0-1に正規化
    if level > 1:
        level = level / 100

    filled = int(level * width)
    empty = width - filled
    return f"[green]{'█' * filled}[/green][dim]{'░' * empty}[/dim]"


def confirm_action(message: str, default: bool = False) -> bool:
    """ユーザーに確認を求める.

    Args:
        message: 確認メッセージ
        default: デフォルト値

    Returns:
        ユーザーの回答
    """
    from rich.prompt import Confirm

    return Confirm.ask(message, default=default)
