"""Mock Embedding Service"""

import hashlib
import logging
import math
from typing import Any

from study_agent.infrastructure.vectordb.embeddings.base import (
    BaseEmbeddingService,
    EmbeddingConfig,
    EmbeddingProvider,
    EmbeddingResult,
)

logger = logging.getLogger(__name__)

DEFAULT_MOCK_DIMENTION = 768


class MockEmbeddingService(BaseEmbeddingService):
    """Mock embedding service"""

    def __init__(
        self,
        config: EmbeddingConfig | None = None,
        dimention: int = DEFAULT_MOCK_DIMENTION,
    ) -> None:
        """
        初期化

        Args:
            config: Embedding設定
            dimention: 埋め込みベクトルの次元数
        """
        if config is None:
            config = EmbeddingConfig.for_mock(dimension=dimention)
        super().__init__(config)

        # モデル名から次元数を抽出
        self._dimention = dimention
        if config.model.startswith("mock-"):
            try:
                self._dimention = int(config.model.split("-")[1])
            except (IndexError, ValueError):
                pass

        self._call_count = 0
        self._embed_history: list[str] = []

    @property
    def provider(self) -> EmbeddingProvider:
        """プロバイダーを取得"""
        return EmbeddingProvider.MOCK

    @property
    def dimension(self) -> int:
        """埋め込みベクトルの次元数を返す"""
        return self._dimention

    @property
    def call_count(self) -> int:
        """呼び出し回数を返す"""
        return self._call_count

    def reset_stats(self) -> None:
        """統計情報をリセット"""
        self._call_count = 0
        self._embed_history.clear()

    def _generate_embedding(self, text: str) -> list[float]:
        """
        テキストから埋め込みベクトルを生成

        Args:
            text: テキスト

        Returns:
            list[float]: 埋め込みベクトル
        """
        # テキストのハッシュ値を計算
        text_hash = hashlib.sha256(text.encode()).hexdigest()
        # ハッシュの各文字を使いベクトル生成
        embedding: list[float] = []
        for i in range(self._dimention):
            hash_idx = i % len(text_hash)
            char_val = int(text_hash[hash_idx], 16)

            # 0-255の値を-1.0から1.0の範囲に正規化
            seed = (i * 17 + char_val * 31) % 256
            value = (seed / 255.0) * 2.0 - 1.0
            embedding.append(value)

        norm = math.sqrt(sum(x * x for x in embedding))
        if norm > 0:
            embedding = [x / norm for x in embedding]

        return embedding

    async def embed_text(self, text: str) -> EmbeddingResult:
        """
        単一テキストを埋め込みベクトルに変換する

        Args:
            text: テキスト

        Returns:
            EmbeddingResult: 埋め込みベクトル

        Raises:
            ValueError: テキストが空の場合
        """
        if not text or not text.strip():
            raise ValueError("Text cannot be empty")

        self._call_count += 1
        self._embed_history.append(text)

        embedding = self._generate_embedding(text)
        return EmbeddingResult(
            embedding=embedding,
            model=self.config.model,
            token_count=len(text.split()),
        )

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """
        複数テキストを埋め込みベクトルに変換する

        Args:
            texts: テキストリスト

        Returns:
            list[list[float]]: 埋め込みベクトルリスト

        Raises:
            ValueError: テキストが空の場合
        """
        if not texts:
            raise ValueError("Texts cannot be empty")

        embeddings: list[list[float]] = []
        for text in texts:
            result = await self.embed_text(text)
            embeddings.append(result.embedding)

        return embeddings

    async def health_check(self) -> bool:
        """ヘルスチェック"""
        return True

    async def close(self) -> None:
        """リソースを解放"""
        pass
