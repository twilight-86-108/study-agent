"""VectorDBの抽象基底クラス"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Optional

from study_agent.domain.models import Chunk


@dataclass
class ChunkData:
    """
    VectorDBに追加するチャンクデータ

    Attributes:
        chunk_id: チャンクID
        content: テキスト内容
        embedding: エンベディングベクトル
        metadata: メタデータ
    """

    chunk_id: str
    content: str
    embedding: list[float]
    metadata: dict[str, Any]


@dataclass
class SearchResult:
    """
    ベクトル検索結果

    Attributes:
        chunk_id: チャンクID
        content: チャンクのテキスト内容
        score: 類似度スコア（0.0-1.0、高いほど類似）
        metadata: 追加メタデータ（document_id, page_number等）
    """

    chunk_id: str
    content: str
    score: float
    metadata: Optional[dict[str, Any]] = None


@dataclass
class VectorDBConfig:
    """
    VectorDB設定

    Attributes:
        provider: プロバイダー名（"chroma"等）
        persist_directory: データ永続化ディレクトリパス
        collection_name: コレクション名
        distance_metric: 距離メトリクス（"cosine", "l2", "ip"）
    """

    provider: str
    persist_directory: str
    collection_name: str
    distance_metric: str

    def __post_init__(self) -> None:
        """バリデーション"""
        valid_metrics = {"cosine", "l2", "ip"}
        if self.distance_metric not in valid_metrics:
            raise ValueError(
                f"Invalid distance metric: {self.distance_metric}"
                f"Must be one of: {valid_metrics}"
            )


@dataclass
class CollectionStats:
    """
    コレクション統計情報

    Attributes:
        count: チャンク数
        collection_name: コレクション名
        metadata: メタデータ
    """

    count: int
    collection_name: str
    metadata: Optional[dict[str, Any]] = field(default_factory=dict)


class BaseVectorDB(ABC):
    """
    VectorDBの抽象基底クラス
    全てのVectorDBクライアントはこのクラスを継承
    """

    def __init__(self, config: VectorDBConfig) -> None:
        """初期化"""
        self.config = config
        self._initialized = False

    @property
    def is_initialized(self) -> bool:
        """初期化済みかどうか"""
        return self._initialized

    @abstractmethod
    async def initialize(self) -> None:
        """
        VectorDBを初期化

        Raises:
            VectorDBError: 初期化に失敗した場合
        """
        ...

    @abstractmethod
    async def add_documents(
        self,
        chunks: list[Chunk],
        embeddings: list[list[float]],
    ) -> list[str]:
        """
        ドキュメントをベクトルDBに追加

        Args:
            chunks: チャンクリスト
            embeddings: エンベディングリスト

        Returns:
            list[str]: ベクトルIDリスト

        Raises:
            VectorDBError: ドキュメント追加に失敗した場合
            ValueError: チャンク数とエンベディング数が一致しない場合
        """
        ...

    @abstractmethod
    async def search(
        self,
        query_embedding: list[float],
        top_k: int = 5,
        filter_metadata: Optional[dict[str, Any]] = None,
    ) -> list[SearchResult]:
        """
        類似検索を実行

        Args:
            query_embedding: クエリのエンベディング
            top_k: 返す結果の最大数
            filter_metadata: フィルタリング用メタデータ

        Returns:
            list[SearchResult]: 類似度が高い順に並んだ検索結果リスト

        Raises:
            SearchError: 検索に失敗した場合
        """
        ...

    @abstractmethod
    async def delete_document(self, document_id: str) -> int:
        """
        指定したドキュメントIDに関連する全てのチャンクを削除する

        Args:
            document_id: ドキュメントID

        Returns:
            int: 削除されたチャンク数

        Raises:
            VectorDBError: ドキュメント削除に失敗した場合
        """
        ...

    @abstractmethod
    async def delete_by_ids(self, embedding_ids: list[str]) -> int:
        """
        指定したベクトルIDに関連するチャンクを削除する

        Args:
            embedding_ids: ベクトルIDリスト

        Returns:
            int: 削除されたチャンク数

        Raises:
            VectorDBError: ベクトルID削除に失敗した場合
        """
        ...

    @abstractmethod
    async def clear_collection(self) -> None:
        """
        コレクションをクリアする

        Raises:
            VectorDBError: コレクションクリアに失敗した場合
        """
        ...

    async def close(self) -> None:
        """
        リソースを解放する
        """
        self._initialized = False

    async def __aenter__(self) -> "BaseVectorDB":
        """
        コンテキストマネージャー用
        """
        await self.initialize()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        """
        コンテキストマネージャー用
        """
        await self.close()
