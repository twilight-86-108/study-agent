"""Progress tracking service.

学習の進捗状況と習熟度を管理するサービス。

主な機能:
    - 習熟度の計算
    - トピックごとの進捗更新
    - 学習履歴の分析
"""

from __future__ import annotations

import logging
from typing import Any

from study_agent.domain import (
    TopicProgress,
    MasteryLevel,
    QuizEvaluation,
)
from study_agent.infrastructure.database import (
    DatabaseManager,
    TopicProgressRepository,
)
from study_agent.infrastructure.database import (
    TopicProgress as TopicProgressModel,
)

logger = logging.getLogger(__name__)


class ProgressService:
    """進捗管理サービス.

    Attributes:
        db_manager: データベースマネージャ
    """

    def __init__(self, db_manager: DatabaseManager) -> None:
        """初期化.

        Args:
            db_manager: データベースマネージャ
        """
        self.db_manager = db_manager

    def calculate_mastery_level(
        self,
        correct_count: int,
        total_count: int,
        study_count: int,
    ) -> int:
        """習熟度（0-100）を計算する.

        計算ロジック:
        1. クイズ未受験（total_count=0）の場合:
           - 学習回数に基づくスコア（最大30点）
           - study_count * 10

        2. クイズ受験済みの場合:
           - 基礎点（最大70点）: 正答率 * 70
           - 経験点（最大30点）: 学習回数 * 5
           - 合計 = 基礎点 + 経験点

        Args:
            correct_count: クイズ正解数
            total_count: クイズ合計数
            study_count: 学習セッション数

        Returns:
            int: 習熟度（0-100）
        """
        # クイズ未受験の場合
        if total_count == 0:
            return min(study_count * 10, 30)

        # 基礎点（正答率ベース）
        accuracy = correct_count / total_count
        base_score = round(accuracy * 70)

        # 経験点（学習回数ベース）
        experience_score = min(study_count * 5, 30)

        return base_score + experience_score

    async def update_progress(
        self,
        topic_id: str,
        quiz_evaluation: QuizEvaluation | None = None,
        is_learning_session: bool = False,
    ) -> TopicProgress:
        """トピックの進捗を更新する.

        Args:
            topic_id: トピックID
            quiz_evaluation: クイズ評価結果（オプション）
            is_learning_session: 学習セッション完了かどうか

        Returns:
            TopicProgress: 更新後の進捗情報
        """
        with self.db_manager.get_session() as session:
            repo = TopicProgressRepository(session)
            progress_model = repo.get_by_topic_id(topic_id)

            # 新規作成
            if not progress_model:
                progress_model = TopicProgressModel(
                    topic_id=topic_id,
                    mastery_level=0,
                    last_studied_at=None,
                    study_count=0,
                    quiz_count=0,
                    correct_count=0,
                )
                session.add(progress_model)

            # 更新
            if is_learning_session:
                progress_model.study_count += 1
                from datetime import datetime

                progress_model.last_studied_at = datetime.now()

            if quiz_evaluation:
                progress_model.quiz_count += 1
                if quiz_evaluation.is_correct:
                    progress_model.correct_count += 1

            # 習熟度再計算
            mastery = self.calculate_mastery_level(
                correct_count=progress_model.correct_count,
                total_count=progress_model.quiz_count,
                study_count=progress_model.study_count,
            )
            progress_model.mastery_level = mastery

            session.commit()

            # ドメインモデルに変換して返す（簡易実装）
            return TopicProgress(
                topic_id=progress_model.topic_id,
                mastery_level=MasteryLevel.from_score(mastery),
                last_studied_at=progress_model.last_studied_at,
                study_count=progress_model.study_count,
                quiz_count=progress_model.quiz_count,
                correct_count=progress_model.correct_count,
            )
