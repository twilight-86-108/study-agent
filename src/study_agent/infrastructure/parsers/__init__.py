"""Document parsers module.

ドキュメント（PDF、Markdown、テキスト）をパースするためのコンポーネント。

主要クラス:
    - BaseParser: パーサーの抽象基底クラス
    - PDFParser: PDFファイルパーサー
    - MarkdownParser: Markdownファイルパーサー
    - TextParser: テキストファイルパーサー
    - TextChunker: テキストチャンク分割ユーティリティ
    - ParserFactory: パーサーファクトリー

データクラス:
    - ParsedDocument: パース結果
    - ParsedChapter: パースされた章
    - ParsedTopic: パースされたトピック
    - TextChunk: テキストチャンク

Example:
    >>> from study_agent.infrastructure.parsers import (
    ...     ParserFactory,
    ...     parse_document,
    ...     TextChunker,
    ... )
    >>>
    >>> # ファクトリーを使用
    >>> doc = await ParserFactory.parse("syllabus.pdf")
    >>> print(f"Title: {doc.title}")
    >>> print(f"Chapters: {len(doc.chapters)}")
    >>>
    >>> # ショートカット関数を使用
    >>> doc = await parse_document("notes.md")
    >>>
    >>> # チャンク分割
    >>> chunker = TextChunker(chunk_size=1000, overlap=200)
    >>> chunks = chunker.chunk_text(doc.content)
"""

from study_agent.infrastructure.parsers.base import (
    BaseParser,
    ParsedChapter,
    ParsedDocument,
    ParsedTopic,
)
from study_agent.infrastructure.parsers.chunker import (
    TextChunk,
    TextChunker,
    create_chunks_from_document,
)
from study_agent.infrastructure.parsers.factory import (
    ParserFactory,
    parse_document,
)
from study_agent.infrastructure.parsers.markdown_parser import MarkdownParser
from study_agent.infrastructure.parsers.pdf_parser import PDFParser
from study_agent.infrastructure.parsers.text_parser import TextParser

__all__ = [
    # Base
    "BaseParser",
    "ParsedDocument",
    "ParsedChapter",
    "ParsedTopic",
    # Parsers
    "PDFParser",
    "MarkdownParser",
    "TextParser",
    # Chunker
    "TextChunker",
    "TextChunk",
    "create_chunks_from_document",
    # Factory
    "ParserFactory",
    "parse_document",
]
