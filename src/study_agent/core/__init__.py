"""コアモジュール（例外・ユーティリティ・定数）"""

from study_agent.core.constants import (
    APP_NAME,
    APP_VERSION,
    DEFAULT_CHUNK_SIZE,
    DEFAULT_CHUNK_OVERLAP,
    DEAFULT_QUIZ_COUNT,
    DEFAULT_QUIZ_DIFFICULTY,
    MASTERY_THRESHOLD,
    WEAK_TOPIC_THRESHOLD,
)
from study_agent.core.exceptions import (
    StudyAgentError,
    ErrorContext,
    DocumentError,
    DocumentNotFoundError,
    UnsupportedFormatError,
    DocumentTooLargeError,
    DocumentParseError,
    LLMError,
    LLMConnectionError,
    LLMTimeoutError,
    LLMResponseError,
    DatabaseError,
    DatabaseConnectionError,
    RecordNotFoundError,
    VectorDBError,
    EmbeddingError,
    SearchError,
    ValidationError,
    ConfigurationError,
)
from study_agent.core.error_handler import Result, handle_errors
from study_agent.core.retry import RetryConfig, with_retry
from study_agent.core.logging_config import setup_logging, get_logger

__all__ = [
    # Constants
    "APP_NAME",
    "APP_VERSION",
    "DEFAULT_CHUNK_SIZE",
    "DEFAULT_CHUNK_OVERLAP",
    "DEFAULT_QUIZ_COUNT",
    "DEFAULT_DIFFICULTY",
    "MASTERY_THRESHOLD",
    "WEAK_TOPIC_THRESHOLD",
    # Exceptions
    "StudyAgentError",
    "ErrorContext",
    "DocumentError",
    "DocumentNotFoundError",
    "UnsupportedFormatError",
    "DocumentTooLargeError",
    "DocumentParseError",
    "LLMError",
    "LLMConnectionError",
    "LLMTimeoutError",
    "LLMResponseError",
    "DatabaseError",
    "DatabaseConnectionError",
    "RecordNotFoundError",
    "VectorDBError",
    "EmbeddingError",
    "SearchError",
    "ValidationError",
    "ConfigurationError",
    # Error handling
    "Result",
    "handle_errors",
    # Retry
    "RetryConfig",
    "with_retry",
    # Logging
    "setup_logging",
    "get_logger",
]
