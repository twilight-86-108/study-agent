"""Text Chunker.

テキストをRAG用のチャンクに分割するユーティリティ。
文の境界やオーバーラップを考慮した分割を行う。
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class TextChunk:
    """テキストチャンク.

    Attributes:
        content: チャンクのテキスト内容
        chunk_index: チャンクのインデックス（0始まり）
        start_char: 元テキストでの開始位置
        end_char: 元テキストでの終了位置
        metadata: メタデータ（ページ番号、章タイトルなど）
    """

    content: str
    chunk_index: int
    start_char: int
    end_char: int
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def char_count(self) -> int:
        """文字数."""
        return len(self.content)

    @property
    def word_count(self) -> int:
        """単語数（空白区切り）."""
        return len(self.content.split())


class TextChunker:
    """テキストチャンカー.

    テキストを指定サイズのチャンクに分割する。
    文の境界を考慮し、オーバーラップで文脈を維持する。

    Example:
        >>> chunker = TextChunker(chunk_size=1000, overlap=200)
        >>> chunks = chunker.chunk_text(long_text)
        >>> for chunk in chunks:
        ...     print(f"Chunk {chunk.chunk_index}: {chunk.char_count} chars")
    """

    # 文の区切りパターン
    SENTENCE_SEPARATORS = [
        r"(?<=[。．.!?！？])\s*",  # 日本語・英語の文末
        r"(?<=\n)\s*",  # 改行
    ]

    # 段落区切りパターン
    PARAGRAPH_SEPARATOR = r"\n{2,}"

    def __init__(
        self,
        chunk_size: int = 1000,
        overlap: int = 200,
        respect_sentence_boundary: bool = True,
    ) -> None:
        """初期化.

        Args:
            chunk_size: チャンクサイズ（文字数）
            overlap: オーバーラップサイズ（文字数）
            respect_sentence_boundary: 文の境界を尊重するか
        """
        if chunk_size <= 0:
            raise ValueError("chunk_size must be positive")
        if overlap < 0:
            raise ValueError("overlap must be non-negative")
        if overlap >= chunk_size:
            raise ValueError("overlap must be smaller than chunk_size")

        self.chunk_size = chunk_size
        self.overlap = overlap
        self.respect_sentence_boundary = respect_sentence_boundary

    def chunk_text(
        self,
        text: str,
        metadata: dict[str, Any] | None = None,
    ) -> list[TextChunk]:
        """テキストをチャンクに分割.

        Args:
            text: 分割するテキスト
            metadata: 全チャンクに付与するメタデータ

        Returns:
            TextChunkのリスト
        """
        if not text.strip():
            return []

        base_metadata = metadata or {}

        if self.respect_sentence_boundary:
            return self._chunk_with_sentence_boundary(text, base_metadata)
        else:
            return self._chunk_simple(text, base_metadata)

    def chunk_by_pages(
        self,
        pages: list[str],
        document_metadata: dict[str, Any] | None = None,
    ) -> list[TextChunk]:
        """ページごとのテキストをチャンクに分割.

        ページ番号情報をメタデータに含める。

        Args:
            pages: ページごとのテキストリスト
            document_metadata: ドキュメント全体のメタデータ

        Returns:
            TextChunkのリスト
        """
        all_chunks: list[TextChunk] = []
        global_index = 0
        global_char_offset = 0

        for page_num, page_text in enumerate(pages, start=1):
            if not page_text.strip():
                global_char_offset += len(page_text)
                continue

            page_metadata = {
                **(document_metadata or {}),
                "page_number": page_num,
            }

            # ページ内でチャンク分割
            page_chunks = self._chunk_with_sentence_boundary(page_text, page_metadata)

            # グローバルインデックスと文字位置を調整
            for chunk in page_chunks:
                chunk.chunk_index = global_index
                chunk.start_char += global_char_offset
                chunk.end_char += global_char_offset
                all_chunks.append(chunk)
                global_index += 1

            global_char_offset += len(page_text)

        logger.debug(f"Created {len(all_chunks)} chunks from {len(pages)} pages")
        return all_chunks

    def _chunk_simple(
        self, text: str, base_metadata: dict[str, Any]
    ) -> list[TextChunk]:
        """単純な文字数ベースのチャンク分割.

        Args:
            text: 分割するテキスト
            base_metadata: 基本メタデータ

        Returns:
            TextChunkのリスト
        """
        chunks: list[TextChunk] = []
        text_len = len(text)
        start = 0
        chunk_index = 0

        while start < text_len:
            end = min(start + self.chunk_size, text_len)
            chunk_content = text[start:end]

            chunks.append(
                TextChunk(
                    content=chunk_content,
                    chunk_index=chunk_index,
                    start_char=start,
                    end_char=end,
                    metadata=base_metadata.copy(),
                )
            )

            # 次の開始位置（オーバーラップを考慮）
            start = end - self.overlap if end < text_len else text_len
            chunk_index += 1

        logger.debug(f"Created {len(chunks)} chunks (simple method)")
        return chunks

    def _chunk_with_sentence_boundary(
        self, text: str, base_metadata: dict[str, Any]
    ) -> list[TextChunk]:
        """文の境界を尊重したチャンク分割.

        Args:
            text: 分割するテキスト
            base_metadata: 基本メタデータ

        Returns:
            TextChunkのリスト
        """
        # 文に分割
        sentences = self._split_into_sentences(text)

        if not sentences:
            return []

        chunks: list[TextChunk] = []
        current_sentences: list[str] = []
        current_length = 0
        chunk_index = 0
        global_char_pos = 0

        for sentence in sentences:
            sentence_len = len(sentence)

            # 現在のチャンクに追加してもサイズ内なら追加
            if current_length + sentence_len <= self.chunk_size:
                current_sentences.append(sentence)
                current_length += sentence_len
            else:
                # 現在のチャンクを確定
                if current_sentences:
                    chunk_content = "".join(current_sentences)
                    chunks.append(
                        TextChunk(
                            content=chunk_content,
                            chunk_index=chunk_index,
                            start_char=global_char_pos,
                            end_char=global_char_pos + len(chunk_content),
                            metadata=base_metadata.copy(),
                        )
                    )
                    global_char_pos += len(chunk_content) - self._get_overlap_length(
                        current_sentences
                    )
                    chunk_index += 1

                # オーバーラップ用の文を保持
                overlap_sentences = self._get_overlap_sentences(current_sentences)
                current_sentences = overlap_sentences + [sentence]
                current_length = sum(len(s) for s in current_sentences)

        # 残りの文をチャンクに
        if current_sentences:
            chunk_content = "".join(current_sentences)
            chunks.append(
                TextChunk(
                    content=chunk_content,
                    chunk_index=chunk_index,
                    start_char=global_char_pos,
                    end_char=global_char_pos + len(chunk_content),
                    metadata=base_metadata.copy(),
                )
            )

        logger.debug(f"Created {len(chunks)} chunks (sentence boundary method)")
        return chunks

    def _split_into_sentences(self, text: str) -> list[str]:
        """テキストを文に分割.

        Args:
            text: 分割するテキスト

        Returns:
            文のリスト
        """
        # 複数の区切りパターンで分割
        combined_pattern = "|".join(self.SENTENCE_SEPARATORS)
        sentences = re.split(combined_pattern, text)

        # 空文字を除去し、空白を正規化
        return [s for s in sentences if s.strip()]

    def _get_overlap_sentences(self, sentences: list[str]) -> list[str]:
        """オーバーラップ用の文を取得.

        Args:
            sentences: 文のリスト

        Returns:
            オーバーラップに含める文のリスト
        """
        if not sentences:
            return []

        overlap_sentences: list[str] = []
        overlap_length = 0

        # 末尾から文を追加
        for sentence in reversed(sentences):
            if overlap_length + len(sentence) <= self.overlap:
                overlap_sentences.insert(0, sentence)
                overlap_length += len(sentence)
            else:
                break

        return overlap_sentences

    def _get_overlap_length(self, sentences: list[str]) -> int:
        """オーバーラップ部分の長さを計算.

        Args:
            sentences: 文のリスト

        Returns:
            オーバーラップの文字数
        """
        overlap_sentences = self._get_overlap_sentences(sentences)
        return sum(len(s) for s in overlap_sentences)


def create_chunks_from_document(
    content: str,
    chunk_size: int = 1000,
    overlap: int = 200,
    page_texts: list[str] | None = None,
    document_id: str | None = None,
    document_title: str | None = None,
) -> list[TextChunk]:
    """ドキュメントからチャンクを作成するヘルパー関数.

    Args:
        content: ドキュメント全文（page_textsがない場合に使用）
        chunk_size: チャンクサイズ
        overlap: オーバーラップサイズ
        page_texts: ページごとのテキスト（あれば使用）
        document_id: ドキュメントID
        document_title: ドキュメントタイトル

    Returns:
        TextChunkのリスト
    """
    chunker = TextChunker(chunk_size=chunk_size, overlap=overlap)

    base_metadata: dict[str, Any] = {}
    if document_id:
        base_metadata["document_id"] = document_id
    if document_title:
        base_metadata["document_title"] = document_title

    if page_texts:
        return chunker.chunk_by_pages(page_texts, base_metadata)
    else:
        return chunker.chunk_text(content, base_metadata)
