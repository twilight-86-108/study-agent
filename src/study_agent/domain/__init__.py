"""Domain module.

ドメインモデル、列挙型、DTOを提供する。

このモジュールはビジネスロジックで使用するデータ構造を定義する。
インフラ層（SQLModel、VectorDB）とは独立した純粋なドメインモデル。

主要コンポーネント:
    - Models: Document, Chapter, Topic, Chunk, Quiz, etc.
    - Enums: FileType, QuizType, Difficulty, Intent, etc.
    - DTOs: LoadDocumentResult, SearchResult, etc.

Example:
    >>> from study_agent.domain import Document, FileType, LoadDocumentResult
    >>>
    >>> doc = Document(
    ...     id="doc-1",
    ...     title="AWS SAA Study Guide",
    ...     file_path="/path/to/file.pdf",
    ...     file_type=FileType.PDF,
    ... )
"""

# Enums
from study_agent.domain.enums import (
    Difficulty,
    FileType,
    Intent,
    MasteryLevel,
    QuizType,
    SessionMode,
    SessionStatus,
)

# Models
from study_agent.domain.models import (
    Chapter,
    Chunk,
    Document,
    LearningSession,
    Quiz,
    QuizAttempt,
    Topic,
    TopicProgress,
    UserSetting,
)

# DTOs
from study_agent.domain.dtos import (
    AgentResponse,
    DocumentProgressSummary,
    DocumentStructure,
    GeneratedQuiz,
    LearningRecommendation,
    LoadDocumentResult,
    QuizEvaluation,
    QuizSessionStats,
    RouterResult,
    SearchContext,
    SearchResult,
    StudyPlan,
    TopicProgressDetail,
)

__all__ = [
    # Enums
    "FileType",
    "QuizType",
    "Difficulty",
    "SessionMode",
    "SessionStatus",
    "Intent",
    "MasteryLevel",
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
    # DTOs
    "LoadDocumentResult",
    "DocumentStructure",
    "SearchResult",
    "SearchContext",
    "GeneratedQuiz",
    "QuizEvaluation",
    "QuizSessionStats",
    "DocumentProgressSummary",
    "TopicProgressDetail",
    "LearningRecommendation",
    "StudyPlan",
    "AgentResponse",
    "RouterResult",
]
