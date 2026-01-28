"""クイズリポジトリ.

Quizモデルのデータアクセス操作を提供する。
"""

from __future__ import annotations

import logging
from typing import Sequence

from sqlmodel import select

from study_agent.infrastructure.database.models import Quiz, QuizType
from study_agent.infrastructure.database.repositories.base import BaseRepository

logger = logging.getLogger(__name__)


class QuizRepository(BaseRepository[Quiz]):
    """Quizリポジトリ.

    クイズのCRUD操作と検索機能を提供する。

    Example:
        ```python
        with db_manager.get_session() as session:
            repo = QuizRepository(session)

            # トピックIDで検索
            quizzes = repo.find_by_topic_id("topic-123")

            # 難易度で検索
            quizzes = repo.find_by_difficulty(3)

            # ランダムに取得
            quizzes = repo.get_random(count=5, document_id="doc-123")
        ```
    """

    @property
    def _model_class(self) -> type[Quiz]:
        """モデルクラスを返す."""
        return Quiz

    def find_by_document_id(self, document_id: str) -> Sequence[Quiz]:
        """ドキュメントIDでクイズを検索する.

        Args:
            document_id: ドキュメントID

        Returns:
            クイズのリスト
        """
        statement = select(Quiz).where(Quiz.document_id == document_id)
        return self._session.exec(statement).all()

    def find_by_topic_id(self, topic_id: str) -> Sequence[Quiz]:
        """トピックIDでクイズを検索する.

        Args:
            topic_id: トピックID

        Returns:
            クイズのリスト
        """
        statement = select(Quiz).where(Quiz.topic_id == topic_id)
        return self._session.exec(statement).all()

    def find_by_difficulty(
        self,
        difficulty: int,
        document_id: str | None = None,
    ) -> Sequence[Quiz]:
        """難易度でクイズを検索する.

        Args:
            difficulty: 難易度（1-5）
            document_id: ドキュメントIDでフィルタ（オプション）

        Returns:
            クイズのリスト
        """
        statement = select(Quiz).where(Quiz.difficulty == difficulty)
        if document_id is not None:
            statement = statement.where(Quiz.document_id == document_id)
        return self._session.exec(statement).all()

    def find_by_difficulty_range(
        self,
        min_difficulty: int,
        max_difficulty: int,
        document_id: str | None = None,
    ) -> Sequence[Quiz]:
        """難易度範囲でクイズを検索する.

        Args:
            min_difficulty: 最小難易度（1-5）
            max_difficulty: 最大難易度（1-5）
            document_id: ドキュメントIDでフィルタ（オプション）

        Returns:
            クイズのリスト
        """
        statement = (
            select(Quiz)
            .where(Quiz.difficulty >= min_difficulty)
            .where(Quiz.difficulty <= max_difficulty)
        )
        if document_id is not None:
            statement = statement.where(Quiz.document_id == document_id)
        return self._session.exec(statement).all()

    def find_by_quiz_type(
        self,
        quiz_type: QuizType,
        document_id: str | None = None,
    ) -> Sequence[Quiz]:
        """クイズタイプで検索する.

        Args:
            quiz_type: クイズタイプ
            document_id: ドキュメントIDでフィルタ（オプション）

        Returns:
            クイズのリスト
        """
        statement = select(Quiz).where(Quiz.quiz_type == quiz_type)
        if document_id is not None:
            statement = statement.where(Quiz.document_id == document_id)
        return self._session.exec(statement).all()

    def get_random(
        self,
        count: int = 5,
        document_id: str | None = None,
        topic_id: str | None = None,
        difficulty: int | None = None,
        quiz_type: QuizType | None = None,
    ) -> Sequence[Quiz]:
        """ランダムにクイズを取得する.

        Args:
            count: 取得数
            document_id: ドキュメントIDでフィルタ（オプション）
            topic_id: トピックIDでフィルタ（オプション）
            difficulty: 難易度でフィルタ（オプション）
            quiz_type: クイズタイプでフィルタ（オプション）

        Returns:
            クイズのリスト
        """
        from sqlalchemy.sql.expression import func

        statement = select(Quiz)

        if document_id is not None:
            statement = statement.where(Quiz.document_id == document_id)
        if topic_id is not None:
            statement = statement.where(Quiz.topic_id == topic_id)
        if difficulty is not None:
            statement = statement.where(Quiz.difficulty == difficulty)
        if quiz_type is not None:
            statement = statement.where(Quiz.quiz_type == quiz_type)

        statement = statement.order_by(func.random()).limit(count)
        return self._session.exec(statement).all()

    def count_by_document_id(self, document_id: str) -> int:
        """ドキュメント内のクイズ数を取得する.

        Args:
            document_id: ドキュメントID

        Returns:
            クイズ数
        """
        quizzes = self.find_by_document_id(document_id)
        return len(quizzes)

    def count_by_topic_id(self, topic_id: str) -> int:
        """トピック内のクイズ数を取得する.

        Args:
            topic_id: トピックID

        Returns:
            クイズ数
        """
        quizzes = self.find_by_topic_id(topic_id)
        return len(quizzes)

    def delete_by_document_id(self, document_id: str) -> int:
        """ドキュメントIDでクイズを削除する.

        Args:
            document_id: ドキュメントID

        Returns:
            削除されたクイズ数
        """
        quizzes = self.find_by_document_id(document_id)
        count = len(quizzes)
        for quiz in quizzes:
            self.delete(quiz)
        return count

    def delete_by_topic_id(self, topic_id: str) -> int:
        """トピックIDでクイズを削除する.

        Args:
            topic_id: トピックID

        Returns:
            削除されたクイズ数
        """
        quizzes = self.find_by_topic_id(topic_id)
        count = len(quizzes)
        for quiz in quizzes:
            self.delete(quiz)
        return count
