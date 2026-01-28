"""Database統合テスト.

DatabaseManager、Models、Repositoriesの統合テスト。
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from study_agent.infrastructure.database import (
    Chapter,
    ChapterRepository,
    Chunk,
    ChunkRepository,
    DatabaseManager,
    Document,
    DocumentRepository,
    FileType,
    LearningSession,
    LearningSessionRepository,
    Quiz,
    QuizAttempt,
    QuizAttemptRepository,
    QuizRepository,
    QuizType,
    SessionMode,
    SessionStatus,
    Topic,
    TopicProgressRepository,
    TopicRepository,
)


# ============================
# Fixtures
# ============================


@pytest.fixture
def temp_db_path():
    """一時データベースパスを作成."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir) / "test.db"


@pytest.fixture
def db_manager(temp_db_path: Path):
    """DatabaseManagerを作成."""
    manager = DatabaseManager(temp_db_path)
    manager.initialize()
    yield manager
    manager.close()


@pytest.fixture
def sample_document_id(db_manager: DatabaseManager) -> str:
    """サンプルドキュメントを作成してIDを返す."""
    with db_manager.get_session() as session:
        repo = DocumentRepository(session)
        doc = Document(
            title="AWS SAA Study Guide",
            file_path="/path/to/aws_saa.pdf",
            file_type=FileType.PDF,
            total_pages=100,
            description="AWS Solutions Architect Associate",
        )
        created = repo.create(doc)
        return created.id


@pytest.fixture
def sample_chapter_id(db_manager: DatabaseManager, sample_document_id: str) -> str:
    """サンプル章を作成してIDを返す."""
    with db_manager.get_session() as session:
        repo = ChapterRepository(session)
        chapter = Chapter(
            document_id=sample_document_id,
            title="Chapter 1: EC2",
            order_index=0,
            page_start=1,
            page_end=20,
        )
        created = repo.create(chapter)
        return created.id


@pytest.fixture
def sample_topic_id(
    db_manager: DatabaseManager,
    sample_document_id: str,
    sample_chapter_id: str,
) -> str:
    """サンプルトピックを作成してIDを返す."""
    with db_manager.get_session() as session:
        repo = TopicRepository(session)
        topic = Topic(
            document_id=sample_document_id,
            chapter_id=sample_chapter_id,
            title="Amazon EC2",
            description="Elastic Compute Cloud",
            order_index=0,
        )
        created = repo.create(topic)
        return created.id


# ============================
# DatabaseManager Tests
# ============================


class TestDatabaseManager:
    """DatabaseManagerのテスト."""

    def test_initialize(self, temp_db_path: Path):
        """初期化."""
        manager = DatabaseManager(temp_db_path)
        assert manager.is_initialized is False

        manager.initialize()
        assert manager.is_initialized is True
        assert temp_db_path.exists()

        manager.close()

    def test_context_manager(self, temp_db_path: Path):
        """コンテキストマネージャー."""
        with DatabaseManager(temp_db_path) as manager:
            assert manager.is_initialized is True

    def test_session(self, db_manager: DatabaseManager):
        """セッション取得."""
        with db_manager.get_session() as session:
            assert session is not None


# ============================
# DocumentRepository Tests
# ============================


class TestDocumentRepository:
    """DocumentRepositoryのテスト."""

    def test_create_and_get(self, db_manager: DatabaseManager):
        """作成と取得."""
        with db_manager.get_session() as session:
            repo = DocumentRepository(session)
            doc = Document(
                title="Test Document",
                file_path="/test/path.pdf",
                file_type=FileType.PDF,
            )
            created = repo.create(doc)

            assert created.id is not None
            assert created.title == "Test Document"

            # 取得
            fetched = repo.get_by_id(created.id)
            assert fetched is not None
            assert fetched.title == created.title

    def test_find_by_file_path(
        self, db_manager: DatabaseManager, sample_document_id: str
    ):
        """ファイルパスで検索."""
        with db_manager.get_session() as session:
            repo = DocumentRepository(session)
            found = repo.find_by_file_path("/path/to/aws_saa.pdf")

            assert found is not None
            assert found.id == sample_document_id

    def test_find_by_title(self, db_manager: DatabaseManager, sample_document_id: str):
        """タイトルで検索."""
        with db_manager.get_session() as session:
            repo = DocumentRepository(session)
            found = repo.find_by_title("AWS")

            assert len(found) >= 1
            assert any(d.id == sample_document_id for d in found)

    def test_find_by_file_type(
        self, db_manager: DatabaseManager, sample_document_id: str
    ):
        """ファイルタイプで検索."""
        with db_manager.get_session() as session:
            repo = DocumentRepository(session)
            found = repo.find_by_file_type(FileType.PDF)

            assert len(found) >= 1

    def test_delete(self, db_manager: DatabaseManager):
        """削除."""
        with db_manager.get_session() as session:
            repo = DocumentRepository(session)
            doc = Document(
                title="To Delete",
                file_path="/delete/me.pdf",
                file_type=FileType.PDF,
            )
            created = repo.create(doc)
            doc_id = created.id

            # 削除
            result = repo.delete_by_id(doc_id)
            assert result is True

            # 確認
            assert repo.get_by_id(doc_id) is None


# ============================
# ChapterRepository Tests
# ============================


class TestChapterRepository:
    """ChapterRepositoryのテスト."""

    def test_find_by_document_id(
        self,
        db_manager: DatabaseManager,
        sample_document_id: str,
        sample_chapter_id: str,
    ):
        """ドキュメントIDで検索."""
        with db_manager.get_session() as session:
            repo = ChapterRepository(session)
            chapters = repo.find_by_document_id(sample_document_id)

            assert len(chapters) >= 1
            assert any(c.id == sample_chapter_id for c in chapters)

    def test_find_by_document_id_ordered(
        self,
        db_manager: DatabaseManager,
        sample_document_id: str,
    ):
        """順序付きで検索."""
        with db_manager.get_session() as session:
            repo = ChapterRepository(session)

            # 複数章を作成
            for i in range(3):
                chapter = Chapter(
                    document_id=sample_document_id,
                    title=f"Chapter {i}",
                    order_index=2 - i,  # 逆順で作成
                )
                repo.create(chapter)

            # 順序付きで取得
            chapters = repo.find_by_document_id_ordered(sample_document_id)
            indices = [c.order_index for c in chapters]

            # order_index順になっていることを確認
            assert indices == sorted(indices)


# ============================
# TopicRepository Tests
# ============================


class TestTopicRepository:
    """TopicRepositoryのテスト."""

    def test_find_by_document_id(
        self,
        db_manager: DatabaseManager,
        sample_document_id: str,
        sample_topic_id: str,
    ):
        """ドキュメントIDで検索."""
        with db_manager.get_session() as session:
            repo = TopicRepository(session)
            topics = repo.find_by_document_id(sample_document_id)

            assert len(topics) >= 1
            assert any(t.id == sample_topic_id for t in topics)

    def test_search_by_title(
        self,
        db_manager: DatabaseManager,
        sample_topic_id: str,
    ):
        """タイトルで検索."""
        with db_manager.get_session() as session:
            repo = TopicRepository(session)
            topics = repo.search_by_title("EC2")

            assert len(topics) >= 1


# ============================
# ChunkRepository Tests
# ============================


class TestChunkRepository:
    """ChunkRepositoryのテスト."""

    def test_create_and_find(
        self,
        db_manager: DatabaseManager,
        sample_document_id: str,
    ):
        """作成と検索."""
        with db_manager.get_session() as session:
            repo = ChunkRepository(session)

            # チャンクを作成
            chunk = Chunk(
                document_id=sample_document_id,
                content="Amazon EC2 is a web service...",
                chunk_index=0,
                page_number=1,
                embedding_id="embed-001",
            )
            created = repo.create(chunk)

            # embedding_idで検索
            found = repo.find_by_embedding_id("embed-001")
            assert found is not None
            assert found.id == created.id

    def test_update_embedding_id(
        self,
        db_manager: DatabaseManager,
        sample_document_id: str,
    ):
        """embedding_id更新."""
        with db_manager.get_session() as session:
            repo = ChunkRepository(session)

            chunk = Chunk(
                document_id=sample_document_id,
                content="Test content",
                chunk_index=0,
            )
            created = repo.create(chunk)

            # 更新
            updated = repo.update_embedding_id(created.id, "new-embed-id")
            assert updated is not None
            assert updated.embedding_id == "new-embed-id"


# ============================
# QuizRepository Tests
# ============================


class TestQuizRepository:
    """QuizRepositoryのテスト."""

    def test_create_and_find(
        self,
        db_manager: DatabaseManager,
        sample_document_id: str,
        sample_topic_id: str,
    ):
        """作成と検索."""
        with db_manager.get_session() as session:
            repo = QuizRepository(session)

            quiz = Quiz(
                document_id=sample_document_id,
                topic_id=sample_topic_id,
                question="What is EC2?",
                correct_answer="Elastic Compute Cloud",
                difficulty=2,
                quiz_type=QuizType.OPEN,
            )
            created = repo.create(quiz)

            # トピックIDで検索
            quizzes = repo.find_by_topic_id(sample_topic_id)
            assert len(quizzes) >= 1
            assert any(q.id == created.id for q in quizzes)

    def test_find_by_difficulty(
        self,
        db_manager: DatabaseManager,
        sample_document_id: str,
    ):
        """難易度で検索."""
        with db_manager.get_session() as session:
            repo = QuizRepository(session)

            # 異なる難易度のクイズを作成
            for difficulty in [1, 3, 5]:
                quiz = Quiz(
                    document_id=sample_document_id,
                    question=f"Question difficulty {difficulty}",
                    correct_answer="Answer",
                    difficulty=difficulty,
                )
                repo.create(quiz)

            # 難易度3で検索
            quizzes = repo.find_by_difficulty(3, document_id=sample_document_id)
            assert all(q.difficulty == 3 for q in quizzes)

    def test_get_random(
        self,
        db_manager: DatabaseManager,
        sample_document_id: str,
    ):
        """ランダム取得."""
        with db_manager.get_session() as session:
            repo = QuizRepository(session)

            # クイズを作成
            for i in range(10):
                quiz = Quiz(
                    document_id=sample_document_id,
                    question=f"Question {i}",
                    correct_answer=f"Answer {i}",
                )
                repo.create(quiz)

            # ランダムに5つ取得
            random_quizzes = repo.get_random(count=5, document_id=sample_document_id)
            assert len(random_quizzes) == 5


# ============================
# TopicProgressRepository Tests
# ============================


class TestTopicProgressRepository:
    """TopicProgressRepositoryのテスト."""

    def test_find_or_create(
        self,
        db_manager: DatabaseManager,
        sample_topic_id: str,
    ):
        """検索または作成."""
        with db_manager.get_session() as session:
            repo = TopicProgressRepository(session)

            # 存在しない場合は作成
            progress = repo.find_or_create(sample_topic_id)
            assert progress is not None
            assert progress.topic_id == sample_topic_id
            assert progress.mastery_level == 0

    def test_update_progress(
        self,
        db_manager: DatabaseManager,
        sample_topic_id: str,
    ):
        """進捗更新."""
        with db_manager.get_session() as session:
            repo = TopicProgressRepository(session)

            # 正解を記録
            progress = repo.update_progress(sample_topic_id, is_correct=True)
            assert progress.correct_count == 1
            assert progress.total_count == 1
            assert progress.mastery_level > 0

            # 不正解を記録
            progress = repo.update_progress(sample_topic_id, is_correct=False)
            assert progress.correct_count == 1
            assert progress.total_count == 2

    def test_find_below_mastery(
        self,
        db_manager: DatabaseManager,
        sample_topic_id: str,
    ):
        """習熟度が低いトピックを検索."""
        with db_manager.get_session() as session:
            repo = TopicProgressRepository(session)

            # 進捗を作成（習熟度0）
            repo.find_or_create(sample_topic_id)

            # 閾値50以下を検索
            weak_topics = repo.find_below_mastery(threshold=50)
            assert len(weak_topics) >= 1


# ============================
# LearningSessionRepository Tests
# ============================


class TestLearningSessionRepository:
    """LearningSessionRepositoryのテスト."""

    def test_start_session(
        self,
        db_manager: DatabaseManager,
        sample_document_id: str,
    ):
        """セッション開始."""
        with db_manager.get_session() as session:
            repo = LearningSessionRepository(session)

            ls = repo.start_session(
                document_id=sample_document_id,
                mode=SessionMode.LEARNING,
            )

            assert ls is not None
            assert ls.status == SessionStatus.ACTIVE
            assert ls.document_id == sample_document_id

    def test_end_session(
        self,
        db_manager: DatabaseManager,
        sample_document_id: str,
    ):
        """セッション終了."""
        with db_manager.get_session() as session:
            repo = LearningSessionRepository(session)

            # 開始
            ls = repo.start_session(document_id=sample_document_id)

            # 終了
            ended = repo.end_session(ls.id)
            assert ended is not None
            assert ended.status == SessionStatus.COMPLETED
            assert ended.ended_at is not None
            assert ended.total_time_seconds is not None

    def test_find_active_session(
        self,
        db_manager: DatabaseManager,
        sample_document_id: str,
    ):
        """アクティブセッション検索."""
        with db_manager.get_session() as session:
            repo = LearningSessionRepository(session)

            # アクティブセッションを作成
            ls = repo.start_session(document_id=sample_document_id)

            # 検索
            active = repo.find_active_session(document_id=sample_document_id)
            assert active is not None
            assert active.id == ls.id

    def test_get_statistics(
        self,
        db_manager: DatabaseManager,
        sample_document_id: str,
    ):
        """統計情報取得."""
        with db_manager.get_session() as session:
            repo = LearningSessionRepository(session)

            # セッションを作成して終了
            ls = repo.start_session(document_id=sample_document_id)
            repo.end_session(ls.id)

            # 統計を取得
            stats = repo.get_statistics(document_id=sample_document_id)
            assert stats["total_sessions"] >= 1
            assert stats["completed_sessions"] >= 1


# ============================
# QuizAttemptRepository Tests
# ============================


class TestQuizAttemptRepository:
    """QuizAttemptRepositoryのテスト."""

    def test_create_and_find(
        self,
        db_manager: DatabaseManager,
        sample_document_id: str,
    ):
        """作成と検索."""
        with db_manager.get_session() as session:
            quiz_repo = QuizRepository(session)
            session_repo = LearningSessionRepository(session)
            attempt_repo = QuizAttemptRepository(session)

            # クイズとセッションを作成
            quiz = quiz_repo.create(
                Quiz(
                    document_id=sample_document_id,
                    question="Test?",
                    correct_answer="Yes",
                )
            )
            ls = session_repo.start_session(document_id=sample_document_id)

            # 回答を作成
            attempt = QuizAttempt(
                quiz_id=quiz.id,
                session_id=ls.id,
                user_answer="Yes",
                is_correct=True,
            )
            created = attempt_repo.create(attempt)

            # セッションIDで検索
            attempts = attempt_repo.find_by_session_id(ls.id)
            assert len(attempts) >= 1
            assert any(a.id == created.id for a in attempts)

    def test_get_statistics_by_session(
        self,
        db_manager: DatabaseManager,
        sample_document_id: str,
    ):
        """セッション統計."""
        with db_manager.get_session() as session:
            quiz_repo = QuizRepository(session)
            session_repo = LearningSessionRepository(session)
            attempt_repo = QuizAttemptRepository(session)

            # クイズとセッションを作成
            quiz = quiz_repo.create(
                Quiz(
                    document_id=sample_document_id,
                    question="Test?",
                    correct_answer="Yes",
                )
            )
            ls = session_repo.start_session(document_id=sample_document_id)

            # 回答を作成（2正解、1不正解）
            for is_correct in [True, True, False]:
                attempt_repo.create(
                    QuizAttempt(
                        quiz_id=quiz.id,
                        session_id=ls.id,
                        user_answer="Answer",
                        is_correct=is_correct,
                    )
                )

            # 統計を取得
            stats = attempt_repo.get_statistics_by_session(ls.id)
            assert stats["total"] == 3
            assert stats["correct"] == 2
            assert stats["incorrect"] == 1
