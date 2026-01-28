"""Router agent for intent classification.

ユーザー入力の意図を分類するエージェント。
パターンマッチングによる高速分類と、LLMによる詳細分類を組み合わせる。

分類される意図:
    - EXPLAIN: 概念説明を求めている
    - TERM: 用語解説を求めている
    - QUIZ: クイズ/テストを希望
    - COMPARE: 比較説明を希望
    - NAVIGATE: トピック移動
    - PROGRESS: 進捗確認
    - CHAT: 一般的な会話
    - UNKNOWN: 判定不能

Example:
    >>> router = RouterAgent(llm_client)
    >>> state = await router.execute(state)
    >>> print(state["intent"])  # Intent.EXPLAIN
"""

from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING

from study_agent.agents.base import BaseAgent
from study_agent.agents.state import AgentState
from study_agent.domain import Intent

if TYPE_CHECKING:
    from study_agent.infrastructure.llm import BaseLLMClient

logger = logging.getLogger(__name__)


# パターンマッチング用の正規表現
INTENT_PATTERNS = {
    Intent.EXPLAIN: [
        r"(?:について|とは|を)(?:教えて|説明|解説)",
        r"(?:何|なん)(?:ですか|だ)",
        r"(?:どう|どの)(?:いう|ような)",
        r"explain|教えて",
    ],
    Intent.TERM: [
        r"(?:用語|単語|語句).*(?:意味|定義)",
        r"(?:意味|定義)(?:は|を|が)",
    ],
    Intent.QUIZ: [
        r"クイズ|テスト|問題|出題",
        r"quiz|test|question",
        r"力試し|腕試し",
    ],
    Intent.COMPARE: [
        r"(?:違い|差|比較)",
        r"(?:と|vs).+(?:の違い|比較)",
        r"compare|difference",
    ],
    Intent.NAVIGATE: [
        r"次(?:の|へ)|前(?:の|へ)",
        r"next|prev|back",
        r"(?:トピック|章).*(?:移動|進む|戻る)",
    ],
    Intent.PROGRESS: [
        r"進捗|習熟|成績|結果",
        r"progress|score|result",
        r"どれ(?:くらい|だけ)(?:できた|学習)",
    ],
    Intent.CHAT: [
        r"^(?:こんにちは|おはよう|こんばんは|ありがとう|さようなら)",
        r"^(?:hi|hello|thanks|bye)",
    ],
}

# LLM用プロンプト
ROUTER_PROMPT = """You are an intent classifier for a learning assistant application.

Classify the user's message into one of these intents:
- explain: User wants explanation of a concept or topic (e.g., "EC2について教えて", "S3とは何ですか")
- term: User wants definition of a specific term (e.g., "VPCの意味は？")
- quiz: User wants to take a quiz or test (e.g., "クイズを出して", "問題を出題して")
- compare: User wants comparison between concepts (e.g., "EC2とLambdaの違い")
- navigate: User wants to move to next/previous topic (e.g., "次のトピックへ")
- progress: User wants to check learning progress (e.g., "進捗を見せて")
- chat: General conversation or greeting (e.g., "こんにちは")
- unknown: Cannot determine the intent

## User Message
{user_query}

## Instructions
Analyze the message carefully and respond with JSON containing:
- intent: One of the above intent values (lowercase)
- confidence: Confidence score from 0.0 to 1.0
- extracted_topic: The main topic mentioned (if any), or null

Important: Focus on the user's PRIMARY intent. If they ask about a topic, it's likely "explain".

Respond with JSON only, no additional text."""


class RouterAgent(BaseAgent):
    """ユーザー意図分類エージェント.

    パターンマッチングとLLMを組み合わせて、
    ユーザー入力の意図を高精度に分類する。

    Attributes:
        llm_client: LLMクライアント
        use_llm_fallback: LLMフォールバックを使用するか

    Example:
        >>> router = RouterAgent(llm_client)
        >>> state["user_query"] = "EC2について教えて"
        >>> state = await router.execute(state)
        >>> print(state["intent"])  # Intent.EXPLAIN
    """

    def __init__(
        self,
        llm_client: BaseLLMClient,
        use_llm_fallback: bool = True,
    ) -> None:
        """初期化.

        Args:
            llm_client: LLMクライアント
            use_llm_fallback: パターンマッチで判定できない場合にLLMを使用
        """
        super().__init__(llm_client, name="RouterAgent")
        self.use_llm_fallback = use_llm_fallback

    async def execute(self, state: AgentState) -> AgentState:
        """ユーザー入力の意図を分類する.

        Args:
            state: 現在の状態

        Returns:
            意図が設定された状態
        """
        self._log_execution_start(state)

        user_query = state.get("user_query", "")

        if not user_query.strip():
            state["intent"] = Intent.UNKNOWN
            state["confidence"] = 1.0
            state["extracted_topic"] = None
            return state

        # 1. パターンマッチングによる高速分類
        intent, confidence = self._pattern_match(user_query)

        if intent is not None and confidence >= 0.8:
            state["intent"] = intent
            state["confidence"] = confidence
            state["extracted_topic"] = self._extract_topic(user_query)
            logger.info(
                f"Intent classified (pattern): {intent.value} "
                f"(confidence={confidence:.2f})"
            )
            return state

        # 2. LLMによる詳細分類
        if self.use_llm_fallback:
            try:
                llm_result = await self._classify_with_llm(user_query)
                state["intent"] = llm_result["intent"]
                state["confidence"] = llm_result["confidence"]
                state["extracted_topic"] = llm_result.get("extracted_topic")
                logger.info(
                    f"Intent classified (LLM): {state['intent'].value} "
                    f"(confidence={state['confidence']:.2f})"
                )
                return state
            except Exception as e:
                logger.warning(f"LLM classification failed: {e}")

        # 3. フォールバック
        if intent is not None:
            state["intent"] = intent
            state["confidence"] = confidence
        else:
            state["intent"] = Intent.CHAT
            state["confidence"] = 0.5
        state["extracted_topic"] = self._extract_topic(user_query)

        logger.info(
            f"Intent classified (fallback): {state['intent'].value} "
            f"(confidence={state['confidence']:.2f})"
        )
        return state

    def _pattern_match(self, query: str) -> tuple[Intent | None, float]:
        """パターンマッチングで意図を分類する.

        Args:
            query: ユーザークエリ

        Returns:
            (意図, 確信度) のタプル。マッチしない場合は (None, 0.0)
        """
        query_lower = query.lower()

        for intent, patterns in INTENT_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, query_lower, re.IGNORECASE):
                    return intent, 0.9

        return None, 0.0

    async def _classify_with_llm(self, query: str) -> dict:
        """LLMを使用して意図を分類する.

        Args:
            query: ユーザークエリ

        Returns:
            分類結果の辞書
        """
        schema = {
            "type": "object",
            "properties": {
                "intent": {
                    "type": "string",
                    "enum": [
                        "explain",
                        "term",
                        "quiz",
                        "compare",
                        "navigate",
                        "progress",
                        "chat",
                        "unknown",
                    ],
                },
                "confidence": {
                    "type": "number",
                    "minimum": 0.0,
                    "maximum": 1.0,
                },
                "extracted_topic": {
                    "type": ["string", "null"],
                },
            },
            "required": ["intent", "confidence"],
        }

        prompt = ROUTER_PROMPT.format(user_query=query)
        result = await self.llm_client.generate_json(prompt, schema)

        # 意図をEnumに変換
        intent_str = result.get("intent", "unknown").lower()
        try:
            intent = Intent(intent_str)
        except ValueError:
            intent = Intent.UNKNOWN

        return {
            "intent": intent,
            "confidence": result.get("confidence", 0.5),
            "extracted_topic": result.get("extracted_topic"),
        }

    def _extract_topic(self, query: str) -> str | None:
        """クエリからトピックを抽出する.

        Args:
            query: ユーザークエリ

        Returns:
            抽出されたトピック、または None
        """
        # パターンベースの抽出
        patterns = [
            r"(.+?)(?:について|とは|を説明|の説明)",
            r"(.+?)(?:と|vs)(.+?)(?:の違い|比較)",
            r"「(.+?)」",
            r"『(.+?)』",
        ]

        for pattern in patterns:
            match = re.search(pattern, query)
            if match:
                topic = match.group(1).strip()
                if topic and len(topic) > 1:
                    return topic

        # 名詞っぽいものを抽出（簡易版）
        # 英単語や日本語の固有名詞
        words = re.findall(r"[A-Za-z][A-Za-z0-9]+|[ァ-ヶー]+|[一-龠]+", query)
        if words:
            # 最も長い単語を返す
            return max(words, key=len)

        return None
