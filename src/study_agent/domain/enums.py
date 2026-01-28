"""Domain Enums.

ドメイン層で使用する列挙型の定義。
"""

from __future__ import annotations

from enum import Enum


class FileType(str, Enum):
    """ファイル形式.

    サポートされるドキュメントファイルの形式。
    """

    PDF = "pdf"
    MARKDOWN = "md"
    TEXT = "txt"

    @classmethod
    def from_extension(cls, extension: str) -> "FileType":
        """拡張子からFileTypeを取得.

        Args:
            extension: ファイル拡張子（ドットなし）

        Returns:
            FileType

        Raises:
            ValueError: サポートされていない拡張子の場合
        """
        ext = extension.lower().lstrip(".")
        mapping = {
            "pdf": cls.PDF,
            "md": cls.MARKDOWN,
            "markdown": cls.MARKDOWN,
            "txt": cls.TEXT,
            "text": cls.TEXT,
        }
        if ext not in mapping:
            raise ValueError(f"Unsupported file extension: {extension}")
        return mapping[ext]


class QuizType(str, Enum):
    """クイズ形式.

    サポートされる問題形式。
    """

    MULTIPLE_CHOICE = "multiple_choice"  # 4択問題
    OPEN = "open"  # 自由記述
    TRUE_FALSE = "true_false"  # ○×問題


class Difficulty(int, Enum):
    """難易度.

    クイズや学習コンテンツの難易度レベル（1-5）。
    """

    BEGINNER = 1  # 入門
    EASY = 2  # 易しい
    MEDIUM = 3  # 普通
    HARD = 4  # 難しい
    EXPERT = 5  # 上級

    @classmethod
    def from_int(cls, value: int) -> "Difficulty":
        """整数から難易度を取得.

        Args:
            value: 難易度値（1-5）

        Returns:
            Difficulty

        Raises:
            ValueError: 範囲外の値の場合
        """
        if value < 1 or value > 5:
            raise ValueError(f"Difficulty must be 1-5, got {value}")
        return cls(value)


class SessionMode(str, Enum):
    """学習セッションモード.

    学習セッションの種類。
    """

    LEARNING = "learning"  # 学習モード（説明＋クイズ）
    QUIZ = "quiz"  # クイズ専用モード
    REVIEW = "review"  # 復習モード


class SessionStatus(str, Enum):
    """セッション状態.

    学習セッションの状態。
    """

    ACTIVE = "active"  # 進行中
    COMPLETED = "completed"  # 正常終了
    ABANDONED = "abandoned"  # 放棄（タイムアウト等）


class Intent(str, Enum):
    """ユーザー意図.

    RouterAgentが判定するユーザーの意図。
    """

    EXPLAIN = "explain"  # 概念説明を求めている
    TERM = "term"  # 用語解説を求めている
    QUIZ = "quiz"  # クイズを希望
    COMPARE = "compare"  # 比較説明を希望
    NAVIGATE = "navigate"  # トピック移動
    PROGRESS = "progress"  # 進捗確認
    CHAT = "chat"  # 一般的な会話
    UNKNOWN = "unknown"  # 判定不能


class MasteryLevel(str, Enum):
    """習熟度レベル.

    トピックの習熟状態を表す。
    """

    NOT_STARTED = "not_started"  # 未学習
    LEARNING = "learning"  # 学習中（0-49）
    DEVELOPING = "developing"  # 発展中（50-79）
    MASTERED = "mastered"  # 習得済み（80-100）

    @classmethod
    def from_score(cls, score: int) -> "MasteryLevel":
        """スコアから習熟度レベルを取得.

        Args:
            score: 習熟度スコア（0-100）

        Returns:
            MasteryLevel
        """
        if score <= 0:
            return cls.NOT_STARTED
        elif score < 50:
            return cls.LEARNING
        elif score < 80:
            return cls.DEVELOPING
        else:
            return cls.MASTERED
