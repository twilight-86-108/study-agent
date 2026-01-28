"""Base parser classes and data structures.

パーサーの抽象基底クラスとパース結果のデータ構造を定義する。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class ParsedChapter:
    """パースされた章の情報.

    Attributes:
        title: 章タイトル
        content: 章の内容テキスト
        order_index: 表示順序（0始まり）
        page_start: 開始ページ（PDFの場合）
        page_end: 終了ページ（PDFの場合）
    """

    title: str
    content: str
    order_index: int
    page_start: int | None = None
    page_end: int | None = None

    def __post_init__(self) -> None:
        """バリデーション."""
        if not self.title.strip():
            raise ValueError("Chapter title cannot be empty")
        if self.order_index < 0:
            raise ValueError("order_index must be non-negative")


@dataclass
class ParsedTopic:
    """パースされたトピック情報.

    Attributes:
        title: トピックタイトル
        description: トピックの説明
        order_index: 表示順序（0始まり）
        chapter_index: 所属する章のインデックス（None=章に属さない）
    """

    title: str
    description: str | None = None
    order_index: int = 0
    chapter_index: int | None = None


@dataclass
class ParsedDocument:
    """パース結果を表すデータクラス.

    Attributes:
        title: ドキュメントタイトル
        content: 全文テキスト
        total_pages: 総ページ数（PDFの場合）
        metadata: メタデータ（著者、作成日など）
        chapters: 章のリスト
        topics: トピックのリスト
    """

    title: str
    content: str
    total_pages: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    chapters: list[ParsedChapter] = field(default_factory=list)
    topics: list[ParsedTopic] = field(default_factory=list)

    def __post_init__(self) -> None:
        """バリデーション."""
        if not self.title.strip():
            raise ValueError("Document title cannot be empty")

    @property
    def word_count(self) -> int:
        """単語数を取得."""
        return len(self.content.split())

    @property
    def char_count(self) -> int:
        """文字数を取得."""
        return len(self.content)


class BaseParser(ABC):
    """ファイルパーサーの抽象基底クラス.

    各ファイル形式（PDF、Markdown、テキスト）のパーサーはこのクラスを継承する。

    Example:
        >>> class PDFParser(BaseParser):
        ...     @property
        ...     def supported_extensions(self) -> list[str]:
        ...         return ["pdf"]
        ...
        ...     async def parse(self, file_path: Path) -> ParsedDocument:
        ...         # PDF parsing implementation
        ...         pass
    """

    @property
    @abstractmethod
    def supported_extensions(self) -> list[str]:
        """サポートするファイル拡張子のリスト（ドットなし）.

        Returns:
            拡張子のリスト（例: ["pdf"], ["md", "markdown"]）
        """
        ...

    @abstractmethod
    async def parse(self, file_path: Path) -> ParsedDocument:
        """ファイルをパースする.

        Args:
            file_path: パースするファイルのパス

        Returns:
            ParsedDocument: パース結果

        Raises:
            DocumentNotFoundError: ファイルが存在しない場合
            DocumentParseError: パースに失敗した場合
            UnsupportedFormatError: サポートされていない形式の場合
            DocumentTooLargeError: ファイルサイズが大きすぎる場合
        """
        ...

    def can_parse(self, file_path: Path) -> bool:
        """このパーサーで処理可能かどうかを判定.

        Args:
            file_path: ファイルパス

        Returns:
            処理可能な場合はTrue
        """
        extension = file_path.suffix.lower().lstrip(".")
        return extension in self.supported_extensions

    def _validate_file(
        self,
        file_path: Path,
        max_size_mb: float = 50.0,
    ) -> None:
        """ファイルのバリデーション.

        Args:
            file_path: ファイルパス
            max_size_mb: 最大ファイルサイズ（MB）

        Raises:
            DocumentNotFoundError: ファイルが存在しない場合
            UnsupportedFormatError: サポートされていない形式の場合
            DocumentTooLargeError: ファイルサイズが大きすぎる場合
        """
        from study_agent.core.exceptions import (
            DocumentNotFoundError,
            DocumentTooLargeError,
            UnsupportedFormatError,
        )

        # ファイル存在チェック
        if not file_path.exists():
            raise DocumentNotFoundError(str(file_path))

        # 形式チェック
        if not self.can_parse(file_path):
            extension = file_path.suffix.lower().lstrip(".")
            raise UnsupportedFormatError(str(file_path), extension)

        # サイズチェック
        file_size_mb = file_path.stat().st_size / (1024 * 1024)
        if file_size_mb > max_size_mb:
            raise DocumentTooLargeError(file_size_mb, max_size_mb)

    def _extract_title_from_path(self, file_path: Path) -> str:
        """ファイルパスからタイトルを抽出.

        Args:
            file_path: ファイルパス

        Returns:
            タイトル文字列
        """
        return file_path.stem.replace("_", " ").replace("-", " ")
