"""Embeddingの基底クラス"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class EmbeddingProvider(str, Enum):
    """Embeddingプロバイダー"""

    OLLAMA = "ollama"
    OPENAI = "openai"
    GEMINI = "gemini"
    MOCK = "mock"


@dataclass
class EmbeddingConfig:
    """
    Embedding設定

    Attributes:
        provider: プロバイダー
        model: モデル名
        base_url: APIベースURL
        api_key: APIキー
        batch_size: バッチサイズ
        timeout: タイムアウト
    """

    provider: EmbeddingProvider
    model: str
    base_url: Optional[str] = None
    api_key: Optional[str] = None
    batch_size: int = 32
    timeout: int = 60

    @classmethod
    def for_ollama(
        cls, model: str = "nomic-embed-text", base_url: str = "http://localhost:11434"
    ) -> EmbeddingConfig:
        """Ollama用のEmbedding設定"""
        return cls(
            provider=EmbeddingProvider.OLLAMA,
            model=model,
            base_url=base_url,
        )

    @classmethod
    def for_openai(
        cls,
        model: str = "text-embedding-3-small",
        api_key: Optional[str] = None,
    ) -> EmbeddingConfig:
        """OpenAI用のEmbedding設定"""
        return cls(
            provider=EmbeddingProvider.OPENAI,
            model=model,
            api_key=api_key,
        )

    @classmethod
    def for_gemini(
        cls,
        model: str = "text-embedding-004",
        api_key: Optional[str] = None,
    ) -> EmbeddingConfig:
        """Gemini用のEmbedding設定"""
        return cls(
            provider=EmbeddingProvider.GEMINI,
            model=model,
            api_key=api_key,
        )

    @classmethod
    def for_mock(
        cls,
        dimension: int = 768,
    ) -> EmbeddingConfig:
        """モック用のEmbedding設定"""
        return cls(
            provider=EmbeddingProvider.MOCK,
            model=f"mock_{dimension}",
        )


@dataclass
class EmbeddingResult:
    """
    Embedding結果

    Attributes:
        embedding: エンベディング
        model: 使用したモデル名
        token_count: 消費トークン数
    """

    embedding: list[float]
    model: str
    token_count: Optional[int] = None


class BaseEmbeddingService(ABC):
    """Embeddingサービスの基底クラス"""

    def __init__(self, config: EmbeddingConfig) -> None:
        """
        初期化

        Args:
            config: Embedding設定
        """
        self.config = config

    @property
    @abstractmethod
    def provider(self) -> EmbeddingProvider:
        """プロバイダー識別子を返す"""
        ...

    @property
    @abstractmethod
    def dimension(self) -> int:
        """
        エンベディング次元数を返す

        Returns:
            次元数
        """
        ...

    @abstractmethod
    async def embed_text(self, text: str) -> EmbeddingResult:
        """
        テキストをエンベディングする

        Args:
            text: テキスト

        Returns:
            EmbeddingResult: Embedding結果

        Raises:
            EmbeddingError: エンベディングに失敗した場合
            ValueError: 入力テキストが空の場合
        """
        ...

    @abstractmethod
    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """
        複数テキストをエンベディングする

        Args:
            texts: 埋め込みテキストのリスト

        Returns:
            list[list[float]]: Embedding結果のリスト

        Raises:
            EmbeddingError: エンベディングに失敗した場合
            ValueError: 入力テキストが空の場合
        """
        ...

    async def embed_text_simple(self, text: str) -> list[float]:
        """
        単一テキストを埋め込みベクトルに変換

        Args:
            text: テキスト

        Returns:
            list[float]: Embedding結果
        """
        result = await self.embed_text(text)
        return result.embedding

    @abstractmethod
    async def health_check(self) -> bool:
        """
        状態を確認

        Returns:
            bool: True: 正常, False: 異常
        """
        ...

    async def close(self) -> None:
        """
        リソースを解放
        """
        pass

    async def __aenter__(self) -> "BaseEmbeddingService":
        """
        非同期コンテキストマネージャーの開始
        """
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> None:
        """
        非同期コンテキストマネージャーの終了
        """
        await self.close()
