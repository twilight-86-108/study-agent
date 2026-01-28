"""チャンクリポジトリ.

Chunkモデルのデータアクセス操作を提供する。
"""

from __future__ import annotations

import logging
from typing import Sequence

from sqlmodel import select

from study_agent.infrastructure.database.models import Chunk
from study_agent.infrastructure.database.repositories.base import BaseRepository

logger = logging.getLogger(__name__)


class ChunkRepository(BaseRepository[Chunk]):
    """Chunkリポジトリ.

    RAGチャンクのCRUD操作と検索機能を提供する。

    Example:
        ```python
        with db_manager.get_session() as session:
            repo = ChunkRepository(session)

            # ドキュメントIDで検索
            chunks = repo.find_by_document_id("doc-123")

            # embedding_idで検索
            chunk = repo.find_by_embedding_id("embed-456")

            # embedding_idを更新
            repo.update_embedding_id("chunk-789", "new-embed-id")
        ```
    """

    @property
    def _model_class(self) -> type[Chunk]:
        """モデルクラスを返す."""
        return Chunk

    def find_by_document_id(self, document_id: str) -> Sequence[Chunk]:
        """ドキュメントIDでチャンクを検索する.

        Args:
            document_id: ドキュメントID

        Returns:
            チャンクのリスト
        """
        statement = select(Chunk).where(Chunk.document_id == document_id)
        return self._session.exec(statement).all()

    def find_by_document_id_ordered(self, document_id: str) -> Sequence[Chunk]:
        """ドキュメントIDでチャンクを検索する（順序付き）.

        Args:
            document_id: ドキュメントID

        Returns:
            チャンクのリスト（chunk_index順）
        """
        statement = (
            select(Chunk)
            .where(Chunk.document_id == document_id)
            .order_by(Chunk.chunk_index)
        )
        return self._session.exec(statement).all()

    def find_by_embedding_id(self, embedding_id: str) -> Chunk | None:
        """embedding_idでチャンクを検索する.

        Args:
            embedding_id: VectorDB内のembedding ID

        Returns:
            チャンク、存在しない場合はNone
        """
        statement = select(Chunk).where(Chunk.embedding_id == embedding_id)
        return self._session.exec(statement).first()

    def find_by_embedding_ids(self, embedding_ids: list[str]) -> Sequence[Chunk]:
        """複数のembedding_idでチャンクを検索する.

        Args:
            embedding_ids: embedding IDのリスト

        Returns:
            チャンクのリスト
        """
        if not embedding_ids:
            return []
        statement = select(Chunk).where(Chunk.embedding_id.in_(embedding_ids))
        return self._session.exec(statement).all()

    def find_by_page_number(
        self,
        document_id: str,
        page_number: int,
    ) -> Sequence[Chunk]:
        """ページ番号でチャンクを検索する.

        Args:
            document_id: ドキュメントID
            page_number: ページ番号

        Returns:
            チャンクのリスト
        """
        statement = (
            select(Chunk)
            .where(Chunk.document_id == document_id)
            .where(Chunk.page_number == page_number)
            .order_by(Chunk.chunk_index)
        )
        return self._session.exec(statement).all()

    def update_embedding_id(
        self,
        chunk_id: str,
        embedding_id: str,
    ) -> Chunk | None:
        """チャンクのembedding_idを更新する.

        Args:
            chunk_id: チャンクID
            embedding_id: 新しいembedding ID

        Returns:
            更新されたチャンク、存在しない場合はNone
        """
        chunk = self.get_by_id(chunk_id)
        if chunk is None:
            return None
        chunk.embedding_id = embedding_id
        return self.update(chunk)

    def update_embedding_ids_batch(
        self,
        chunk_embedding_map: dict[str, str],
    ) -> int:
        """複数チャンクのembedding_idを一括更新する.

        Args:
            chunk_embedding_map: {chunk_id: embedding_id} の辞書

        Returns:
            更新されたチャンク数
        """
        count = 0
        for chunk_id, embedding_id in chunk_embedding_map.items():
            if self.update_embedding_id(chunk_id, embedding_id) is not None:
                count += 1
        return count

    def count_by_document_id(self, document_id: str) -> int:
        """ドキュメント内のチャンク数を取得する.

        Args:
            document_id: ドキュメントID

        Returns:
            チャンク数
        """
        chunks = self.find_by_document_id(document_id)
        return len(chunks)

    def delete_by_document_id(self, document_id: str) -> int:
        """ドキュメントIDでチャンクを削除する.

        Args:
            document_id: ドキュメントID

        Returns:
            削除されたチャンク数
        """
        chunks = self.find_by_document_id(document_id)
        count = len(chunks)
        for chunk in chunks:
            self.delete(chunk)
        return count

    def get_embedding_ids_by_document(self, document_id: str) -> list[str]:
        """ドキュメントに関連するすべてのembedding_idを取得する.

        Args:
            document_id: ドキュメントID

        Returns:
            embedding_idのリスト（Noneは除外）
        """
        chunks = self.find_by_document_id(document_id)
        return [
            chunk.embedding_id for chunk in chunks if chunk.embedding_id is not None
        ]
