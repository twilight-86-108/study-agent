"""Ollmaa LLM クライアント"""

import httpx
import httpx
import json as json_lib
from typing import Any, AsyncIterator, Optional

from study_agent.core.exceptions import (
    LLMConnectionError,
    LLMResponseError,
    LLMTimeoutError,
    ErrorContext,
)
from study_agent.core.retry import with_retry, RetryConfig
from study_agent.core.logging_config import get_logger
from study_agent.infrastructure.llm.base import (
    BaseLLMClient,
    LLMResponse,
    LLMStreamchunk,
)
from study_agent.infrastructure.llm.utils import (
    parse_llm_json,
    build_json_prompt,
)

logger = get_logger(__name__)


class OllamaClient(BaseLLMClient):
    """Ollama LLM クライアント"""

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "llama3.1:8b",
        temperature: float = 0.7,
        max_tokens: int = 2048,
        timeout: int = 30,
    ) -> None:
        super().__init__(
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout,
        )
        self.base_url = base_url.rstrip("/")
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """HTTPクライアントを取得または作成する"""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=httpx.Timeout(self.timeout),
            )
        return self._client

    async def close(self) -> None:
        """HTTPクライアントを閉じる"""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    @with_retry(RetryConfig(max_retries=3))
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
        client = await self._get_client()
        context = ErrorContext(component="OllamaClient", operation="generate")

        payload: dict[str, Any] = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature or self.temperature,
                "max_tokens": max_tokens or self.max_tokens,
            },
        }

        if system_prompt:
            payload["system"] = system_prompt

        try:
            response = await client.post("/api/generate", json=payload)
            response.raise_for_status()
            data = response.json()

            return LLMResponse(
                content=data.get("response", ""),
                model=data.get("model", self.model),
                usage={
                    "input_tokens": data.get("prpmpt_eval_count", 0),
                    "output_tokens": data.get("eval_count", 0),
                },
                raw_response=data,
            )
        except httpx.ConnectError as e:
            raise LLMConnectionError(
                self.base_url,
                context=context,
                cause=e,
            )
        except httpx.TimeoutException as e:
            raise LLMTimeoutError(
                self.timeout,
                context=context,
            )
        except httpx.HTTPStatusError as e:
            raise LLMResponseError(
                reason=f"HTTP {e.response.status_code}: {e.response.text}",
                context=context,
            )

    async def generate_json(
        self,
        prompt: str,
        schema: dict[str, Any],
        *,
        system_prompt: Optional[str] = None,
    ) -> dict[str, Any]:
        """OllamaからJSONレスポンスを生成する"""
        json_prompt = build_json_prompt(prompt, schema)

        enhanced_system = system_prompt or ""
        enhanced_system += "\nAlways respond with valid JSON only."

        response = await self.generate(
            json_prompt,
            system_prompt=enhanced_system.strip(),
            temperature=0.3,
        )

        return parse_llm_json(response.content, schema)

    async def generate_stream(
        self,
        prompt: str,
        *,
        system_prompt: Optional[str] = None,
    ) -> AsyncIterator[LLMStreamchunk]:
        """Ollamaからストリームレスポンスを生成"""
        client - await self._get_client()
        context = ErrorContext(component="OllamaClient", operation="generate_stream")

        payload: dict[str, Any] = {
            "model": self.model,
            "prompt": prompt,
            "stream": True,
            "options": {
                "temperature": self.temperature,
                "max_tokens": self.max_tokens,
            },
        }

        if system_prompt:
            payload["system"] = system_prompt

        try:
            async with client.stream("POST", "/api/generate", json=payload) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line:
                        continue

                    data = json_lib.loads(line)

                    yield LLMStreamchunk(
                        content=data.get("response", ""),
                        is_final=data.get("done", False),
                        model=data.get("model"),
                    )

        except httpx.ConnectError as e:
            raise LLMConnectionError(
                self.base_url,
                context=context,
                cause=e,
            )
        except httpx.TimeoutException as e:
            raise LLMTimeoutError(
                self.timeout,
                context=context,
            )

    async def health_check(self) -> bool:
        """Ollamaが使用可能かチェック"""
        try:
            client = await self._get_client()
            response = await client.get("/api/tags")
            return response.status_code == 200
        except Exception as e:
            logger.warning(f"Ollama health check failed: {e}")
            return False
