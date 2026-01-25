"""エラー処理"""

from types import NoneType
import logging
from dataclasses import dataclass
from typing import TypeVar, Generic, Callable, Awaitable, Any
from functools import wraps

from study_agent.core.exceptions import StudyAgentError, ErrorContext

logger = logging.getLogger(__name__)

T = TypeVar("T")
U = TypeVar("U")


@dataclass
class Result(Generic[T]):
    """失敗可能性のある操作の結果タイプ"""

    _value: T | None = None
    _error: StudyAgentError | None = None

    @property
    def is_success(self) -> bool:
        """成功したかどうかを返す"""
        return self._error is None

    @property
    def is_failure(self) -> bool:
        """失敗したかどうかを返す"""
        return self._error is not None

    @property
    def value(self) -> T:
        """値を取得。結果が失敗の場合、例外を発生"""
        if self._error is not None:
            raise self._error
        if self._value is None:
            raise ValueError("Result has no value")
        return self._value

    @property
    def error(self) -> StudyAgentError | None:
        """失敗した場合のエラーを取得"""
        return self._error

    @classmethod
    def success(cls, value: T) -> "Result[T]":
        """成功した結果を作成"""
        return cls(_value=value)

    @classmethod
    def failure(cls, error: StudyAgentError) -> "Result[T]":
        """失敗した結果を作成"""
        return cls(_error=error)

    def map(self, func: Callable[[T], U]) -> "Result[U]":
        """成功した場合、値に関数を適用"""
        if self.is_failure:
            return Result.failure(self._error)
        return Result.success(func(self._value))

    def flat_map(self, func: Callable[[T], "Result[U]"]) -> "Result[U]":
        """Resultを返す関数を適用"""
        if self.is_failure:
            return Result.failure(self._error)
        return func(self._value)


def handle_errors(
    component: str,
    operation: str,
) -> Callable[[Callable[..., Awaitable[T]]], Callable[..., Awaitable[T]]]:
    """
    非同期関数をエラー処理でラップするためのデコレーター
    例外をキャッチし、Result型を返す

    Usage:
        @handle_errors("DocumentService", "load_document")
        async def load_document(path: str) -> Document:
            ...
    """

    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Result[T]:
            context = ErrorContext(component=component, operation=operation)

            try:
                result = await func(*args, **kwargs)
                return Result.success(result)
            except StudyAgentError as e:
                if e.context is None:
                    e.context = context
                logger.error(f"Error in {component}.{operation}: {e.message}")
                return Result.failure(e)
            except Exception as e:
                from study_agent.core.messages import MSG_UNEXPECTED_ERROR

                wrapped = StudyAgentError(
                    message=MSG_UNEXPECTED_ERROR.format(
                        component=component, operation=operation
                    ),
                    context=context,
                    cause=e,
                )
                logger.exception(f"Unexpected error in {component}.{operation}")
                return Result.failure(wrapped)

        return wrapper

    return decorator
