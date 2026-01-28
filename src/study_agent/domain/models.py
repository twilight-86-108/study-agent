"""ドメインモデル定義"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional


@dataclass
class Chunk:
    """
    RAG用のチャンク

    ドキュメントから分割したテキストチャンクで、ベクトルDBに保存され、RAG検索に使用される

    Attributes:
        id: チャンクID（UUID）
        document_id: ドキュメントID
        content: テキストコンテンツ
        chunk_index: ドキュメント内でのチャンクのインデックス
        page_number: ページ番号
        embedding_id: ベクトルID
        metadata: メタデータ
        created_at: 作成日時
    """

    id: str
    document_id: str
    content: str
    chunk_index: int
    page_number: Optional[int] = None
    embedding_id: Optional[str] = None
    metadata: Optional[dict[str, Any]] = None
    created_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self) -> None:
        """バリデーション"""
        if not self.content or not self.content.strip():
            raise ValueError("Chunk content cannot be empty")
        if self.chunk_index < 0:
            raise ValueError("Chunk index must be non-negative")
