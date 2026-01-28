"""ドキュメントリポジトリ.

Documentモデルのデータアクセス操作を提供する。
"""

from __future__ import annotations

import logging
from typing import Optional, Sequence

from sqlmodel import select

from study_agent.infrastructure.database.models import Document, FileType
from study_agent.infrastructure.database.repositories.base import BaseRepository

logger = logging.getLogger(__name__)


class DocumentRepository(BaseRepository[Document]):
    """Documentリポジトリ.

    ドキュメントのCRUD操作と検索機能を提供する。

    Example:
        ```python
        with db_manager.get_session() as session:
            repo = DocumentRepository(session)

            # ファイルパスで検索
            doc = repo.find_by_file_path("/path/to/file.pdf")

            # タイトルで検索
            docs = repo.find_by_title("AWS SAA")

            # ファイルタイプで検索
            pdfs = repo.find_by_file_type(FileType.PDF)
        ```
    """

    @property
    def _model_class(self) -> type[Document]:
        """モデルクラスを返す."""
        return Document

    def find_by_file_path(self, file_path: str) -> Document | None:
        """ファイルパスでドキュメントを検索する.

        Args:
            file_path: ファイルパス

        Returns:
            ドキュメント、存在しない場合はNone
        """
        statement = select(Document).where(Document.file_path == file_path)
        return self._session.exec(statement).first()

    def find_by_title(
        self,
        title: str,
        exact_match: bool = False,
    ) -> Sequence[Document]:
        """タイトルでドキュメントを検索する.

        Args:
            title: 検索するタイトル
            exact_match: 完全一致検索の場合True

        Returns:
            マッチしたドキュメントのリスト
        """
        if exact_match:
            statement = select(Document).where(Document.title == title)
        else:
            statement = select(Document).where(Document.title.contains(title))
        return self._session.exec(statement).all()

    def find_by_file_type(self, file_type: FileType) -> Sequence[Document]:
        """ファイルタイプでドキュメントを検索する.

        Args:
            file_type: ファイルタイプ

        Returns:
            マッチしたドキュメントのリスト
        """
        statement = select(Document).where(Document.file_type == file_type)
        return self._session.exec(statement).all()

    def get_recent(self, limit: int = 10) -> Sequence[Document]:
        """最近追加されたドキュメントを取得する.

        Args:
            limit: 取得数

        Returns:
            ドキュメントのリスト（作成日時降順）
        """
        statement = select(Document).order_by(Document.created_at.desc()).limit(limit)
        return self._session.exec(statement).all()

    def exists_by_file_path(self, file_path: str) -> bool:
        """ファイルパスでドキュメントの存在を確認する.

        Args:
            file_path: ファイルパス

        Returns:
            存在する場合True
        """
        return self.find_by_file_path(file_path) is not None
