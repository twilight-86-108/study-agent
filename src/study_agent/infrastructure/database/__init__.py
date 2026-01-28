"""データベースモジュール.

SQLiteデータベースとの連携機能を提供する。
- DatabaseManager: 接続管理
- models: SQLModelモデル定義
- repositories: リポジトリパターン実装
"""

from study_agent.infrastructure.database.connection import (
    DatabaseManager,
    get_database_manager,
    set_database_manager,
)
from study_agent.infrastructure.database.models import (
    Chapter,
    Chunk,
    Document,
    FileType,
    LearningSession,
    Quiz,
    QuizAttempt,
    QuizType,
    SessionMode,
    SessionStatus,
    Topic,
    TopicProgress,
    UserSetting,
)
from study_agent.infrastructure.database.repositories import (
    BaseRepository,
    ChapterRepository,
    ChunkRepository,
    DocumentRepository,
    LearningSessionRepository,
    QuizAttemptRepository,
    QuizRepository,
    TopicProgressRepository,
    TopicRepository,
)

__all__ = [
    # Connection
    "DatabaseManager",
    "get_database_manager",
    "set_database_manager",
    # Models
    "Document",
    "Chapter",
    "Topic",
    "Chunk",
    "Quiz",
    "QuizAttempt",
    "TopicProgress",
    "LearningSession",
    "UserSetting",
    # Enums
    "FileType",
    "QuizType",
    "SessionMode",
    "SessionStatus",
    # Repositories
    "BaseRepository",
    "DocumentRepository",
    "ChapterRepository",
    "TopicRepository",
    "ChunkRepository",
    "QuizRepository",
    "QuizAttemptRepository",
    "TopicProgressRepository",
    "LearningSessionRepository",
]
