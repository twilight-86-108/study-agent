"""SQLModelデータベースモデル定義.

データベーステーブルに対応するSQLModelモデルを定義する。
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from sqlmodel import Field, SQLModel


def generate_uuid() -> str:
    """UUID v4を生成する."""
    return str(uuid.uuid4())


def utcnow() -> datetime:
    """現在のUTC時刻を取得する."""
    return datetime.now(timezone.utc)


class FileType(str, Enum):
    """ファイルタイプ."""

    PDF = "pdf"
    MARKDOWN = "md"
    TEXT = "txt"


class QuizType(str, Enum):
    """クイズタイプ."""

    OPEN = "open"
    MULTIPLE_CHOICE = "multiple_choice"
    TRUE_FALSE = "true_false"


class SessionMode(str, Enum):
    """セッションモード."""

    LEARNING = "learning"
    QUIZ = "quiz"
    REVIEW = "review"


class SessionStatus(str, Enum):
    """セッションステータス."""

    ACTIVE = "active"
    COMPLETED = "completed"
    ABANDONED = "abandoned"


class Document(SQLModel, table=True):
    """ドキュメントモデル."""

    __tablename__ = "documents"

    id: str = Field(default_factory=generate_uuid, primary_key=True)
    title: str = Field(index=True)
    file_path: str = Field(unique=True, index=True)
    file_type: FileType
    total_pages: Optional[int] = None
    description: Optional[str] = None
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


class Chapter(SQLModel, table=True):
    """章モデル."""

    __tablename__ = "chapters"

    id: str = Field(default_factory=generate_uuid, primary_key=True)
    document_id: str = Field(foreign_key="documents.id", index=True)
    title: str
    order_index: int
    page_start: Optional[int] = None
    page_end: Optional[int] = None
    created_at: datetime = Field(default_factory=utcnow)


class Topic(SQLModel, table=True):
    """トピックモデル."""

    __tablename__ = "topics"

    id: str = Field(default_factory=generate_uuid, primary_key=True)
    document_id: str = Field(foreign_key="documents.id", index=True)
    chapter_id: Optional[str] = Field(
        foreign_key="chapters.id", index=True, default=None
    )
    title: str = Field(index=True)
    description: Optional[str] = None
    order_index: int = 0
    created_at: datetime = Field(default_factory=utcnow)


class Chunk(SQLModel, table=True):
    """チャンクモデル."""

    __tablename__ = "chunks"

    id: str = Field(default_factory=generate_uuid, primary_key=True)
    document_id: str = Field(foreign_key="documents.id", index=True)
    content: str
    chunk_index: int
    page_number: Optional[int] = None
    embedding_id: Optional[str] = Field(default=None, index=True)
    metadata_json: Optional[str] = None
    created_at: datetime = Field(default_factory=utcnow)


class Quiz(SQLModel, table=True):
    """クイズモデル."""

    __tablename__ = "quizzes"

    id: str = Field(default_factory=generate_uuid, primary_key=True)
    document_id: Optional[str] = Field(
        foreign_key="documents.id", index=True, default=None
    )
    topic_id: Optional[str] = Field(foreign_key="topics.id", index=True, default=None)
    question: str
    correct_answer: str
    options_json: Optional[str] = None
    explanation: Optional[str] = None
    difficulty: int = Field(default=3, ge=1, le=5)
    quiz_type: QuizType = QuizType.OPEN
    created_at: datetime = Field(default_factory=utcnow)


class QuizAttempt(SQLModel, table=True):
    """クイズ回答モデル."""

    __tablename__ = "quiz_attempts"

    id: str = Field(default_factory=generate_uuid, primary_key=True)
    quiz_id: str = Field(foreign_key="quizzes.id", index=True)
    session_id: str = Field(foreign_key="learning_sessions.id", index=True)
    user_answer: str
    is_correct: bool
    score: Optional[int] = Field(default=None, ge=0, le=100)
    feedback: Optional[str] = None
    answered_at: datetime = Field(default_factory=utcnow)


class TopicProgress(SQLModel, table=True):
    """トピック進捗モデル."""

    __tablename__ = "topic_progress"

    id: str = Field(default_factory=generate_uuid, primary_key=True)
    topic_id: str = Field(foreign_key="topics.id", unique=True, index=True)
    study_count: int = 0
    correct_count: int = 0
    total_count: int = 0
    mastery_level: int = Field(default=0, ge=0, le=100)
    last_studied_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


class LearningSession(SQLModel, table=True):
    """学習セッションモデル."""

    __tablename__ = "learning_sessions"

    id: str = Field(default_factory=generate_uuid, primary_key=True)
    document_id: Optional[str] = Field(
        foreign_key="documents.id", index=True, default=None
    )
    mode: SessionMode = SessionMode.LEARNING
    status: SessionStatus = SessionStatus.ACTIVE
    started_at: datetime = Field(default_factory=utcnow)
    ended_at: Optional[datetime] = None
    total_time_seconds: Optional[int] = None
    created_at: datetime = Field(default_factory=utcnow)


class UserSetting(SQLModel, table=True):
    """ユーザー設定モデル."""

    __tablename__ = "user_settings"

    id: str = Field(default_factory=generate_uuid, primary_key=True)
    key: str = Field(unique=True, index=True)
    value: str
    updated_at: datetime = Field(default_factory=utcnow)
