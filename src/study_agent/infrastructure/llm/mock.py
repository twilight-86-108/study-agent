"""モックテスト"""

from dataclasses import dataclass
from typing import Any, AsyncIterator, Optional

from study_agent.infrastructure.llm.base import (
    BaseLLMClient,
    LLMResponse,
    LLMStreamchunk,
)


@dataclass
class MockCall:
    """モック呼び出しの記録"""

    prompt: str
    system_prompt: Optional[str]
    kwargs: dict[str, Any]


class MockLLMClient(BaseLLMClient):
    """テスト用モックLLMクライアント"""

    def __init__(
        self,
        model: str = "mock-model",
        default_response: str = "This is a mock response.",
        **kwargs: Any,
    ) -> None:
        super().__init__(model=model, **kwargs)
        self.default_response = default_response
        self._responses: list[str] = []
        self._json_responses: list[dict[str, Any]] = []
        self.call_history: list[MockCall] = []

    def set_response(self, response: str) -> None:
        """次の応答を設定"""
        self._responses.append(response)

    def set_json_response(self, rsponse: dict[str, Any]) -> None:
        """次のJSON応答の設定"""
        self._json_responses.append(response)

    def clear_history(self) -> None:
        """呼び出し履歴をクリア"""
        self.call_history.clear()

    async def generate(
        self,
        prompt: str,
        *,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        """LLMからモック応答を生成"""
        self.call_history.append(
            MockCall(
                prompt=prompt,
                system_prompt=system_prompt,
                kwargs={
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                },
            )
        )

        content = self._responses.pop(0) if self._responses else self.default_response
        return LLMResponse(
            content=content,
            model=self.model,
            usage={
                "input_tokens": len(prompt) // 4,
                "output_tokens": len(content) // 4,
            },
        )

    async def generate_json(
        self,
        prompt: str,
        schema: dict[str, Any],
        *,
        system_prompt: Optional[str] = None,
    ) -> dict[str, Any]:
        """LLMからモックJSON応答を生成"""
        self.call_history.append(
            MockCall(
                prompt=prompt,
                system_prompt=system_prompt,
                kwargs={
                    "schema": schema,
                },
            )
        )

        if self._json_responses:
            return self._json_responses.pop(0)

        return self._generate_default_json(schema)

    def _generate_default_json(
        self,
        schema: dict[str, Any],
    ) -> dict[str, Any]:
        """スキーマに基づいたデフォルトのJSONを生成"""
        properties = schema.get("properties", {})
        result: dict[str, Any] = {}

        for key, prop in properties.items():
            prop_type = prop.get("type", "string")
            if prop_type == "string":
                result[key] = f"mock_{key}"
            elif prop_type == "integer":
                result[key] = 0
            elif prop_type == "number":
                result[key] = 0.0
            elif prop_type == "boolean":
                result[key] = True
            elif prop_type == "array":
                result[key] = []
            elif prop_type == "object":
                result[key] = {}

        return result

    async def generate_stream(
        self,
        prompt: str,
        *,
        system_prompt: Optional[str] = None,
    ) -> AsyncIterator[LLMStreamchunk]:
        """モックストリーム返答を生成"""
        self.call_history.append(
            MockCall(
                prompt=prompt,
                system_prompt=system_prompt,
                kwargs={},
            )
        )

        content = self._responses.pop(0) if self._responses else self.default_response

        words = content.split()
        for i, word in enumerate(words):
            yield LLMStreamchunk(
                content=word + " ",
                is_final=(i == len(words) - 1),
                model=self.model,
            )

    async def health_check(self) -> None:
        """ヘルスチェック"""
        return True
