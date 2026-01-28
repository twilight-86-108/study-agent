"""Agents layer unit tests.

エージェント層のユニットテスト。
モックを使用して依存関係を分離する。
"""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock

from study_agent.agents import (
    AgentState,
    create_initial_state,
    BaseAgent,
    RouterAgent,
    TutorAgent,
    QuizGeneratorAgent,
    EvaluatorAgent,
    PlannerAgent,
)
from study_agent.domain import Intent, QuizType, Quiz, Difficulty


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_llm_client():
    """モックLLMクライアント."""
    client = AsyncMock()
    client.generate = AsyncMock()
    client.generate_json = AsyncMock()
    return client


@pytest.fixture
def mock_search_service():
    """モック検索サービス."""
    service = AsyncMock()
    service.get_context_for_explanation = AsyncMock(
        return_value=MagicMock(
            context="テストコンテキスト",
            source_chunks=[MagicMock(id="chunk-1")],
        )
    )
    return service


@pytest.fixture
def mock_quiz_service():
    """モッククイズサービス."""
    service = AsyncMock()
    return service


@pytest.fixture
def mock_progress_service():
    """モック進捗サービス."""
    service = AsyncMock()
    return service


# =============================================================================
# AgentState Tests
# =============================================================================


class TestAgentState:
    """AgentStateのテスト."""

    def test_create_initial_state_minimal(self):
        """最小限の初期状態を作成."""
        state = create_initial_state(
            user_query="テスト",
            session_id="session-1",
        )

        assert state["user_query"] == "テスト"
        assert state["session_id"] == "session-1"
        assert state["document_id"] is None
        assert state["messages"] == []
        assert state["source_chunks"] == []

    def test_create_initial_state_full(self):
        """フル指定の初期状態を作成."""
        quiz = MagicMock()
        state = create_initial_state(
            user_query="テスト",
            session_id="session-1",
            document_id="doc-1",
            quiz=quiz,
        )

        assert state["document_id"] == "doc-1"
        assert state["quiz"] == quiz


# =============================================================================
# RouterAgent Tests
# =============================================================================


class TestRouterAgent:
    """RouterAgentのテスト."""

    @pytest.fixture
    def router(self, mock_llm_client):
        """RouterAgentインスタンス."""
        return RouterAgent(mock_llm_client, use_llm_fallback=False)

    @pytest.mark.asyncio
    async def test_classify_explain_pattern(self, router):
        """説明意図のパターンマッチング."""
        state = create_initial_state(
            user_query="EC2について教えて",
            session_id="test",
        )

        result = await router.execute(state)

        assert result["intent"] == Intent.EXPLAIN
        assert result["confidence"] >= 0.8

    @pytest.mark.asyncio
    async def test_classify_quiz_pattern(self, router):
        """クイズ意図のパターンマッチング."""
        state = create_initial_state(
            user_query="クイズを出して",
            session_id="test",
        )

        result = await router.execute(state)

        assert result["intent"] == Intent.QUIZ
        assert result["confidence"] >= 0.8

    @pytest.mark.asyncio
    async def test_classify_progress_pattern(self, router):
        """進捗確認意図のパターンマッチング."""
        state = create_initial_state(
            user_query="進捗を見せて",
            session_id="test",
        )

        result = await router.execute(state)

        assert result["intent"] == Intent.PROGRESS

    @pytest.mark.asyncio
    async def test_extract_topic(self, router):
        """トピック抽出."""
        state = create_initial_state(
            user_query="Amazon EC2について教えて",
            session_id="test",
        )

        result = await router.execute(state)

        assert result["extracted_topic"] is not None
        assert (
            "EC2" in result["extracted_topic"] or "Amazon" in result["extracted_topic"]
        )

    @pytest.mark.asyncio
    async def test_empty_query(self, router):
        """空のクエリ."""
        state = create_initial_state(
            user_query="",
            session_id="test",
        )

        result = await router.execute(state)

        assert result["intent"] == Intent.UNKNOWN


# =============================================================================
# TutorAgent Tests
# =============================================================================


class TestTutorAgent:
    """TutorAgentのテスト."""

    @pytest.fixture
    def tutor(self, mock_llm_client, mock_search_service):
        """TutorAgentインスタンス."""
        return TutorAgent(mock_llm_client, mock_search_service)

    @pytest.mark.asyncio
    async def test_execute_generates_explanation(self, tutor, mock_llm_client):
        """説明を生成."""
        mock_llm_client.generate.return_value = MagicMock(
            content="【概要】\nEC2はコンピューティングサービスです。"
        )

        state = create_initial_state(
            user_query="EC2について教えて",
            session_id="test",
        )
        state["extracted_topic"] = "Amazon EC2"
        state["intent"] = Intent.EXPLAIN

        result = await tutor.execute(state)

        assert result["explanation"] is not None
        assert result["response"] is not None
        assert result["context"] == "テストコンテキスト"

    @pytest.mark.asyncio
    async def test_execute_without_topic(self, tutor):
        """トピックなしでエラー."""
        state = create_initial_state(
            user_query="",
            session_id="test",
        )
        state["extracted_topic"] = None

        result = await tutor.execute(state)

        assert result.get("error") is not None


# =============================================================================
# QuizGeneratorAgent Tests
# =============================================================================


class TestQuizGeneratorAgent:
    """QuizGeneratorAgentのテスト."""

    @pytest.fixture
    def generator(self, mock_llm_client, mock_quiz_service):
        """QuizGeneratorAgentインスタンス."""
        return QuizGeneratorAgent(mock_llm_client, mock_quiz_service)

    @pytest.mark.asyncio
    async def test_execute_generates_quiz(self, generator, mock_quiz_service):
        """クイズを生成."""
        mock_quiz = Quiz(
            id="quiz-1",
            document_id="doc-1",
            question="EC2とは？",
            correct_answer="A",
            quiz_type=QuizType.MULTIPLE_CHOICE,
            options={
                "A": "コンピュート",
                "B": "ストレージ",
                "C": "ネットワーク",
                "D": "データベース",
            },
        )
        mock_quiz_service.generate_quiz.return_value = MagicMock(
            quiz=mock_quiz,
            context_used="context",
            source_chunks=["chunk-1"],
        )

        state = create_initial_state(
            user_query="クイズを出して",
            session_id="test",
        )
        state["extracted_topic"] = "EC2"

        result = await generator.execute(state)

        assert result["quiz"] == mock_quiz
        assert "【問題】" in result["response"]

    def test_format_quiz_multiple_choice(self, generator):
        """選択式クイズのフォーマット."""
        quiz = Quiz(
            id="quiz-1",
            document_id="doc-1",
            question="テスト問題？",
            correct_answer="A",
            quiz_type=QuizType.MULTIPLE_CHOICE,
            options={"A": "選択肢A", "B": "選択肢B", "C": "選択肢C", "D": "選択肢D"},
        )

        result = generator._format_quiz_for_display(quiz)

        assert "【問題】" in result
        assert "A." in result
        assert "B." in result

    def test_determine_quiz_type(self, generator):
        """クイズタイプの判定."""
        assert generator._determine_quiz_type("記述式で出して") == QuizType.OPEN
        assert generator._determine_quiz_type("○×問題") == QuizType.TRUE_FALSE
        assert generator._determine_quiz_type("クイズ") == QuizType.MULTIPLE_CHOICE


# =============================================================================
# EvaluatorAgent Tests
# =============================================================================


class TestEvaluatorAgent:
    """EvaluatorAgentのテスト."""

    @pytest.fixture
    def evaluator(self, mock_llm_client, mock_quiz_service, mock_progress_service):
        """EvaluatorAgentインスタンス."""
        return EvaluatorAgent(mock_llm_client, mock_quiz_service, mock_progress_service)

    @pytest.mark.asyncio
    async def test_execute_without_quiz(self, evaluator):
        """クイズなしでエラー."""
        state = create_initial_state(
            user_query="A",
            session_id="test",
        )

        result = await evaluator.execute(state)

        assert result.get("error") is not None
        assert "クイズがありません" in result["response"]

    @pytest.mark.asyncio
    async def test_execute_with_quiz(self, evaluator, mock_quiz_service):
        """クイズありで評価."""
        mock_evaluation = MagicMock(
            is_correct=True,
            score=100,
            feedback="正解！",
            correct_answer="A",
            matched_points=[],
            missed_points=[],
        )
        mock_quiz_service.evaluate_answer.return_value = mock_evaluation

        quiz = Quiz(
            id="quiz-1",
            document_id="doc-1",
            question="テスト？",
            correct_answer="A",
            quiz_type=QuizType.MULTIPLE_CHOICE,
        )

        state = create_initial_state(
            user_query="A",
            session_id="test",
        )
        state["quiz"] = quiz

        result = await evaluator.execute(state)

        assert result["evaluation"] == mock_evaluation
        assert result["quiz"] is None  # クリアされる

    def test_should_execute(self, evaluator):
        """実行判定."""
        state_with_quiz = {"quiz": MagicMock()}
        state_without_quiz = {"quiz": None}

        assert evaluator.should_execute(state_with_quiz) is True
        assert evaluator.should_execute(state_without_quiz) is False


# =============================================================================
# PlannerAgent Tests
# =============================================================================


class TestPlannerAgent:
    """PlannerAgentのテスト."""

    @pytest.fixture
    def planner(self, mock_llm_client, mock_progress_service):
        """PlannerAgentインスタンス."""
        return PlannerAgent(mock_llm_client, mock_progress_service)

    @pytest.mark.asyncio
    async def test_execute_navigation(self, planner, mock_progress_service):
        """ナビゲーション処理."""
        mock_progress_service.get_recommended_topic.return_value = MagicMock(
            topic=MagicMock(title="VPC"),
            reason="次のトピックです",
        )

        state = create_initial_state(
            user_query="次のトピックへ",
            session_id="test",
            document_id="doc-1",
        )
        state["intent"] = Intent.NAVIGATE

        result = await planner.execute(state)

        assert result["recommended_topic"] == "VPC"
        assert "VPC" in result["response"]
