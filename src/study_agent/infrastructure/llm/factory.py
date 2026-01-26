"""LLMクライアントファクトリー"""

from typing import Literal

from study_agent.core.exceptions import ConfigurationError
from study_agent.core.logging_config import get_logger
from study_agent.infrastructure.config.settings import LLMConfig
from study_agent.infrastructure.llm.base import BaseLLMClient
from study_agent.infrastructure.llm.ollama import OllamaClient
from study_agent.infrastructure.llm.mock import MockLLMClient

logger = get_logger(__name__)

LLMProvider = Literal["ollama", "gemini", "claude", "openai", "mock"]


class LLMClientFactory:
    """LLMクライアントを作るファクトリー"""

    @staticmethod
    def create(config: LLMConfig) -> BaseLLMClient:
        """
        設定を元にLLMクライアントを作成する

        Args:
            config: LLM設定

        Returns:
            BaseLLMClient: LLMクライアント

        Raises:
            ConfigurationError: プロバイダーがサポートされていない場合
        """
        provider = config.provider
        logger.info(f"Creating LLM client for provider: {provider}")

        if provider == "ollama":
            return OllamaClient(
                base_url=config.ollama.base_url,
                model=config.ollama.model,
                temperature=config.ollama.temperature,
                max_tokens=config.ollama.max_tokens,
                timeout=config.ollama.timeout,
            )
        elif provider == "mock":
            return MockLLMClient(
                temperature=config.temperature,
                max_tokens=config.max_tokens,
            )
        elif provider == "gemini":
            pass
        elif provider == "claude":
            pass
        elif provider == "openai":
            pass
        else:
            raise ConfigurationError(f"Unsupported LLM provider: {provider}")
