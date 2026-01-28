"""Domain models and enums unit tests.

ドメインモデルとEnumのユニットテスト。
"""

from __future__ import annotations

import pytest
from datetime import datetime, timezone

from study_agent.domain import (
    # Enums
    Difficulty,
    FileType,
    Intent,
    MasteryLevel,
    QuizType,
    SessionMode,
    SessionStatus,
    # Models
    Chapter,
    Chunk,
    Document,
    LearningSession,
    Quiz,
    QuizAttempt,
    Topic,
    TopicProgress,
    UserSetting,
    # DTOs
    DocumentProgressSummary,
    GeneratedQuiz,
    LoadDocumentResult,
    QuizEvaluation,
    QuizSessionStats,
    SearchResult,
    TopicProgressDetail,
)


# =============================================================================
# Enum Tests
# =============================================================================


class TestFileType:
    """FileType Enumのテスト."""

    def test_values(self):
        """値の確認."""
        assert FileType.PDF.value == "pdf"
        assert FileType.MARKDOWN.value == "md"
        assert FileType.TEXT.value == "txt"

    def test_from_extension_pdf(self):
        """PDF拡張子から変換."""
        assert FileType.from_extension("pdf") == FileType.PDF
        assert FileType.from_extension("PDF") == FileType.PDF
        assert FileType.from_extension(".pdf") == FileType.PDF

    def test_from_extension_markdown(self):
        """Markdown拡張子から変換."""
        assert FileType.from_extension("md") == FileType.MARKDOWN
        assert FileType.from_extension("markdown") == FileType.MARKDOWN

    def test_from_extension_text(self):
        """テキスト拡張子から変換."""
        assert FileType.from_extension("txt") == FileType.TEXT
        assert FileType.from_extension("text") == FileType.TEXT

    def test_from_extension_unsupported(self):
        """サポートされていない拡張子でエラー."""
        with pytest.raises(ValueError, match="Unsupported"):
            FileType.from_extension("doc")


class TestDifficulty:
    """Difficulty Enumのテスト."""

    def test_values(self):
        """値の確認."""
        assert Difficulty.BEGINNER.value == 1
        assert Difficulty.EASY.value == 2
        assert Difficulty.MEDIUM.value == 3
        assert Difficulty.HARD.value == 4
        assert Difficulty.EXPERT.value == 5

    def test_from_int(self):
        """整数から変換."""
        assert Difficulty.from_int(1) == Difficulty.BEGINNER
        assert Difficulty.from_int(3) == Difficulty.MEDIUM
        assert Difficulty.from_int(5) == Difficulty.EXPERT

    def test_from_int_invalid(self):
        """範囲外の値でエラー."""
        with pytest.raises(ValueError):
            Difficulty.from_int(0)
        with pytest.raises(ValueError):
            Difficulty.from_int(6)


class TestMasteryLevel:
    """MasteryLevel Enumのテスト."""

    def test_from_score_not_started(self):
        """スコア0で未学習."""
        assert MasteryLevel.from_score(0) == MasteryLevel.NOT_STARTED
        assert MasteryLevel.from_score(-5) == MasteryLevel.NOT_STARTED

    def test_from_score_learning(self):
        """スコア1-49で学習中."""
        assert MasteryLevel.from_score(1) == MasteryLevel.LEARNING
        assert MasteryLevel.from_score(49) == MasteryLevel.LEARNING

    def test_from_score_developing(self):
        """スコア50-79で発展中."""
        assert MasteryLevel.from_score(50) == MasteryLevel.DEVELOPING
        assert MasteryLevel.from_score(79) == MasteryLevel.DEVELOPING

    def test_from_score_mastered(self):
        """スコア80以上で習得済み."""
        assert MasteryLevel.from_score(80) == MasteryLevel.MASTERED
        assert MasteryLevel.from_score(100) == MasteryLevel.MASTERED


class TestIntent:
    """Intent Enumのテスト."""

    def test_values(self):
        """値の確認."""
        assert Intent.EXPLAIN.value == "explain"
        assert Intent.QUIZ.value == "quiz"
        assert Intent.CHAT.value == "chat"


class TestSessionStatus:
    """SessionStatus Enumのテスト."""

    def test_values(self):
        """値の確認."""
        assert SessionStatus.ACTIVE.value == "active"
        assert SessionStatus.COMPLETED.value == "completed"
        assert SessionStatus.ABANDONED.value == "abandoned"


# =============================================================================
# Document Model Tests
# =============================================================================


class TestDocument:
    """Documentモデルのテスト."""

    def test_create_basic(self):
        """基本的な作成."""
        doc = Document(
            id="doc-1",
            title="Test Document",
            file_path="/path/to/file.pdf",
            file_type=FileType.PDF,
        )
        assert doc.id == "doc-1"
        assert doc.title == "Test Document"
        assert doc.file_type == FileType.PDF
        assert doc.chapters == []
        assert doc.topics == []

    def test_create_with_pages(self):
        """ページ数付きで作成."""
        doc = Document(
            id="doc-1",
            title="Test Document",
            file_path="/path/to/file.pdf",
            file_type=FileType.PDF,
            total_pages=100,
        )
        assert doc.total_pages == 100

    def test_empty_title_raises(self):
        """空タイトルでエラー."""
        with pytest.raises(ValueError, match="title cannot be empty"):
            Document(
                id="doc-1",
                title="",
                file_path="/path/to/file.pdf",
                file_type=FileType.PDF,
            )

    def test_empty_file_path_raises(self):
        """空ファイルパスでエラー."""
        with pytest.raises(ValueError, match="file_path cannot be empty"):
            Document(
                id="doc-1",
                title="Test",
                file_path="",
                file_type=FileType.PDF,
            )

    def test_chapter_count(self):
        """章数プロパティ."""
        doc = Document(
            id="doc-1",
            title="Test",
            file_path="/path.pdf",
            file_type=FileType.PDF,
            chapters=[
                Chapter(id="ch-1", document_id="doc-1", title="Ch1", order_index=0),
                Chapter(id="ch-2", document_id="doc-1", title="Ch2", order_index=1),
            ],
        )
        assert doc.chapter_count == 2


class TestChapter:
    """Chapterモデルのテスト."""

    def test_create_basic(self):
        """基本的な作成."""
        chapter = Chapter(
            id="ch-1",
            document_id="doc-1",
            title="Chapter 1",
            order_index=0,
        )
        assert chapter.title == "Chapter 1"
        assert chapter.order_index == 0

    def test_create_with_pages(self):
        """ページ範囲付きで作成."""
        chapter = Chapter(
            id="ch-1",
            document_id="doc-1",
            title="Chapter 1",
            order_index=0,
            page_start=1,
            page_end=10,
        )
        assert chapter.page_start == 1
        assert chapter.page_end == 10

    def test_empty_title_raises(self):
        """空タイトルでエラー."""
        with pytest.raises(ValueError, match="title cannot be empty"):
            Chapter(id="ch-1", document_id="doc-1", title="", order_index=0)

    def test_negative_order_index_raises(self):
        """負のorder_indexでエラー."""
        with pytest.raises(ValueError, match="non-negative"):
            Chapter(id="ch-1", document_id="doc-1", title="Ch", order_index=-1)


class TestTopic:
    """Topicモデルのテスト."""

    def test_create_basic(self):
        """基本的な作成."""
        topic = Topic(
            id="topic-1",
            document_id="doc-1",
            title="Topic 1",
            order_index=0,
        )
        assert topic.title == "Topic 1"
        assert topic.chapter_id is None

    def test_create_with_chapter(self):
        """章付きで作成."""
        topic = Topic(
            id="topic-1",
            document_id="doc-1",
            title="Topic 1",
            order_index=0,
            chapter_id="ch-1",
        )
        assert topic.chapter_id == "ch-1"


class TestChunk:
    """Chunkモデルのテスト."""

    def test_create_basic(self):
        """基本的な作成."""
        chunk = Chunk(
            id="chunk-1",
            document_id="doc-1",
            content="This is test content.",
            chunk_index=0,
        )
        assert chunk.content == "This is test content."
        assert chunk.chunk_index == 0

    def test_empty_content_raises(self):
        """空コンテンツでエラー."""
        with pytest.raises(ValueError, match="content cannot be empty"):
            Chunk(id="chunk-1", document_id="doc-1", content="", chunk_index=0)

    def test_char_count(self):
        """文字数プロパティ."""
        chunk = Chunk(
            id="chunk-1",
            document_id="doc-1",
            content="Hello World",
            chunk_index=0,
        )
        assert chunk.char_count == 11

    def test_word_count(self):
        """単語数プロパティ."""
        chunk = Chunk(
            id="chunk-1",
            document_id="doc-1",
            content="Hello World Test",
            chunk_index=0,
        )
        assert chunk.word_count == 3


# =============================================================================
# Quiz Model Tests
# =============================================================================


class TestQuiz:
    """Quizモデルのテスト."""

    def test_create_multiple_choice(self):
        """選択式クイズの作成."""
        quiz = Quiz(
            id="quiz-1",
            document_id="doc-1",
            question="What is EC2?",
            correct_answer="A",
            quiz_type=QuizType.MULTIPLE_CHOICE,
            options={"A": "Compute", "B": "Storage", "C": "Network", "D": "Database"},
        )
        assert quiz.quiz_type == QuizType.MULTIPLE_CHOICE
        assert len(quiz.options) == 4

    def test_create_open_quiz(self):
        """記述式クイズの作成."""
        quiz = Quiz(
            id="quiz-1",
            document_id="doc-1",
            question="Explain EC2",
            correct_answer="EC2 is a compute service",
            quiz_type=QuizType.OPEN,
        )
        assert quiz.quiz_type == QuizType.OPEN
        assert quiz.options is None

    def test_multiple_choice_without_options_raises(self):
        """選択式でオプションなしでエラー."""
        with pytest.raises(ValueError, match="must have options"):
            Quiz(
                id="quiz-1",
                document_id="doc-1",
                question="What is EC2?",
                correct_answer="A",
                quiz_type=QuizType.MULTIPLE_CHOICE,
            )

    def test_is_correct(self):
        """正解判定."""
        quiz = Quiz(
            id="quiz-1",
            document_id="doc-1",
            question="What is EC2?",
            correct_answer="A",
            quiz_type=QuizType.MULTIPLE_CHOICE,
            options={"A": "Compute", "B": "Storage"},
        )
        assert quiz.is_correct("A") is True
        assert quiz.is_correct("a") is True  # 大文字小文字無視
        assert quiz.is_correct("B") is False


class TestQuizAttempt:
    """QuizAttemptモデルのテスト."""

    def test_create_basic(self):
        """基本的な作成."""
        attempt = QuizAttempt(
            id="attempt-1",
            quiz_id="quiz-1",
            session_id="session-1",
            user_answer="A",
            is_correct=True,
        )
        assert attempt.is_correct is True

    def test_invalid_score_raises(self):
        """範囲外のスコアでエラー."""
        with pytest.raises(ValueError, match="between 0 and 100"):
            QuizAttempt(
                id="attempt-1",
                quiz_id="quiz-1",
                session_id="session-1",
                user_answer="A",
                is_correct=True,
                score=150,
            )


# =============================================================================
# Progress Model Tests
# =============================================================================


class TestTopicProgress:
    """TopicProgressモデルのテスト."""

    def test_create_basic(self):
        """基本的な作成."""
        progress = TopicProgress(
            id="progress-1",
            topic_id="topic-1",
        )
        assert progress.study_count == 0
        assert progress.mastery_level == 0

    def test_accuracy_rate_zero_total(self):
        """回答なしの正答率."""
        progress = TopicProgress(
            id="progress-1",
            topic_id="topic-1",
        )
        assert progress.accuracy_rate == 0.0

    def test_accuracy_rate_with_answers(self):
        """回答ありの正答率."""
        progress = TopicProgress(
            id="progress-1",
            topic_id="topic-1",
            correct_count=7,
            total_count=10,
        )
        assert progress.accuracy_rate == 0.7

    def test_mastery_status(self):
        """習熟度ステータス."""
        progress = TopicProgress(
            id="progress-1",
            topic_id="topic-1",
            mastery_level=85,
        )
        assert progress.mastery_status == MasteryLevel.MASTERED

    def test_calculate_mastery(self):
        """習熟度計算."""
        progress = TopicProgress(
            id="progress-1",
            topic_id="topic-1",
            study_count=5,
            correct_count=8,
            total_count=10,
        )
        # 正答率80% × 70 = 56
        # 学習回数5 × 5 = 25
        # 合計 = 81
        assert progress.calculate_mastery() == 81

    def test_invalid_mastery_level_raises(self):
        """範囲外の習熟度でエラー."""
        with pytest.raises(ValueError, match="between 0 and 100"):
            TopicProgress(
                id="progress-1",
                topic_id="topic-1",
                mastery_level=150,
            )

    def test_correct_count_exceeds_total_raises(self):
        """正答数が総数を超えるとエラー."""
        with pytest.raises(ValueError, match="cannot exceed"):
            TopicProgress(
                id="progress-1",
                topic_id="topic-1",
                correct_count=10,
                total_count=5,
            )


class TestLearningSession:
    """LearningSessionモデルのテスト."""

    def test_create_basic(self):
        """基本的な作成."""
        session = LearningSession(
            id="session-1",
            document_id="doc-1",
        )
        assert session.mode == SessionMode.LEARNING
        assert session.status == SessionStatus.ACTIVE
        assert session.is_active is True

    def test_accuracy_rate(self):
        """正答率."""
        session = LearningSession(
            id="session-1",
            document_id="doc-1",
            quizzes_completed=10,
            correct_answers=7,
        )
        assert session.accuracy_rate == 0.7


# =============================================================================
# DTO Tests
# =============================================================================


class TestSearchResult:
    """SearchResult DTOのテスト."""

    def test_create_basic(self):
        """基本的な作成."""
        chunks = [
            Chunk(id="c1", document_id="d1", content="Content 1", chunk_index=0),
            Chunk(id="c2", document_id="d1", content="Content 2", chunk_index=1),
        ]
        result = SearchResult(
            chunks=chunks,
            scores=[0.9, 0.7],
            query="test query",
        )
        assert result.total_results == 2
        assert result.best_match == chunks[0]

    def test_mismatched_lengths_raises(self):
        """長さ不一致でエラー."""
        chunks = [
            Chunk(id="c1", document_id="d1", content="Content 1", chunk_index=0),
        ]
        with pytest.raises(ValueError, match="same length"):
            SearchResult(
                chunks=chunks,
                scores=[0.9, 0.7],
                query="test",
            )

    def test_context_text(self):
        """コンテキストテキスト."""
        chunks = [
            Chunk(id="c1", document_id="d1", content="Content 1", chunk_index=0),
            Chunk(id="c2", document_id="d1", content="Content 2", chunk_index=1),
        ]
        result = SearchResult(
            chunks=chunks,
            scores=[0.9, 0.7],
            query="test",
        )
        assert "Content 1" in result.context_text
        assert "Content 2" in result.context_text

    def test_get_chunks_above_threshold(self):
        """閾値以上のチャンク取得."""
        chunks = [
            Chunk(id="c1", document_id="d1", content="Content 1", chunk_index=0),
            Chunk(id="c2", document_id="d1", content="Content 2", chunk_index=1),
        ]
        result = SearchResult(
            chunks=chunks,
            scores=[0.9, 0.4],
            query="test",
        )
        above = result.get_chunks_above_threshold(0.5)
        assert len(above) == 1
        assert above[0].id == "c1"


class TestQuizSessionStats:
    """QuizSessionStats DTOのテスト."""

    def test_update(self):
        """統計更新."""
        stats = QuizSessionStats()
        stats.update(is_correct=True, score=100, topic_id="topic-1")
        stats.update(is_correct=False, score=50, topic_id="topic-1")

        assert stats.total_questions == 2
        assert stats.correct_answers == 1
        assert stats.accuracy_rate == 0.5
        assert stats.average_score == 75.0
        assert stats.by_topic["topic-1"]["correct"] == 1
        assert stats.by_topic["topic-1"]["total"] == 2


class TestDocumentProgressSummary:
    """DocumentProgressSummary DTOのテスト."""

    def test_completion_rate(self):
        """完了率."""
        summary = DocumentProgressSummary(
            document_id="doc-1",
            document_title="Test Doc",
            total_topics=10,
            studied_topics=5,
        )
        assert summary.completion_rate == 0.5

    def test_mastery_rate(self):
        """習得率."""
        summary = DocumentProgressSummary(
            document_id="doc-1",
            document_title="Test Doc",
            total_topics=10,
            mastered_topics=3,
        )
        assert summary.mastery_rate == 0.3


class TestLoadDocumentResult:
    """LoadDocumentResult DTOのテスト."""

    def test_summary(self):
        """サマリー文字列."""
        doc = Document(
            id="doc-1",
            title="Test Document",
            file_path="/path.pdf",
            file_type=FileType.PDF,
        )
        chapters = [
            Chapter(id="ch-1", document_id="doc-1", title="Ch1", order_index=0),
        ]
        topics = [
            Topic(id="t-1", document_id="doc-1", title="Topic1", order_index=0),
            Topic(id="t-2", document_id="doc-1", title="Topic2", order_index=1),
        ]
        result = LoadDocumentResult(
            document=doc,
            chapters=chapters,
            topics=topics,
            chunks_count=10,
        )
        assert "Test Document" in result.summary
        assert "1 chapters" in result.summary
        assert "2 topics" in result.summary
        assert "10 chunks" in result.summary
