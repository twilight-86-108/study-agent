"""Ollama Embedding Service"""

import logging
from typing import Any

import httpx

from study_agent.core.exceptions import EmbeddingError
from study_agent.infrastructure.vectordb.embeddings.base import (
    BaseEmbeddingService,
    EmbeddingConfig,
    EmbeddingProvider,
    EmbeddingResult,
)

logger = logging.getLogger(__name__)

OLLAMA_MODEL_DIMENSIONS = {
    "nomic-embed-text": 768,
    "mxbai-embed-large": 1024,
    "all-minilm": 384,
    "snowflake-arctic-embed": 1024,
}

DEFAULT_DIMENTION = 768


class OllamaEmbeddingService(BaseEmbeddingService):
    """
    Ollama Embedding Service
    Ollamaのローカルサーバーを利用し、埋め込みベクトルを生成
    """

    def __init__(self, config: EmbeddingConfig) -> None:
        """
        初期化

        Args:
            config: Embedidng設定
        """
        super().__init__(config)
        self._base_url = config.base_url or "http://localhost:11434"
        self._client: httpx.AsyncClient | None = None
        self._dimention: int | None = None

    @property
    def provider(self) -> EmbeddingProvider:
        """プロバイダーを取得"""
        return EmbeddingProvider.OLLAMA

    @property
    def dimension(self) -> int:
        """埋め込みベクトルの次元数を返す"""
        if self._dimention is not None:
            return self._dimention

        # モデルから次元数を取得
        model_name = self.config.model.lower()
        for model_key, dim in OLLAMA_MODEL_DIMENSIONS.items():
            if model_key in model_name:
                self._dimention = dim
                return dim
        # 不明な場合、デフォルト
        logger.warning(
            f"Unknown model: {self.config.model}. Using default dimension: {DEFAULT_DIMENTION}"
        )
        self._dimention = DEFAULT_DIMENTION
        return DEFAULT_DIMENTION

    def _get_client(self) -> httpx.AsyncClient:
        """HTTPクライアントを取得"""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self._base_url,
                timeout=httpx.Timeout(self.config.timeout),
            )
        return self._client

    async def embed_text(self, text: str) -> EmbeddingResult:
        """
        単一テキストを埋め込みベクトルに変換する

        Args:
            text: テキスト

        Returns:
            EmbeddingResult: 埋め込みベクトル

        Raises:
            EmbeddingError: 埋め込み生成に失敗した場合
            ValueError: テキストが空の場合
        """
        if not text or not text.strip():
            raise ValueError("Text cannot be empty")

        client = self._get_client()

        try:
            response = await client.post(
                "/api/embeddings",
                json={
                    "model": self.config.model,
                    "input": text,
                },
            )
            response.raise_for_status()
            data = response.json()

            embedding = data.get("embedding")
            if embedding is None:
                raise EmbeddingError(
                    message="No embedding in response",
                    details={"response": data},
                )

            # 次元数を記録
            if self._dimention is None:
                self._dimention = len(embedding)

            return EmbeddingResult(
                embedding=embedding,
                model=self.config.model,
            )

        except httpx.ConnectError as e:
            raise EmbeddingError(
                message="Failed to connect to Ollama server",
                details={"base_url": self._base_url},
                cause=e,
            ) from e
        except httpx.TimeoutException as e:
            raise EmbeddingError(
                message="Ollama server timeout",
                details={"timeout": self.config.timeout},
                cause=e,
            ) from e
        except httpx.HTTPStatusError as e:
            raise EmbeddingError(
                message=f"Ollama server error: {e.response.status_code}",
                details={
                    "status_code": e.response.status_code,
                    "response": e.response.text,
                },
                cause=e,
            ) from e
        except Exception as e:
            raise EmbeddingError(
                message=f"Unexpected error during embedding: {e}",
                cause=e,
            ) from e

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """
        複数テキストを埋め込みベクトルに変換する

        Args:
            texts: テキストリスト

        Returns:
            list[list[float]]: 埋め込みベクトルリスト

        Raises:
            EmbeddingError: 埋め込み生成に失敗した場合
            ValueError: テキストが空の場合
        """
        if not texts:
            raise ValueError("Texts cannot be empty")

        embeddings: list[list[float]] = []

        total = len(texts)
        for i, text in enumerate(texts):
            if i % 10 == 0:
                logger.debug(f"Embedding {i}/{total}")

            result = await self.embed_text(text)
            embeddings.append(result.embedding)

        logger.info(f"Embedded {total} texts using {self.config.model}")
        return embeddings

    async def health_check(self) -> bool:
        """ヘルスチェック"""
        client = self._get_client()

        try:
            response = await client.get("/api/tags")
            if response.status_code == 200:
                # モデル利用可か確認
                data = response.json()
                models = data.get("models", [])
                model_names = [m.get("name", "").split(":")[0] for m in models]

                model_base = self.config.model.split(":")[0]
                if model_base in model_names:
                    return True

                logger.warning(
                    f"Model '{self.config.model}' not found."
                    f"Available models: {model_names}"
                )
                return False

            return False
        except Exception as e:
            logger.warning(f"Ollama health check failed: {e}")
            return False

    async def close(self) -> None:
        """クライアントを閉じる"""
        if self._client is not None:
            await self._client.aclose()
            self._client = None
