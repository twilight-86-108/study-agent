"""クイズ回答リポジトリ.

QuizAttemptモデルのデータアクセス操作を提供する。
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Sequence

from sqlmodel import select

from study_agent.infrastructure.database.models import QuizAttempt
from study_agent.infrastructure.database.repositories.base import BaseRepository

logger = logging.getLogger(__name__)


class QuizAttemptRepository(BaseRepository[QuizAttempt]):
    """QuizAttemptリポジトリ.

    クイズ回答履歴のCRUD操作と検索機能を提供する。

    Example:
        ```python
        with db_manager.get_session() as session:
            repo = QuizAttemptRepository(session)

            # セッションIDで検索
            attempts = repo.find_by_session_id("session-123")

            # クイズIDで検索
            attempts = repo.find_by_quiz_id("quiz-456")

            # 統計情報を取得
            stats = repo.get_statistics_by_session("session-123")
        ```
    """

    @property
    def _model_class(self) -> type[QuizAttempt]:
        """モデルクラスを返す."""
        return QuizAttempt

    def find_by_session_id(self, session_id: str) -> Sequence[QuizAttempt]:
        """セッションIDで回答履歴を検索する.

        Args:
            session_id: セッションID

        Returns:
            回答履歴のリスト
        """
        statement = select(QuizAttempt).where(QuizAttempt.session_id == session_id)
        return self._session.exec(statement).all()

    def find_by_session_id_ordered(self, session_id: str) -> Sequence[QuizAttempt]:
        """セッションIDで回答履歴を検索する（時系列順）.

        Args:
            session_id: セッションID

        Returns:
            回答履歴のリスト（回答日時順）
        """
        statement = (
            select(QuizAttempt)
            .where(QuizAttempt.session_id == session_id)
            .order_by(QuizAttempt.answered_at)
        )
        return self._session.exec(statement).all()

    def find_by_quiz_id(self, quiz_id: str) -> Sequence[QuizAttempt]:
        """クイズIDで回答履歴を検索する.

        Args:
            quiz_id: クイズID

        Returns:
            回答履歴のリスト
        """
        statement = select(QuizAttempt).where(QuizAttempt.quiz_id == quiz_id)
        return self._session.exec(statement).all()

    def find_by_date_range(
        self,
        start_date: datetime,
        end_date: datetime,
    ) -> Sequence[QuizAttempt]:
        """日付範囲で回答履歴を検索する.

        Args:
            start_date: 開始日時
            end_date: 終了日時

        Returns:
            回答履歴のリスト
        """
        statement = (
            select(QuizAttempt)
            .where(QuizAttempt.answered_at >= start_date)
            .where(QuizAttempt.answered_at <= end_date)
            .order_by(QuizAttempt.answered_at)
        )
        return self._session.exec(statement).all()

    def get_correct_count_by_session(self, session_id: str) -> int:
        """セッション内の正解数を取得する.

        Args:
            session_id: セッションID

        Returns:
            正解数
        """
        statement = (
            select(QuizAttempt)
            .where(QuizAttempt.session_id == session_id)
            .where(QuizAttempt.is_correct == True)  # noqa: E712
        )
        return len(self._session.exec(statement).all())

    def get_statistics_by_session(self, session_id: str) -> dict[str, int]:
        """セッションの統計情報を取得する.

        Args:
            session_id: セッションID

        Returns:
            統計情報 {"total": int, "correct": int, "incorrect": int, "accuracy": float}
        """
        attempts = self.find_by_session_id(session_id)
        total = len(attempts)
        correct = sum(1 for a in attempts if a.is_correct)
        incorrect = total - correct
        accuracy = (correct / total * 100) if total > 0 else 0.0

        return {
            "total": total,
            "correct": correct,
            "incorrect": incorrect,
            "accuracy": round(accuracy, 1),
        }

    def get_statistics_by_quiz(self, quiz_id: str) -> dict[str, int]:
        """クイズの統計情報を取得する.

        Args:
            quiz_id: クイズID

        Returns:
            統計情報 {"total": int, "correct": int, "accuracy": float}
        """
        attempts = self.find_by_quiz_id(quiz_id)
        total = len(attempts)
        correct = sum(1 for a in attempts if a.is_correct)
        accuracy = (correct / total * 100) if total > 0 else 0.0

        return {
            "total": total,
            "correct": correct,
            "accuracy": round(accuracy, 1),
        }

    def get_recent(
        self,
        limit: int = 10,
        session_id: str | None = None,
    ) -> Sequence[QuizAttempt]:
        """最近の回答履歴を取得する.

        Args:
            limit: 取得数
            session_id: セッションIDでフィルタ（オプション）

        Returns:
            回答履歴のリスト（回答日時降順）
        """
        statement = select(QuizAttempt)
        if session_id is not None:
            statement = statement.where(QuizAttempt.session_id == session_id)
        statement = statement.order_by(QuizAttempt.answered_at.desc()).limit(limit)
        return self._session.exec(statement).all()

    def delete_by_session_id(self, session_id: str) -> int:
        """セッションIDで回答履歴を削除する.

        Args:
            session_id: セッションID

        Returns:
            削除された回答履歴数
        """
        attempts = self.find_by_session_id(session_id)
        count = len(attempts)
        for attempt in attempts:
            self.delete(attempt)
        return count

    def delete_by_quiz_id(self, quiz_id: str) -> int:
        """クイズIDで回答履歴を削除する.

        Args:
            quiz_id: クイズID

        Returns:
            削除された回答履歴数
        """
        attempts = self.find_by_quiz_id(quiz_id)
        count = len(attempts)
        for attempt in attempts:
            self.delete(attempt)
        return count
