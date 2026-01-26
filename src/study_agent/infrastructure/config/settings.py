"""Pydanticを使用したアプリケーション設定"""

from pathlib import Path
from typing import Optional, Literal
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class OllamaConfig(BaseModel):
    """Ollama設定"""

    base_url: str = "http://localhost:11434"
    model: str = "llama3.1:8b"
    embedding_model: str = "nomic-embed-text"
    fallback_model: Optional[str] = None


class GeminiConfig(BaseModel):
    """Gemini設定"""

    api_key: Optional[str] = None
    model: str = "gemini-3-flash-preview"
    fallback_model: Optional[str] = None


class ClaudeConfig(BaseModel):
    """Claude設定"""

    api_key: Optional[str] = None
    model: str = "claude-4-5-sonnet-20250929"
    enable_caching: bool = True
    fallback_model: Optional[str] = None


class OpenAIConfig(BaseModel):
    """OpenAI設定"""

    api_key: Optional[str] = None
    model: str = "gpt-4o-mini"
    fallback_model: Optional[str] = None


class LLMConfig(BaseModel):
    """LLM設定"""

    provider: Literal["ollama", "gemini", "claude", "openai", "mock"] = "ollama"
    temperature: float = Field(default=0.7, ge=0.0, le=1.0)
    max_tokens: int = Field(default=2048, ge=1)
    timeout: int = Field(default=30, ge=1)
    max_retries: int = Field(default=3, ge=0)

    ollama: OllamaConfig = Field(default_factory=OllamaConfig)
    gemini: GeminiConfig = Field(default_factory=GeminiConfig)
    claude: ClaudeConfig = Field(default_factory=ClaudeConfig)
    openai: OpenAIConfig = Field(default_factory=OpenAIConfig)


class EmbeddingConfig(BaseModel):
    """Embedding設定"""

    provider: Literal["ollama", "gemini", "openai"] = "ollama"
    dimension: int = 768


class VectorDBConfig(BaseModel):
    """VectorDB設定"""

    provider: Literal["chroma"] = "chroma"
    persist_directory: str = "data/vectors/chroma"
    collection_name: str = "study_agent"


class DatabaseConfig(BaseModel):
    """データベース設定"""

    provider: Literal["sqlite"] = "sqlite"
    path: str = "data/db/study_agent.db"


class ChunkingConfig(BaseModel):
    """Chunking設定"""

    chunk_size: int = Field(default=1000, ge=100)
    chunk_overlap: int = Field(default=200, ge=0)


class DocumentConfig(BaseModel):
    """Document設定"""

    max_file_size_mb: int = Field(default=50, ge=1)
    max_pages: int = Field(default=500, ge=1)
    supported_formats: list[str] = Field(default_factory=lambda: ["pdf", "md", "txt"])


class QuizConfig(BaseModel):
    """Quiz設定"""

    default_difficulty: int = Field(default=3, ge=1, le=5)
    default_count: int = Field(default=5, ge=1)
    default_type: Literal["multiple_choice", "open", "true_false"] = "multiple_choice"


class ProgressConfig(BaseModel):
    """Progress設定"""

    mastery_threshold: int = Field(default=80, ge=0, le=100)
    weak_topic_threshold: int = Field(default=50, ge=0, le=100)


class LoggingConfig(BaseModel):
    """Logging設定"""

    level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    file: Optional[str] = "data/logs/study_agent.log"
    json_format: bool = False


class CLIConfig(BaseModel):
    """CLI設定"""

    rich_output: bool = True
    show_timestamp: bool = False
    color_theme: Literal["dark", "light", "auto"] = "auto"


class AppConfig(BaseModel):
    """アプリケーション設定"""

    model_config = SettingsConfigDict(
        env_prefix="STUDYAGENT_",
        env_nested_delimiter="__",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "StudyAgent"
    version: str = "0.1.0"
    debug: bool = False

    llm: LLMConfig = Field(default_factory=LLMConfig)
    embedding: EmbeddingConfig = Field(default_factory=EmbeddingConfig)
    vector_db: VectorDBConfig = Field(default_factory=VectorDBConfig)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    chunking: ChunkingConfig = Field(default_factory=ChunkingConfig)
    document: DocumentConfig = Field(default_factory=DocumentConfig)
    quiz: QuizConfig = Field(default_factory=QuizConfig)
    progress: ProgressConfig = Field(default_factory=ProgressConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    cli: CLIConfig = Field(default_factory=CLIConfig)
