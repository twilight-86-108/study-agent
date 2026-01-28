"""Session management service.

学習セッションの開始、終了、管理を行うサービス。

主な機能:
    - セッションの開始と終了
    - 現在のセッションの追跡
    - セッション履歴の管理
    - セッション統計の計算

Example:
    >>> service = SessionService(db_manager)
    >>> session = await service.start_session(document_id, SessionMode.LEARNING)
    >>> # ... 学習 ...
    >>> await service.end_session(session.id)
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Sequence

from study_agent.domain import (
    LearningSession,
    SessionMode,
    SessionStatus,
)
from study_agent.infrastructure.database import (
    DatabaseManager,
    LearningSessionRepository,
)
from study_agent.infrastructure.database import LearningSession as LearningSessionModel

logger = logging.getLogger(__name__)


class SessionService:
    """セッション管理サービス.

    学習セッションのライフサイクルを管理する。

    Attributes:
        db_manager: データベースマネージャ
        _current_session: 現在アクティブなセッション

    Example:
        >>> service = SessionService(db_manager)
        >>> session = await service.start_session("doc-123", SessionMode.QUIZ)
        >>> print(f"Started: {session.id}")
    """

    def __init__(self, db_manager: DatabaseManager) -> None:
        """初期化.

        Args:
            db_manager: データベースマネージャ
        """
        self.db_manager = db_manager
        self._current_session: LearningSession | None = None

    def _generate_id(self) -> str:
        """UUID v4を生成する."""
        return str(uuid.uuid4())

    def _utcnow(self) -> datetime:
        """現在のUTC時刻を取得する."""
        return datetime.now(timezone.utc)

    async def start_session(
        self,
        document_id: str | None = None,
        mode: SessionMode = SessionMode.LEARNING,
    ) -> LearningSession:
        """新しい学習セッションを開始する.

        既存のアクティブセッションがある場合は自動的に終了する。

        Args:
            document_id: 学習対象のドキュメントID（オプション）
            mode: セッションモード

        Returns:
            開始されたセッション
        """
        # 既存のアクティブセッションを終了
        if (
            self._current_session
            and self._current_session.status == SessionStatus.ACTIVE
        ):
            await self.end_session(self._current_session.id)
            logger.info(f"Auto-ended previous session: {self._current_session.id}")

        # 新しいセッションを作成
        session = LearningSession(
            id=self._generate_id(),
            document_id=document_id,
            mode=mode,
            status=SessionStatus.ACTIVE,
            started_at=self._utcnow(),
        )

        # DBに保存
        with self.db_manager.get_session() as db_session:
            session_repo = LearningSessionRepository(db_session)
            session_model = LearningSessionModel(
                id=session.id,
                document_id=session.document_id,
                mode=session.mode,
                status=session.status,
                started_at=session.started_at,
            )
            session_repo.create(session_model)

        self._current_session = session
        logger.info(f"Session started: {session.id} (mode={mode.value})")

        return session

    async def end_session(
        self,
        session_id: str,
        status: SessionStatus = SessionStatus.COMPLETED,
    ) -> LearningSession:
        """セッションを終了する.

        Args:
            session_id: 終了するセッションID
            status: 終了ステータス

        Returns:
            終了されたセッション
        """
        with self.db_manager.get_session() as db_session:
            session_repo = LearningSessionRepository(db_session)
            session_model = session_repo.get_by_id(session_id)

            if session_model is None:
                logger.warning(f"Session not found: {session_id}")
                # セッションが見つからない場合は空のセッションを返す
                return LearningSession(
                    id=session_id,
                    mode=SessionMode.LEARNING,
                    status=SessionStatus.ABANDONED,
                )

            # 終了時刻と合計時間を計算
            ended_at = self._utcnow()
            total_time_seconds = None

            if session_model.started_at:
                delta = ended_at - session_model.started_at
                total_time_seconds = int(delta.total_seconds())

            # 更新
            session_model.status = status
            session_model.ended_at = ended_at
            session_model.total_time_seconds = total_time_seconds
            session_model.updated_at = self._utcnow()
            session_repo.update(session_model)

            session = self._to_domain(session_model)

        # 現在のセッションをクリア
        if self._current_session and self._current_session.id == session_id:
            self._current_session = None

        logger.info(
            f"Session ended: {session_id} "
            f"(status={status.value}, duration={total_time_seconds}s)"
        )

        return session

    async def abandon_session(self, session_id: str) -> LearningSession:
        """セッションを放棄する.

        タイムアウトや中断時に使用。

        Args:
            session_id: 放棄するセッションID

        Returns:
            放棄されたセッション
        """
        return await self.end_session(session_id, SessionStatus.ABANDONED)

    def get_current_session(self) -> LearningSession | None:
        """現在のアクティブセッションを取得する.

        Returns:
            アクティブセッション（存在しない場合はNone）
        """
        return self._current_session

    async def get_session(self, session_id: str) -> LearningSession | None:
        """IDでセッションを取得する.

        Args:
            session_id: セッションID

        Returns:
            セッション（存在しない場合はNone）
        """
        with self.db_manager.get_session() as db_session:
            session_repo = LearningSessionRepository(db_session)
            session_model = session_repo.get_by_id(session_id)

            if session_model is None:
                return None

            return self._to_domain(session_model)

    async def get_recent_sessions(
        self,
        limit: int = 10,
        document_id: str | None = None,
    ) -> list[LearningSession]:
        """最近のセッション一覧を取得する.

        Args:
            limit: 最大取得数
            document_id: ドキュメントフィルター（オプション）

        Returns:
            セッションリスト（新しい順）
        """
        with self.db_manager.get_session() as db_session:
            session_repo = LearningSessionRepository(db_session)

            if document_id:
                session_models = session_repo.find_by_document_id(document_id)
            else:
                session_models = session_repo.get_recent(limit)

            return [self._to_domain(m) for m in session_models[:limit]]

    async def get_active_sessions(self) -> list[LearningSession]:
        """アクティブなセッション一覧を取得する.

        通常は1つ以下だが、異常終了時に複数残る可能性がある。

        Returns:
            アクティブセッションのリスト
        """
        with self.db_manager.get_session() as db_session:
            session_repo = LearningSessionRepository(db_session)
            session_models = session_repo.find_active()

            return [self._to_domain(m) for m in session_models]

    async def cleanup_stale_sessions(
        self,
        timeout_hours: int = 24,
    ) -> int:
        """古いアクティブセッションをクリーンアップする.

        指定時間以上前に開始されたアクティブセッションを放棄状態にする。

        Args:
            timeout_hours: タイムアウト時間（時間）

        Returns:
            クリーンアップされたセッション数
        """
        active_sessions = await self.get_active_sessions()
        now = self._utcnow()
        cleaned = 0

        for session in active_sessions:
            if session.started_at:
                elapsed = (now - session.started_at).total_seconds() / 3600
                if elapsed > timeout_hours:
                    await self.abandon_session(session.id)
                    cleaned += 1
                    logger.info(f"Cleaned stale session: {session.id}")

        if cleaned > 0:
            logger.info(f"Cleaned up {cleaned} stale sessions")

        return cleaned

    async def get_session_stats(
        self,
        document_id: str | None = None,
    ) -> dict:
        """セッション統計を取得する.

        Args:
            document_id: ドキュメントフィルター（オプション）

        Returns:
            統計情報の辞書
        """
        sessions = await self.get_recent_sessions(limit=100, document_id=document_id)

        total_sessions = len(sessions)
        completed_sessions = sum(
            1 for s in sessions if s.status == SessionStatus.COMPLETED
        )
        abandoned_sessions = sum(
            1 for s in sessions if s.status == SessionStatus.ABANDONED
        )
        total_time_seconds = sum(s.total_time_seconds or 0 for s in sessions)
        average_time_seconds = (
            total_time_seconds / completed_sessions if completed_sessions > 0 else 0
        )

        return {
            "total_sessions": total_sessions,
            "completed_sessions": completed_sessions,
            "abandoned_sessions": abandoned_sessions,
            "completion_rate": (
                completed_sessions / total_sessions * 100 if total_sessions > 0 else 0
            ),
            "total_study_time_seconds": total_time_seconds,
            "average_session_time_seconds": average_time_seconds,
        }

    def _to_domain(self, model: LearningSessionModel) -> LearningSession:
        """DBモデルをドメインモデルに変換する."""
        return LearningSession(
            id=model.id,
            document_id=model.document_id,
            mode=(
                SessionMode(model.mode.value)
                if isinstance(model.mode, SessionMode)
                else SessionMode(model.mode)
            ),
            status=(
                SessionStatus(model.status.value)
                if isinstance(model.status, SessionStatus)
                else SessionStatus(model.status)
            ),
            started_at=model.started_at,
            ended_at=model.ended_at,
            total_time_seconds=model.total_time_seconds,
            created_at=model.created_at,
        )
