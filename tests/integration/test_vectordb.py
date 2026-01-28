"""VectorDB統合テスト"""

import tempfile
import uuid
from pathlib import Path

import pytest

from study_agent.domain.models import Chunk
from study_agent.infrastructure.vectordb import (
    ChromaDBClient,
    EmbeddingServiceFactory,
    VectorDBConfig,
    VectorDBFactory,
)
from study_agent.infrastructure.vectordb.embeddings.mock import MockEmbeddingService


@pytest.fixture
def temp_persist_dir():
    """一時的な永続化ディレクトリを作成."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def vectordb_config(temp_persist_dir: str) -> VectorDBConfig:
    """テスト用VectorDB設定."""
    return VectorDBConfig(
        provider="chroma",
        persist_directory=temp_persist_dir,
        collection_name=f"test_{uuid.uuid4().hex[:8]}",
        distance_metric="cosine",
    )


@pytest.fixture
def mock_embedding_service() -> MockEmbeddingService:
    """MockEmbeddingServiceを作成."""
    return EmbeddingServiceFactory.create_mock(dimension=768)


@pytest.fixture
async def chroma_client(vectordb_config: VectorDBConfig) -> ChromaDBClient:
    """初期化済みChromaDBクライアントを作成."""
    client = ChromaDBClient(vectordb_config)
    await client.initialize()
    yield client
    await client.close()


@pytest.fixture
def sample_chunks() -> list[Chunk]:
    """テスト用チャンクを作成."""
    return [
        Chunk(
            id=str(uuid.uuid4()),
            document_id="doc-001",
            content="Amazon EC2はクラウドコンピューティングサービスです。仮想サーバーをオンデマンドで提供します。",
            chunk_index=0,
            page_number=1,
            metadata={"section": "compute"},
        ),
        Chunk(
            id=str(uuid.uuid4()),
            document_id="doc-001",
            content="Amazon S3はオブジェクトストレージサービスです。大量のデータを保存できます。",
            chunk_index=1,
            page_number=2,
            metadata={"section": "storage"},
        ),
        Chunk(
            id=str(uuid.uuid4()),
            document_id="doc-001",
            content="AWS Lambdaはサーバーレスコンピューティングサービスです。コードを実行できます。",
            chunk_index=2,
            page_number=3,
            metadata={"section": "compute"},
        ),
    ]


class TestMockEmbeddingService:
    """MockEmbeddingServiceのテスト."""

    @pytest.mark.asyncio
    async def test_embed_text(self, mock_embedding_service: MockEmbeddingService):
        """単一テキストの埋め込み."""
        result = await mock_embedding_service.embed_text("Hello, world!")

        assert result.embedding is not None
        assert len(result.embedding) == 768
        assert result.model.startswith("mock-")
        assert mock_embedding_service.call_count == 1

    @pytest.mark.asyncio
    async def test_embed_texts(self, mock_embedding_service: MockEmbeddingService):
        """複数テキストの埋め込み."""
        texts = ["First text", "Second text", "Third text"]
        embeddings = await mock_embedding_service.embed_texts(texts)

        assert len(embeddings) == 3
        assert all(len(e) == 768 for e in embeddings)
        assert mock_embedding_service.call_count == 3

    @pytest.mark.asyncio
    async def test_deterministic_embedding(
        self, mock_embedding_service: MockEmbeddingService
    ):
        """同じテキストは同じ埋め込みを返す."""
        text = "Deterministic test"
        result1 = await mock_embedding_service.embed_text(text)
        result2 = await mock_embedding_service.embed_text(text)

        assert result1.embedding == result2.embedding

    @pytest.mark.asyncio
    async def test_different_texts_different_embeddings(
        self, mock_embedding_service: MockEmbeddingService
    ):
        """異なるテキストは異なる埋め込みを返す."""
        result1 = await mock_embedding_service.embed_text("Text A")
        result2 = await mock_embedding_service.embed_text("Text B")

        assert result1.embedding != result2.embedding

    @pytest.mark.asyncio
    async def test_empty_text_raises_error(
        self, mock_embedding_service: MockEmbeddingService
    ):
        """空のテキストはエラー."""
        with pytest.raises(ValueError, match="cannot be empty"):
            await mock_embedding_service.embed_text("")

    @pytest.mark.asyncio
    async def test_health_check(self, mock_embedding_service: MockEmbeddingService):
        """ヘルスチェック."""
        assert await mock_embedding_service.health_check() is True


class TestChromaDBClient:
    """ChromaDBClientのテスト."""

    @pytest.mark.asyncio
    async def test_initialize(
        self, vectordb_config: VectorDBConfig, temp_persist_dir: str
    ):
        """初期化."""
        client = ChromaDBClient(vectordb_config)

        assert client.is_initialized is False
        await client.initialize()
        assert client.is_initialized is True

        # ディレクトリが作成されている
        assert Path(temp_persist_dir).exists()

        await client.close()

    @pytest.mark.asyncio
    async def test_add_documents(
        self,
        chroma_client: ChromaDBClient,
        mock_embedding_service: MockEmbeddingService,
        sample_chunks: list[Chunk],
    ):
        """ドキュメントの追加."""
        # 埋め込みを生成
        embeddings = await mock_embedding_service.embed_texts(
            [chunk.content for chunk in sample_chunks]
        )

        # ドキュメントを追加
        embedding_ids = await chroma_client.add_documents(sample_chunks, embeddings)

        assert len(embedding_ids) == len(sample_chunks)

        # 統計を確認
        stats = await chroma_client.get_collection_stats()
        assert stats.count == len(sample_chunks)

    @pytest.mark.asyncio
    async def test_search(
        self,
        chroma_client: ChromaDBClient,
        mock_embedding_service: MockEmbeddingService,
        sample_chunks: list[Chunk],
    ):
        """検索."""
        # ドキュメントを追加
        embeddings = await mock_embedding_service.embed_texts(
            [chunk.content for chunk in sample_chunks]
        )
        await chroma_client.add_documents(sample_chunks, embeddings)

        # 検索クエリの埋め込みを生成
        query_embedding = await mock_embedding_service.embed_text_simple(
            "クラウドコンピューティング EC2"
        )

        # 検索
        results = await chroma_client.search(query_embedding, top_k=2)

        assert len(results) <= 2
        assert all(result.score >= 0 for result in results)
        assert all(result.content for result in results)

    @pytest.mark.asyncio
    async def test_search_with_filter(
        self,
        chroma_client: ChromaDBClient,
        mock_embedding_service: MockEmbeddingService,
        sample_chunks: list[Chunk],
    ):
        """フィルタ付き検索."""
        # ドキュメントを追加
        embeddings = await mock_embedding_service.embed_texts(
            [chunk.content for chunk in sample_chunks]
        )
        await chroma_client.add_documents(sample_chunks, embeddings)

        # フィルタ付きで検索
        query_embedding = await mock_embedding_service.embed_text_simple("サービス")
        results = await chroma_client.search(
            query_embedding,
            top_k=10,
            filter_metadata={"document_id": "doc-001"},
        )

        # すべての結果が指定したdocument_idを持つ
        assert all(
            result.metadata and result.metadata.get("document_id") == "doc-001"
            for result in results
        )

    @pytest.mark.asyncio
    async def test_delete_by_document_id(
        self,
        chroma_client: ChromaDBClient,
        mock_embedding_service: MockEmbeddingService,
        sample_chunks: list[Chunk],
    ):
        """ドキュメントIDによる削除."""
        # ドキュメントを追加
        embeddings = await mock_embedding_service.embed_texts(
            [chunk.content for chunk in sample_chunks]
        )
        await chroma_client.add_documents(sample_chunks, embeddings)

        # 削除前のカウント
        stats_before = await chroma_client.get_collection_stats()
        assert stats_before.count == 3

        # 削除
        deleted_count = await chroma_client.delete_by_document_id("doc-001")
        assert deleted_count == 3

        # 削除後のカウント
        stats_after = await chroma_client.get_collection_stats()
        assert stats_after.count == 0

    @pytest.mark.asyncio
    async def test_clear_collection(
        self,
        chroma_client: ChromaDBClient,
        mock_embedding_service: MockEmbeddingService,
        sample_chunks: list[Chunk],
    ):
        """コレクションのクリア."""
        # ドキュメントを追加
        embeddings = await mock_embedding_service.embed_texts(
            [chunk.content for chunk in sample_chunks]
        )
        await chroma_client.add_documents(sample_chunks, embeddings)

        # クリア前
        stats_before = await chroma_client.get_collection_stats()
        assert stats_before.count > 0

        # クリア
        await chroma_client.clear_collection()

        # クリア後
        stats_after = await chroma_client.get_collection_stats()
        assert stats_after.count == 0


class TestVectorDBFactory:
    """VectorDBFactoryのテスト."""

    def test_create_chroma(self, temp_persist_dir: str):
        """ChromaDBClientの作成."""
        client = VectorDBFactory.create_chroma(
            persist_directory=temp_persist_dir,
            collection_name="test_collection",
        )

        assert isinstance(client, ChromaDBClient)
        assert client.config.collection_name == "test_collection"

    def test_unsupported_provider(self):
        """サポートされていないプロバイダー."""
        from study_agent.core.exceptions import ConfigurationError

        config = VectorDBConfig(
            provider="unsupported",
            persist_directory="./data",
            collection_name="test",
        )

        with pytest.raises(ConfigurationError, match="Unsupported"):
            VectorDBFactory.create(config)


class TestEmbeddingServiceFactory:
    """EmbeddingServiceFactoryのテスト."""

    def test_create_mock(self):
        """MockEmbeddingServiceの作成."""
        service = EmbeddingServiceFactory.create_mock(dimension=512)

        assert isinstance(service, MockEmbeddingService)
        assert service.dimension == 512
