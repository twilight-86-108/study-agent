"""Search service for RAG.

RAG（Retrieval-Augmented Generation）のための検索サービス。
ベクトル検索を使用して、クエリに関連するコンテキストを取得する。

主な機能:
    - セマンティック検索
    - ドキュメントフィルタリング
    - コンテキスト生成（説明用、クイズ用）

Example:
    >>> service = SearchService(vectordb, embedding_service, db_manager)
    >>> results = await service.search("EC2とは", top_k=5)
    >>> context = await service.get_context_for_explanation("Amazon EC2")
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Sequence

from study_agent.domain import Chunk, SearchResult, SearchContext
from study_agent.infrastructure.database import DatabaseManager, ChunkRepository
from study_agent.infrastructure.vectordb import (
    BaseVectorDB,
    BaseEmbeddingService,
    SearchResult as VectorSearchResult,
)

logger = logging.getLogger(__name__)


class SearchService:
    """RAG検索サービス.

    セマンティック検索を使用して、関連するコンテンツを取得する。

    Attributes:
        vectordb: ベクトルDBクライアント
        embedding_service: 埋め込みサービス
        db_manager: データベースマネージャ

    Example:
        >>> service = SearchService(vectordb, embedding_service, db_manager)
        >>> results = await service.search("EC2", top_k=5)
        >>> print(f"Found {len(results)} results")
    """

    def __init__(
        self,
        vectordb: BaseVectorDB,
        embedding_service: BaseEmbeddingService,
        db_manager: DatabaseManager,
    ) -> None:
        """初期化.

        Args:
            vectordb: ベクトルDBクライアント
            embedding_service: 埋め込みサービス
            db_manager: データベースマネージャ
        """
        self.vectordb = vectordb
        self.embedding_service = embedding_service
        self.db_manager = db_manager

    async def search(
        self,
        query: str,
        top_k: int = 5,
        document_id: str | None = None,
        min_score: float = 0.0,
    ) -> SearchResult:
        """クエリに関連するチャンクを検索する.

        Args:
            query: 検索クエリ
            top_k: 返す結果数
            document_id: 特定のドキュメントに限定（オプション）
            min_score: 最小スコア閾値

        Returns:
            SearchResult: 検索結果
        """
        start_time = time.time()

        # クエリの埋め込みを生成
        query_embedding = await self.embedding_service.embed_text(query)

        # フィルター構築
        filter_metadata = None
        if document_id:
            filter_metadata = {"document_id": document_id}

        # ベクトル検索実行
        vector_results = await self.vectordb.search(
            query_embedding=query_embedding,
            top_k=top_k,
            filter_metadata=filter_metadata,
        )

        # スコアでフィルタリング
        filtered_results = [r for r in vector_results if r.score >= min_score]

        # ドメインモデルに変換
        chunks: list[Chunk] = []
        scores: list[float] = []

        for result in filtered_results:
            chunks.append(
                Chunk(
                    id=result.chunk_id,
                    document_id=(
                        result.metadata.get("document_id", "")
                        if result.metadata
                        else ""
                    ),
                    content=result.content,
                    chunk_index=(
                        result.metadata.get("chunk_index", 0) if result.metadata else 0
                    ),
                )
            )
            scores.append(result.score)

        search_time_ms = (time.time() - start_time) * 1000

        logger.debug(
            f"Search completed: query='{query[:50]}...', "
            f"results={len(chunks)}, time={search_time_ms:.2f}ms"
        )

        return SearchResult(
            chunks=chunks,
            scores=scores,
            query=query,
            search_time_ms=search_time_ms,
        )

    async def get_context_for_explanation(
        self,
        topic: str,
        document_id: str | None = None,
        max_chunks: int = 5,
    ) -> SearchContext:
        """概念説明用のコンテキストを取得する.

        検索結果を整形して、LLMに渡しやすい形式にする。

        Args:
            topic: 説明するトピック
            document_id: ドキュメントフィルター（オプション）
            max_chunks: 最大チャンク数

        Returns:
            SearchContext: 整形されたコンテキスト
        """
        search_result = await self.search(
            query=topic,
            top_k=max_chunks,
            document_id=document_id,
        )

        if not search_result.chunks:
            return SearchContext(
                context="関連する情報が見つかりませんでした。",
                source_chunks=[],
                relevance_scores=[],
                total_chunks=0,
            )

        # コンテキストを整形
        context_parts: list[str] = []
        source_chunks: list[Chunk] = []
        relevance_scores: list[float] = []

        for i, (chunk, score) in enumerate(
            zip(search_result.chunks, search_result.scores)
        ):
            context_parts.append(f"[参考{i + 1}]\n{chunk.content}")
            source_chunks.append(chunk)
            relevance_scores.append(score)

        context = "\n\n".join(context_parts)

        return SearchContext(
            context=context,
            source_chunks=source_chunks,
            relevance_scores=relevance_scores,
            total_chunks=len(source_chunks),
        )

    async def get_context_for_quiz(
        self,
        topic: str,
        document_id: str | None = None,
        max_chunks: int = 3,
    ) -> SearchContext:
        """クイズ生成用のコンテキストを取得する.

        説明用よりも少ないチャンクで、より焦点を絞った内容を取得。

        Args:
            topic: クイズのトピック
            document_id: ドキュメントフィルター（オプション）
            max_chunks: 最大チャンク数

        Returns:
            SearchContext: 整形されたコンテキスト
        """
        search_result = await self.search(
            query=topic,
            top_k=max_chunks,
            document_id=document_id,
            min_score=0.3,  # クイズ生成にはより関連性の高いもののみ
        )

        if not search_result.chunks:
            return SearchContext(
                context="",
                source_chunks=[],
                relevance_scores=[],
                total_chunks=0,
            )

        # コンテキストを結合
        context = "\n\n".join(chunk.content for chunk in search_result.chunks)

        return SearchContext(
            context=context,
            source_chunks=search_result.chunks,
            relevance_scores=search_result.scores,
            total_chunks=len(search_result.chunks),
        )

    async def search_by_keyword(
        self,
        keyword: str,
        document_id: str | None = None,
        limit: int = 10,
    ) -> list[Chunk]:
        """キーワードでチャンクを検索する（完全一致・部分一致）.

        セマンティック検索ではなく、テキスト検索を行う。

        Args:
            keyword: 検索キーワード
            document_id: ドキュメントフィルター（オプション）
            limit: 最大結果数

        Returns:
            マッチしたチャンクのリスト
        """
        with self.db_manager.get_session() as session:
            chunk_repo = ChunkRepository(session)

            if document_id:
                chunk_models = chunk_repo.find_by_document_id(document_id)
            else:
                chunk_models = chunk_repo.get_all()

            # キーワードでフィルタリング
            matched = [
                Chunk(
                    id=m.id,
                    document_id=m.document_id,
                    content=m.content,
                    chunk_index=m.chunk_index,
                    page_number=m.page_number,
                    embedding_id=m.embedding_id,
                    created_at=m.created_at,
                )
                for m in chunk_models
                if keyword.lower() in m.content.lower()
            ]

            return matched[:limit]

    async def get_related_chunks(
        self,
        chunk_id: str,
        top_k: int = 5,
    ) -> SearchResult:
        """指定したチャンクに関連するチャンクを検索する.

        Args:
            chunk_id: 基準となるチャンクID
            top_k: 返す結果数

        Returns:
            SearchResult: 関連チャンク
        """
        # 基準チャンクを取得
        with self.db_manager.get_session() as session:
            chunk_repo = ChunkRepository(session)
            chunk_model = chunk_repo.get_by_id(chunk_id)

            if chunk_model is None:
                return SearchResult(
                    chunks=[],
                    scores=[],
                    query=f"related to {chunk_id}",
                )

        # 基準チャンクの内容で検索
        return await self.search(
            query=chunk_model.content[:500],  # 最初の500文字を使用
            top_k=top_k + 1,  # 自分自身を含む可能性があるので+1
        )
