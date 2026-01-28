"""Base agent class.

すべてのエージェントの基底クラス。
共通のインターフェースとユーティリティメソッドを提供。

Example:
    >>> class MyAgent(BaseAgent):
    ...     async def execute(self, state: AgentState) -> AgentState:
    ...         # エージェント固有のロジック
    ...         return state
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from study_agent.agents.state import AgentState

if TYPE_CHECKING:
    from study_agent.infrastructure.llm import BaseLLMClient

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """エージェントの抽象基底クラス.

    すべてのエージェントはこのクラスを継承し、
    executeメソッドを実装する必要がある。

    Attributes:
        llm_client: LLMクライアント
        name: エージェント名（ログ用）

    Example:
        >>> class TutorAgent(BaseAgent):
        ...     async def execute(self, state: AgentState) -> AgentState:
        ...         # 説明を生成
        ...         state["response"] = await self.generate_explanation(...)
        ...         return state
    """

    def __init__(
        self,
        llm_client: BaseLLMClient,
        name: str = "BaseAgent",
    ) -> None:
        """初期化.

        Args:
            llm_client: LLMクライアント
            name: エージェント名
        """
        self.llm_client = llm_client
        self.name = name

    @abstractmethod
    async def execute(self, state: AgentState) -> AgentState:
        """エージェントのメインロジックを実行する.

        Args:
            state: 現在のエージェント状態

        Returns:
            更新されたエージェント状態
        """
        pass

    def should_execute(self, state: AgentState) -> bool:
        """このエージェントを実行すべきか判定する.

        サブクラスでオーバーライドして、
        実行条件を追加できる。

        Args:
            state: 現在の状態

        Returns:
            実行すべき場合True
        """
        return True

    def _log_execution_start(self, state: AgentState) -> None:
        """エージェント実行開始をログ出力する.

        Args:
            state: 現在の状態
        """
        query = state.get("user_query", "")
        truncated = query[:50] + "..." if len(query) > 50 else query
        logger.debug(f"{self.name} executing: {truncated}")

    def _log_execution_end(self, state: AgentState) -> None:
        """エージェント実行終了をログ出力する.

        Args:
            state: 更新された状態
        """
        response = state.get("response", "")
        truncated = response[:50] + "..." if len(response) > 50 else response
        logger.debug(f"{self.name} completed: {truncated}")

    def _set_error(
        self,
        state: AgentState,
        error_message: str,
        error_code: str | None = None,
    ) -> AgentState:
        """状態にエラー情報を設定する.

        Args:
            state: 現在の状態
            error_message: エラーメッセージ
            error_code: エラーコード（オプション）

        Returns:
            エラー情報が設定された状態
        """
        state["error"] = error_message
        state["error_code"] = error_code
        state["response"] = f"エラーが発生しました: {error_message}"
        logger.error(f"{self.name} error: {error_message}")
        return state


class AgentResult:
    """エージェント実行結果を表すヘルパークラス.

    成功・失敗を明示的に扱うためのクラス。

    Attributes:
        success: 成功したかどうか
        data: 結果データ
        error: エラーメッセージ（失敗時）
    """

    def __init__(
        self,
        success: bool,
        data: dict | None = None,
        error: str | None = None,
    ) -> None:
        """初期化.

        Args:
            success: 成功フラグ
            data: 結果データ
            error: エラーメッセージ
        """
        self.success = success
        self.data = data or {}
        self.error = error

    @classmethod
    def ok(cls, data: dict | None = None) -> "AgentResult":
        """成功結果を作成する.

        Args:
            data: 結果データ

        Returns:
            成功結果
        """
        return cls(success=True, data=data)

    @classmethod
    def fail(cls, error: str) -> "AgentResult":
        """失敗結果を作成する.

        Args:
            error: エラーメッセージ

        Returns:
            失敗結果
        """
        return cls(success=False, error=error)
