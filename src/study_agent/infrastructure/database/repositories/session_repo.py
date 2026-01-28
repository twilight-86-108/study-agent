"""学習セッションリポジトリ.

LearningSessionモデルのデータアクセス操作を提供する。
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Sequence

from sqlmodel import select

from study_agent.infrastructure.database.models import (
    LearningSession,
    SessionMode,
    SessionStatus,
)
from study_agent.infrastructure.database.repositories.base import BaseRepository

logger = logging.getLogger(__name__)


class LearningSessionRepository(BaseRepository[LearningSession]):
    """LearningSessionリポジトリ.

    学習セッションのCRUD操作と検索機能を提供する。

    Example:
        ```python
        with db_manager.get_session() as session:
            repo = LearningSessionRepository(session)

            # 新しいセッションを開始
            session = repo.start_session(
                document_id="doc-123",
                mode=SessionMode.LEARNING,
            )

            # アクティブなセッションを取得
            active = repo.find_active_session()

            # セッションを終了
            repo.end_session(session.id)
        ```
    """

    @property
    def _model_class(self) -> type[LearningSession]:
        """モデルクラスを返す."""
        return LearningSession

    def find_by_document_id(self, document_id: str) -> Sequence[LearningSession]:
        """ドキュメントIDでセッションを検索する.

        Args:
            document_id: ドキュメントID

        Returns:
            セッションのリスト
        """
        statement = select(LearningSession).where(
            LearningSession.document_id == document_id
        )
        return self._session.exec(statement).all()

    def find_by_status(self, status: SessionStatus) -> Sequence[LearningSession]:
        """ステータスでセッションを検索する.

        Args:
            status: セッションステータス

        Returns:
            セッションのリスト
        """
        statement = select(LearningSession).where(LearningSession.status == status)
        return self._session.exec(statement).all()

    def find_by_mode(self, mode: SessionMode) -> Sequence[LearningSession]:
        """モードでセッションを検索する.

        Args:
            mode: セッションモード

        Returns:
            セッションのリスト
        """
        statement = select(LearningSession).where(LearningSession.mode == mode)
        return self._session.exec(statement).all()

    def find_active_session(
        self,
        document_id: str | None = None,
    ) -> LearningSession | None:
        """アクティブなセッションを取得する.

        Args:
            document_id: ドキュメントIDでフィルタ（オプション）

        Returns:
            アクティブなセッション、存在しない場合はNone
        """
        statement = select(LearningSession).where(
            LearningSession.status == SessionStatus.ACTIVE
        )
        if document_id is not None:
            statement = statement.where(LearningSession.document_id == document_id)
        statement = statement.order_by(LearningSession.started_at.desc())
        return self._session.exec(statement).first()

    def find_by_date_range(
        self,
        start_date: datetime,
        end_date: datetime,
    ) -> Sequence[LearningSession]:
        """日付範囲でセッションを検索する.

        Args:
            start_date: 開始日時
            end_date: 終了日時

        Returns:
            セッションのリスト
        """
        statement = (
            select(LearningSession)
            .where(LearningSession.started_at >= start_date)
            .where(LearningSession.started_at <= end_date)
            .order_by(LearningSession.started_at)
        )
        return self._session.exec(statement).all()

    def get_recent(self, limit: int = 10) -> Sequence[LearningSession]:
        """最近のセッションを取得する.

        Args:
            limit: 取得数

        Returns:
            セッションのリスト（開始日時降順）
        """
        statement = (
            select(LearningSession)
            .order_by(LearningSession.started_at.desc())
            .limit(limit)
        )
        return self._session.exec(statement).all()

    def start_session(
        self,
        document_id: str | None = None,
        mode: SessionMode = SessionMode.LEARNING,
    ) -> LearningSession:
        """新しいセッションを開始する.

        Args:
            document_id: ドキュメントID（オプション）
            mode: セッションモード

        Returns:
            作成されたセッション
        """
        session = LearningSession(
            document_id=document_id,
            mode=mode,
            status=SessionStatus.ACTIVE,
            started_at=datetime.now(timezone.utc),
        )
        return self.create(session)

    def end_session(
        self,
        session_id: str,
        status: SessionStatus = SessionStatus.COMPLETED,
    ) -> LearningSession | None:
        """セッションを終了する.

        Args:
            session_id: セッションID
            status: 終了ステータス

        Returns:
            更新されたセッション、存在しない場合はNone
        """
        session = self.get_by_id(session_id)
        if session is None:
            return None

        now = datetime.now(timezone.utc)
        session.status = status
        session.ended_at = now

        # 経過時間を計算
        if session.started_at:
            # SQLiteから読み込んだdatetimeはoffset-naiveなので変換
            started = session.started_at
            if started.tzinfo is None:
                started = started.replace(tzinfo=timezone.utc)
            delta = now - started
            session.total_time_seconds = int(delta.total_seconds())

        return self.update(session)

    def abandon_session(self, session_id: str) -> LearningSession | None:
        """セッションを放棄する.

        Args:
            session_id: セッションID

        Returns:
            更新されたセッション、存在しない場合はNone
        """
        return self.end_session(session_id, status=SessionStatus.ABANDONED)

    def abandon_stale_sessions(
        self,
        max_age_hours: int = 24,
    ) -> int:
        """古いアクティブセッションを放棄する.

        Args:
            max_age_hours: 最大経過時間（時間）

        Returns:
            放棄されたセッション数
        """
        from datetime import timedelta

        cutoff = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
        statement = (
            select(LearningSession)
            .where(LearningSession.status == SessionStatus.ACTIVE)
            .where(LearningSession.started_at < cutoff)
        )
        stale_sessions = self._session.exec(statement).all()

        count = 0
        for session in stale_sessions:
            if self.abandon_session(session.id) is not None:
                count += 1

        return count

    def get_total_study_time(
        self,
        document_id: str | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> int:
        """総学習時間を取得する.

        Args:
            document_id: ドキュメントIDでフィルタ（オプション）
            start_date: 開始日時でフィルタ（オプション）
            end_date: 終了日時でフィルタ（オプション）

        Returns:
            総学習時間（秒）
        """
        statement = select(LearningSession).where(
            LearningSession.status == SessionStatus.COMPLETED
        )

        if document_id is not None:
            statement = statement.where(LearningSession.document_id == document_id)
        if start_date is not None:
            statement = statement.where(LearningSession.started_at >= start_date)
        if end_date is not None:
            statement = statement.where(LearningSession.started_at <= end_date)

        sessions = self._session.exec(statement).all()
        return sum(s.total_time_seconds or 0 for s in sessions)

    def get_statistics(
        self,
        document_id: str | None = None,
    ) -> dict[str, int | float]:
        """セッション統計を取得する.

        Args:
            document_id: ドキュメントIDでフィルタ（オプション）

        Returns:
            統計情報
        """
        statement = select(LearningSession)
        if document_id is not None:
            statement = statement.where(LearningSession.document_id == document_id)

        sessions = list(self._session.exec(statement).all())

        if not sessions:
            return {
                "total_sessions": 0,
                "completed_sessions": 0,
                "active_sessions": 0,
                "abandoned_sessions": 0,
                "total_time_seconds": 0,
                "average_time_seconds": 0.0,
            }

        completed = [s for s in sessions if s.status == SessionStatus.COMPLETED]
        active = [s for s in sessions if s.status == SessionStatus.ACTIVE]
        abandoned = [s for s in sessions if s.status == SessionStatus.ABANDONED]

        total_time = sum(s.total_time_seconds or 0 for s in completed)
        avg_time = total_time / len(completed) if completed else 0.0

        return {
            "total_sessions": len(sessions),
            "completed_sessions": len(completed),
            "active_sessions": len(active),
            "abandoned_sessions": len(abandoned),
            "total_time_seconds": total_time,
            "average_time_seconds": round(avg_time, 1),
        }
