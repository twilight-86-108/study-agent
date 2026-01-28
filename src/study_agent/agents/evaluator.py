"""Evaluator agent for quiz answers.

クイズの回答を評価し、フィードバックを生成するエージェント。
QuizServiceとProgressServiceを使用して、評価と進捗更新を行う。

Example:
    >>> evaluator = EvaluatorAgent(llm_client, quiz_service, progress_service)
    >>> state = await evaluator.execute(state)
    >>> print(state["evaluation"].feedback)
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from study_agent.agents.base import BaseAgent
from study_agent.agents.state import AgentState

if TYPE_CHECKING:
    from study_agent.infrastructure.llm import BaseLLMClient
    from study_agent.services import QuizService, ProgressService

logger = logging.getLogger(__name__)


class EvaluatorAgent(BaseAgent):
    """回答評価エージェント.

    ユーザーのクイズ回答を評価し、
    フィードバックを生成して進捗を更新する。

    Attributes:
        llm_client: LLMクライアント
        quiz_service: クイズサービス
        progress_service: 進捗サービス

    Example:
        >>> evaluator = EvaluatorAgent(llm_client, quiz_service, progress_service)
        >>> state["quiz"] = quiz
        >>> state["user_query"] = "A"  # ユーザーの回答
        >>> state = await evaluator.execute(state)
    """

    def __init__(
        self,
        llm_client: BaseLLMClient,
        quiz_service: QuizService,
        progress_service: ProgressService,
    ) -> None:
        """初期化.

        Args:
            llm_client: LLMクライアント
            quiz_service: クイズサービス
            progress_service: 進捗サービス
        """
        super().__init__(llm_client, name="EvaluatorAgent")
        self.quiz_service = quiz_service
        self.progress_service = progress_service

    async def execute(self, state: AgentState) -> AgentState:
        """クイズの回答を評価する.

        Args:
            state: 現在の状態

        Returns:
            評価結果が設定された状態
        """
        self._log_execution_start(state)

        quiz = state.get("quiz")
        user_answer = state.get("user_query", "")
        session_id = state.get("session_id", "")

        if not quiz:
            state["response"] = "評価するクイズがありません。クイズを生成してください。"
            state["error"] = "No quiz to evaluate"
            logger.warning("No quiz in state for evaluation")
            return state

        if not user_answer.strip():
            state["response"] = "回答が入力されていません。回答を入力してください。"
            state["error"] = "No answer provided"
            return state

        try:
            # 回答を評価
            evaluation = await self.quiz_service.evaluate_answer(
                quiz=quiz,
                user_answer=user_answer,
                session_id=session_id,
            )

            state["evaluation"] = evaluation

            # 進捗を更新（トピックIDがある場合）
            if quiz.topic_id:
                await self.progress_service.record_quiz_result(
                    topic_id=quiz.topic_id,
                    is_correct=evaluation.is_correct,
                    score=evaluation.score,
                )
                logger.debug(f"Updated progress for topic: {quiz.topic_id}")

            # レスポンスを構築
            response = self._format_evaluation(evaluation)
            state["response"] = response

            # クイズをクリア（次の問題に備える）
            state["quiz"] = None

            logger.info(
                f"Evaluated answer: correct={evaluation.is_correct}, "
                f"score={evaluation.score}"
            )

        except Exception as e:
            logger.error(f"Failed to evaluate answer: {e}")
            return self._set_error(state, f"回答の評価に失敗しました: {e}")

        self._log_execution_end(state)
        return state

    def _format_evaluation(self, evaluation) -> str:
        """評価結果をフォーマットする.

        Args:
            evaluation: 評価結果

        Returns:
            フォーマットされた文字列
        """
        lines = ["━" * 40]

        # 正解/不正解の表示
        if evaluation.is_correct:
            lines.append("🎉 正解！")
        else:
            lines.append("❌ 不正解")

        lines.append("")

        # スコア
        lines.append(f"スコア: {evaluation.score}点")
        lines.append("")

        # 正解
        lines.append(f"【正解】 {evaluation.correct_answer}")
        lines.append("")

        # フィードバック
        if evaluation.feedback:
            lines.append("【フィードバック】")
            lines.append(evaluation.feedback)
            lines.append("")

        # マッチしたポイント/不足しているポイント（記述式の場合）
        if evaluation.matched_points:
            lines.append("【カバーできたポイント】")
            for point in evaluation.matched_points:
                lines.append(f"  ✓ {point}")
            lines.append("")

        if evaluation.missed_points:
            lines.append("【不足しているポイント】")
            for point in evaluation.missed_points:
                lines.append(f"  • {point}")
            lines.append("")

        lines.append("━" * 40)

        return "\n".join(lines)

    def should_execute(self, state: AgentState) -> bool:
        """このエージェントを実行すべきか判定する.

        クイズがある場合のみ実行する。

        Args:
            state: 現在の状態

        Returns:
            クイズがある場合True
        """
        return state.get("quiz") is not None
