"""Document parser integration tests.

パーサーモジュールの統合テスト。
PDF、Markdown、テキストのパースとチャンク分割をテストする。
"""

from __future__ import annotations

import pytest
from pathlib import Path
from tempfile import TemporaryDirectory

from study_agent.core.exceptions import (
    DocumentNotFoundError,
    UnsupportedFormatError,
)
from study_agent.infrastructure.parsers import (
    BaseParser,
    MarkdownParser,
    ParsedChapter,
    ParsedDocument,
    ParsedTopic,
    ParserFactory,
    PDFParser,
    TextChunk,
    TextChunker,
    TextParser,
    create_chunks_from_document,
    parse_document,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def temp_dir():
    """一時ディレクトリを作成."""
    with TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_markdown(temp_dir: Path) -> Path:
    """サンプルMarkdownファイルを作成."""
    content = """---
title: Test Document
author: Test Author
---

# Introduction

This is the introduction section.

## Background

Some background information here.

### Topic 1

Details about topic 1.

### Topic 2

Details about topic 2.

# Main Content

This is the main content section.

## Section A

Content for section A.

## Section B

Content for section B.
"""
    file_path = temp_dir / "test.md"
    file_path.write_text(content, encoding="utf-8")
    return file_path


@pytest.fixture
def sample_text(temp_dir: Path) -> Path:
    """サンプルテキストファイルを作成."""
    content = """Sample Document Title

1. First Section

This is the content of the first section.
It contains multiple lines of text.

2. Second Section

This is the content of the second section.
More text goes here.

3. Third Section

Final section content.
"""
    file_path = temp_dir / "test.txt"
    file_path.write_text(content, encoding="utf-8")
    return file_path


@pytest.fixture
def long_text() -> str:
    """長いテキストを生成."""
    paragraph = "This is a sample sentence for testing chunking. " * 50
    return paragraph * 10


# =============================================================================
# ParsedDocument / ParsedChapter Tests
# =============================================================================


class TestParsedDocument:
    """ParsedDocumentデータクラスのテスト."""

    def test_create_basic(self):
        """基本的な作成."""
        doc = ParsedDocument(
            title="Test Doc",
            content="Test content",
        )
        assert doc.title == "Test Doc"
        assert doc.content == "Test content"
        assert doc.total_pages is None
        assert doc.chapters == []
        assert doc.topics == []

    def test_create_with_chapters(self):
        """章付きで作成."""
        chapters = [
            ParsedChapter(title="Ch1", content="Content 1", order_index=0),
            ParsedChapter(title="Ch2", content="Content 2", order_index=1),
        ]
        doc = ParsedDocument(
            title="Test Doc",
            content="Full content",
            chapters=chapters,
        )
        assert len(doc.chapters) == 2
        assert doc.chapters[0].title == "Ch1"

    def test_word_count(self):
        """単語数カウント."""
        doc = ParsedDocument(
            title="Test",
            content="One two three four five",
        )
        assert doc.word_count == 5

    def test_char_count(self):
        """文字数カウント."""
        doc = ParsedDocument(
            title="Test",
            content="Hello",
        )
        assert doc.char_count == 5

    def test_empty_title_raises(self):
        """空タイトルでエラー."""
        with pytest.raises(ValueError, match="title cannot be empty"):
            ParsedDocument(title="", content="Content")


class TestParsedChapter:
    """ParsedChapterデータクラスのテスト."""

    def test_create_basic(self):
        """基本的な作成."""
        chapter = ParsedChapter(
            title="Chapter 1",
            content="Chapter content",
            order_index=0,
        )
        assert chapter.title == "Chapter 1"
        assert chapter.order_index == 0
        assert chapter.page_start is None

    def test_create_with_pages(self):
        """ページ情報付きで作成."""
        chapter = ParsedChapter(
            title="Chapter 1",
            content="Content",
            order_index=0,
            page_start=1,
            page_end=10,
        )
        assert chapter.page_start == 1
        assert chapter.page_end == 10

    def test_empty_title_raises(self):
        """空タイトルでエラー."""
        with pytest.raises(ValueError, match="title cannot be empty"):
            ParsedChapter(title="  ", content="Content", order_index=0)

    def test_negative_order_index_raises(self):
        """負のorder_indexでエラー."""
        with pytest.raises(ValueError, match="non-negative"):
            ParsedChapter(title="Chapter", content="Content", order_index=-1)


# =============================================================================
# MarkdownParser Tests
# =============================================================================


class TestMarkdownParser:
    """MarkdownParserのテスト."""

    @pytest.fixture
    def parser(self) -> MarkdownParser:
        return MarkdownParser()

    def test_supported_extensions(self, parser: MarkdownParser):
        """サポートする拡張子."""
        assert "md" in parser.supported_extensions
        assert "markdown" in parser.supported_extensions

    def test_can_parse_md(self, parser: MarkdownParser, sample_markdown: Path):
        """Markdownファイルを判定."""
        assert parser.can_parse(sample_markdown) is True

    def test_cannot_parse_txt(self, parser: MarkdownParser, sample_text: Path):
        """テキストファイルは判定しない."""
        assert parser.can_parse(sample_text) is False

    @pytest.mark.asyncio
    async def test_parse_markdown(self, parser: MarkdownParser, sample_markdown: Path):
        """Markdownをパース."""
        doc = await parser.parse(sample_markdown)

        assert doc.title == "Test Document"
        assert "introduction" in doc.content.lower()
        assert len(doc.chapters) >= 2  # Introduction, Main Content
        assert len(doc.topics) >= 2

    @pytest.mark.asyncio
    async def test_parse_extracts_frontmatter(
        self, parser: MarkdownParser, sample_markdown: Path
    ):
        """フロントマターを抽出."""
        doc = await parser.parse(sample_markdown)

        assert doc.metadata.get("author") == "Test Author"

    @pytest.mark.asyncio
    async def test_parse_nonexistent_file(self, parser: MarkdownParser, temp_dir: Path):
        """存在しないファイルでエラー."""
        with pytest.raises(DocumentNotFoundError):
            await parser.parse(temp_dir / "nonexistent.md")


# =============================================================================
# TextParser Tests
# =============================================================================


class TestTextParser:
    """TextParserのテスト."""

    @pytest.fixture
    def parser(self) -> TextParser:
        return TextParser()

    def test_supported_extensions(self, parser: TextParser):
        """サポートする拡張子."""
        assert "txt" in parser.supported_extensions
        assert "text" in parser.supported_extensions

    @pytest.mark.asyncio
    async def test_parse_text(self, parser: TextParser, sample_text: Path):
        """テキストをパース."""
        doc = await parser.parse(sample_text)

        assert doc.title is not None
        assert "First Section" in doc.content
        assert len(doc.chapters) >= 3  # 3 sections

    @pytest.mark.asyncio
    async def test_parse_text_extracts_sections(
        self, parser: TextParser, sample_text: Path
    ):
        """セクションを抽出."""
        doc = await parser.parse(sample_text)

        section_titles = [c.title for c in doc.chapters]
        assert any("First" in t for t in section_titles)


# =============================================================================
# TextChunker Tests
# =============================================================================


class TestTextChunker:
    """TextChunkerのテスト."""

    def test_basic_chunking(self, long_text: str):
        """基本的なチャンク分割."""
        chunker = TextChunker(chunk_size=1000, overlap=200)
        chunks = chunker.chunk_text(long_text)

        assert len(chunks) > 1
        for chunk in chunks:
            assert chunk.char_count <= 1000 + 200  # 許容範囲

    def test_chunk_indices(self, long_text: str):
        """チャンクインデックス."""
        chunker = TextChunker(chunk_size=500, overlap=100)
        chunks = chunker.chunk_text(long_text)

        for i, chunk in enumerate(chunks):
            assert chunk.chunk_index == i

    def test_chunk_positions(self, long_text: str):
        """チャンクの位置情報."""
        chunker = TextChunker(chunk_size=500, overlap=100)
        chunks = chunker.chunk_text(long_text)

        for chunk in chunks:
            assert chunk.start_char >= 0
            assert chunk.end_char > chunk.start_char

    def test_chunk_metadata(self):
        """メタデータの付与."""
        chunker = TextChunker(chunk_size=100, overlap=20)
        text = "A" * 500
        metadata = {"document_id": "doc1", "source": "test"}

        chunks = chunker.chunk_text(text, metadata)

        for chunk in chunks:
            assert chunk.metadata["document_id"] == "doc1"
            assert chunk.metadata["source"] == "test"

    def test_empty_text(self):
        """空テキスト."""
        chunker = TextChunker(chunk_size=100, overlap=20)
        chunks = chunker.chunk_text("")

        assert chunks == []

    def test_short_text(self):
        """短いテキスト（1チャンク以下）."""
        chunker = TextChunker(chunk_size=1000, overlap=200)
        text = "Short text"

        chunks = chunker.chunk_text(text)

        assert len(chunks) == 1
        assert chunks[0].content == text

    def test_invalid_chunk_size(self):
        """無効なchunk_size."""
        with pytest.raises(ValueError):
            TextChunker(chunk_size=0, overlap=20)

    def test_invalid_overlap(self):
        """無効なoverlap."""
        with pytest.raises(ValueError):
            TextChunker(chunk_size=100, overlap=-1)

    def test_overlap_greater_than_chunk_size(self):
        """overlapがchunk_sizeより大きい."""
        with pytest.raises(ValueError):
            TextChunker(chunk_size=100, overlap=150)

    def test_chunk_by_pages(self):
        """ページごとのチャンク分割."""
        chunker = TextChunker(chunk_size=100, overlap=20)
        pages = [
            "Page 1 content. " * 10,
            "Page 2 content. " * 10,
            "Page 3 content. " * 10,
        ]

        chunks = chunker.chunk_by_pages(pages)

        # ページ番号がメタデータに含まれる
        page_numbers = set(c.metadata.get("page_number") for c in chunks)
        assert 1 in page_numbers
        assert 2 in page_numbers
        assert 3 in page_numbers


class TestCreateChunksFromDocument:
    """create_chunks_from_documentヘルパー関数のテスト."""

    def test_basic_usage(self):
        """基本的な使用."""
        content = "Sample content. " * 100
        chunks = create_chunks_from_document(
            content=content,
            chunk_size=200,
            overlap=50,
            document_id="doc123",
            document_title="Test Doc",
        )

        assert len(chunks) > 1
        assert all(c.metadata.get("document_id") == "doc123" for c in chunks)
        assert all(c.metadata.get("document_title") == "Test Doc" for c in chunks)


# =============================================================================
# ParserFactory Tests
# =============================================================================


class TestParserFactory:
    """ParserFactoryのテスト."""

    def test_get_parser_pdf(self, temp_dir: Path):
        """PDFパーサーを取得."""
        pdf_path = temp_dir / "test.pdf"
        pdf_path.touch()

        parser = ParserFactory.get_parser(pdf_path)
        assert isinstance(parser, PDFParser)

    def test_get_parser_markdown(self, temp_dir: Path):
        """Markdownパーサーを取得."""
        md_path = temp_dir / "test.md"
        md_path.touch()

        parser = ParserFactory.get_parser(md_path)
        assert isinstance(parser, MarkdownParser)

    def test_get_parser_text(self, temp_dir: Path):
        """テキストパーサーを取得."""
        txt_path = temp_dir / "test.txt"
        txt_path.touch()

        parser = ParserFactory.get_parser(txt_path)
        assert isinstance(parser, TextParser)

    def test_get_parser_unsupported(self, temp_dir: Path):
        """サポートされていない形式でエラー."""
        doc_path = temp_dir / "test.doc"
        doc_path.touch()

        with pytest.raises(UnsupportedFormatError):
            ParserFactory.get_parser(doc_path)

    def test_supported_extensions(self):
        """サポートされる拡張子のリスト."""
        extensions = ParserFactory.supported_extensions()

        assert "pdf" in extensions
        assert "md" in extensions
        assert "txt" in extensions

    def test_is_supported(self, temp_dir: Path):
        """サポート判定."""
        assert ParserFactory.is_supported(temp_dir / "test.pdf") is True
        assert ParserFactory.is_supported(temp_dir / "test.md") is True
        assert ParserFactory.is_supported(temp_dir / "test.doc") is False

    @pytest.mark.asyncio
    async def test_parse_markdown(self, sample_markdown: Path):
        """ファクトリー経由でMarkdownをパース."""
        doc = await ParserFactory.parse(sample_markdown)

        assert doc.title == "Test Document"
        assert len(doc.chapters) >= 2

    @pytest.mark.asyncio
    async def test_parse_text(self, sample_text: Path):
        """ファクトリー経由でテキストをパース."""
        doc = await ParserFactory.parse(sample_text)

        assert doc.title is not None
        assert len(doc.chapters) >= 3


class TestParseDocumentFunction:
    """parse_documentショートカット関数のテスト."""

    @pytest.mark.asyncio
    async def test_parse_markdown(self, sample_markdown: Path):
        """Markdownをパース."""
        doc = await parse_document(sample_markdown)

        assert doc.title == "Test Document"

    @pytest.mark.asyncio
    async def test_parse_text(self, sample_text: Path):
        """テキストをパース."""
        doc = await parse_document(sample_text)

        assert doc.title is not None


# =============================================================================
# PDFParser Tests (requires PyMuPDF)
# =============================================================================


class TestPDFParser:
    """PDFParserのテスト."""

    @pytest.fixture
    def parser(self) -> PDFParser:
        return PDFParser()

    def test_supported_extensions(self, parser: PDFParser):
        """サポートする拡張子."""
        assert "pdf" in parser.supported_extensions

    def test_can_parse_pdf(self, parser: PDFParser, temp_dir: Path):
        """PDFファイルを判定."""
        pdf_path = temp_dir / "test.pdf"
        pdf_path.touch()
        assert parser.can_parse(pdf_path) is True

    def test_cannot_parse_txt(self, parser: PDFParser, temp_dir: Path):
        """テキストファイルは判定しない."""
        txt_path = temp_dir / "test.txt"
        txt_path.touch()
        assert parser.can_parse(txt_path) is False

    @pytest.mark.asyncio
    async def test_parse_nonexistent_file(self, parser: PDFParser, temp_dir: Path):
        """存在しないファイルでエラー."""
        with pytest.raises(DocumentNotFoundError):
            await parser.parse(temp_dir / "nonexistent.pdf")

    @pytest.mark.asyncio
    async def test_parse_unsupported_format(self, parser: PDFParser, sample_text: Path):
        """サポートされていない形式でエラー."""
        with pytest.raises(UnsupportedFormatError):
            await parser.parse(sample_text)
