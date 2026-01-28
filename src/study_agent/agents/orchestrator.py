"""Agent orchestrator using LangGraph.

LangGraphを使用してエージェント間の連携を制御する。
ユーザー入力をRouterで分類し、適切なエージェントにルーティングする。

ワークフロー:
    START → Router → [Tutor | QuizGenerator | Planner | Evaluator | DirectResponse] → END

Example:
    >>> orchestrator = AgentOrchestrator(router, tutor, quiz_generator, evaluator, planner)
    >>> result = await orchestrator.process("EC2について教えて", session_id="123")
    >>> print(result["response"])
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Literal

from langgraph.graph import StateGraph, END

from study_agent.agents.state import AgentState, create_initial_state
from study_agent.agents.router import RouterAgent
from study_agent.agents.tutor import TutorAgent
from study_agent.agents.quiz_generator import QuizGeneratorAgent
from study_agent.agents.evaluator import EvaluatorAgent
from study_agent.agents.planner import PlannerAgent
from study_agent.domain import Intent, Quiz

logger = logging.getLogger(__name__)

# ルーティング先の型定義
RouteDestination = Literal["tutor", "quiz", "evaluate", "planner", "direct"]


class AgentOrchestrator:
    """エージェントオーケストレーター.

    LangGraphを使用してエージェント間の状態遷移を管理する。

    Attributes:
        router: ルーターエージェント
        tutor: チューターエージェント
        quiz_generator: クイズ生成エージェント
        evaluator: 評価エージェント
        planner: 計画エージェント

    Example:
        >>> orchestrator = AgentOrchestrator(router, tutor, quiz_generator, evaluator, planner)
        >>> state = await orchestrator.process("EC2について教えて", "session-123")
        >>> print(state["response"])
    """

    def __init__(
        self,
        router: RouterAgent,
        tutor: TutorAgent,
        quiz_generator: QuizGeneratorAgent,
        evaluator: EvaluatorAgent,
        planner: PlannerAgent,
    ) -> None:
        """初期化.

        Args:
            router: ルーターエージェント
            tutor: チューターエージェント
            quiz_generator: クイズ生成エージェント
            evaluator: 評価エージェント
            planner: 計画エージェント
        """
        self.router = router
        self.tutor = tutor
        self.quiz_generator = quiz_generator
        self.evaluator = evaluator
        self.planner = planner
        self._graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        """LangGraphワークフローを構築する.

        Returns:
            コンパイル済みのStateGraph
        """
        # グラフを作成
        workflow = StateGraph(AgentState)

        # ノードを追加
        workflow.add_node("router", self._router_node)
        workflow.add_node("tutor", self._tutor_node)
        workflow.add_node("quiz_generator", self._quiz_node)
        workflow.add_node("evaluator", self._evaluator_node)
        workflow.add_node("planner", self._planner_node)
        workflow.add_node("direct_response", self._direct_response_node)

        # エントリーポイントを設定
        workflow.set_entry_point("router")

        # Routerからの条件分岐
        workflow.add_conditional_edges(
            "router",
            self._route_decision,
            {
                "tutor": "tutor",
                "quiz": "quiz_generator",
                "evaluate": "evaluator",
                "planner": "planner",
                "direct": "direct_response",
            },
        )

        # 各ノードからENDへのエッジ
        workflow.add_edge("tutor", END)
        workflow.add_edge("quiz_generator", END)
        workflow.add_edge("evaluator", END)
        workflow.add_edge("planner", END)
        workflow.add_edge("direct_response", END)

        return workflow.compile()

    async def _router_node(self, state: AgentState) -> AgentState:
        """Routerノード.

        Args:
            state: 現在の状態

        Returns:
            更新された状態
        """
        return await self.router.execute(state)

    async def _tutor_node(self, state: AgentState) -> AgentState:
        """Tutorノード.

        Args:
            state: 現在の状態

        Returns:
            更新された状態
        """
        return await self.tutor.execute(state)

    async def _quiz_node(self, state: AgentState) -> AgentState:
        """QuizGeneratorノード.

        Args:
            state: 現在の状態

        Returns:
            更新された状態
        """
        return await self.quiz_generator.execute(state)

    async def _evaluator_node(self, state: AgentState) -> AgentState:
        """Evaluatorノード.

        Args:
            state: 現在の状態

        Returns:
            更新された状態
        """
        return await self.evaluator.execute(state)

    async def _planner_node(self, state: AgentState) -> AgentState:
        """Plannerノード.

        Args:
            state: 現在の状態

        Returns:
            更新された状態
        """
        return await self.planner.execute(state)

    async def _direct_response_node(self, state: AgentState) -> AgentState:
        """直接応答ノード.

        シンプルな意図に対して直接応答を返す。

        Args:
            state: 現在の状態

        Returns:
            更新された状態
        """
        intent = state.get("intent")

        if intent == Intent.PROGRESS:
            state["response"] = self._progress_response()
        elif intent == Intent.CHAT:
            state["response"] = self._chat_response(state.get("user_query", ""))
        else:
            state["response"] = self._help_response()

        return state

    def _route_decision(self, state: AgentState) -> RouteDestination:
        """ルーティング先を決定する.

        Args:
            state: 現在の状態

        Returns:
            ルーティング先
        """
        intent = state.get("intent")
        quiz = state.get("quiz")

        # アクティブなクイズがあり、回答待ちの場合
        if quiz and intent not in [Intent.QUIZ]:
            return "evaluate"

        # 意図に基づいてルーティング
        if intent in [Intent.EXPLAIN, Intent.TERM, Intent.COMPARE]:
            return "tutor"
        elif intent == Intent.QUIZ:
            return "quiz"
        elif intent == Intent.NAVIGATE:
            return "planner"
        elif intent == Intent.PROGRESS:
            return "direct"
        elif intent == Intent.CHAT:
            return "direct"
        else:
            return "direct"

    def _progress_response(self) -> str:
        """進捗確認の応答を生成する.

        Returns:
            応答文字列
        """
        return """【進捗確認】

進捗を確認するには、以下のコマンドを使用してください：

• `progress` - 全体の進捗を表示
• `progress --document <名前>` - 特定のドキュメントの進捗

詳細な進捗情報は、CLIコマンドで確認できます。"""

    def _chat_response(self, query: str) -> str:
        """チャット応答を生成する.

        Args:
            query: ユーザークエリ

        Returns:
            応答文字列
        """
        query_lower = query.lower()

        if any(word in query_lower for word in ["こんにちは", "hello", "hi"]):
            return "こんにちは！何を学習しましょうか？"
        elif any(word in query_lower for word in ["ありがとう", "thanks"]):
            return "どういたしまして！他に質問があれば聞いてください。"
        elif any(word in query_lower for word in ["さようなら", "bye"]):
            return "お疲れ様でした！また学習しましょう！"
        else:
            return self._help_response()

    def _help_response(self) -> str:
        """ヘルプ応答を生成する.

        Returns:
            応答文字列
        """
        return """【StudyAgent ヘルプ】

🎓 使い方：

【概念を学ぶ】
• 「EC2について教えて」
• 「VPCとは何ですか」
• 「S3とEBSの違いは？」

【クイズに挑戦】
• 「クイズを出して」
• 「EC2のクイズ」
• 「テストしたい」

【進捗確認】
• 「進捗を見せて」

【ナビゲーション】
• 「次のトピックへ」
• 「前に戻る」

💡 ヒント: 具体的なトピック名を入れると、より正確な説明が得られます。"""

    async def process(
        self,
        user_query: str,
        session_id: str,
        document_id: str | None = None,
        current_quiz: Quiz | None = None,
    ) -> AgentState:
        """ユーザークエリを処理する.

        Args:
            user_query: ユーザーの入力
            session_id: セッションID
            document_id: ドキュメントID（オプション）
            current_quiz: アクティブなクイズ（オプション）

        Returns:
            最終的なエージェント状態
        """
        # 初期状態を作成
        initial_state = create_initial_state(
            user_query=user_query,
            session_id=session_id,
            document_id=document_id,
            quiz=current_quiz,
        )

        logger.info(f"Processing query: {user_query[:50]}...")

        # グラフを実行
        try:
            final_state = await self._graph.ainvoke(initial_state)
            logger.info(f"Response generated (intent={final_state.get('intent')})")
            return final_state
        except Exception as e:
            logger.error(f"Graph execution failed: {e}")
            initial_state["error"] = str(e)
            initial_state["response"] = f"エラーが発生しました: {e}"
            return initial_state

    async def process_stream(
        self,
        user_query: str,
        session_id: str,
        document_id: str | None = None,
        current_quiz: Quiz | None = None,
    ):
        """ユーザークエリをストリーム処理する.

        Args:
            user_query: ユーザーの入力
            session_id: セッションID
            document_id: ドキュメントID（オプション）
            current_quiz: アクティブなクイズ（オプション）

        Yields:
            各ノードの実行結果
        """
        initial_state = create_initial_state(
            user_query=user_query,
            session_id=session_id,
            document_id=document_id,
            quiz=current_quiz,
        )

        async for event in self._graph.astream(initial_state):
            yield event
