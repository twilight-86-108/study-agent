"""Text Parser.

プレーンテキストファイルをパースする。
段落や空行を基準にした簡易的な構造認識を行う。
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

from study_agent.core.exceptions import DocumentParseError
from study_agent.infrastructure.parsers.base import (
    BaseParser,
    ParsedChapter,
    ParsedDocument,
    ParsedTopic,
)

logger = logging.getLogger(__name__)


class TextParser(BaseParser):
    """プレーンテキストファイルパーサー.

    .txtファイルをパースし、段落や空行を基準に構造を認識する。

    Features:
        - 空行区切りで段落を認識
        - 番号付きセクションの検出
        - 大文字タイトル行の検出

    Example:
        >>> parser = TextParser()
        >>> doc = await parser.parse(Path("notes.txt"))
        >>> print(f"Content length: {doc.char_count}")
    """

    # セクションパターン（番号付き）
    SECTION_PATTERNS = [
        # "1. Section Title" or "1) Section Title"
        r"^(\d+)[.\)]\s+(.+)$",
        # "Section 1: Title"
        r"^Section\s+(\d+)[:\s]+(.+)$",
        # "CHAPTER 1" (大文字)
        r"^([A-Z][A-Z\s]+)$",
    ]

    # 段落間の最小空行数
    MIN_PARAGRAPH_GAP = 1

    @property
    def supported_extensions(self) -> list[str]:
        """サポートする拡張子."""
        return ["txt", "text"]

    async def parse(
        self,
        file_path: Path,
        max_size_mb: float = 10.0,
    ) -> ParsedDocument:
        """テキストファイルをパース.

        Args:
            file_path: テキストファイルのパス
            max_size_mb: 最大ファイルサイズ（MB）

        Returns:
            ParsedDocument: パース結果

        Raises:
            DocumentNotFoundError: ファイルが存在しない場合
            DocumentParseError: パースに失敗した場合
            UnsupportedFormatError: テキスト以外の形式の場合
            DocumentTooLargeError: ファイルサイズが大きすぎる場合
        """
        self._validate_file(file_path, max_size_mb)

        try:
            # ファイル読み込み（複数エンコーディング試行）
            content = self._read_file_with_encoding(file_path)

            # タイトル抽出
            title = self._extract_title_from_content(
                content
            ) or self._extract_title_from_path(file_path)

            # 章構造の抽出
            chapters = self._extract_chapters(content)

            # トピック抽出
            topics = self._extract_topics(content, chapters)

            logger.info(
                f"Parsed Text: {file_path.name}, "
                f"chapters={len(chapters)}, topics={len(topics)}"
            )

            return ParsedDocument(
                title=title,
                content=content,
                total_pages=None,
                metadata={},
                chapters=chapters,
                topics=topics,
            )

        except DocumentParseError:
            raise
        except Exception as e:
            logger.exception(f"Failed to parse text: {file_path}")
            raise DocumentParseError(
                str(file_path),
                reason=str(e),
                cause=e,
            )

    def _read_file_with_encoding(self, file_path: Path) -> str:
        """複数エンコーディングを試行してファイルを読み込む.

        Args:
            file_path: ファイルパス

        Returns:
            ファイル内容

        Raises:
            DocumentParseError: 読み込めない場合
        """
        encodings = ["utf-8", "utf-8-sig", "shift_jis", "cp932", "euc-jp", "latin-1"]

        for encoding in encodings:
            try:
                return file_path.read_text(encoding=encoding)
            except UnicodeDecodeError:
                continue

        raise DocumentParseError(
            str(file_path),
            reason=f"Unable to decode file with encodings: {encodings}",
        )

    def _extract_title_from_content(self, content: str) -> str | None:
        """内容の最初の行からタイトルを抽出.

        Args:
            content: ファイル内容

        Returns:
            タイトル文字列、見つからない場合はNone
        """
        lines = content.strip().split("\n")
        if not lines:
            return None

        # 最初の非空行
        for line in lines[:5]:  # 最初の5行を検索
            line = line.strip()
            if line:
                # 行が短すぎたり長すぎたりしない
                if 3 <= len(line) <= 100:
                    return line
        return None

    def _extract_chapters(self, content: str) -> list[ParsedChapter]:
        """セクションパターンから章を抽出.

        Args:
            content: ファイル内容

        Returns:
            ParsedChapterのリスト
        """
        lines = content.split("\n")
        section_positions: list[tuple[int, str]] = []  # (line_idx, title)

        for idx, line in enumerate(lines):
            line_stripped = line.strip()
            if not line_stripped:
                continue

            for pattern in self.SECTION_PATTERNS:
                match = re.match(pattern, line_stripped, re.IGNORECASE)
                if match:
                    # マッチしたグループからタイトルを取得
                    if match.lastindex and match.lastindex >= 2:
                        title = match.group(2).strip()
                    else:
                        title = line_stripped
                    section_positions.append((idx, title))
                    break

        # セクションがない場合は段落ベースで分割
        if not section_positions:
            return self._extract_chapters_by_paragraphs(content)

        # 章の内容を抽出
        chapters: list[ParsedChapter] = []
        for i, (line_idx, title) in enumerate(section_positions):
            end_idx = (
                section_positions[i + 1][0]
                if i + 1 < len(section_positions)
                else len(lines)
            )

            chapter_content = "\n".join(lines[line_idx + 1 : end_idx]).strip()

            if chapter_content:
                chapters.append(
                    ParsedChapter(
                        title=title,
                        content=chapter_content,
                        order_index=len(chapters),
                        page_start=None,
                        page_end=None,
                    )
                )

        logger.debug(f"Extracted {len(chapters)} chapters from patterns")
        return chapters

    def _extract_chapters_by_paragraphs(
        self, content: str, max_chapters: int = 10
    ) -> list[ParsedChapter]:
        """段落（空行区切り）から章を作成.

        Args:
            content: ファイル内容
            max_chapters: 最大章数

        Returns:
            ParsedChapterのリスト
        """
        # 2行以上の空行で分割
        paragraphs = re.split(r"\n{2,}", content.strip())

        chapters: list[ParsedChapter] = []
        for i, para in enumerate(paragraphs[:max_chapters]):
            para = para.strip()
            if not para:
                continue

            # 最初の行をタイトルとして使用
            lines = para.split("\n")
            title = lines[0].strip()[:50]  # 最大50文字
            if not title:
                title = f"Section {i + 1}"

            chapters.append(
                ParsedChapter(
                    title=title,
                    content=para,
                    order_index=i,
                    page_start=None,
                    page_end=None,
                )
            )

        logger.debug(f"Extracted {len(chapters)} chapters from paragraphs")
        return chapters

    def _extract_topics(
        self, content: str, chapters: list[ParsedChapter]
    ) -> list[ParsedTopic]:
        """章からトピックを抽出.

        各章をトピックとして扱う。

        Args:
            content: ファイル内容
            chapters: 章リスト

        Returns:
            ParsedTopicのリスト
        """
        topics: list[ParsedTopic] = []

        if not chapters:
            # 章がない場合は全体を1つのトピックに
            first_line = content.strip().split("\n")[0][:50]
            topics.append(
                ParsedTopic(
                    title=first_line or "Main Content",
                    description=(
                        content[:200] + "..." if len(content) > 200 else content
                    ),
                    order_index=0,
                    chapter_index=None,
                )
            )
            return topics

        # 各章をトピックに変換
        for i, chapter in enumerate(chapters):
            topics.append(
                ParsedTopic(
                    title=chapter.title,
                    description=(
                        chapter.content[:200] + "..."
                        if len(chapter.content) > 200
                        else chapter.content
                    ),
                    order_index=i,
                    chapter_index=i,
                )
            )

        return topics
