"""AI Agents module.

LangGraphを使用したエージェントシステム。
ユーザー入力を処理し、適切な応答を生成する。

アーキテクチャ上の位置:
    Presentation Layer (CLI)
           ↓
    **Application Layer (Agents)** ← ここ
           ↓
    Domain Layer (Services)
           ↓
    Infrastructure Layer (LLM, VectorDB, Database)

主要コンポーネント:
    - AgentState: エージェント間で共有される状態
    - BaseAgent: エージェントの基底クラス
    - RouterAgent: 意図分類エージェント
    - TutorAgent: 概念説明エージェント
    - QuizGeneratorAgent: クイズ生成エージェント
    - EvaluatorAgent: 回答評価エージェント
    - PlannerAgent: 学習計画エージェント
    - AgentOrchestrator: エージェント統括

ワークフロー:
    User Input → Router → [Tutor | Quiz | Planner | Evaluator] → Response

Example:
    >>> from study_agent.agents import AgentOrchestrator, RouterAgent, TutorAgent
    >>>
    >>> # オーケストレーターの初期化（通常はDIコンテナから取得）
    >>> orchestrator = AgentOrchestrator(router, tutor, quiz_generator, evaluator, planner)
    >>>
    >>> # クエリを処理
    >>> result = await orchestrator.process("EC2について教えて", session_id="123")
    >>> print(result["response"])
"""

from study_agent.agents.state import AgentState, create_initial_state
from study_agent.agents.base import BaseAgent, AgentResult
from study_agent.agents.router import RouterAgent
from study_agent.agents.tutor import TutorAgent
from study_agent.agents.quiz_generator import QuizGeneratorAgent
from study_agent.agents.evaluator import EvaluatorAgent
from study_agent.agents.planner import PlannerAgent
from study_agent.agents.orchestrator import AgentOrchestrator

__all__ = [
    # State
    "AgentState",
    "create_initial_state",
    # Base
    "BaseAgent",
    "AgentResult",
    # Agents
    "RouterAgent",
    "TutorAgent",
    "QuizGeneratorAgent",
    "EvaluatorAgent",
    "PlannerAgent",
    # Orchestrator
    "AgentOrchestrator",
]
