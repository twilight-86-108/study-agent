"""ChromaDB Client"""

import logging
import uuid
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional

from study_agent.core.exceptions import SearchError, VectorDBError
from study_agent.infrastructure.vectordb.base import (
    BaseVectorDB,
    CollectionStats,
    SearchResult,
    VectorDBConfig,
)

if TYPE_CHECKING:
    import chromadb
    from chromadb.api.models.Collection import Collection

from study_agent.domain.models import Chunk

logger = logging.getLogger(__name__)


class ChromaDBClient(BaseVectorDB):
    """ChromaDBクライアント"""

    def __init__(self, config: VectorDBConfig) -> None:
        """
        初期化

        Args:
            config: VectorDB設定
        """
        super().__init__(config)
        self._client: Optional[chromadb.PersistentClient] = None
        self._collection: Optional[Collection] = None

    def _get_distance_function(self) -> str:
        """ChromaDBの距離関数を返す"""
        metric_map = {
            "cosine": "cosine",
            "l2": "l2",
            "ip": "ip",
        }
        return metric_map.get(self.config.distance_metric, "cosine")

    async def initialize(self) -> None:
        """
        ChromaDBを初期化

        Raises:
            VectorDBError: 初期化に失敗した場合
        """
        if self._inirtialized:
            logger.debug("ChromaDB is already initialized")
            return

        try:
            import chromadb
            from chromadb.config import Settings

            presist_path = Path(self.config.persist_directory)
            presist_path.mkdir(parents=True, exist_ok=True)

            self._client = chromadb.PersistentClient(
                path=str(presist_path),
                settings=Settings(
                    anonymized_telemetry=False,
                    allow_reset=True,
                ),
            )

            distance_function = self._get_distance_function()
            self._collection = self._client.get_or_create_collection(
                name=self.config.collection_name,
                metadata={"hnsw:space": distance_function},
            )

            self._initialized = True
            logger.info(
                f"ChromaDB initialized: collection='{self.config.collection_name}',"
                f"path='{presist_path}', distance='{distance_function}'"
            )

        except ImportError as e:
            raise VectorDBError(
                message="ChromaDB is not installed. Please install it first.",
                cause=e,
            ) from e
        except Exception as e:
            raise VectorDBError(
                message=f"Failed to initialize ChromaDB: {e}",
                details={
                    "collection_name": self.config.collection_name,
                    "persist_directory": self.config.persist_directory,
                },
                cause=e,
            ) from e

    def _ensure_initialized(self) -> None:
        """初期化済みを確認する"""
        if not self._initialized or self._collection is None:
            raise VectorDBError("ChromaDB is not initialized")

    async def add_documents(
        self,
        chunks: list[Chunk],
        embeddings: list[list[float]],
    ) -> list[str]:
        """
        ドキュメントをベクトルDBに追加

        Args:
            chunks: チャンクリスト
            embeddings: エンベディングリスト

        Returns:
            list[str]: ベクトルIDリスト

        Raises:
            VectorDBError: ドキュメント追加に失敗した場合
            ValueError: チャンク数とエンベディング数が一致しない場合
        """
        self._ensure_initialized()

        if len(chunk) != len(embeddings):
            raise ValueError("Chunk list and embedding list must have the same length")

        if not chunks:
            return []

        try:
            # embedding_idを生成
            embedding_ids = [
                chunk.embedding_id or str(uuid.uuid4()) for chunk in chunks
            ]
            # ドキュメント内容
            documents = [chunk.content for chunk in chunks]
            # メタデータ
            metadatas = []
            for chunk in chunks:
                metadata: dict[str, Any] = {
                    "chunk_id": chunk.id,
                    "document_id": chunk.document_id,
                    "chunk_index": chunk.chunk_index,
                }
                if chunk.page_number is not None:
                    metadata["page_number"] = chunk.page_number
                if chunk.metadata:
                    for ley, value in chunk.metadata.items():
                        if isinstance(value, (str, int, float, bool)):
                            metadata[ley] = value
                metadatas.append(metadata)
            # ChromaDBに追加
            assert self._collection is not None
            self._collection.add(
                ids=embedding_ids,
                embeddings=embeddings,
                documents=documents,
                metadatas=metadatas,
            )

            logger.info(f"Added {len(chunks)} documents to ChromaDB")
            return embedding_ids

        except Exception as e:
            raise VectorDBError(
                message=f"Failed to add documents to ChromaDB: {e}",
                cause=e,
            ) from e

    async def search(
        self,
        query_embedding: list[float],
        top_k: int = 5,
        filter_metadata: Optional[dict[str, Any]] = None,
    ) -> list[SearchResult]:
        """
        類似検索を実行

        Args:
            query_embedding: クエリのエンベディング
            top_k: 類似度が高い順に返す数
            filter_metadata: メタデータでフィルタリングする条件

        Returns:
            list[SearchResult]: 類似度が高い順に返す数の検索結果

        Raises:
            SearchError: 検索に失敗した場合
        """
        self._ensure_initialized()

        try:
            assert self._collection is not None
            # フィルタ条件を構築
            where_filter = None
            if filter_metadata:
                if len(filter_metadata) == 1:
                    key, value = next(iter(filter_metadata.items()))
                    where_filter = {key: value}
                else:
                    where_filter = {
                        "$and": [{key: value} for key, value in filter_metadata.items()]
                    }
            # 検索実行
            results = self._collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                where=where_filter,
                include=["documents", "metadatas", "distances"],
            )

            # 結果を変換
            search_results: list[SearchResult] = []

            if results["ids"] and results["ids"][0]:
                ids = results["ids"][0]
                documents = (
                    results["documents"][0]
                    if results["documents"]
                    else [None] * len(ids)
                )
                metadatas = (
                    results["metadatas"][0]
                    if results["metadatas"]
                    else [None] * len(ids)
                )
                distances = (
                    results["distances"][0]
                    if results["distances"]
                    else [None] * len(ids)
                )

                for i, embedding_id in enumerate(ids):
                    # 距離を変換
                    distance = distances[i] if i < len(distances) else 0.0
                    if self.config.distance_metric == "cosine":
                        score = max(0.0, 1.0 - distance / 2.0)
                    else:
                        score = 1.0 / (1.0 + distance)

                    metadata = metadatas[i] if i < len(metadatas) else {}
                    chunk_id = (
                        metadata.get("chunk_id", embedding_id)
                        if metadata
                        else embedding_id
                    )

                    search_results.append(
                        SearchResult(
                            chunk_id=chunk_id,
                            content=(
                                documents[i]
                                if i < len(documents) and documents[i]
                                else ""
                            ),
                            score=score,
                            metadata=metadata,
                        )
                    )

            logger.debug(f"Search returned {len(search_results)} results")
            return search_results

        except Exception as e:
            raise SearchError(
                message=f"Failed to search in ChromaDB: {e}",
                cause=e,
            ) from e

    async def delete_by_document_id(self, document_id: str) -> int:
        """
        指定したドキュメントIDに関する全てのチャンクを削除

        Args:
            document_id: 文書ID

        Raises:
            VectorDBError: ベクトルDB削除に失敗した場合
        """
        self._ensure_initialized()

        try:
            assert self._collection is not None
            # 削除対象のIDを取得
            results = self._collection.get(
                where={"document_id": document_id},
                include=[],
            )

            ids_to_delete = results["ids"] if results["ids"] else []

            if not ids_to_delete:
                logger.debug(f"No chunks found for document_id: {document_id}")
                return 0

            # 削除実行
            self._collection.delete(ids=ids_to_delete)
            logger.debug(
                f"Deleted {len(ids_to_delete)} chunks for document_id: {document_id}"
            )
            return len(ids_to_delete)

        except Exception as e:
            raise VectorDBError(
                message=f"Failed to delete chunks from ChromaDB: {e}",
                cause=e,
            ) from e

    async def delete_by_ids(self, document_ids: list[str]) -> int:
        """
        指定したembedding_idのチャンクを削除する

        Args:
            embedding_ids: 削除対象のembedding_idのリスト

        Returns:
            int: 削除したチャンクの数

        Raises:
            VectorDBError: ベクトルDB削除に失敗した場合
        """
        self._ensure_initialized()

        if not embedding_ids:
            return 0

        try:
            assert self._collection is not None
            self._collection.delete(ids=embedding_ids)

            logger.info(f"Deleted {len(embedding_ids)} chunks")
            return len(embedding_ids)

        except Exception as e:
            raise VectorDBError(
                message=f"Failed to delete chunks from ChromaDB: {e}",
                cause=e,
            ) from e

    async def get_collection_stats(self) -> CollectionStats:
        """
        コレクションの統計情報を取得

        Returns:
            CollectionStats: コレクションの統計情報

        Raises:
            VectorDBError: コレクション統計情報取得に失敗した場合
        """
        self._ensure_initialized()

        try:
            assert self._collection is not None
            count = self._collection.count()

            return CollectionStats(
                count=count,
                collection_name=self._collection_name,
                metadata={
                    "presist_directory": self.config.persist_directory,
                    "distance_metric": self.config.distance_metric,
                },
            )

        except Exception as e:
            raise VectorDBError(
                message=f"Failed to get collection stats from ChromaDB: {e}",
                cause=e,
            ) from e

    async def clear_collection(self) -> None:
        """
        コレクション内の全データを削除

        Raises:
            VectorDBError: コレクションクリアに失敗した場合
        """
        self._ensure_initialized()

        try:
            assert self._client is not None
            self._client.delete_collection(name=self._collection_name)

            distance_function = self._get_distance_function()

            self._collection = self._client.create_collection(
                name=self.config.collection_name,
                metadata={"hnsw:space": distance_function},
            )

            logger.info(f"Cleared collection: {self.config.collection_name}")

        except Exception as e:
            raise VectorDBError(
                message=f"Failed to clear collection from ChromaDB: {e}",
                cause=e,
            ) from e

    async def close(self) -> None:
        """
        リソースを解放
        """
        self._collection = None
        self._client = None
        self._initialized = False
        logger.info("Closed ChromaDB")
