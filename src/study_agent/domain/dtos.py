"""Service DTOs (Data Transfer Objects).

サービス層で使用するデータ転送オブジェクト。
サービス間のデータ受け渡しや、サービスの戻り値として使用。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from study_agent.domain.models import (
    Chapter,
    Chunk,
    Document,
    Quiz,
    QuizAttempt,
    Topic,
    TopicProgress,
)


# =============================================================================
# Document Service DTOs
# =============================================================================


@dataclass
class LoadDocumentResult:
    """ドキュメント読み込み結果.

    DocumentServiceのload_documentメソッドの戻り値。

    Attributes:
        document: 読み込まれたドキュメント
        chapters: 抽出された章
        topics: 抽出されたトピック
        chunks_count: 作成されたチャンク数
        embeddings_created: 埋め込みが作成されたか
    """

    document: Document
    chapters: list[Chapter]
    topics: list[Topic]
    chunks_count: int
    embeddings_created: bool = False

    @property
    def summary(self) -> str:
        """読み込み結果のサマリー."""
        return (
            f"Loaded: {self.document.title} "
            f"({len(self.chapters)} chapters, "
            f"{len(self.topics)} topics, "
            f"{self.chunks_count} chunks)"
        )


@dataclass
class DocumentStructure:
    """ドキュメント構造.

    ドキュメントの章・トピック構造を表す。

    Attributes:
        document: ドキュメント情報
        chapters: 章リスト（トピック含む）
        orphan_topics: 章に属さないトピック
    """

    document: Document
    chapters: list[Chapter]
    orphan_topics: list[Topic] = field(default_factory=list)


# =============================================================================
# Search Service DTOs
# =============================================================================


@dataclass
class SearchResult:
    """検索結果.

    RAG検索の結果を表す。

    Attributes:
        chunks: マッチしたチャンク
        scores: 各チャンクのスコア（類似度）
        query: 検索クエリ
        total_results: 総結果数
        search_time_ms: 検索時間（ミリ秒）
    """

    chunks: list[Chunk]
    scores: list[float]
    query: str
    total_results: int = 0
    search_time_ms: float = 0.0

    def __post_init__(self) -> None:
        """バリデーション."""
        if len(self.chunks) != len(self.scores):
            raise ValueError("chunks and scores must have same length")
        self.total_results = len(self.chunks)

    @property
    def best_match(self) -> Chunk | None:
        """最もスコアの高いチャンク."""
        if not self.chunks:
            return None
        return self.chunks[0]

    @property
    def context_text(self) -> str:
        """チャンクを結合したコンテキストテキスト."""
        return "\n\n".join(chunk.content for chunk in self.chunks)

    def get_chunks_above_threshold(self, threshold: float = 0.5) -> list[Chunk]:
        """閾値以上のスコアを持つチャンクを取得.

        Args:
            threshold: スコア閾値

        Returns:
            閾値以上のチャンクリスト
        """
        return [
            chunk
            for chunk, score in zip(self.chunks, self.scores)
            if score >= threshold
        ]


@dataclass
class SearchContext:
    """検索コンテキスト.

    LLMに渡すための検索結果コンテキスト。

    Attributes:
        context_text: 結合されたコンテキストテキスト
        source_chunks: ソースチャンク情報
        relevance_scores: 関連度スコア
    """

    context_text: str
    source_chunks: list[dict[str, Any]]
    relevance_scores: list[float]


# =============================================================================
# Quiz Service DTOs
# =============================================================================


@dataclass
class GeneratedQuiz:
    """生成されたクイズ.

    QuizServiceのgenerate_quizメソッドの戻り値。

    Attributes:
        quiz: 生成されたクイズ
        context_used: 生成に使用したコンテキスト
        generation_time_ms: 生成時間（ミリ秒）
    """

    quiz: Quiz
    context_used: str | None = None
    generation_time_ms: float = 0.0


@dataclass
class QuizEvaluation:
    """クイズ評価結果.

    ユーザー回答の評価結果。

    Attributes:
        attempt: クイズ回答記録
        is_correct: 正解かどうか
        score: スコア（0-100）
        feedback: フィードバックメッセージ
        correct_answer: 正解（不正解時に表示）
        explanation: 解説
    """

    attempt: QuizAttempt
    is_correct: bool
    score: int
    feedback: str
    correct_answer: str | None = None
    explanation: str | None = None


@dataclass
class QuizSessionStats:
    """クイズセッション統計.

    セッション中のクイズ統計。

    Attributes:
        total_questions: 出題数
        correct_answers: 正答数
        incorrect_answers: 誤答数
        accuracy_rate: 正答率
        average_score: 平均スコア
        by_topic: トピック別統計
    """

    total_questions: int = 0
    correct_answers: int = 0
    incorrect_answers: int = 0
    accuracy_rate: float = 0.0
    average_score: float = 0.0
    by_topic: dict[str, dict[str, int]] = field(default_factory=dict)

    def update(self, is_correct: bool, score: int, topic_id: str | None = None) -> None:
        """統計を更新.

        Args:
            is_correct: 正解かどうか
            score: スコア
            topic_id: トピックID（オプション）
        """
        self.total_questions += 1
        if is_correct:
            self.correct_answers += 1
        else:
            self.incorrect_answers += 1

        self.accuracy_rate = self.correct_answers / self.total_questions
        # 移動平均でスコアを更新
        self.average_score = (
            self.average_score * (self.total_questions - 1) + score
        ) / self.total_questions

        if topic_id:
            if topic_id not in self.by_topic:
                self.by_topic[topic_id] = {"correct": 0, "total": 0}
            self.by_topic[topic_id]["total"] += 1
            if is_correct:
                self.by_topic[topic_id]["correct"] += 1


# =============================================================================
# Progress Service DTOs
# =============================================================================


@dataclass
class DocumentProgressSummary:
    """ドキュメント進捗サマリー.

    ドキュメント全体の学習進捗。

    Attributes:
        document_id: ドキュメントID
        document_title: ドキュメントタイトル
        total_topics: 総トピック数
        studied_topics: 学習済みトピック数
        mastered_topics: 習得済みトピック数（習熟度80以上）
        average_mastery: 平均習熟度
        total_study_time_seconds: 総学習時間（秒）
        weak_topics: 弱点トピック（習熟度50未満）
        last_studied_at: 最終学習日時
    """

    document_id: str
    document_title: str
    total_topics: int
    studied_topics: int = 0
    mastered_topics: int = 0
    average_mastery: float = 0.0
    total_study_time_seconds: int = 0
    weak_topics: list[Topic] = field(default_factory=list)
    last_studied_at: datetime | None = None

    @property
    def completion_rate(self) -> float:
        """完了率（学習済み/総トピック）."""
        if self.total_topics == 0:
            return 0.0
        return self.studied_topics / self.total_topics

    @property
    def mastery_rate(self) -> float:
        """習得率（習得済み/総トピック）."""
        if self.total_topics == 0:
            return 0.0
        return self.mastered_topics / self.total_topics


@dataclass
class TopicProgressDetail:
    """トピック進捗詳細.

    トピックの詳細な進捗情報。

    Attributes:
        topic: トピック情報
        progress: 進捗情報
        accuracy_rate: 正答率
        recent_attempts: 最近の回答履歴
        recommended_action: 推奨アクション（復習、次へ進む等）
    """

    topic: Topic
    progress: TopicProgress
    accuracy_rate: float = 0.0
    recent_attempts: list[QuizAttempt] = field(default_factory=list)
    recommended_action: str = "study"  # study, review, advance


@dataclass
class LearningRecommendation:
    """学習推奨.

    次に学習すべきトピックの推奨。

    Attributes:
        topic: 推奨トピック
        reason: 推奨理由
        priority: 優先度（1-5）
        estimated_time_minutes: 推定学習時間（分）
    """

    topic: Topic
    reason: str
    priority: int = 3
    estimated_time_minutes: int = 15


@dataclass
class StudyPlan:
    """学習プラン.

    複数トピックの学習計画。

    Attributes:
        recommendations: 推奨トピックリスト
        total_estimated_time_minutes: 総推定学習時間（分）
        focus_areas: 重点エリア（弱点等）
        generated_at: 生成日時
    """

    recommendations: list[LearningRecommendation]
    total_estimated_time_minutes: int = 0
    focus_areas: list[str] = field(default_factory=list)
    generated_at: datetime = field(default_factory=datetime.utcnow)

    def __post_init__(self) -> None:
        """総時間を計算."""
        self.total_estimated_time_minutes = sum(
            r.estimated_time_minutes for r in self.recommendations
        )


# =============================================================================
# Agent DTOs
# =============================================================================


@dataclass
class AgentResponse:
    """エージェント応答.

    エージェントの応答を表す。

    Attributes:
        content: 応答内容
        agent_name: エージェント名
        confidence: 信頼度（0.0-1.0）
        metadata: 追加メタデータ
        processing_time_ms: 処理時間（ミリ秒）
    """

    content: str
    agent_name: str
    confidence: float = 1.0
    metadata: dict[str, Any] = field(default_factory=dict)
    processing_time_ms: float = 0.0


@dataclass
class RouterResult:
    """ルーター結果.

    RouterAgentの判定結果。

    Attributes:
        intent: 判定された意図
        confidence: 信頼度（0.0-1.0）
        entities: 抽出されたエンティティ（トピック名等）
        suggested_action: 推奨アクション
    """

    from study_agent.domain.enums import Intent

    intent: Intent
    confidence: float
    entities: dict[str, str] = field(default_factory=dict)
    suggested_action: str | None = None
