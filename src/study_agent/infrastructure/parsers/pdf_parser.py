"""PDF Parser using PyMuPDF.

PyMuPDF（fitz）を使用してPDFファイルをパースする。
章構造の自動検出、目次抽出、メタデータ取得をサポート。
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

from study_agent.core.exceptions import DocumentParseError
from study_agent.infrastructure.parsers.base import (
    BaseParser,
    ParsedChapter,
    ParsedDocument,
    ParsedTopic,
)

logger = logging.getLogger(__name__)


class PDFParser(BaseParser):
    """PDFファイルパーサー.

    PyMuPDF (fitz) を使用してPDFファイルをパースする。

    Features:
        - テキスト抽出
        - 目次（TOC）からの章構造認識
        - メタデータ（著者、タイトル、作成日）取得
        - ヘッダーパターンからの章自動検出

    Example:
        >>> parser = PDFParser()
        >>> doc = await parser.parse(Path("syllabus.pdf"))
        >>> print(f"Chapters: {len(doc.chapters)}")
    """

    # 章を検出する正規表現パターン
    CHAPTER_PATTERNS = [
        # "Chapter 1: Introduction" or "第1章 はじめに"
        r"^(?:Chapter|第)\s*(\d+)[:\s：章]?\s*(.+)$",
        # "1. Introduction" or "1　はじめに"
        r"^(\d+)[.\s．\s　]\s*(.+)$",
        # "Part I: Overview"
        r"^Part\s+([IVX\d]+)[:\s]\s*(.+)$",
    ]

    # 最小章サイズ（文字数）- これより短い章は無視
    MIN_CHAPTER_SIZE = 100

    @property
    def supported_extensions(self) -> list[str]:
        """サポートする拡張子."""
        return ["pdf"]

    async def parse(
        self,
        file_path: Path,
        max_size_mb: float = 50.0,
        max_pages: int = 500,
    ) -> ParsedDocument:
        """PDFファイルをパース.

        Args:
            file_path: PDFファイルのパス
            max_size_mb: 最大ファイルサイズ（MB）
            max_pages: 最大ページ数

        Returns:
            ParsedDocument: パース結果

        Raises:
            DocumentNotFoundError: ファイルが存在しない場合
            DocumentParseError: パースに失敗した場合
            UnsupportedFormatError: PDF以外の形式の場合
            DocumentTooLargeError: ファイルサイズが大きすぎる場合
        """
        self._validate_file(file_path, max_size_mb)

        try:
            import fitz  # PyMuPDF
        except ImportError as e:
            raise DocumentParseError(
                str(file_path),
                reason="PyMuPDF is not installed. Run: pip install pymupdf",
                cause=e,
            )

        try:
            doc = fitz.open(file_path)

            # ページ数チェック
            if doc.page_count > max_pages:
                doc.close()
                raise DocumentParseError(
                    str(file_path),
                    reason=f"Too many pages: {doc.page_count} > {max_pages}",
                )

            # メタデータ取得
            metadata = self._extract_metadata(doc)

            # タイトル決定
            title = metadata.get("title") or self._extract_title_from_path(file_path)

            # テキスト抽出（ページごと）
            pages_text: list[str] = []
            for page_num in range(doc.page_count):
                page = doc[page_num]
                text = page.get_text()
                pages_text.append(text)

            full_content = "\n".join(pages_text)

            # 章構造の抽出
            chapters = self._extract_chapters(doc, pages_text)

            # トピック抽出（簡易版）
            topics = self._extract_topics_from_chapters(chapters)

            doc.close()

            logger.info(
                f"Parsed PDF: {file_path.name}, "
                f"pages={len(pages_text)}, chapters={len(chapters)}"
            )

            return ParsedDocument(
                title=title,
                content=full_content,
                total_pages=len(pages_text),
                metadata=metadata,
                chapters=chapters,
                topics=topics,
            )

        except DocumentParseError:
            raise
        except Exception as e:
            logger.exception(f"Failed to parse PDF: {file_path}")
            raise DocumentParseError(
                str(file_path),
                reason=str(e),
                cause=e,
            )

    def _extract_metadata(self, doc: Any) -> dict[str, Any]:
        """PDFメタデータを抽出.

        Args:
            doc: PyMuPDF Document object

        Returns:
            メタデータ辞書
        """
        metadata: dict[str, Any] = {}

        try:
            raw_metadata = doc.metadata
            if raw_metadata:
                if raw_metadata.get("title"):
                    metadata["title"] = raw_metadata["title"]
                if raw_metadata.get("author"):
                    metadata["author"] = raw_metadata["author"]
                if raw_metadata.get("subject"):
                    metadata["subject"] = raw_metadata["subject"]
                if raw_metadata.get("creationDate"):
                    metadata["created_at"] = raw_metadata["creationDate"]
                if raw_metadata.get("modDate"):
                    metadata["modified_at"] = raw_metadata["modDate"]
        except Exception as e:
            logger.warning(f"Failed to extract metadata: {e}")

        return metadata

    def _extract_chapters(self, doc: Any, pages_text: list[str]) -> list[ParsedChapter]:
        """章構造を抽出.

        まずTOC（目次）からの抽出を試み、失敗したらヘッダーパターンから検出。

        Args:
            doc: PyMuPDF Document object
            pages_text: ページごとのテキストリスト

        Returns:
            ParsedChapterのリスト
        """
        # まずTOCから抽出を試みる
        chapters = self._extract_chapters_from_toc(doc, pages_text)
        if chapters:
            return chapters

        # TOCがない場合はヘッダーパターンから検出
        return self._extract_chapters_from_patterns(pages_text)

    def _extract_chapters_from_toc(
        self, doc: Any, pages_text: list[str]
    ) -> list[ParsedChapter]:
        """TOC（目次）から章を抽出.

        Args:
            doc: PyMuPDF Document object
            pages_text: ページごとのテキストリスト

        Returns:
            ParsedChapterのリスト
        """
        try:
            toc = doc.get_toc()
            if not toc:
                return []

            chapters: list[ParsedChapter] = []
            # TOCエントリ: [level, title, page_number]
            level_1_entries = [
                (title, page) for level, title, page in toc if level == 1
            ]

            for i, (title, page_start) in enumerate(level_1_entries):
                # 次の章の開始ページ（または最終ページ）
                page_end = (
                    level_1_entries[i + 1][1] - 1
                    if i + 1 < len(level_1_entries)
                    else doc.page_count
                )

                # ページ範囲のテキストを結合
                content = "\n".join(pages_text[page_start - 1 : page_end])

                if len(content) >= self.MIN_CHAPTER_SIZE:
                    chapters.append(
                        ParsedChapter(
                            title=title.strip(),
                            content=content,
                            order_index=i,
                            page_start=page_start,
                            page_end=page_end,
                        )
                    )

            logger.debug(f"Extracted {len(chapters)} chapters from TOC")
            return chapters

        except Exception as e:
            logger.warning(f"Failed to extract chapters from TOC: {e}")
            return []

    def _extract_chapters_from_patterns(
        self, pages_text: list[str]
    ) -> list[ParsedChapter]:
        """ヘッダーパターンから章を検出.

        Args:
            pages_text: ページごとのテキストリスト

        Returns:
            ParsedChapterのリスト
        """
        full_text = "\n".join(pages_text)
        lines = full_text.split("\n")

        chapter_positions: list[tuple[int, str, int]] = []  # (line_idx, title, page)

        for line_idx, line in enumerate(lines):
            line_stripped = line.strip()
            if not line_stripped:
                continue

            for pattern in self.CHAPTER_PATTERNS:
                match = re.match(pattern, line_stripped, re.IGNORECASE)
                if match:
                    # ページ番号を推定（大まかに）
                    page_estimate = self._estimate_page(line_idx, lines, pages_text)
                    chapter_positions.append((line_idx, line_stripped, page_estimate))
                    break

        # 章の内容を抽出
        chapters: list[ParsedChapter] = []
        for i, (line_idx, title, page_start) in enumerate(chapter_positions):
            # 次の章の開始位置（またはドキュメント終端）
            end_idx = (
                chapter_positions[i + 1][0]
                if i + 1 < len(chapter_positions)
                else len(lines)
            )
            page_end = (
                chapter_positions[i + 1][2]
                if i + 1 < len(chapter_positions)
                else len(pages_text)
            )

            content = "\n".join(lines[line_idx:end_idx])

            if len(content) >= self.MIN_CHAPTER_SIZE:
                chapters.append(
                    ParsedChapter(
                        title=title,
                        content=content,
                        order_index=i,
                        page_start=page_start,
                        page_end=page_end,
                    )
                )

        logger.debug(f"Extracted {len(chapters)} chapters from patterns")
        return chapters

    def _estimate_page(
        self, line_idx: int, lines: list[str], pages_text: list[str]
    ) -> int:
        """行インデックスからページ番号を推定.

        Args:
            line_idx: 行インデックス
            lines: 全行リスト
            pages_text: ページごとのテキスト

        Returns:
            推定ページ番号（1始まり）
        """
        char_count = sum(len(line) for line in lines[:line_idx])
        total_chars = sum(len(page) for page in pages_text)
        if total_chars == 0:
            return 1
        return max(1, int((char_count / total_chars) * len(pages_text)) + 1)

    def _extract_topics_from_chapters(
        self, chapters: list[ParsedChapter]
    ) -> list[ParsedTopic]:
        """章からトピックを抽出（簡易版）.

        各章をトピックとして扱う。
        より高度な抽出はLLMを使用するPhaseで実装予定。

        Args:
            chapters: 章リスト

        Returns:
            ParsedTopicのリスト
        """
        topics: list[ParsedTopic] = []

        for chapter in chapters:
            # 章タイトルからトピックを作成
            topics.append(
                ParsedTopic(
                    title=chapter.title,
                    description=(
                        chapter.content[:200] + "..."
                        if len(chapter.content) > 200
                        else chapter.content
                    ),
                    order_index=chapter.order_index,
                    chapter_index=chapter.order_index,
                )
            )

        return topics
