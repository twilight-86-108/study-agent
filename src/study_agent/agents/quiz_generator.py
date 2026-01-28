"""Quiz generator agent.

クイズ（問題）を生成するエージェント。
QuizServiceを使用して、トピックに関する問題を生成する。

Example:
    >>> generator = QuizGeneratorAgent(llm_client, quiz_service)
    >>> state = await generator.execute(state)
    >>> print(state["quiz"].question)
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from study_agent.agents.base import BaseAgent
from study_agent.agents.state import AgentState
from study_agent.domain import QuizType, Difficulty

if TYPE_CHECKING:
    from study_agent.infrastructure.llm import BaseLLMClient
    from study_agent.services import QuizService

logger = logging.getLogger(__name__)


class QuizGeneratorAgent(BaseAgent):
    """クイズ生成エージェント.

    QuizServiceを使用してクイズを生成し、
    ユーザーに提示する形式にフォーマットする。

    Attributes:
        llm_client: LLMクライアント
        quiz_service: クイズサービス
        default_quiz_type: デフォルトのクイズタイプ
        default_difficulty: デフォルトの難易度

    Example:
        >>> generator = QuizGeneratorAgent(llm_client, quiz_service)
        >>> state["extracted_topic"] = "Amazon EC2"
        >>> state = await generator.execute(state)
    """

    def __init__(
        self,
        llm_client: BaseLLMClient,
        quiz_service: QuizService,
        default_quiz_type: QuizType = QuizType.MULTIPLE_CHOICE,
        default_difficulty: Difficulty = Difficulty.MEDIUM,
    ) -> None:
        """初期化.

        Args:
            llm_client: LLMクライアント
            quiz_service: クイズサービス
            default_quiz_type: デフォルトのクイズタイプ
            default_difficulty: デフォルトの難易度
        """
        super().__init__(llm_client, name="QuizGeneratorAgent")
        self.quiz_service = quiz_service
        self.default_quiz_type = default_quiz_type
        self.default_difficulty = default_difficulty

    async def execute(self, state: AgentState) -> AgentState:
        """クイズを生成する.

        Args:
            state: 現在の状態

        Returns:
            クイズが設定された状態
        """
        self._log_execution_start(state)

        topic = state.get("extracted_topic") or state.get("user_query", "")
        document_id = state.get("document_id")

        # クエリからクイズタイプを判定
        quiz_type = self._determine_quiz_type(state.get("user_query", ""))
        difficulty = self._determine_difficulty(state.get("user_query", ""))

        try:
            # クイズを生成
            generated = await self.quiz_service.generate_quiz(
                topic=topic,
                quiz_type=quiz_type,
                difficulty=difficulty,
                document_id=document_id,
                save=True,
            )

            state["quiz"] = generated.quiz
            state["context"] = generated.context_used
            state["source_chunks"] = generated.source_chunks

            # 表示用にフォーマット
            response = self._format_quiz_for_display(generated.quiz)
            state["response"] = response

            logger.info(f"Generated {quiz_type.value} quiz for: {topic}")

        except Exception as e:
            logger.error(f"Failed to generate quiz: {e}")
            return self._set_error(state, f"クイズの生成に失敗しました: {e}")

        self._log_execution_end(state)
        return state

    def _determine_quiz_type(self, query: str) -> QuizType:
        """クエリからクイズタイプを判定する.

        Args:
            query: ユーザークエリ

        Returns:
            クイズタイプ
        """
        query_lower = query.lower()

        if any(word in query_lower for word in ["記述", "自由", "説明", "open"]):
            return QuizType.OPEN
        elif any(word in query_lower for word in ["○×", "まるばつ", "true", "false"]):
            return QuizType.TRUE_FALSE
        else:
            return self.default_quiz_type

    def _determine_difficulty(self, query: str) -> Difficulty:
        """クエリから難易度を判定する.

        Args:
            query: ユーザークエリ

        Returns:
            難易度
        """
        query_lower = query.lower()

        if any(word in query_lower for word in ["簡単", "易しい", "初心者", "easy"]):
            return Difficulty.EASY
        elif any(
            word in query_lower for word in ["難しい", "上級", "エキスパート", "hard"]
        ):
            return Difficulty.HARD
        else:
            return self.default_difficulty

    def _format_quiz_for_display(self, quiz) -> str:
        """クイズを表示用にフォーマットする.

        Args:
            quiz: クイズオブジェクト

        Returns:
            フォーマットされた文字列
        """
        lines = [
            "━" * 40,
            "【問題】",
            "",
            quiz.question,
            "",
        ]

        if quiz.quiz_type == QuizType.MULTIPLE_CHOICE and quiz.options:
            lines.append("【選択肢】")
            for key in sorted(quiz.options.keys()):
                lines.append(f"  {key}. {quiz.options[key]}")
            lines.append("")
            lines.append("回答を A, B, C, D のいずれかで入力してください。")

        elif quiz.quiz_type == QuizType.TRUE_FALSE:
            lines.append("【選択肢】")
            lines.append("  ○ (正しい)")
            lines.append("  × (誤り)")
            lines.append("")
            lines.append("回答を ○ または × で入力してください。")

        else:  # OPEN
            lines.append("回答を自由に入力してください。")

        lines.append("━" * 40)

        return "\n".join(lines)

    async def generate_multiple_quizzes(
        self,
        state: AgentState,
        count: int = 3,
    ) -> list:
        """複数のクイズを生成する.

        Args:
            state: 現在の状態
            count: 生成するクイズの数

        Returns:
            生成されたクイズのリスト
        """
        topic = state.get("extracted_topic") or state.get("user_query", "")
        document_id = state.get("document_id")

        quizzes = []

        for i in range(count):
            try:
                generated = await self.quiz_service.generate_quiz(
                    topic=topic,
                    quiz_type=self.default_quiz_type,
                    difficulty=self.default_difficulty,
                    document_id=document_id,
                    save=True,
                )
                quizzes.append(generated.quiz)
            except Exception as e:
                logger.warning(f"Failed to generate quiz {i+1}: {e}")
                continue

        return quizzes
