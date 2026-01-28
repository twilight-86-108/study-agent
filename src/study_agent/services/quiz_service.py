"""Quiz management service.

クイズの生成、保存、回答評価を管理するサービス。

主な機能:
    - LLMを使用したクイズ生成（選択式・記述式）
    - 回答の評価とフィードバック
    - クイズ履歴の管理

Example:
    >>> service = QuizService(llm_client, search_service, db_manager)
    >>> quiz = await service.generate_quiz("Amazon EC2", QuizType.MULTIPLE_CHOICE)
    >>> result = await service.evaluate_answer(quiz, "A", session_id)
"""

from __future__ import annotations

import json
import logging
import uuid
from typing import Any

from study_agent.core.exceptions import LLMError, ErrorContext
from study_agent.domain import (
    Quiz,
    QuizAttempt,
    QuizType,
    Difficulty,
    GeneratedQuiz,
    QuizEvaluation,
)
from study_agent.infrastructure.llm import BaseLLMClient
from study_agent.infrastructure.database import (
    DatabaseManager,
    QuizRepository,
    QuizAttemptRepository,
)
from study_agent.infrastructure.database import (
    Quiz as QuizModel,
    QuizAttempt as QuizAttemptModel,
)
from study_agent.services.search_service import SearchService

logger = logging.getLogger(__name__)


class QuizService:
    """クイズ管理サービス.

    LLMを使用してクイズを生成し、回答を評価する。

    Attributes:
        llm_client: LLMクライアント
        search_service: 検索サービス
        db_manager: データベースマネージャ

    Example:
        >>> service = QuizService(llm_client, search_service, db_manager)
        >>> quiz = await service.generate_quiz("EC2", QuizType.MULTIPLE_CHOICE)
        >>> print(quiz.question)
    """

    def __init__(
        self,
        llm_client: BaseLLMClient,
        search_service: SearchService,
        db_manager: DatabaseManager,
    ) -> None:
        """初期化.

        Args:
            llm_client: LLMクライアント
            search_service: 検索サービス
            db_manager: データベースマネージャ
        """
        self.llm_client = llm_client
        self.search_service = search_service
        self.db_manager = db_manager

    def _generate_id(self) -> str:
        """UUID v4を生成する."""
        return str(uuid.uuid4())

    async def generate_quiz(
        self,
        topic: str,
        quiz_type: QuizType = QuizType.MULTIPLE_CHOICE,
        difficulty: Difficulty | int = Difficulty.MEDIUM,
        document_id: str | None = None,
        save: bool = True,
    ) -> GeneratedQuiz:
        """トピックに関するクイズを生成する.

        Args:
            topic: クイズのトピック
            quiz_type: クイズタイプ（選択式/記述式）
            difficulty: 難易度（1-5またはDifficulty）
            document_id: ドキュメントフィルター（オプション）
            save: DBに保存するか

        Returns:
            GeneratedQuiz: 生成されたクイズとコンテキスト

        Raises:
            LLMError: LLM呼び出しに失敗した場合
        """
        # 難易度を数値に変換
        if isinstance(difficulty, Difficulty):
            difficulty_value = difficulty.value
        else:
            difficulty_value = difficulty

        # コンテキストを取得
        context_result = await self.search_service.get_context_for_quiz(
            topic=topic,
            document_id=document_id,
            max_chunks=3,
        )

        # プロンプトを構築
        if quiz_type == QuizType.MULTIPLE_CHOICE:
            quiz = await self._generate_multiple_choice(
                topic=topic,
                context=context_result.context,
                difficulty=difficulty_value,
                document_id=document_id,
            )
        elif quiz_type == QuizType.TRUE_FALSE:
            quiz = await self._generate_true_false(
                topic=topic,
                context=context_result.context,
                difficulty=difficulty_value,
                document_id=document_id,
            )
        else:
            quiz = await self._generate_open_question(
                topic=topic,
                context=context_result.context,
                difficulty=difficulty_value,
                document_id=document_id,
            )

        # DBに保存
        if save:
            with self.db_manager.get_session() as session:
                quiz_repo = QuizRepository(session)
                quiz_model = QuizModel(
                    id=quiz.id,
                    document_id=quiz.document_id,
                    topic_id=quiz.topic_id,
                    question=quiz.question,
                    correct_answer=quiz.correct_answer,
                    options_json=json.dumps(quiz.options) if quiz.options else None,
                    explanation=quiz.explanation,
                    difficulty=(
                        quiz.difficulty.value
                        if isinstance(quiz.difficulty, Difficulty)
                        else quiz.difficulty
                    ),
                    quiz_type=quiz.quiz_type,
                )
                quiz_repo.create(quiz_model)
                logger.info(f"Quiz saved: {quiz.id}")

        logger.info(f"Quiz generated for topic: {topic}")

        return GeneratedQuiz(
            quiz=quiz,
            context_used=context_result.context,
            source_chunks=[c.id for c in context_result.source_chunks],
        )

    async def _generate_multiple_choice(
        self,
        topic: str,
        context: str,
        difficulty: int,
        document_id: str | None,
    ) -> Quiz:
        """選択式問題を生成する."""
        schema = {
            "type": "object",
            "properties": {
                "question": {"type": "string", "description": "問題文（日本語）"},
                "correct_answer": {"type": "string", "enum": ["A", "B", "C", "D"]},
                "options": {
                    "type": "object",
                    "properties": {
                        "A": {"type": "string"},
                        "B": {"type": "string"},
                        "C": {"type": "string"},
                        "D": {"type": "string"},
                    },
                    "required": ["A", "B", "C", "D"],
                },
                "explanation": {"type": "string", "description": "解説（日本語）"},
            },
            "required": ["question", "correct_answer", "options", "explanation"],
        }

        prompt = f"""You are a quiz generator for a learning application.

## Reference Material
{context if context else "No specific reference material available."}

## Topic
{topic}

## Instructions
Generate a multiple-choice question about "{topic}" in Japanese.

Difficulty Level: {difficulty}/5 (1=beginner, 5=expert)

Requirements:
1. Create a clear, specific question
2. Provide 4 options (A, B, C, D) - only one correct
3. Make wrong options plausible but clearly incorrect
4. Include a brief explanation

Respond with JSON only, no additional text."""

        result = await self.llm_client.generate_json(prompt, schema)

        return Quiz(
            id=self._generate_id(),
            document_id=document_id,
            question=result["question"],
            correct_answer=result["correct_answer"],
            quiz_type=QuizType.MULTIPLE_CHOICE,
            difficulty=Difficulty.from_int(difficulty),
            options=result["options"],
            explanation=result.get("explanation"),
        )

    async def _generate_true_false(
        self,
        topic: str,
        context: str,
        difficulty: int,
        document_id: str | None,
    ) -> Quiz:
        """○×問題を生成する."""
        schema = {
            "type": "object",
            "properties": {
                "question": {"type": "string", "description": "問題文（日本語）"},
                "correct_answer": {"type": "string", "enum": ["○", "×"]},
                "explanation": {"type": "string", "description": "解説（日本語）"},
            },
            "required": ["question", "correct_answer", "explanation"],
        }

        prompt = f"""You are a quiz generator for a learning application.

## Reference Material
{context if context else "No specific reference material available."}

## Topic
{topic}

## Instructions
Generate a true/false question about "{topic}" in Japanese.

Difficulty Level: {difficulty}/5 (1=beginner, 5=expert)

Requirements:
1. Create a statement that is clearly true or false
2. Answer should be "○" for true or "×" for false
3. Include an explanation

Respond with JSON only, no additional text."""

        result = await self.llm_client.generate_json(prompt, schema)

        return Quiz(
            id=self._generate_id(),
            document_id=document_id,
            question=result["question"],
            correct_answer=result["correct_answer"],
            quiz_type=QuizType.TRUE_FALSE,
            difficulty=Difficulty.from_int(difficulty),
            options={"○": "正しい", "×": "誤り"},
            explanation=result.get("explanation"),
        )

    async def _generate_open_question(
        self,
        topic: str,
        context: str,
        difficulty: int,
        document_id: str | None,
    ) -> Quiz:
        """記述式問題を生成する."""
        schema = {
            "type": "object",
            "properties": {
                "question": {"type": "string", "description": "問題文（日本語）"},
                "correct_answer": {"type": "string", "description": "模範解答"},
                "explanation": {"type": "string", "description": "解説（日本語）"},
                "key_points": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "採点のキーポイント",
                },
            },
            "required": ["question", "correct_answer", "explanation"],
        }

        prompt = f"""You are a quiz generator for a learning application.

## Reference Material
{context if context else "No specific reference material available."}

## Topic
{topic}

## Instructions
Generate an open-ended question about "{topic}" in Japanese.

Difficulty Level: {difficulty}/5 (1=beginner, 5=expert)

Requirements:
1. Create a question that requires explanation or description
2. Provide a model answer
3. List key points for evaluation
4. Include a brief explanation

Respond with JSON only, no additional text."""

        result = await self.llm_client.generate_json(prompt, schema)

        return Quiz(
            id=self._generate_id(),
            document_id=document_id,
            question=result["question"],
            correct_answer=result["correct_answer"],
            quiz_type=QuizType.OPEN,
            difficulty=Difficulty.from_int(difficulty),
            explanation=result.get("explanation"),
            key_points=result.get("key_points", []),
        )

    async def evaluate_answer(
        self,
        quiz: Quiz,
        user_answer: str,
        session_id: str,
    ) -> QuizEvaluation:
        """ユーザーの回答を評価する.

        Args:
            quiz: クイズ
            user_answer: ユーザーの回答
            session_id: セッションID

        Returns:
            QuizEvaluation: 評価結果
        """
        if quiz.quiz_type == QuizType.MULTIPLE_CHOICE:
            result = self._evaluate_multiple_choice(quiz, user_answer)
        elif quiz.quiz_type == QuizType.TRUE_FALSE:
            result = self._evaluate_true_false(quiz, user_answer)
        else:
            result = await self._evaluate_open_answer(quiz, user_answer)

        # 回答履歴を保存
        with self.db_manager.get_session() as session:
            attempt_model = QuizAttemptModel(
                id=self._generate_id(),
                quiz_id=quiz.id,
                session_id=session_id,
                user_answer=user_answer,
                is_correct=result.is_correct,
                score=result.score,
                feedback=result.feedback,
            )
            session.add(attempt_model)
            session.commit()

        logger.info(
            f"Answer evaluated: quiz={quiz.id}, "
            f"correct={result.is_correct}, score={result.score}"
        )

        return result

    def _evaluate_multiple_choice(
        self,
        quiz: Quiz,
        user_answer: str,
    ) -> QuizEvaluation:
        """選択式問題を評価する."""
        # 大文字小文字を無視して比較
        is_correct = user_answer.upper().strip() == quiz.correct_answer.upper().strip()
        score = 100 if is_correct else 0

        if is_correct:
            feedback = "🎉 正解です！"
        else:
            feedback = f"❌ 不正解です。正解は {quiz.correct_answer} でした。"

        if quiz.explanation:
            feedback += f"\n\n【解説】\n{quiz.explanation}"

        return QuizEvaluation(
            is_correct=is_correct,
            score=score,
            feedback=feedback,
            correct_answer=quiz.correct_answer,
            matched_points=[],
            missed_points=[],
        )

    def _evaluate_true_false(
        self,
        quiz: Quiz,
        user_answer: str,
    ) -> QuizEvaluation:
        """○×問題を評価する."""
        # 入力の正規化
        normalized = user_answer.strip()
        if normalized.lower() in ["o", "true", "yes", "まる", "正"]:
            normalized = "○"
        elif normalized.lower() in ["x", "false", "no", "ばつ", "誤"]:
            normalized = "×"

        is_correct = normalized == quiz.correct_answer
        score = 100 if is_correct else 0

        if is_correct:
            feedback = "🎉 正解です！"
        else:
            feedback = f"❌ 不正解です。正解は {quiz.correct_answer} でした。"

        if quiz.explanation:
            feedback += f"\n\n【解説】\n{quiz.explanation}"

        return QuizEvaluation(
            is_correct=is_correct,
            score=score,
            feedback=feedback,
            correct_answer=quiz.correct_answer,
            matched_points=[],
            missed_points=[],
        )

    async def _evaluate_open_answer(
        self,
        quiz: Quiz,
        user_answer: str,
    ) -> QuizEvaluation:
        """記述式問題をLLMで評価する."""
        schema = {
            "type": "object",
            "properties": {
                "score": {
                    "type": "integer",
                    "minimum": 0,
                    "maximum": 100,
                    "description": "スコア（0-100）",
                },
                "is_correct": {
                    "type": "boolean",
                    "description": "正解とみなせるか（60点以上）",
                },
                "feedback": {
                    "type": "string",
                    "description": "フィードバック（日本語）",
                },
                "matched_points": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "カバーされているポイント",
                },
                "missed_points": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "不足しているポイント",
                },
            },
            "required": ["score", "is_correct", "feedback"],
        }

        prompt = f"""You are an evaluator for a learning application.

## Question
{quiz.question}

## Model Answer
{quiz.correct_answer}

## Student's Answer
{user_answer}

## Instructions
Evaluate the student's answer in Japanese.

Scoring Guidelines:
- 80-100: Excellent, covers all key concepts
- 60-79: Good, covers most key points
- 40-59: Partial understanding
- 20-39: Limited understanding
- 0-19: Incorrect or irrelevant

Provide:
1. A numerical score (0-100)
2. Whether the answer is acceptable (score >= 60)
3. Constructive feedback
4. Points that were covered well
5. Points that were missed

Respond with JSON only, no additional text."""

        try:
            result = await self.llm_client.generate_json(prompt, schema)

            feedback = result["feedback"]
            if quiz.explanation:
                feedback += f"\n\n【模範解答】\n{quiz.correct_answer}"
                feedback += f"\n\n【解説】\n{quiz.explanation}"

            return QuizEvaluation(
                is_correct=result.get("is_correct", result["score"] >= 60),
                score=result["score"],
                feedback=feedback,
                correct_answer=quiz.correct_answer,
                matched_points=result.get("matched_points", []),
                missed_points=result.get("missed_points", []),
            )

        except LLMError:
            # フォールバック: 単純な文字列比較
            logger.warning("LLM evaluation failed, using simple comparison")
            similarity = self._simple_similarity(user_answer, quiz.correct_answer)
            is_correct = similarity >= 0.6
            score = int(similarity * 100)

            return QuizEvaluation(
                is_correct=is_correct,
                score=score,
                feedback=f"自動評価: {score}点\n\n【模範解答】\n{quiz.correct_answer}",
                correct_answer=quiz.correct_answer,
                matched_points=[],
                missed_points=[],
            )

    def _simple_similarity(self, text1: str, text2: str) -> float:
        """単純な文字列類似度を計算する."""
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())

        if not words1 or not words2:
            return 0.0

        intersection = words1 & words2
        union = words1 | words2

        return len(intersection) / len(union)

    async def get_quiz(self, quiz_id: str) -> Quiz | None:
        """IDでクイズを取得する.

        Args:
            quiz_id: クイズID

        Returns:
            Quiz: クイズ（見つからない場合はNone）
        """
        with self.db_manager.get_session() as session:
            quiz_repo = QuizRepository(session)
            quiz_model = quiz_repo.get_by_id(quiz_id)

            if quiz_model is None:
                return None

            return self._model_to_domain(quiz_model)

    async def list_quizzes(
        self,
        document_id: str | None = None,
        topic_id: str | None = None,
        limit: int = 20,
    ) -> list[Quiz]:
        """クイズ一覧を取得する.

        Args:
            document_id: ドキュメントフィルター（オプション）
            topic_id: トピックフィルター（オプション）
            limit: 最大取得数

        Returns:
            クイズのリスト
        """
        with self.db_manager.get_session() as session:
            quiz_repo = QuizRepository(session)

            if document_id:
                quiz_models = quiz_repo.find_by_document_id(document_id)
            elif topic_id:
                quiz_models = quiz_repo.find_by_topic_id(topic_id)
            else:
                quiz_models = quiz_repo.get_all()

            return [self._model_to_domain(m) for m in quiz_models[:limit]]

    def _model_to_domain(self, model: QuizModel) -> Quiz:
        """DBモデルをドメインモデルに変換する."""
        options = None
        if model.options_json:
            options = json.loads(model.options_json)

        return Quiz(
            id=model.id,
            document_id=model.document_id,
            topic_id=model.topic_id,
            question=model.question,
            correct_answer=model.correct_answer,
            quiz_type=QuizType(model.quiz_type.value),
            difficulty=(
                Difficulty.from_int(model.difficulty)
                if model.difficulty
                else Difficulty.MEDIUM
            ),
            options=options,
            explanation=model.explanation,
            created_at=model.created_at,
        )
