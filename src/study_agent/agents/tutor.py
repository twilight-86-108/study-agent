"""Tutor agent for concept explanation.

トピックの概念説明、用語解説、比較説明を生成するエージェント。
RAG検索で取得したコンテキストを基に、わかりやすい説明を生成する。

Example:
    >>> tutor = TutorAgent(llm_client, search_service)
    >>> state = await tutor.execute(state)
    >>> print(state["explanation"])
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from study_agent.agents.base import BaseAgent
from study_agent.agents.state import AgentState
from study_agent.domain import Intent

if TYPE_CHECKING:
    from study_agent.infrastructure.llm import BaseLLMClient
    from study_agent.services import SearchService

logger = logging.getLogger(__name__)


# 概念説明用プロンプト
EXPLAIN_PROMPT = """あなたは学習支援アプリケーションの優れた講師です。

## 参考資料
{context}

## トピック
{topic}

## 指示
「{topic}」について、学習者にわかりやすく説明してください。

難易度: {difficulty}/5
- レベル1-2: 初心者向け、専門用語を避ける
- レベル3: 標準的な説明、適度に技術用語を使用
- レベル4-5: 詳細な技術的説明

以下の形式で回答してください：

【概要】
（1-2文で簡潔に要約）

【説明】
（メインの説明、200-300文字程度）

【ポイント】
• （重要ポイント1）
• （重要ポイント2）
• （重要ポイント3）

参考資料がない場合は、一般的な知識に基づいて説明してください。"""


# 用語解説用プロンプト
TERM_PROMPT = """あなたは学習支援アプリケーションの講師です。

## 参考資料
{context}

## 用語
{term}

## 指示
「{term}」の意味を簡潔に説明してください。

以下の形式で回答してください：

【定義】
（1-2文で定義）

【補足】
（必要に応じて補足説明）"""


# 比較説明用プロンプト
COMPARE_PROMPT = """あなたは学習支援アプリケーションの講師です。

## 参考資料
{context}

## 比較対象
- {concept_a}
- {concept_b}

## 指示
「{concept_a}」と「{concept_b}」を比較して、違いをわかりやすく説明してください。

以下の形式で回答してください：

【共通点】
• （共通点1）
• （共通点2）

【違い】
| 観点 | {concept_a} | {concept_b} |
|------|-------------|-------------|
| 用途 | ... | ... |
| 特徴 | ... | ... |

【使い分け】
（どのような場面でどちらを使うべきか）"""


class TutorAgent(BaseAgent):
    """概念説明エージェント.

    RAG検索を使用してコンテキストを取得し、
    LLMで説明を生成する。

    Attributes:
        llm_client: LLMクライアント
        search_service: 検索サービス
        default_difficulty: デフォルト難易度

    Example:
        >>> tutor = TutorAgent(llm_client, search_service)
        >>> state["extracted_topic"] = "Amazon EC2"
        >>> state = await tutor.execute(state)
    """

    def __init__(
        self,
        llm_client: BaseLLMClient,
        search_service: SearchService,
        default_difficulty: int = 3,
    ) -> None:
        """初期化.

        Args:
            llm_client: LLMクライアント
            search_service: 検索サービス
            default_difficulty: デフォルト難易度（1-5）
        """
        super().__init__(llm_client, name="TutorAgent")
        self.search_service = search_service
        self.default_difficulty = default_difficulty

    async def execute(self, state: AgentState) -> AgentState:
        """トピックの説明を生成する.

        Args:
            state: 現在の状態

        Returns:
            説明が設定された状態
        """
        self._log_execution_start(state)

        intent = state.get("intent", Intent.EXPLAIN)
        topic = state.get("extracted_topic") or state.get("user_query", "")
        document_id = state.get("document_id")

        if not topic:
            return self._set_error(state, "説明するトピックが指定されていません")

        try:
            # RAGでコンテキストを取得
            context_result = await self.search_service.get_context_for_explanation(
                topic=topic,
                document_id=document_id,
                max_chunks=5,
            )

            state["context"] = context_result.context
            state["source_chunks"] = [c.id for c in context_result.source_chunks]

            # 意図に応じて説明を生成
            if intent == Intent.COMPARE:
                explanation = await self._generate_comparison(
                    state.get("user_query", ""),
                    context_result.context,
                )
            elif intent == Intent.TERM:
                explanation = await self._generate_term_definition(
                    topic,
                    context_result.context,
                )
            else:
                explanation = await self._generate_explanation(
                    topic,
                    context_result.context,
                    self.default_difficulty,
                )

            state["explanation"] = explanation
            state["response"] = explanation

            logger.info(f"Generated explanation for: {topic}")

        except Exception as e:
            logger.error(f"Failed to generate explanation: {e}")
            return self._set_error(state, f"説明の生成に失敗しました: {e}")

        self._log_execution_end(state)
        return state

    async def _generate_explanation(
        self,
        topic: str,
        context: str,
        difficulty: int,
    ) -> str:
        """概念説明を生成する.

        Args:
            topic: 説明するトピック
            context: RAGで取得したコンテキスト
            difficulty: 難易度（1-5）

        Returns:
            生成された説明
        """
        prompt = EXPLAIN_PROMPT.format(
            topic=topic,
            context=context if context else "（参考資料なし）",
            difficulty=difficulty,
        )

        response = await self.llm_client.generate(
            prompt=prompt,
            temperature=0.7,
            max_tokens=1000,
        )

        return response.content

    async def _generate_term_definition(
        self,
        term: str,
        context: str,
    ) -> str:
        """用語の定義を生成する.

        Args:
            term: 定義する用語
            context: RAGで取得したコンテキスト

        Returns:
            生成された定義
        """
        prompt = TERM_PROMPT.format(
            term=term,
            context=context if context else "（参考資料なし）",
        )

        response = await self.llm_client.generate(
            prompt=prompt,
            temperature=0.5,
            max_tokens=500,
        )

        return response.content

    async def _generate_comparison(
        self,
        query: str,
        context: str,
    ) -> str:
        """比較説明を生成する.

        Args:
            query: ユーザークエリ（比較対象を含む）
            context: RAGで取得したコンテキスト

        Returns:
            生成された比較説明
        """
        # クエリから比較対象を抽出
        concepts = self._extract_comparison_concepts(query)
        concept_a = concepts[0] if len(concepts) > 0 else "概念A"
        concept_b = concepts[1] if len(concepts) > 1 else "概念B"

        prompt = COMPARE_PROMPT.format(
            concept_a=concept_a,
            concept_b=concept_b,
            context=context if context else "（参考資料なし）",
        )

        response = await self.llm_client.generate(
            prompt=prompt,
            temperature=0.7,
            max_tokens=1000,
        )

        return response.content

    def _extract_comparison_concepts(self, query: str) -> list[str]:
        """クエリから比較対象を抽出する.

        Args:
            query: ユーザークエリ

        Returns:
            比較対象のリスト
        """
        import re

        # "AとBの違い" パターン
        patterns = [
            r"(.+?)と(.+?)(?:の違い|比較|の差)",
            r"(.+?)\s*vs\.?\s*(.+)",
            r"(.+?)(?:と|、)(.+?)(?:を比較)",
        ]

        for pattern in patterns:
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                return [match.group(1).strip(), match.group(2).strip()]

        return []

    async def answer_question(
        self,
        question: str,
        context: str,
    ) -> str:
        """質問に回答する.

        Args:
            question: ユーザーの質問
            context: RAGで取得したコンテキスト

        Returns:
            回答
        """
        prompt = f"""あなたは学習支援アプリケーションの講師です。

## 参考資料
{context if context else "（参考資料なし）"}

## 質問
{question}

## 指示
質問に対して、参考資料に基づいて簡潔に回答してください。
参考資料に情報がない場合は、一般的な知識で回答してください。"""

        response = await self.llm_client.generate(
            prompt=prompt,
            temperature=0.7,
            max_tokens=500,
        )

        return response.content
