"""CLI tests.

CLIコマンドのユニットテスト。
"""

import pytest
from typer.testing import CliRunner
from unittest.mock import AsyncMock, patch, MagicMock

from study_agent.cli.app import app
from study_agent.cli.utils import format_file_size, truncate_text, get_progress_bar
from study_agent.core.constants import APP_NAME, APP_VERSION


runner = CliRunner()


# =============================================================================
# App Tests
# =============================================================================


class TestAppCommands:
    """CLIアプリケーションのテスト."""

    def test_version(self):
        """--version オプションのテスト."""
        result = runner.invoke(app, ["--version"])
        assert result.exit_code == 0
        assert APP_NAME in result.output
        assert APP_VERSION in result.output

    def test_help(self):
        """--help オプションのテスト."""
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "AI-Powered Learning Assistant" in result.output
        assert "load" in result.output
        assert "chat" in result.output

    def test_no_args(self):
        """引数なしで実行した場合のテスト."""
        result = runner.invoke(app, [])
        assert result.exit_code == 0
        # ウェルカムメッセージが表示される
        assert APP_NAME in result.output

    def test_load_help(self):
        """load --help のテスト."""
        result = runner.invoke(app, ["load", "--help"])
        assert result.exit_code == 0
        assert "Load documents" in result.output or "load" in result.output.lower()

    def test_explain_help(self):
        """explain --help のテスト."""
        result = runner.invoke(app, ["explain", "--help"])
        assert result.exit_code == 0
        assert "Topic or concept to explain" in result.output

    def test_quiz_help(self):
        """quiz --help のテスト."""
        result = runner.invoke(app, ["quiz", "--help"])
        assert result.exit_code == 0
        assert "quiz" in result.output.lower()

    def test_progress_help(self):
        """progress --help のテスト."""
        result = runner.invoke(app, ["progress", "--help"])
        assert result.exit_code == 0
        assert "learning progress" in result.output.lower()

    def test_chat_help(self):
        """chat --help のテスト."""
        result = runner.invoke(app, ["chat", "--help"])
        assert result.exit_code == 0
        assert "interactive" in result.output.lower()


# =============================================================================
# Utility Tests
# =============================================================================


class TestUtils:
    """ユーティリティ関数のテスト."""

    def test_format_file_size_bytes(self):
        """バイト単位のサイズフォーマット."""
        assert format_file_size(100) == "100.0 B"
        assert format_file_size(500) == "500.0 B"

    def test_format_file_size_kb(self):
        """KB単位のサイズフォーマット."""
        assert format_file_size(1024) == "1.0 KB"
        assert format_file_size(2048) == "2.0 KB"

    def test_format_file_size_mb(self):
        """MB単位のサイズフォーマット."""
        assert format_file_size(1024 * 1024) == "1.0 MB"
        assert format_file_size(5 * 1024 * 1024) == "5.0 MB"

    def test_format_file_size_gb(self):
        """GB単位のサイズフォーマット."""
        assert format_file_size(1024 * 1024 * 1024) == "1.0 GB"

    def test_truncate_text_short(self):
        """短いテキストの切り詰め（切り詰めなし）."""
        text = "Hello World"
        assert truncate_text(text, 50) == text

    def test_truncate_text_exact(self):
        """ちょうどの長さのテキスト."""
        text = "12345"
        assert truncate_text(text, 5) == text

    def test_truncate_text_long(self):
        """長いテキストの切り詰め."""
        text = "Hello World, this is a long text"
        result = truncate_text(text, 15)
        assert len(result) == 15
        assert result.endswith("...")

    def test_get_progress_bar_empty(self):
        """進捗0%のバー."""
        bar = get_progress_bar(0)
        assert "░" in bar
        assert "█" not in bar or bar.count("█") == 0

    def test_get_progress_bar_full(self):
        """進捗100%のバー."""
        bar = get_progress_bar(1.0)
        assert "█" in bar

    def test_get_progress_bar_half(self):
        """進捗50%のバー."""
        bar = get_progress_bar(0.5)
        assert "█" in bar
        assert "░" in bar

    def test_get_progress_bar_percentage(self):
        """パーセンテージ入力（0-100）."""
        bar = get_progress_bar(50)  # 50%
        assert "█" in bar


# =============================================================================
# Load Command Tests
# =============================================================================


class TestLoadCommand:
    """loadコマンドのテスト."""

    def test_load_file_not_found(self):
        """存在しないファイルの読み込み."""
        result = runner.invoke(app, ["load", "file", "nonexistent.pdf"])
        # exit_codeは0または1（handle_errorsデコレータによる）
        assert "not found" in result.output.lower() or "error" in result.output.lower()

    def test_load_list_empty(self):
        """ドキュメントなしのリスト表示."""
        with patch("study_agent.cli.commands.load.get_container") as mock_container:
            mock_cm = AsyncMock()
            mock_cm.__aenter__.return_value.document_service.list_documents = AsyncMock(
                return_value=[]
            )
            mock_container.return_value = mock_cm

            result = runner.invoke(app, ["load", "list"])
            assert result.exit_code == 0
            assert "no documents" in result.output.lower()


# =============================================================================
# Topics Command Tests
# =============================================================================


class TestTopicsCommand:
    """topicsコマンドのテスト."""

    def test_topics_no_documents(self):
        """ドキュメントなしのトピック表示."""
        with patch("study_agent.cli.commands.topics.get_container") as mock_container:
            mock_cm = AsyncMock()
            mock_cm.__aenter__.return_value.document_service.list_documents = AsyncMock(
                return_value=[]
            )
            mock_container.return_value = mock_cm

            result = runner.invoke(app, ["topics"])
            assert result.exit_code == 0
            assert "no documents" in result.output.lower()


# =============================================================================
# Container Tests
# =============================================================================


class TestContainer:
    """Containerのテスト."""

    @pytest.mark.asyncio
    async def test_container_create(self):
        """コンテナの作成."""
        from study_agent.container import Container
        from study_agent.infrastructure.config import AppConfig, DatabaseConfig

        # In-memory DBを使用
        config = AppConfig()
        config.database = DatabaseConfig(url="sqlite:///:memory:")
        container = await Container.create(config, use_mock=True)

        assert container is not None
        assert container.config == config
        assert container.llm_client is not None
        assert container.vectordb is not None

        await container.close()

    @pytest.mark.asyncio
    async def test_container_context_manager(self):
        """コンテナのコンテキストマネージャ."""
        from study_agent.container import Container
        from study_agent.infrastructure.config import AppConfig, DatabaseConfig

        # In-memory DBを使用
        config = AppConfig()
        config.database = DatabaseConfig(url="sqlite:///:memory:")

        async with await Container.create(config, use_mock=True) as container:
            assert container is not None

    @pytest.mark.asyncio
    async def test_container_services(self):
        """コンテナからサービスを取得."""
        from study_agent.container import Container
        from study_agent.infrastructure.config import AppConfig, DatabaseConfig

        # In-memory DBを使用
        config = AppConfig()
        config.database = DatabaseConfig(url="sqlite:///:memory:")
        container = await Container.create(config, use_mock=True)

        # サービスは遅延初期化
        assert container._document_service is None

        # アクセスすると初期化される
        doc_service = container.document_service
        assert doc_service is not None
        assert container._document_service is not None

        await container.close()


# =============================================================================
# Mock LLM Tests
# =============================================================================


class TestMockLLM:
    """MockLLMClientのテスト."""

    @pytest.mark.asyncio
    async def test_mock_generate(self):
        """モックLLMのテキスト生成."""
        from study_agent.container import MockLLMClient

        client = MockLLMClient()
        response = await client.generate("Test prompt")

        assert response.content is not None
        assert response.model == "mock"

    @pytest.mark.asyncio
    async def test_mock_generate_json(self):
        """モックLLMのJSON生成."""
        from study_agent.container import MockLLMClient

        client = MockLLMClient()
        response = await client.generate_json("Test prompt", {"type": "object"})

        assert isinstance(response, dict)
        assert "mock" in response

    @pytest.mark.asyncio
    async def test_mock_embed(self):
        """モックLLMのエンベッディング."""
        from study_agent.container import MockLLMClient

        client = MockLLMClient()
        embedding = await client.embed_text("Test text")

        assert isinstance(embedding, list)
        assert len(embedding) > 0
        assert all(isinstance(v, float) for v in embedding)
