"""Vector DB Settings"""

from typing import Literal, Optional
from pydantic import BaseModel, Field


class OllamaEmbeddingConfig(BaseModel):
    """Ollama Embedding 設定"""

    base_url: str = "http://localhost:11434"
    model: str = "nomic-embed-text"


class OpenAIEmbeddingConfig(BaseModel):
    """OpenAI Embedding 設定"""

    api_key: Optional[str] = None
    model: str = "text-embedding-3-small"


class GeminiEmbeddingConfig(BaseModel):
    """Gemini Embedding 設定"""

    api_key: Optional[str] = None
    model: str = "text-embedding-004"


class EmbeddingConfig(BaseModel):
    """Embedding 設定"""

    provider: Literal["ollama", "openai", "gemini", "mock"] = "ollama"
    timeout: int = Field(default=60, ge=1, description="Embedding timeout")

    ollama: OllamaEmbeddingConfig = Field(default_factory=OllamaEmbeddingConfig)
    openai: OpenAIEmbeddingConfig = Field(default_factory=OpenAIEmbeddingConfig)
    gemini: GeminiEmbeddingConfig = Field(default_factory=GeminiEmbeddingConfig)


class VectorDBConfig(BaseModel):
    """Vector DB 設定"""

    provider: Literal["chroma"] = "chroma"
    presist_directory: str = Field(
        default="./data/vectors/chroma",
        description="データ永続化（VectorDB）用ディレクトリ",
    )
    collection_name: str = Field(default="study_agent", description="コレクション名")
    distance_metric: Literal["cosine", "l2", "ip"] = Field(
        default="cosine", description="距離測定方法"
    )
