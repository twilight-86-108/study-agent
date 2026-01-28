"""トピック進捗リポジトリ.

TopicProgressモデルのデータアクセス操作を提供する。
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Sequence

from sqlmodel import select

from study_agent.infrastructure.database.models import TopicProgress
from study_agent.infrastructure.database.repositories.base import BaseRepository

logger = logging.getLogger(__name__)


class TopicProgressRepository(BaseRepository[TopicProgress]):
    """TopicProgressリポジトリ.

    トピック進捗のCRUD操作と検索機能を提供する。

    Example:
        ```python
        with db_manager.get_session() as session:
            repo = TopicProgressRepository(session)

            # トピックIDで検索
            progress = repo.find_by_topic_id("topic-123")

            # 進捗を更新
            repo.update_progress("topic-123", is_correct=True)

            # 習熟度でフィルタ
            weak_topics = repo.find_below_mastery(threshold=50)
        ```
    """

    @property
    def _model_class(self) -> type[TopicProgress]:
        """モデルクラスを返す."""
        return TopicProgress

    def find_by_topic_id(self, topic_id: str) -> TopicProgress | None:
        """トピックIDで進捗を検索する.

        Args:
            topic_id: トピックID

        Returns:
            進捗、存在しない場合はNone
        """
        statement = select(TopicProgress).where(TopicProgress.topic_id == topic_id)
        return self._session.exec(statement).first()

    def find_or_create(self, topic_id: str) -> TopicProgress:
        """トピックIDで進捗を検索し、存在しない場合は作成する.

        Args:
            topic_id: トピックID

        Returns:
            進捗
        """
        progress = self.find_by_topic_id(topic_id)
        if progress is None:
            progress = TopicProgress(topic_id=topic_id)
            progress = self.create(progress)
        return progress

    def find_by_topic_ids(self, topic_ids: list[str]) -> Sequence[TopicProgress]:
        """複数トピックIDで進捗を検索する.

        Args:
            topic_ids: トピックIDのリスト

        Returns:
            進捗のリスト
        """
        if not topic_ids:
            return []
        statement = select(TopicProgress).where(TopicProgress.topic_id.in_(topic_ids))
        return self._session.exec(statement).all()

    def find_below_mastery(self, threshold: int = 50) -> Sequence[TopicProgress]:
        """習熟度が閾値以下の進捗を検索する.

        Args:
            threshold: 習熟度の閾値

        Returns:
            進捗のリスト
        """
        statement = select(TopicProgress).where(
            TopicProgress.mastery_level <= threshold
        )
        return self._session.exec(statement).all()

    def find_above_mastery(self, threshold: int = 80) -> Sequence[TopicProgress]:
        """習熟度が閾値以上の進捗を検索する.

        Args:
            threshold: 習熟度の閾値

        Returns:
            進捗のリスト
        """
        statement = select(TopicProgress).where(
            TopicProgress.mastery_level >= threshold
        )
        return self._session.exec(statement).all()

    def update_progress(
        self,
        topic_id: str,
        is_correct: bool,
        increment_study: bool = True,
    ) -> TopicProgress:
        """トピックの進捗を更新する.

        Args:
            topic_id: トピックID
            is_correct: 正解したかどうか
            increment_study: study_countをインクリメントするかどうか

        Returns:
            更新された進捗
        """
        progress = self.find_or_create(topic_id)

        # カウントを更新
        progress.total_count += 1
        if is_correct:
            progress.correct_count += 1
        if increment_study:
            progress.study_count += 1

        # 習熟度を計算
        progress.mastery_level = self._calculate_mastery(
            correct_count=progress.correct_count,
            total_count=progress.total_count,
            study_count=progress.study_count,
        )

        # 最終学習日時を更新
        progress.last_studied_at = datetime.now(timezone.utc)
        progress.updated_at = datetime.now(timezone.utc)

        return self.update(progress)

    def _calculate_mastery(
        self,
        correct_count: int,
        total_count: int,
        study_count: int,
    ) -> int:
        """習熟度を計算する.

        計算式:
        - 基本スコア = 正答率 * 70
        - 経験ボーナス = min(study_count * 5, 30)
        - 習熟度 = 基本スコア + 経験ボーナス

        Args:
            correct_count: 正解数
            total_count: 総回答数
            study_count: 学習回数

        Returns:
            習熟度（0-100）
        """
        if total_count == 0:
            return 0

        accuracy = correct_count / total_count
        base_score = accuracy * 70
        experience_bonus = min(study_count * 5, 30)
        mastery = base_score + experience_bonus

        return min(int(mastery), 100)

    def reset_progress(self, topic_id: str) -> TopicProgress | None:
        """トピックの進捗をリセットする.

        Args:
            topic_id: トピックID

        Returns:
            リセットされた進捗、存在しない場合はNone
        """
        progress = self.find_by_topic_id(topic_id)
        if progress is None:
            return None

        progress.study_count = 0
        progress.correct_count = 0
        progress.total_count = 0
        progress.mastery_level = 0
        progress.last_studied_at = None
        progress.updated_at = datetime.now(timezone.utc)

        return self.update(progress)

    def get_average_mastery(self, topic_ids: list[str] | None = None) -> float:
        """平均習熟度を取得する.

        Args:
            topic_ids: トピックIDのリスト（Noneの場合は全体）

        Returns:
            平均習熟度
        """
        if topic_ids:
            progresses = self.find_by_topic_ids(topic_ids)
        else:
            progresses = self.get_all()

        if not progresses:
            return 0.0

        total_mastery = sum(p.mastery_level for p in progresses)
        return round(total_mastery / len(progresses), 1)

    def get_statistics(
        self,
        topic_ids: list[str] | None = None,
    ) -> dict[str, float | int]:
        """進捗統計を取得する.

        Args:
            topic_ids: トピックIDのリスト（Noneの場合は全体）

        Returns:
            統計情報
        """
        if topic_ids:
            progresses = list(self.find_by_topic_ids(topic_ids))
        else:
            progresses = list(self.get_all())

        if not progresses:
            return {
                "count": 0,
                "average_mastery": 0.0,
                "mastered_count": 0,
                "weak_count": 0,
                "total_study_count": 0,
                "total_correct_count": 0,
                "total_attempt_count": 0,
            }

        mastered = [p for p in progresses if p.mastery_level >= 80]
        weak = [p for p in progresses if p.mastery_level < 50]

        return {
            "count": len(progresses),
            "average_mastery": round(
                sum(p.mastery_level for p in progresses) / len(progresses), 1
            ),
            "mastered_count": len(mastered),
            "weak_count": len(weak),
            "total_study_count": sum(p.study_count for p in progresses),
            "total_correct_count": sum(p.correct_count for p in progresses),
            "total_attempt_count": sum(p.total_count for p in progresses),
        }
