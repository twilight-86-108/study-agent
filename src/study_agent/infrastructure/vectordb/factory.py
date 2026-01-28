"""VectorDBファクトリー"""

import logging
from typing import TYPE_CHECKING

from study_agent.core.exceptions import ConfigurationError
from study_agent.infrastructure.vectordb.base import (
    BaseVectorDB,
    VectorDBConfig,
)
from study_agent.infrastructure.vectordb.chroma import ChromaDBClient

if TYPE_CHECKING:
    from study_agent.infrastructure.config.settings import VectorDBConfig

logger = logging.getLogger(__name__)


class VectorDBFactory:
    """VectorDBファクトリー"""

    SUPPORTED_PROVIDERS = {"chroma"}

    @staticmethod
    def create(config: VectorDBConfig) -> BaseVectorDB:
        """
        VectorDBを生成

        Args:
            config: VectorDB設定

        Returns:
            BaseVectorDB: VectorDBインスタンス

        Raises:
            ConfigurationError: 設定が無効な場合
        """
        provider = config.provider.lower()
        if provider == "chroma":
            logger.info(
                f"Creating ChromaDBClient: collection='{config.collection_name}'"
            )
            return ChromaDBClient(config)
        else:
            raise ConfigurationError(
                message=f"Unsupported VectorDB provider: {provider}"
            )

    @staticmethod
    def from_settings(settings: VectorDBConfig) -> BaseVectorDB:
        """
        設定からVectorDBを生成

        Args:
            settings: VectorDB設定

        Returns:
            BaseVectorDB: VectorDBインスタンス

        Raises:
            ConfigurationError: 設定が無効な場合
        """
        provider = settings.provider.lower()

        if provider not in VectorDBFactory.SUPPORTED_PROVIDERS:
            raise ConfigurationError(
                message=f"Unsupported VectorDB provider: {provider}"
            )

        config = VectorDBConfig(
            provider=provider,
            collection_name=settings.collection_name,
            persist_directory=settings.persist_directory,
            distance_metric=getattr(settings, "distance_metric", "cosine"),
        )

        return VectorDBFactory.create(config)

    @staticmethod
    def create_chroma(
        presist_directory: str = "./data/vectors/chroma",
        collection_name: str = "study_agent",
        distance_metric: str = "cosine",
    ) -> ChromaDBClient:
        """
        ChromaDBクライアントを生成

        Args:
            presist_directory:永続化ディレクトリ
            collection_name: コレクション名
            distance_metric: 距離関数

        Returns:
            ChromaDBClient: ChromaDBクライアントインスタンス
        """
        config = VectorDBConfig(
            provider="chroma",
            collection_name=collection_name,
            persist_directory=presist_directory,
            distance_metric=distance_metric,
        )
        return ChromaDBClient(config)
