"""リポジトリモジュール.

データアクセス層のリポジトリパターン実装を提供する。
"""

from study_agent.infrastructure.database.repositories.base import BaseRepository
from study_agent.infrastructure.database.repositories.document_repo import (
    DocumentRepository,
)
from study_agent.infrastructure.database.repositories.chapter_repo import (
    ChapterRepository,
)
from study_agent.infrastructure.database.repositories.topic_repo import (
    TopicRepository,
)
from study_agent.infrastructure.database.repositories.chunk_repo import (
    ChunkRepository,
)
from study_agent.infrastructure.database.repositories.quiz_repo import (
    QuizRepository,
)
from study_agent.infrastructure.database.repositories.attempt_repo import (
    QuizAttemptRepository,
)
from study_agent.infrastructure.database.repositories.progress_repo import (
    TopicProgressRepository,
)
from study_agent.infrastructure.database.repositories.session_repo import (
    LearningSessionRepository,
)

__all__ = [
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
