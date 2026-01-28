"""Dependency injection container.

アプリケーションの依存関係を管理するDIコンテナ。
すべてのサービス、エージェント、インフラストラクチャコンポーネントの
インスタンス化とライフサイクル管理を担当する。

Example:
    >>> config = load_config()
    >>> async with Container.create(config) as container:
    ...     result = await container.document_service.load_document("doc.pdf")
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from study_agent.infrastructure.config import AppConfig
from study_agent.infrastructure.database import DatabaseManager
from study_agent.infrastructure.llm import BaseLLMClient, LLMResponse
from study_agent.infrastructure.vectordb import BaseVectorDB, BaseEmbeddingService
from study_agent.services import (
    DocumentService,
    SearchService,
    QuizService,
    ProgressService,
    SessionService,
)
from study_agent.agents import (
    AgentOrchestrator,
    RouterAgent,
    TutorAgent,
    QuizGeneratorAgent,
    EvaluatorAgent,
    PlannerAgent,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Mock implementations for CLI testing
# =============================================================================


class MockLLMClient(BaseLLMClient):
    """モック LLM クライアント（テスト/デモ用）."""

    async def generate(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 1000,
        **kwargs: Any,
    ) -> LLMResponse:
        """テキストを生成."""
        return LLMResponse(
            content="これはモック応答です。実際のLLM接続が必要な場合はOllamaを設定してください。",
            model="mock",
            tokens_used=10,
        )

    async def generate_json(
        self,
        prompt: str,
        schema: dict[str, Any],
        temperature: float = 0.3,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """JSON形式でテキストを生成."""
        # スキーマに基づいてモックデータを生成
        return {"mock": True, "message": "Mock JSON response"}

    async def embed_text(self, text: str) -> list[float]:
        """テキストをエンベッディングに変換."""
        # 384次元のダミーベクトル
        import hashlib

        h = hashlib.md5(text.encode()).hexdigest()
        return [float(int(h[i : i + 2], 16)) / 255.0 for i in range(0, 32, 2)] * 24

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """複数テキストをエンベッディングに変換."""
        return [await self.embed_text(t) for t in texts]


class MockVectorDB(BaseVectorDB):
    """モック VectorDB（テスト/デモ用）."""

    def __init__(self) -> None:
        self._documents: dict[str, dict[str, Any]] = {}

    async def add_documents(self, documents: list[Any]) -> list[str]:
        """ドキュメントを追加."""
        ids = []
        for doc in documents:
            doc_id = getattr(doc, "id", str(len(self._documents)))
            self._documents[doc_id] = {
                "id": doc_id,
                "content": getattr(doc, "content", ""),
                "metadata": getattr(doc, "metadata", {}),
            }
            ids.append(doc_id)
        return ids

    async def search(
        self,
        query_embedding: list[float],
        top_k: int = 5,
        filter_dict: dict[str, Any] | None = None,
    ) -> list[Any]:
        """類似検索."""
        from study_agent.infrastructure.vectordb import VectorSearchResult

        results = []
        for doc_id, doc in list(self._documents.items())[:top_k]:
            results.append(
                VectorSearchResult(
                    id=doc_id,
                    content=doc.get("content", ""),
                    score=0.9,
                    metadata=doc.get("metadata", {}),
                )
            )
        return results

    async def delete_by_document_id(self, document_id: str) -> int:
        """ドキュメントIDで削除."""
        count = 0
        to_delete = [
            k
            for k, v in self._documents.items()
            if v.get("metadata", {}).get("document_id") == document_id
        ]
        for key in to_delete:
            del self._documents[key]
            count += 1
        return count

    async def get_by_ids(self, ids: list[str]) -> list[dict[str, Any]]:
        """IDで取得."""
        return [self._documents[id] for id in ids if id in self._documents]


class MockEmbeddingService(BaseEmbeddingService):
    """モック エンベッディングサービス（テスト/デモ用）."""

    async def embed_text(self, text: str) -> list[float]:
        """テキストをエンベッディングに変換."""
        import hashlib

        h = hashlib.md5(text.encode()).hexdigest()
        return [float(int(h[i : i + 2], 16)) / 255.0 for i in range(0, 32, 2)] * 24

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """複数テキストをエンベッディングに変換."""
        return [await self.embed_text(t) for t in texts]


# =============================================================================
# Container
# =============================================================================


@dataclass
class Container:
    """依存関係注入コンテナ.

    アプリケーションの全コンポーネントを管理する。

    Attributes:
        config: アプリケーション設定
        db_manager: データベースマネージャ
        llm_client: LLMクライアント
        vectordb: VectorDBクライアント
        embedding_service: エンベッディングサービス
        document_service: ドキュメントサービス
        search_service: 検索サービス
        quiz_service: クイズサービス
        progress_service: 進捗サービス
        session_service: セッションサービス
        orchestrator: エージェントオーケストレータ
    """

    config: AppConfig
    db_manager: DatabaseManager
    llm_client: BaseLLMClient
    vectordb: BaseVectorDB
    embedding_service: BaseEmbeddingService

    # Services (initialized lazily)
    _document_service: DocumentService | None = field(default=None, repr=False)
    _search_service: SearchService | None = field(default=None, repr=False)
    _quiz_service: QuizService | None = field(default=None, repr=False)
    _progress_service: ProgressService | None = field(default=None, repr=False)
    _session_service: SessionService | None = field(default=None, repr=False)
    _orchestrator: AgentOrchestrator | None = field(default=None, repr=False)

    @classmethod
    async def create(cls, config: AppConfig, use_mock: bool = True) -> "Container":
        """コンテナを作成.

        Args:
            config: アプリケーション設定
            use_mock: モック実装を使用するかどうか（デフォルト: True）

        Returns:
            初期化されたコンテナ
        """
        # データベースマネージャを初期化
        db_manager = DatabaseManager(config.database.url)
        db_manager.create_tables()

        if use_mock:
            # モック実装を使用
            llm_client = MockLLMClient()
            vectordb = MockVectorDB()
            embedding_service = MockEmbeddingService()
        else:
            # 本番実装（Ollama）を使用
            # TODO: 実際のOllamaクライアントを実装
            llm_client = MockLLMClient()
            vectordb = MockVectorDB()
            embedding_service = MockEmbeddingService()

        return cls(
            config=config,
            db_manager=db_manager,
            llm_client=llm_client,
            vectordb=vectordb,
            embedding_service=embedding_service,
        )

    async def close(self) -> None:
        """リソースを解放."""
        # 必要に応じてリソースをクリーンアップ
        logger.debug("Container resources released")

    async def __aenter__(self) -> "Container":
        """非同期コンテキストマネージャのエントリ."""
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """非同期コンテキストマネージャのイグジット."""
        await self.close()

    @property
    def document_service(self) -> DocumentService:
        """DocumentServiceを取得（遅延初期化）."""
        if self._document_service is None:
            self._document_service = DocumentService(
                config=self.config,
                db_manager=self.db_manager,
                vectordb=self.vectordb,
                embedding_service=self.embedding_service,
            )
        return self._document_service

    @property
    def search_service(self) -> SearchService:
        """SearchServiceを取得（遅延初期化）."""
        if self._search_service is None:
            self._search_service = SearchService(
                vectordb=self.vectordb,
                embedding_service=self.embedding_service,
                db_manager=self.db_manager,
            )
        return self._search_service

    @property
    def quiz_service(self) -> QuizService:
        """QuizServiceを取得（遅延初期化）."""
        if self._quiz_service is None:
            self._quiz_service = QuizService(
                llm_client=self.llm_client,
                search_service=self.search_service,
                db_manager=self.db_manager,
            )
        return self._quiz_service

    @property
    def progress_service(self) -> ProgressService:
        """ProgressServiceを取得（遅延初期化）."""
        if self._progress_service is None:
            self._progress_service = ProgressService(
                db_manager=self.db_manager,
            )
        return self._progress_service

    @property
    def session_service(self) -> SessionService:
        """SessionServiceを取得（遅延初期化）."""
        if self._session_service is None:
            self._session_service = SessionService(
                db_manager=self.db_manager,
            )
        return self._session_service

    @property
    def orchestrator(self) -> AgentOrchestrator:
        """AgentOrchestratorを取得（遅延初期化）."""
        if self._orchestrator is None:
            # 各エージェントを初期化
            router = RouterAgent(self.llm_client)
            tutor = TutorAgent(self.llm_client, self.search_service)
            quiz_generator = QuizGeneratorAgent(self.llm_client, self.quiz_service)
            evaluator = EvaluatorAgent(
                self.llm_client, self.quiz_service, self.progress_service
            )
            planner = PlannerAgent(
                self.llm_client, self.progress_service, self.document_service
            )

            self._orchestrator = AgentOrchestrator(
                router=router,
                tutor=tutor,
                quiz_generator=quiz_generator,
                evaluator=evaluator,
                planner=planner,
            )
        return self._orchestrator
