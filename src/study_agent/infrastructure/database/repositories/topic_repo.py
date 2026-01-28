"""トピックリポジトリ.

Topicモデルのデータアクセス操作を提供する。
"""

from __future__ import annotations

import logging
from typing import Sequence

from sqlmodel import select

from study_agent.infrastructure.database.models import Topic
from study_agent.infrastructure.database.repositories.base import BaseRepository

logger = logging.getLogger(__name__)


class TopicRepository(BaseRepository[Topic]):
    """Topicリポジトリ.

    トピックのCRUD操作と検索機能を提供する。

    Example:
        ```python
        with db_manager.get_session() as session:
            repo = TopicRepository(session)

            # ドキュメントIDで検索
            topics = repo.find_by_document_id("doc-123")

            # 章IDで検索
            topics = repo.find_by_chapter_id("chap-456")

            # タイトルで検索
            topics = repo.search_by_title("EC2")
        ```
    """

    @property
    def _model_class(self) -> type[Topic]:
        """モデルクラスを返す."""
        return Topic

    def find_by_document_id(self, document_id: str) -> Sequence[Topic]:
        """ドキュメントIDでトピックを検索する.

        Args:
            document_id: ドキュメントID

        Returns:
            トピックのリスト
        """
        statement = select(Topic).where(Topic.document_id == document_id)
        return self._session.exec(statement).all()

    def find_by_document_id_ordered(self, document_id: str) -> Sequence[Topic]:
        """ドキュメントIDでトピックを検索する（順序付き）.

        Args:
            document_id: ドキュメントID

        Returns:
            トピックのリスト（order_index順）
        """
        statement = (
            select(Topic)
            .where(Topic.document_id == document_id)
            .order_by(Topic.order_index)
        )
        return self._session.exec(statement).all()

    def find_by_chapter_id(self, chapter_id: str) -> Sequence[Topic]:
        """章IDでトピックを検索する.

        Args:
            chapter_id: 章ID

        Returns:
            トピックのリスト
        """
        statement = select(Topic).where(Topic.chapter_id == chapter_id)
        return self._session.exec(statement).all()

    def find_by_chapter_id_ordered(self, chapter_id: str) -> Sequence[Topic]:
        """章IDでトピックを検索する（順序付き）.

        Args:
            chapter_id: 章ID

        Returns:
            トピックのリスト（order_index順）
        """
        statement = (
            select(Topic)
            .where(Topic.chapter_id == chapter_id)
            .order_by(Topic.order_index)
        )
        return self._session.exec(statement).all()

    def search_by_title(
        self,
        title: str,
        document_id: str | None = None,
    ) -> Sequence[Topic]:
        """タイトルでトピックを検索する.

        Args:
            title: 検索するタイトル（部分一致）
            document_id: ドキュメントIDでフィルタ（オプション）

        Returns:
            マッチしたトピックのリスト
        """
        statement = select(Topic).where(Topic.title.contains(title))
        if document_id is not None:
            statement = statement.where(Topic.document_id == document_id)
        return self._session.exec(statement).all()

    def find_by_title_exact(
        self,
        title: str,
        document_id: str,
    ) -> Topic | None:
        """タイトルでトピックを検索する（完全一致）.

        Args:
            title: トピックタイトル
            document_id: ドキュメントID

        Returns:
            トピック、存在しない場合はNone
        """
        statement = (
            select(Topic)
            .where(Topic.title == title)
            .where(Topic.document_id == document_id)
        )
        return self._session.exec(statement).first()

    def count_by_document_id(self, document_id: str) -> int:
        """ドキュメント内のトピック数を取得する.

        Args:
            document_id: ドキュメントID

        Returns:
            トピック数
        """
        topics = self.find_by_document_id(document_id)
        return len(topics)

    def delete_by_document_id(self, document_id: str) -> int:
        """ドキュメントIDでトピックを削除する.

        Args:
            document_id: ドキュメントID

        Returns:
            削除されたトピック数
        """
        topics = self.find_by_document_id(document_id)
        count = len(topics)
        for topic in topics:
            self.delete(topic)
        return count
