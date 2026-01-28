"""Domain Models.

ビジネスロジックで使用するデータモデル。
インフラ層（SQLModelモデル）とは独立した純粋なドメインモデル。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from study_agent.domain.enums import (
    Difficulty,
    FileType,
    MasteryLevel,
    QuizType,
    SessionMode,
    SessionStatus,
)


def _utcnow() -> datetime:
    """UTC現在時刻を取得."""
    return datetime.now(timezone.utc)


# =============================================================================
# Document Models
# =============================================================================


@dataclass
class Document:
    """ドキュメント.

    学習対象のドキュメント（PDF、Markdown、テキスト）。

    Attributes:
        id: ドキュメントID（UUID）
        title: タイトル
        file_path: ファイルパス
        file_type: ファイル形式
        total_pages: 総ページ数（PDFの場合）
        description: 説明
        created_at: 作成日時
        updated_at: 更新日時
        chapters: 章リスト
        topics: トピックリスト
    """

    id: str
    title: str
    file_path: str
    file_type: FileType
    total_pages: int | None = None
    description: str | None = None
    created_at: datetime = field(default_factory=_utcnow)
    updated_at: datetime = field(default_factory=_utcnow)
    chapters: list["Chapter"] = field(default_factory=list)
    topics: list["Topic"] = field(default_factory=list)

    def __post_init__(self) -> None:
        """バリデーション."""
        if not self.title.strip():
            raise ValueError("Document title cannot be empty")
        if not self.file_path.strip():
            raise ValueError("Document file_path cannot be empty")

    @property
    def chapter_count(self) -> int:
        """章数."""
        return len(self.chapters)

    @property
    def topic_count(self) -> int:
        """トピック数."""
        return len(self.topics)


@dataclass
class Chapter:
    """章.

    ドキュメント内の章（セクション）。

    Attributes:
        id: 章ID（UUID）
        document_id: 所属するドキュメントのID
        title: 章タイトル
        order_index: 表示順序（0始まり）
        page_start: 開始ページ
        page_end: 終了ページ
        created_at: 作成日時
        topics: この章に属するトピックリスト
    """

    id: str
    document_id: str
    title: str
    order_index: int
    page_start: int | None = None
    page_end: int | None = None
    created_at: datetime = field(default_factory=_utcnow)
    topics: list["Topic"] = field(default_factory=list)

    def __post_init__(self) -> None:
        """バリデーション."""
        if not self.title.strip():
            raise ValueError("Chapter title cannot be empty")
        if self.order_index < 0:
            raise ValueError("order_index must be non-negative")


@dataclass
class Topic:
    """トピック.

    学習対象となるトピック（概念、用語）。

    Attributes:
        id: トピックID（UUID）
        document_id: 所属するドキュメントのID
        title: トピックタイトル
        order_index: 表示順序（0始まり）
        chapter_id: 所属する章のID（オプション）
        description: 説明
        created_at: 作成日時
        progress: 学習進捗（関連データ）
    """

    id: str
    document_id: str
    title: str
    order_index: int
    chapter_id: str | None = None
    description: str | None = None
    created_at: datetime = field(default_factory=_utcnow)
    progress: "TopicProgress | None" = None

    def __post_init__(self) -> None:
        """バリデーション."""
        if not self.title.strip():
            raise ValueError("Topic title cannot be empty")
        if self.order_index < 0:
            raise ValueError("order_index must be non-negative")


@dataclass
class Chunk:
    """RAG用チャンク.

    ドキュメントから分割されたテキストチャンク。
    ベクトルDBに保存され、RAG検索に使用される。

    Attributes:
        id: チャンクID（UUID）
        document_id: 所属するドキュメントのID
        content: テキスト内容
        chunk_index: ドキュメント内でのインデックス
        page_number: ページ番号（PDF等の場合）
        embedding_id: VectorDB内でのembedding ID
        metadata: 追加メタデータ
        created_at: 作成日時
    """

    id: str
    document_id: str
    content: str
    chunk_index: int
    page_number: int | None = None
    embedding_id: str | None = None
    metadata: dict[str, Any] | None = None
    created_at: datetime = field(default_factory=_utcnow)

    def __post_init__(self) -> None:
        """バリデーション."""
        if not self.content or not self.content.strip():
            raise ValueError("Chunk content cannot be empty")
        if self.chunk_index < 0:
            raise ValueError("chunk_index must be non-negative")

    @property
    def char_count(self) -> int:
        """文字数."""
        return len(self.content)

    @property
    def word_count(self) -> int:
        """単語数（空白区切り）."""
        return len(self.content.split())


# =============================================================================
# Quiz Models
# =============================================================================


@dataclass
class Quiz:
    """クイズ.

    学習確認用のクイズ問題。

    Attributes:
        id: クイズID（UUID）
        document_id: 関連ドキュメントのID
        topic_id: 関連トピックのID（オプション）
        question: 問題文
        correct_answer: 正解
        quiz_type: クイズ形式
        difficulty: 難易度
        options: 選択肢（選択式の場合）
        explanation: 解説
        metadata: 追加メタデータ
        created_at: 作成日時
    """

    id: str
    document_id: str
    question: str
    correct_answer: str
    quiz_type: QuizType = QuizType.MULTIPLE_CHOICE
    difficulty: Difficulty = Difficulty.MEDIUM
    topic_id: str | None = None
    options: dict[str, str] | None = None  # {"A": "選択肢1", "B": "選択肢2", ...}
    explanation: str | None = None
    metadata: dict[str, Any] | None = None
    created_at: datetime = field(default_factory=_utcnow)

    def __post_init__(self) -> None:
        """バリデーション."""
        if not self.question.strip():
            raise ValueError("Quiz question cannot be empty")
        if not self.correct_answer.strip():
            raise ValueError("Quiz correct_answer cannot be empty")
        if self.quiz_type == QuizType.MULTIPLE_CHOICE and not self.options:
            raise ValueError("Multiple choice quiz must have options")

    def is_correct(self, answer: str) -> bool:
        """回答が正解かどうかを判定.

        Args:
            answer: ユーザーの回答

        Returns:
            正解の場合True
        """
        # 大文字小文字を無視して比較
        return answer.strip().lower() == self.correct_answer.strip().lower()


@dataclass
class QuizAttempt:
    """クイズ回答.

    ユーザーのクイズ回答記録。

    Attributes:
        id: 回答ID（UUID）
        quiz_id: クイズID
        session_id: 学習セッションID
        user_answer: ユーザーの回答
        is_correct: 正解かどうか
        score: スコア（0-100、記述式用）
        feedback: フィードバック
        answered_at: 回答日時
    """

    id: str
    quiz_id: str
    session_id: str
    user_answer: str
    is_correct: bool
    score: int | None = None
    feedback: str | None = None
    answered_at: datetime = field(default_factory=_utcnow)

    def __post_init__(self) -> None:
        """バリデーション."""
        if self.score is not None and (self.score < 0 or self.score > 100):
            raise ValueError("Score must be between 0 and 100")


# =============================================================================
# Progress Models
# =============================================================================


@dataclass
class TopicProgress:
    """トピック進捗.

    トピックごとの学習進捗。

    Attributes:
        id: 進捗ID（UUID）
        topic_id: トピックID
        study_count: 学習回数
        correct_count: 正答数
        total_count: 回答総数
        mastery_level: 習熟度（0-100）
        last_studied_at: 最終学習日時
        created_at: 作成日時
        updated_at: 更新日時
    """

    id: str
    topic_id: str
    study_count: int = 0
    correct_count: int = 0
    total_count: int = 0
    mastery_level: int = 0
    last_studied_at: datetime | None = None
    created_at: datetime = field(default_factory=_utcnow)
    updated_at: datetime = field(default_factory=_utcnow)

    def __post_init__(self) -> None:
        """バリデーション."""
        if self.mastery_level < 0 or self.mastery_level > 100:
            raise ValueError("mastery_level must be between 0 and 100")
        if self.correct_count > self.total_count:
            raise ValueError("correct_count cannot exceed total_count")

    @property
    def accuracy_rate(self) -> float:
        """正答率（0.0-1.0）."""
        if self.total_count == 0:
            return 0.0
        return self.correct_count / self.total_count

    @property
    def mastery_status(self) -> MasteryLevel:
        """習熟度ステータス."""
        return MasteryLevel.from_score(self.mastery_level)

    def calculate_mastery(self) -> int:
        """習熟度を計算.

        計算式: 正答率×70 + min(学習回数×5, 30)

        Returns:
            習熟度（0-100）
        """
        accuracy_score = self.accuracy_rate * 70
        experience_bonus = min(self.study_count * 5, 30)
        return min(100, int(accuracy_score + experience_bonus))


@dataclass
class LearningSession:
    """学習セッション.

    ユーザーの学習セッション。

    Attributes:
        id: セッションID（UUID）
        document_id: 学習対象ドキュメントのID
        mode: セッションモード
        status: セッション状態
        started_at: 開始日時
        ended_at: 終了日時
        duration_seconds: 学習時間（秒）
        topics_studied: 学習したトピック数
        quizzes_completed: 完了したクイズ数
        correct_answers: 正答数
    """

    id: str
    document_id: str
    mode: SessionMode = SessionMode.LEARNING
    status: SessionStatus = SessionStatus.ACTIVE
    started_at: datetime = field(default_factory=_utcnow)
    ended_at: datetime | None = None
    duration_seconds: int | None = None
    topics_studied: int = 0
    quizzes_completed: int = 0
    correct_answers: int = 0

    @property
    def is_active(self) -> bool:
        """アクティブかどうか."""
        return self.status == SessionStatus.ACTIVE

    @property
    def accuracy_rate(self) -> float:
        """正答率."""
        if self.quizzes_completed == 0:
            return 0.0
        return self.correct_answers / self.quizzes_completed


# =============================================================================
# User Settings
# =============================================================================


@dataclass
class UserSetting:
    """ユーザー設定.

    ユーザーの個人設定。

    Attributes:
        id: 設定ID（UUID）
        key: 設定キー
        value: 設定値（JSON文字列）
        created_at: 作成日時
        updated_at: 更新日時
    """

    id: str
    key: str
    value: str
    created_at: datetime = field(default_factory=_utcnow)
    updated_at: datetime = field(default_factory=_utcnow)

    def __post_init__(self) -> None:
        """バリデーション."""
        if not self.key.strip():
            raise ValueError("Setting key cannot be empty")
