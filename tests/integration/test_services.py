"""Services layer unit tests.

サービス層のユニットテスト。
モックを使用してInfrastructure層との依存を分離する。
"""

from __future__ import annotations

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

# Import services
from study_agent.services import (
    DocumentService,
    SearchService,
    QuizService,
    ProgressService,
    SessionService,
)

# Import domain models
from study_agent.domain import (
    Document,
    Chunk,
    Quiz,
    QuizType,
    Difficulty,
    FileType,
    SessionMode,
    SessionStatus,
    TopicProgress,
    LearningSession,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_config():
    """モック設定."""
    config = MagicMock()
    config.document.max_file_size_mb = 50
    config.chunking.chunk_size = 1000
    config.chunking.chunk_overlap = 200
    return config


@pytest.fixture
def mock_db_manager():
    """モックDatabaseManager."""
    manager = MagicMock()
    manager.get_session = MagicMock()
    return manager


@pytest.fixture
def mock_vectordb():
    """モックVectorDB."""
    vectordb = AsyncMock()
    vectordb.add_documents = AsyncMock()
    vectordb.search = AsyncMock(return_value=[])
    vectordb.delete_by_document_id = AsyncMock()
    return vectordb


@pytest.fixture
def mock_embedding_service():
    """モックEmbeddingService."""
    service = AsyncMock()
    service.embed_text = AsyncMock(return_value=[0.1] * 768)
    service.embed_texts = AsyncMock(return_value=[[0.1] * 768])
    return service


@pytest.fixture
def mock_llm_client():
    """モックLLMClient."""
    client = AsyncMock()
    client.generate_json = AsyncMock(
        return_value={
            "question": "テスト問題",
            "correct_answer": "A",
            "options": {"A": "選択肢A", "B": "選択肢B", "C": "選択肢C", "D": "選択肢D"},
            "explanation": "解説テスト",
        }
    )
    return client


# =============================================================================
# DocumentService Tests
# =============================================================================


class TestDocumentService:
    """DocumentServiceのテスト."""

    def test_init(
        self, mock_config, mock_db_manager, mock_vectordb, mock_embedding_service
    ):
        """初期化テスト."""
        service = DocumentService(
            mock_config, mock_db_manager, mock_vectordb, mock_embedding_service
        )
        assert service.config == mock_config
        assert service.db_manager == mock_db_manager

    def test_generate_id(
        self, mock_config, mock_db_manager, mock_vectordb, mock_embedding_service
    ):
        """UUID生成テスト."""
        service = DocumentService(
            mock_config, mock_db_manager, mock_vectordb, mock_embedding_service
        )
        id1 = service._generate_id()
        id2 = service._generate_id()

        assert id1 != id2
        assert len(id1) == 36  # UUID format

    def test_split_into_chunks_empty(
        self, mock_config, mock_db_manager, mock_vectordb, mock_embedding_service
    ):
        """空文字列のチャンク分割."""
        service = DocumentService(
            mock_config, mock_db_manager, mock_vectordb, mock_embedding_service
        )
        chunks = service._split_into_chunks("", 100, 20)
        assert chunks == []

    def test_split_into_chunks_short_text(
        self, mock_config, mock_db_manager, mock_vectordb, mock_embedding_service
    ):
        """短いテキストのチャンク分割."""
        service = DocumentService(
            mock_config, mock_db_manager, mock_vectordb, mock_embedding_service
        )
        chunks = service._split_into_chunks("Short text", 100, 20)
        assert len(chunks) == 1
        assert chunks[0] == "Short text"

    def test_split_into_chunks_long_text(
        self, mock_config, mock_db_manager, mock_vectordb, mock_embedding_service
    ):
        """長いテキストのチャンク分割."""
        service = DocumentService(
            mock_config, mock_db_manager, mock_vectordb, mock_embedding_service
        )
        long_text = "This is a test. " * 100  # 1600文字程度
        chunks = service._split_into_chunks(long_text, 200, 50)

        assert len(chunks) > 1
        for chunk in chunks:
            assert len(chunk) <= 250  # chunk_size + margin


# =============================================================================
# SearchService Tests
# =============================================================================


class TestSearchService:
    """SearchServiceのテスト."""

    @pytest.fixture
    def search_service(self, mock_vectordb, mock_embedding_service, mock_db_manager):
        """SearchServiceインスタンス."""
        return SearchService(mock_vectordb, mock_embedding_service, mock_db_manager)

    @pytest.mark.asyncio
    async def test_search_empty_results(self, search_service, mock_vectordb):
        """検索結果が空の場合."""
        mock_vectordb.search.return_value = []

        result = await search_service.search("test query")

        assert len(result.chunks) == 0
        assert result.query == "test query"

    @pytest.mark.asyncio
    async def test_search_with_results(self, search_service, mock_vectordb):
        """検索結果がある場合."""
        from study_agent.infrastructure.vectordb import (
            SearchResult as VectorSearchResult,
        )

        mock_vectordb.search.return_value = [
            VectorSearchResult(
                chunk_id="chunk-1",
                content="Test content about EC2",
                score=0.9,
                metadata={"document_id": "doc-1", "chunk_index": 0},
            )
        ]

        result = await search_service.search("EC2")

        assert len(result.chunks) == 1
        assert result.chunks[0].content == "Test content about EC2"
        assert result.scores[0] == 0.9

    @pytest.mark.asyncio
    async def test_get_context_for_explanation_empty(
        self, search_service, mock_vectordb
    ):
        """コンテキスト取得（結果なし）."""
        mock_vectordb.search.return_value = []

        context = await search_service.get_context_for_explanation("unknown topic")

        assert "見つかりませんでした" in context.context
        assert context.total_chunks == 0


# =============================================================================
# QuizService Tests
# =============================================================================


class TestQuizService:
    """QuizServiceのテスト."""

    @pytest.fixture
    def quiz_service(
        self, mock_llm_client, mock_vectordb, mock_embedding_service, mock_db_manager
    ):
        """QuizServiceインスタンス."""
        search_service = SearchService(
            mock_vectordb, mock_embedding_service, mock_db_manager
        )
        return QuizService(mock_llm_client, search_service, mock_db_manager)

    def test_evaluate_multiple_choice_correct(self, mock_llm_client, mock_db_manager):
        """選択式問題の正解評価."""
        search_service = MagicMock()
        service = QuizService(mock_llm_client, search_service, mock_db_manager)

        quiz = Quiz(
            id="quiz-1",
            document_id="doc-1",
            question="What is EC2?",
            correct_answer="A",
            quiz_type=QuizType.MULTIPLE_CHOICE,
            options={"A": "Compute", "B": "Storage", "C": "Network", "D": "Database"},
        )

        result = service._evaluate_multiple_choice(quiz, "A")

        assert result.is_correct is True
        assert result.score == 100
        assert "正解" in result.feedback

    def test_evaluate_multiple_choice_incorrect(self, mock_llm_client, mock_db_manager):
        """選択式問題の不正解評価."""
        search_service = MagicMock()
        service = QuizService(mock_llm_client, search_service, mock_db_manager)

        quiz = Quiz(
            id="quiz-1",
            document_id="doc-1",
            question="What is EC2?",
            correct_answer="A",
            quiz_type=QuizType.MULTIPLE_CHOICE,
            options={"A": "Compute", "B": "Storage", "C": "Network", "D": "Database"},
        )

        result = service._evaluate_multiple_choice(quiz, "B")

        assert result.is_correct is False
        assert result.score == 0
        assert "不正解" in result.feedback

    def test_evaluate_true_false_correct(self, mock_llm_client, mock_db_manager):
        """○×問題の正解評価."""
        search_service = MagicMock()
        service = QuizService(mock_llm_client, search_service, mock_db_manager)

        quiz = Quiz(
            id="quiz-1",
            document_id="doc-1",
            question="EC2はコンピューティングサービスである",
            correct_answer="○",
            quiz_type=QuizType.TRUE_FALSE,
        )

        result = service._evaluate_true_false(quiz, "○")

        assert result.is_correct is True
        assert result.score == 100


# =============================================================================
# ProgressService Tests
# =============================================================================


class TestProgressService:
    """ProgressServiceのテスト."""

    @pytest.fixture
    def progress_service(self, mock_db_manager):
        """ProgressServiceインスタンス."""
        return ProgressService(mock_db_manager)

    def test_calculate_mastery_no_quiz(self, progress_service):
        """クイズ未受験時の習熟度計算."""
        mastery = progress_service.calculate_mastery_level(
            correct_count=0,
            total_count=0,
            study_count=3,
        )
        assert mastery == 30  # study_count * 10, max 30

    def test_calculate_mastery_with_quiz(self, progress_service):
        """クイズ受験時の習熟度計算."""
        mastery = progress_service.calculate_mastery_level(
            correct_count=8,
            total_count=10,
            study_count=5,
        )
        # 基礎点 = 80% * 0.7 = 56
        # 経験点 = min(5 * 5, 30) = 25
        # 合計 = 81
        assert mastery == 81

    def test_calculate_mastery_perfect(self, progress_service):
        """完璧な成績の習熟度計算."""
        mastery = progress_service.calculate_mastery_level(
            correct_count=10,
            total_count=10,
            study_count=10,
        )
        # 基礎点 = 100% * 0.7 = 70
        # 経験点 = min(10 * 5, 30) = 30
        # 合計 = 100
        assert mastery == 100


# =============================================================================
# SessionService Tests
# =============================================================================


class TestSessionService:
    """SessionServiceのテスト."""

    @pytest.fixture
    def session_service(self, mock_db_manager):
        """SessionServiceインスタンス."""
        return SessionService(mock_db_manager)

    def test_init(self, session_service):
        """初期化テスト."""
        assert session_service._current_session is None

    def test_get_current_session_none(self, session_service):
        """現在のセッションがない場合."""
        assert session_service.get_current_session() is None

    @pytest.mark.asyncio
    async def test_start_session_creates_new(self, session_service, mock_db_manager):
        """新しいセッションの開始."""
        # モックセッションを設定
        mock_session = MagicMock()
        mock_repo = MagicMock()
        mock_db_manager.get_session.return_value.__enter__ = MagicMock(
            return_value=mock_session
        )
        mock_db_manager.get_session.return_value.__exit__ = MagicMock(
            return_value=False
        )

        with patch.object(
            session_service.db_manager, "get_session"
        ) as mock_get_session:
            mock_context = MagicMock()
            mock_context.__enter__ = MagicMock(return_value=mock_session)
            mock_context.__exit__ = MagicMock(return_value=False)
            mock_get_session.return_value = mock_context

            # LearningSessionRepositoryをモック
            with patch(
                "study_agent.services.session_service.LearningSessionRepository"
            ) as mock_repo_class:
                mock_repo_instance = MagicMock()
                mock_repo_class.return_value = mock_repo_instance

                session = await session_service.start_session(
                    document_id="doc-1",
                    mode=SessionMode.LEARNING,
                )

        assert session is not None
        assert session.document_id == "doc-1"
        assert session.mode == SessionMode.LEARNING
        assert session.status == SessionStatus.ACTIVE
        assert session_service._current_session == session
