"""Parser Factory.

ファイル形式に応じた適切なパーサーを提供するファクトリー。
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Type

from study_agent.core.exceptions import UnsupportedFormatError
from study_agent.infrastructure.parsers.base import BaseParser, ParsedDocument
from study_agent.infrastructure.parsers.markdown_parser import MarkdownParser
from study_agent.infrastructure.parsers.pdf_parser import PDFParser
from study_agent.infrastructure.parsers.text_parser import TextParser

logger = logging.getLogger(__name__)


class ParserFactory:
    """パーサーファクトリー.

    ファイル拡張子に基づいて適切なパーサーを提供する。

    Example:
        >>> factory = ParserFactory()
        >>> parser = factory.get_parser(Path("document.pdf"))
        >>> doc = await parser.parse(Path("document.pdf"))

        # または直接パース
        >>> doc = await factory.parse(Path("notes.md"))
    """

    # 拡張子とパーサークラスのマッピング
    _parser_registry: dict[str, Type[BaseParser]] = {
        "pdf": PDFParser,
        "md": MarkdownParser,
        "markdown": MarkdownParser,
        "txt": TextParser,
        "text": TextParser,
    }

    # パーサーインスタンスのキャッシュ
    _instances: dict[str, BaseParser] = {}

    @classmethod
    def register_parser(cls, extension: str, parser_class: Type[BaseParser]) -> None:
        """新しいパーサーを登録.

        Args:
            extension: ファイル拡張子（ドットなし）
            parser_class: パーサークラス
        """
        cls._parser_registry[extension.lower()] = parser_class
        logger.info(f"Registered parser for .{extension}: {parser_class.__name__}")

    @classmethod
    def get_parser(cls, file_path: Path | str) -> BaseParser:
        """ファイルに適したパーサーを取得.

        Args:
            file_path: ファイルパス

        Returns:
            BaseParser: パーサーインスタンス

        Raises:
            UnsupportedFormatError: サポートされていない形式の場合
        """
        if isinstance(file_path, str):
            file_path = Path(file_path)

        extension = file_path.suffix.lower().lstrip(".")

        if extension not in cls._parser_registry:
            raise UnsupportedFormatError(
                str(file_path),
                extension,
            )

        # キャッシュからインスタンスを取得または作成
        if extension not in cls._instances:
            parser_class = cls._parser_registry[extension]
            cls._instances[extension] = parser_class()
            logger.debug(f"Created parser instance: {parser_class.__name__}")

        return cls._instances[extension]

    @classmethod
    async def parse(
        cls,
        file_path: Path | str,
        **kwargs,
    ) -> ParsedDocument:
        """ファイルをパース.

        適切なパーサーを自動選択してパースを実行する。

        Args:
            file_path: ファイルパス
            **kwargs: パーサー固有のオプション

        Returns:
            ParsedDocument: パース結果

        Raises:
            DocumentNotFoundError: ファイルが存在しない場合
            DocumentParseError: パースに失敗した場合
            UnsupportedFormatError: サポートされていない形式の場合
            DocumentTooLargeError: ファイルサイズが大きすぎる場合
        """
        if isinstance(file_path, str):
            file_path = Path(file_path)

        parser = cls.get_parser(file_path)
        return await parser.parse(file_path, **kwargs)

    @classmethod
    def supported_extensions(cls) -> list[str]:
        """サポートする拡張子のリストを取得.

        Returns:
            拡張子のリスト
        """
        return list(cls._parser_registry.keys())

    @classmethod
    def is_supported(cls, file_path: Path | str) -> bool:
        """ファイル形式がサポートされているかチェック.

        Args:
            file_path: ファイルパス

        Returns:
            サポートされている場合はTrue
        """
        if isinstance(file_path, str):
            file_path = Path(file_path)

        extension = file_path.suffix.lower().lstrip(".")
        return extension in cls._parser_registry

    @classmethod
    def clear_cache(cls) -> None:
        """パーサーインスタンスのキャッシュをクリア."""
        cls._instances.clear()
        logger.debug("Parser instance cache cleared")


# 便利なエイリアス関数
async def parse_document(
    file_path: Path | str,
    **kwargs,
) -> ParsedDocument:
    """ドキュメントをパースするショートカット関数.

    Args:
        file_path: ファイルパス
        **kwargs: パーサー固有のオプション

    Returns:
        ParsedDocument: パース結果

    Example:
        >>> from study_agent.infrastructure.parsers import parse_document
        >>> doc = await parse_document("notes.md")
    """
    return await ParserFactory.parse(file_path, **kwargs)
