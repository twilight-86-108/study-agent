"""Markdown Parser.

Markdownファイルをパースし、見出し構造から章とトピックを抽出する。
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


class MarkdownParser(BaseParser):
    """Markdownファイルパーサー.

    Markdownファイルを解析し、見出し（#, ##, ###）から章構造を抽出する。

    Features:
        - H1/H2から章構造を認識
        - H3以下からトピックを抽出
        - YAMLフロントマターからメタデータを取得
        - リンク、コードブロックの処理

    Example:
        >>> parser = MarkdownParser()
        >>> doc = await parser.parse(Path("notes.md"))
        >>> print(f"Topics: {len(doc.topics)}")
    """

    # 見出しパターン
    HEADING_PATTERN = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)

    # YAMLフロントマターパターン
    FRONTMATTER_PATTERN = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)

    @property
    def supported_extensions(self) -> list[str]:
        """サポートする拡張子."""
        return ["md", "markdown"]

    async def parse(
        self,
        file_path: Path,
        max_size_mb: float = 10.0,
    ) -> ParsedDocument:
        """Markdownファイルをパース.

        Args:
            file_path: Markdownファイルのパス
            max_size_mb: 最大ファイルサイズ（MB）

        Returns:
            ParsedDocument: パース結果

        Raises:
            DocumentNotFoundError: ファイルが存在しない場合
            DocumentParseError: パースに失敗した場合
            UnsupportedFormatError: Markdown以外の形式の場合
            DocumentTooLargeError: ファイルサイズが大きすぎる場合
        """
        self._validate_file(file_path, max_size_mb)

        try:
            # ファイル読み込み
            content = file_path.read_text(encoding="utf-8")

            # フロントマター抽出
            metadata, content_body = self._extract_frontmatter(content)

            # タイトル決定
            title = (
                metadata.get("title")
                or self._extract_title_from_content(content_body)
                or self._extract_title_from_path(file_path)
            )

            # 章構造の抽出
            chapters = self._extract_chapters(content_body)

            # トピック抽出
            topics = self._extract_topics(content_body, chapters)

            logger.info(
                f"Parsed Markdown: {file_path.name}, "
                f"chapters={len(chapters)}, topics={len(topics)}"
            )

            return ParsedDocument(
                title=title,
                content=content_body,
                total_pages=None,  # Markdownにはページ概念なし
                metadata=metadata,
                chapters=chapters,
                topics=topics,
            )

        except DocumentParseError:
            raise
        except Exception as e:
            logger.exception(f"Failed to parse Markdown: {file_path}")
            raise DocumentParseError(
                str(file_path),
                reason=str(e),
                cause=e,
            )

    def _extract_frontmatter(self, content: str) -> tuple[dict, str]:
        """YAMLフロントマターを抽出.

        Args:
            content: ファイル全体の内容

        Returns:
            (メタデータ辞書, フロントマターを除いた本文)
        """
        match = self.FRONTMATTER_PATTERN.match(content)
        if not match:
            return {}, content

        yaml_content = match.group(1)
        body = content[match.end() :]

        # 簡易YAMLパース
        metadata: dict = {}
        for line in yaml_content.split("\n"):
            line = line.strip()
            if ":" in line:
                key, value = line.split(":", 1)
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                metadata[key] = value

        return metadata, body

    def _extract_title_from_content(self, content: str) -> str | None:
        """本文の最初のH1からタイトルを抽出.

        Args:
            content: 本文

        Returns:
            タイトル文字列、見つからない場合はNone
        """
        for line in content.split("\n"):
            line = line.strip()
            if line.startswith("# ") and not line.startswith("##"):
                return line[2:].strip()
        return None

    def _extract_chapters(self, content: str) -> list[ParsedChapter]:
        """見出しから章構造を抽出.

        H1またはH2を章として認識する。

        Args:
            content: 本文

        Returns:
            ParsedChapterのリスト
        """
        lines = content.split("\n")
        chapter_positions: list[tuple[int, str, int]] = []  # (line_idx, title, level)

        for idx, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith("#"):
                match = self.HEADING_PATTERN.match(stripped)
                if match:
                    level = len(match.group(1))
                    title = match.group(2).strip()
                    # H1, H2を章として扱う
                    if level <= 2:
                        chapter_positions.append((idx, title, level))

        # 章の内容を抽出
        chapters: list[ParsedChapter] = []
        for i, (line_idx, title, _level) in enumerate(chapter_positions):
            # 次の章の開始位置（またはドキュメント終端）
            end_idx = (
                chapter_positions[i + 1][0]
                if i + 1 < len(chapter_positions)
                else len(lines)
            )

            chapter_content = "\n".join(lines[line_idx + 1 : end_idx]).strip()

            # 空の章はスキップ
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

        logger.debug(f"Extracted {len(chapters)} chapters from headings")
        return chapters

    def _extract_topics(
        self, content: str, chapters: list[ParsedChapter]
    ) -> list[ParsedTopic]:
        """H3以下の見出しからトピックを抽出.

        Args:
            content: 本文
            chapters: 章リスト

        Returns:
            ParsedTopicのリスト
        """
        topics: list[ParsedTopic] = []
        lines = content.split("\n")

        current_chapter_idx: int | None = None
        chapter_starts: dict[int, int] = {}  # chapter_idx -> line_idx

        # 章の開始位置をマッピング
        for i, chapter in enumerate(chapters):
            for idx, line in enumerate(lines):
                if chapter.title in line:
                    chapter_starts[i] = idx
                    break

        topic_order = 0
        for idx, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith("###"):
                match = self.HEADING_PATTERN.match(stripped)
                if match:
                    level = len(match.group(1))
                    title = match.group(2).strip()

                    if level >= 3:  # H3以下
                        # 所属する章を特定
                        current_chapter_idx = self._find_chapter_for_line(
                            idx, chapter_starts
                        )

                        # トピック説明（次の見出しまでの内容）
                        description = self._extract_topic_description(idx, lines)

                        topics.append(
                            ParsedTopic(
                                title=title,
                                description=description,
                                order_index=topic_order,
                                chapter_index=current_chapter_idx,
                            )
                        )
                        topic_order += 1

        # 章もトピックとして追加（H3がない場合の対策）
        if not topics and chapters:
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

        logger.debug(f"Extracted {len(topics)} topics")
        return topics

    def _find_chapter_for_line(
        self, line_idx: int, chapter_starts: dict[int, int]
    ) -> int | None:
        """行インデックスが属する章を特定.

        Args:
            line_idx: 行インデックス
            chapter_starts: 章の開始位置マッピング

        Returns:
            章インデックス、見つからない場合はNone
        """
        current_chapter: int | None = None
        current_start = -1

        for chapter_idx, start_idx in chapter_starts.items():
            if start_idx <= line_idx and start_idx > current_start:
                current_chapter = chapter_idx
                current_start = start_idx

        return current_chapter

    def _extract_topic_description(
        self, heading_idx: int, lines: list[str], max_lines: int = 10
    ) -> str:
        """トピックの説明文を抽出.

        見出しの直後から次の見出しまでの内容を取得。

        Args:
            heading_idx: 見出しの行インデックス
            lines: 全行リスト
            max_lines: 最大行数

        Returns:
            説明文
        """
        description_lines: list[str] = []

        for i in range(heading_idx + 1, min(heading_idx + 1 + max_lines, len(lines))):
            line = lines[i]
            # 次の見出しに到達したら終了
            if line.strip().startswith("#"):
                break
            description_lines.append(line)

        description = "\n".join(description_lines).strip()

        # 200文字に切り詰め
        if len(description) > 200:
            description = description[:200] + "..."

        return description
