"""Planner agent for learning plan generation.

学習計画の立案、次のトピックの推薦を行うエージェント。
進捗サービスを使用して、学習者の状態に基づいた計画を生成する。

Example:
    >>> planner = PlannerAgent(llm_client, progress_service)
    >>> state = await planner.execute(state)
    >>> print(state["recommended_topic"])
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from study_agent.agents.base import BaseAgent
from study_agent.agents.state import AgentState
from study_agent.domain import Intent

if TYPE_CHECKING:
    from study_agent.infrastructure.llm import BaseLLMClient
    from study_agent.services import ProgressService, DocumentService

logger = logging.getLogger(__name__)


# 学習計画生成用プロンプト
PLANNER_PROMPT = """あなたは学習支援アプリケーションの学習プランナーです。

## 学習者の進捗状況
{progress_summary}

## 利用可能なトピック
{available_topics}

## ユーザーのリクエスト
{user_request}

## 指示
学習者に最適な次の学習ステップを提案してください。

以下の形式でJSON形式で回答してください：
{{
    "recommended_topic": "推薦するトピック名",
    "action": "explain" | "quiz" | "review",
    "reason": "推薦理由（日本語で簡潔に）",
    "priority_topics": ["優先度の高いトピック1", "トピック2", "トピック3"]
}}

推薦の基準：
1. 未学習のトピックを優先
2. 習熟度の低いトピックを復習
3. 順序を考慮（前のトピックを理解してから次へ）

JSON形式のみで回答してください。"""


class PlannerAgent(BaseAgent):
    """学習計画エージェント.

    学習者の進捗状況に基づいて、
    次に学習すべきトピックを推薦する。

    Attributes:
        llm_client: LLMクライアント
        progress_service: 進捗サービス
        document_service: ドキュメントサービス

    Example:
        >>> planner = PlannerAgent(llm_client, progress_service)
        >>> state["document_id"] = "doc-123"
        >>> state = await planner.execute(state)
    """

    def __init__(
        self,
        llm_client: BaseLLMClient,
        progress_service: ProgressService,
        document_service: DocumentService | None = None,
    ) -> None:
        """初期化.

        Args:
            llm_client: LLMクライアント
            progress_service: 進捗サービス
            document_service: ドキュメントサービス（オプション）
        """
        super().__init__(llm_client, name="PlannerAgent")
        self.progress_service = progress_service
        self.document_service = document_service

    async def execute(self, state: AgentState) -> AgentState:
        """学習計画を生成する.

        Args:
            state: 現在の状態

        Returns:
            計画が設定された状態
        """
        self._log_execution_start(state)

        document_id = state.get("document_id")
        user_query = state.get("user_query", "")
        intent = state.get("intent", Intent.NAVIGATE)

        try:
            # ナビゲーション意図の場合は次/前のトピックを取得
            if intent == Intent.NAVIGATE:
                plan = await self._handle_navigation(document_id, user_query)
            else:
                plan = await self._generate_learning_plan(document_id, user_query)

            state["plan"] = plan
            state["recommended_topic"] = plan.get("recommended_topic")

            # レスポンスを構築
            response = self._format_plan(plan)
            state["response"] = response

            logger.info(f"Generated plan: {plan.get('recommended_topic')}")

        except Exception as e:
            logger.error(f"Failed to generate plan: {e}")
            return self._set_error(state, f"学習計画の生成に失敗しました: {e}")

        self._log_execution_end(state)
        return state

    async def _handle_navigation(
        self,
        document_id: str | None,
        user_query: str,
    ) -> dict[str, Any]:
        """ナビゲーションリクエストを処理する.

        Args:
            document_id: ドキュメントID
            user_query: ユーザークエリ

        Returns:
            ナビゲーション結果
        """
        # "次" or "前" を判定
        is_next = any(word in user_query for word in ["次", "next", "進む"])

        if document_id:
            # 推薦トピックを取得
            recommendation = await self.progress_service.get_recommended_topic(
                document_id
            )

            if recommendation:
                return {
                    "recommended_topic": recommendation.topic.title,
                    "action": "explain",
                    "reason": recommendation.reason,
                    "priority_topics": [],
                }

        return {
            "recommended_topic": None,
            "action": "explain",
            "reason": "次のトピックが見つかりませんでした",
            "priority_topics": [],
        }

    async def _generate_learning_plan(
        self,
        document_id: str | None,
        user_query: str,
    ) -> dict[str, Any]:
        """LLMを使用して学習計画を生成する.

        Args:
            document_id: ドキュメントID
            user_query: ユーザークエリ

        Returns:
            学習計画
        """
        # 進捗サマリーを取得
        progress_summary = "進捗情報なし"
        available_topics = "トピック情報なし"

        if document_id:
            try:
                summary = await self.progress_service.get_document_summary(document_id)
                progress_summary = (
                    f"学習済みトピック: {summary.studied_topics}/{summary.total_topics}\n"
                    f"習得済み: {summary.mastered_topics}\n"
                    f"平均習熟度: {summary.average_mastery:.1f}%"
                )

                if summary.weak_topics:
                    weak_list = ", ".join(t.title for t in summary.weak_topics[:5])
                    progress_summary += f"\n弱点トピック: {weak_list}"

                # トピック一覧を取得
                if self.document_service:
                    topics = await self.document_service.get_topics(document_id)
                    available_topics = "\n".join(f"- {t.title}" for t in topics[:10])
            except Exception as e:
                logger.warning(f"Failed to get progress: {e}")

        # LLMで計画を生成
        schema = {
            "type": "object",
            "properties": {
                "recommended_topic": {"type": ["string", "null"]},
                "action": {
                    "type": "string",
                    "enum": ["explain", "quiz", "review"],
                },
                "reason": {"type": "string"},
                "priority_topics": {
                    "type": "array",
                    "items": {"type": "string"},
                },
            },
            "required": ["action", "reason"],
        }

        prompt = PLANNER_PROMPT.format(
            progress_summary=progress_summary,
            available_topics=available_topics,
            user_request=user_query,
        )

        try:
            result = await self.llm_client.generate_json(prompt, schema)
            return result
        except Exception as e:
            logger.warning(f"LLM planning failed: {e}")
            # フォールバック: 推薦トピックを返す
            if document_id:
                recommendation = await self.progress_service.get_recommended_topic(
                    document_id
                )
                if recommendation:
                    return {
                        "recommended_topic": recommendation.topic.title,
                        "action": "explain",
                        "reason": recommendation.reason,
                        "priority_topics": [],
                    }

            return {
                "recommended_topic": None,
                "action": "explain",
                "reason": "計画を生成できませんでした",
                "priority_topics": [],
            }

    def _format_plan(self, plan: dict[str, Any]) -> str:
        """計画をフォーマットする.

        Args:
            plan: 学習計画

        Returns:
            フォーマットされた文字列
        """
        lines = ["━" * 40, "【学習プラン】", ""]

        recommended = plan.get("recommended_topic")
        if recommended:
            lines.append(f"📚 次のトピック: {recommended}")
        else:
            lines.append("📚 推薦トピックはありません")

        lines.append("")

        action = plan.get("action", "explain")
        action_map = {
            "explain": "説明を読む",
            "quiz": "クイズに挑戦",
            "review": "復習する",
        }
        lines.append(f"💡 アクション: {action_map.get(action, action)}")
        lines.append("")

        reason = plan.get("reason", "")
        if reason:
            lines.append(f"📝 理由: {reason}")
            lines.append("")

        priority_topics = plan.get("priority_topics", [])
        if priority_topics:
            lines.append("🎯 優先トピック:")
            for i, topic in enumerate(priority_topics[:3], 1):
                lines.append(f"  {i}. {topic}")
            lines.append("")

        lines.append("━" * 40)

        return "\n".join(lines)
