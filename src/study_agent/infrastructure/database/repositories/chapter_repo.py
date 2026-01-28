"""章リポジトリ.

Chapterモデルのデータアクセス操作を提供する。
"""

from __future__ import annotations

import logging
from typing import Sequence

from sqlmodel import select

from study_agent.infrastructure.database.models import Chapter
from study_agent.infrastructure.database.repositories.base import BaseRepository

logger = logging.getLogger(__name__)


class ChapterRepository(BaseRepository[Chapter]):
    """Chapterリポジトリ.

    章のCRUD操作と検索機能を提供する。

    Example:
        ```python
        with db_manager.get_session() as session:
            repo = ChapterRepository(session)

            # ドキュメントIDで検索
            chapters = repo.find_by_document_id("doc-123")

            # 順序付きで取得
            chapters = repo.find_by_document_id_ordered("doc-123")
        ```
    """

    @property
    def _model_class(self) -> type[Chapter]:
        """モデルクラスを返す."""
        return Chapter

    def find_by_document_id(self, document_id: str) -> Sequence[Chapter]:
        """ドキュメントIDで章を検索する.

        Args:
            document_id: ドキュメントID

        Returns:
            章のリスト
        """
        statement = select(Chapter).where(Chapter.document_id == document_id)
        return self._session.exec(statement).all()

    def find_by_document_id_ordered(self, document_id: str) -> Sequence[Chapter]:
        """ドキュメントIDで章を検索する（順序付き）.

        Args:
            document_id: ドキュメントID

        Returns:
            章のリスト（order_index順）
        """
        statement = (
            select(Chapter)
            .where(Chapter.document_id == document_id)
            .order_by(Chapter.order_index)
        )
        return self._session.exec(statement).all()

    def find_by_title(
        self,
        document_id: str,
        title: str,
    ) -> Chapter | None:
        """ドキュメント内で章タイトルを検索する.

        Args:
            document_id: ドキュメントID
            title: 章タイトル

        Returns:
            章、存在しない場合はNone
        """
        statement = (
            select(Chapter)
            .where(Chapter.document_id == document_id)
            .where(Chapter.title == title)
        )
        return self._session.exec(statement).first()

    def find_by_page(
        self,
        document_id: str,
        page_number: int,
    ) -> Chapter | None:
        """ページ番号で章を検索する.

        Args:
            document_id: ドキュメントID
            page_number: ページ番号

        Returns:
            章、存在しない場合はNone
        """
        statement = (
            select(Chapter)
            .where(Chapter.document_id == document_id)
            .where(Chapter.page_start <= page_number)
            .where(Chapter.page_end >= page_number)
        )
        return self._session.exec(statement).first()

    def count_by_document_id(self, document_id: str) -> int:
        """ドキュメント内の章数を取得する.

        Args:
            document_id: ドキュメントID

        Returns:
            章数
        """
        chapters = self.find_by_document_id(document_id)
        return len(chapters)

    def delete_by_document_id(self, document_id: str) -> int:
        """ドキュメントIDで章を削除する.

        Args:
            document_id: ドキュメントID

        Returns:
            削除された章数
        """
        chapters = self.find_by_document_id(document_id)
        count = len(chapters)
        for chapter in chapters:
            self.delete(chapter)
        return count
