"""Agent state definition for LangGraph.

LangGraphワークフローで共有されるエージェント状態を定義。
TypedDictを使用して、各エージェントが読み書きするフィールドを型安全に管理。

Annotatedフィールド:
    - source_chunks: 検索で見つかったチャンクIDが累積
    - messages: 会話履歴が累積

Example:
    >>> from study_agent.agents.state import AgentState
    >>> state: AgentState = {
    ...     "user_query": "EC2について教えて",
    ...     "session_id": "session-123",
    ... }
"""

from __future__ import annotations

from operator import add
from typing import Annotated, Any, TypedDict

from study_agent.domain import Intent, Quiz, QuizEvaluation


class AgentState(TypedDict, total=False):
    """LangGraphワークフローで共有されるエージェント状態.

    各エージェントは必要なフィールドを読み書きして状態を更新する。
    total=False により、すべてのフィールドがオプショナルになる。

    Attributes:
        user_query: ユーザーの入力クエリ
        session_id: 現在のセッションID
        document_id: 対象ドキュメントID（オプション）

        intent: RouterAgentが判定した意図
        confidence: 意図判定の確信度（0.0-1.0）
        extracted_topic: クエリから抽出されたトピック

        context: RAG検索で取得したコンテキスト
        source_chunks: ソースチャンクIDのリスト（累積）

        plan: PlannerAgentが生成した学習計画
        recommended_topic: 推薦されるトピック

        explanation: TutorAgentが生成した説明

        quiz: QuizGeneratorAgentが生成したクイズ

        evaluation: EvaluatorAgentが生成した評価結果

        response: 最終的なユーザーへの応答
        should_continue: 対話を続けるかどうか

        error: エラーメッセージ
        error_code: エラーコード

        messages: 会話履歴（累積）
    """

    # === Input (Required) ===
    user_query: str
    session_id: str

    # === Input (Optional) ===
    document_id: str | None

    # === Router Output ===
    intent: Intent
    confidence: float
    extracted_topic: str | None

    # === RAG Search Results ===
    context: str
    source_chunks: Annotated[list[str], add]

    # === Planner Output ===
    plan: dict[str, Any] | None
    recommended_topic: str | None

    # === Tutor Output ===
    explanation: str | None

    # === Quiz Output ===
    quiz: Quiz | None

    # === Evaluator Output ===
    evaluation: QuizEvaluation | None

    # === Final Response ===
    response: str
    should_continue: bool

    # === Error Information ===
    error: str | None
    error_code: str | None

    # === Message History (Accumulates) ===
    messages: Annotated[list[dict[str, Any]], add]


def create_initial_state(
    user_query: str,
    session_id: str,
    document_id: str | None = None,
    quiz: Quiz | None = None,
) -> AgentState:
    """初期状態を作成する.

    Args:
        user_query: ユーザーの入力
        session_id: セッションID
        document_id: ドキュメントID（オプション）
        quiz: アクティブなクイズ（オプション）

    Returns:
        AgentState: 初期化された状態
    """
    return AgentState(
        user_query=user_query,
        session_id=session_id,
        document_id=document_id,
        quiz=quiz,
        messages=[],
        source_chunks=[],
        should_continue=True,
    )
