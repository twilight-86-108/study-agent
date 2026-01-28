"""Embedding Service Factory"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from study_agent.core.exceptions import ConfigurationError
from study_agent.infrastructure.vectordb.settings import (
    EmbeddingConfig as EmbeddingSettings,
)
from study_agent.infrastructure.vectordb.embeddings.base import (
    BaseEmbeddingService,
    EmbeddingConfig,
    EmbeddingProvider,
)
from study_agent.infrastructure.vectordb.embeddings.mock import MockEmbeddingService
from study_agent.infrastructure.vectordb.embeddings.ollama import OllamaEmbeddingService


logger = logging.getLogger(__name__)


class EmbeddingServiceFactory:
    """Embedding Serviceのファクトリー"""

    @staticmethod
    def create(config: EmbeddingConfig) -> BaseEmbeddingService:
        """
        Embedding Serviceを生成

        Args:
            config: Embedding設定

        Returns:
            BaseEmbeddingService: Embedding Service

        Raises:
            ConfigurationError: 設定が無効な場合
        """
        provider = config.provider
        if provider == EmbeddingProvider.MOCK:
            logger.info("Using mock embedding service")
            return MockEmbeddingService(config)
        elif provider == EmbeddingProvider.OLLAMA:
            logger.info("Using ollama embedding service")
            return OllamaEmbeddingService(config)
        elif provider == EmbeddingProvider.OPENAI:
            # TODO: 後ほど実装
            raise ConfigurationError(
                message="OpenAI embedding service is not implemented yet",
                details={"provider": provider.value},
            )
        elif provider == EmbeddingProvider.GEMINI:
            # TODO: 後ほど実装
            raise ConfigurationError(
                message="Gemini embedding service is not implemented yet",
                details={"provider": provider.value},
            )
        else:
            raise ConfigurationError(
                message=f"Unsupported embedding provider: {provider}",
                details={
                    "provider": (
                        provider.value if hasattr(provider, "value") else str(provider)
                    )
                },
            )

    @staticmethod
    def from_settings(settings: EmbeddingSettings) -> BaseEmbeddingService:
        """
        Embedding設定からEmbedding Serviceを生成

        Args:
            settings: Embedding設定

        Returns:
            BaseEmbeddingService: Embedding Service

        Raises:
            ConfigurationError: 設定が無効な場合
        """
        try:
            provider = EmbeddingProvider(settings.provider)
        except ValueError:
            raise ConfigurationError(
                message=f"Invalid embedding provider: {settings.provider}",
                details={
                    "provider": settings.provider,
                    "valid_providers": [p.value for p in EmbeddingProvider],
                },
            )

        # プロバイダー別の設定
        if provider == EmbeddingProvider.OLLAMA:
            config = EmbeddingConfig(
                provider=provider,
                model=settings.ollama.model,
                base_url=settings.ollama.base_url,
                timeout=settings.timeout,
            )
        elif provider == EmbeddingProvider.OPENAI:
            config = EmbeddingConfig(
                provider=provider,
                model=settings.openai.model,
                api_key=settings.openai.api_key,
                timeout=settings.timeout,
            )
        elif provider == EmbeddingProvider.GEMINI:
            config = EmbeddingConfig(
                provider=provider,
                model=settings.gemini.model,
                api_key=settings.gemini.api_key,
                timeout=settings.timeout,
            )
        elif provider == EmbeddingProvider.MOCK:
            config = EmbeddingConfig.for_mock()
        else:
            raise ConfigurationError(
                message=f"Unsupported embedding provider: {provider}",
            )
        return EmbeddingServiceFactory.create(config)

    @staticmethod
    def create_mock(dimention: int = 768) -> MockEmbeddingService:
        """
        モックEmbedding Serviceを生成

        Args:
            dimention: 埋め込みベクトルの次元数

        Returns:
            MockEmbeddingServce: モックEmbedding Service
        """
        return MockEmbeddingService(dimention=dimention)
