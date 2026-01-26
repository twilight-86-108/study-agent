"""一時的な障害に対するリトライ"""

import asyncio
import logging
from dataclasses import dataclass, field
from typing import TypeVar, Callable, Awaitable, Type, Any
from functools import wraps

from study_agent.core.exceptions import StudyAgentError, LLMError, VectorDBError

logger = logging.getLogger(__name__)

T = TypeVar("T")


@dataclass
class RetryConfig:
    """リトライ設定"""

    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 30.0
    exponential_base: float = 2.0
    retryable_exceptions: tuple[Type[Exception], ...] = field(
        default_factory=lambda: (LLMError, VectorDBError, ConnectionError, TimeoutError)
    )

    def calculate_delay(self, attempt: int) -> float:
        """指数バックオフを用いて、指定された試行の遅延を計算"""
        delay = self.base_delay * (self.exponential_base**attempt)
        return min(delay, self.max_delay)


def with_retry(
    config: RetryConfig | None = None,
) -> Callable[[Callable[..., Awaitable[T]]], Callable[..., Awaitable[T]]]:
    """
    指数バックオフを用いた非同期関数の再試行用デコレータ

    Usage:
        @with_retry(RetryConfig(max_retries=3))
        async def call_llm(prompt: str) -> str:
            ...
    """
    if config is None:
        config = RetryConfig()

    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            last_exception: Exception | None = None
            for attempt in range(1, config.max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except config.retryable_exceptions as e:
                    last_exception = e

                    if attempt < config.max_retries:
                        delay = config.calculate_delay(attempt)
                        logger.warning(
                            f"Attempt {attempt + 1} / {config.max_retries + 1} failed: {e}"
                            "Retrying in {delay} seconds..."
                        )
                        await asyncio.sleep(delay)
                    else:
                        logger.error(
                            "All {config.max_retries + 1} attempts failed for {func.__name__}"
                        )
                except Exception:
                    raise

            if last_exception:
                raise last_exception
            raise RuntimeError("Unexpected state in retry")

        return wrapper

    return decorator
