"""LLM基底クライアントインターフェース"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, AsyncIterator, Optional


@dataclass
class LLMResponse:
    """LLMからのレスポンス"""

    content: str
    model: str
    usage: Optional[dict[str, int]] = None
    raw_response: Any = None

    @property
    def input_tokens(self) -> int:
        """入力トークン数を取得"""

        if self.usage:
            return self.usage.get("input_tokens", 0)
        return 0

    @property
    def output_tokens(self) -> int:
        """出力トークン数を取得"""

        if self.usage:
            return self.usage.get("output_tokens", 0)
        return 0


@dataclass
class LLMStreamchunk:
    """LLMストリーミング応答からのチャンク"""

    content: str
    is_final: bool = False
    model: Optional[str] = None


class BaseLLMClient(ABC):
    """LLMクライアントのための抽象基底クラス"""

    def __init__(
        self,
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        timeout: int = 30,
    ) -> None:
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        *,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        """
        LLMから応答を生成

        Args:
            prompt: プロンプト
            system_prompt: システムプロンプト
            temperature: 温度
            max_tokens: 最大トークン数

        Returns:
            LLMResponse: LLMからの応答

        Raises:
            LLMConnectionError: LLMとの接続に失敗した場合
            LLMTimeoutError: LLMとの接続にタイムアウトした場合
            LLMResponseError: LLMからの応答に失敗した場合
        """
        pass

    @abstractmethod
    async def generate_json(
        self,
        prompt: str,
        schema: dict[str, Any],
        *,
        system_prompt: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        LLMからJSON形式の応答を生成

        Args:
            prompt: プロンプト
            schema: JSONスキーマ
            system_prompt: システムプロンプト

        Returns:
            dict[str, Any]: JSON形式の応答

        Raises:
            LLMResponseError: LLMからの応答に失敗した場合
        """
        pass

    @abstractmethod
    async def generate_stream(
        self,
        prompt: str,
        *,
        system_prompt: Optional[str] = None,
    ) -> AsyncIterator[LLMStreamchunk]:
        """
        LLMからストリーミング応答を生成

        Args:
            prompt: プロンプト
            system_prompt: システムプロンプト

        Yields:
            コンテンツフラグメント付きLLMストリームチャンク
        """
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """
        LLMクライアントのヘルスチェック

        Returns:
            bool: サービスが利用可能な場合にTrue
        """
        pass
