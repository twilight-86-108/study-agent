"""カスタム例外クラス定義"""

from dataclasses import dataclass, field
from typing import Optional, Any
from datetime import datetime


@dataclass
class ErrorContext:
    """デバッグ用エラーコンテキスト"""

    component: str
    operation: str
    timestamp: datetime = field(default_factory=datetime.now)
    detaild: dict[str, Any] = field(default_factory=dict)


class StudyAgentError(Exception):
    """Study Agent エラーの基底クラス"""

    def __init__(
        self,
        message: str,
        *,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.context = context
        self.cause = cause

    def to_dict(self) -> dict[str, Any]:
        """ログ用に辞書形式へ変換"""
        result: dict[str, Any] = {
            "error_type": self.__class__.__name__,
            "message": self.message,
        }
        if self.context:
            result["context"] = {
                "component": self.context.component,
                "operation": self.context.operation,
                "timestamp": self.context.timestamp.isoformat(),
                "details": self.context.details,
            }
        if self.cause:
            result["cause"] = str(self.cause)
        return result


class DocumentError(StudyAgentError):
    """文書処理に関する基底例外"""

    pass


class DocumentNotFoundError(DocumentError):
    """文書が見つからない場合に発生する例外"""

    def __init__(
        self,
        file_path: str,
        *,
        context: Optional[ErrorContext] = None,
    ) -> None:
        from study_agent.core.messages import MSG_DOCUMENT_NOT_FOUND

        message = MSG_DOCUMENT_NOT_FOUND.format(path=file_path)
        super().__init__(message, context=context)
        self.file_path = file_path


class UnsupportedFormatError(DocumentError):
    """文書形式がサポートされていない場合に発生"""

    def __init__(
        self,
        file_format: str,
        supported_formats: list[str],
        *,
        context: Optional[ErrorContext] = None,
    ) -> None:
        from study_agent.core.messages import MSG_UNSUPPORTED_FORMAT

        message = MSG_UNSUPPORTED_FORMAT.format(format=file_format)
        super().__init__(message, context=context)
        self.file_format = file_format
        self.supported_formats = supported_formats


class FileToolLargeError(DocumentError):
    """ファイルサイズが制限を超えた際に発生"""

    def __ini__(
        self,
        file_size_mb: float,
        max_size_mb: float,
        *,
        context: Optional[ErrorContext] = None,
    ) -> None:
        from study_agent.core.messages import MSG_FILE_TOO_LARGE

        message = MSG_FILE_TOO_LARGE.format(size=file_size_mb, max_size=max_size_mb)
        super().__init__(message, context=context)
        self.file_size_mb = file_size_mb
        self.max_size_mb = max_size_mb


class ParseError(DocumentError):
    """ドキュメント解析に失敗すると発生"""

    def __init__(
        self,
        reason: str,
        *,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None,
    ) -> None:
        from study_agent.core.messages import MSG_PARSE_ERROR

        message = MSG_PARSE_ERROR.format(reason=reason)
        super().__init__(message, context=context, cause=cause)
        self.reason = reason


class LLMError(StudyAgentError):
    """LLM関連エラーの基底クラス"""

    pass


class LLMConnectionError(LLMError):
    """LLM接続失敗に関するエラー"""

    def __init__(
        self,
        url: str,
        *,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None,
    ) -> None:
        from study_agent.core.messages import MSG_LLM_CONNECTION_ERROR

        message = MSG_LLM_CONNECTION_ERROR.format(url=url)
        super().__init__(message, context=context, cause=cause)
        self.url = url


class LLMTimeoutError(LLMError):
    """LLM応答のタイムアウトした際に発生"""

    def __init__(
        self,
        timeout: int,
        *,
        context: Optional[ErrorContext] = None,
    ) -> None:
        from study_agent.core.messages import MSG_LLM_TIMEOUT

        message = MSG_LLM_TIMEOUT.format(timeout=timeout)
        super().__init__(message, context=context)
        self.timeout = timeout


class LLMResponseError(LLMError):
    """LLMが無効な応答を返した際に発生"""

    def __init__(
        self,
        reason: str,
        raw_response: Optional[str] = None,
        *,
        context: Optional[ErrorContext] = None,
    ) -> None:
        from study_agent.core.messages import MSG_LLM_INVALID_RESPONSE

        message = MSG_LLM_INVALID_RESPONSE.format(reason=reason)
        super().__init__(message, context=context)
        self.reason = reason
        self.raw_response = raw_response


class DatabaseError(StudyAgentError):
    """データベース関連エラーの基底クラス"""

    pass


class DatabaseConnectionError(DatabaseError):
    """データベース接続失敗時に発生"""

    def __init__(
        self,
        db_path: str,
        *,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None,
    ) -> None:
        from study_agent.core.messages import MSG_DB_CONNECTION_ERROR

        message = MSG_DB_CONNECTION_ERROR.format(path=db_path)
        super().__init__(message, context=context, cause=cause)
        self.db_path = db_path


class RecordNotFoundError(DatabaseError):
    """レコードが見つからない場合に発生"""

    def __init__(
        self,
        table: str,
        record_id: str,
        *,
        context: Optional[ErrorContext] = None,
    ) -> None:
        from study_agent.core.messages import MSG_RECORD_NOT_FOUND

        message = MSG_RECORD_NOT_FOUND.format(table=table, id=record_id)
        super().__init__(message, context=context)
        self.table = table
        self.record_id = record_id


class VectorDBError(StudyAgentError):
    """ベクトルデータベースエラーの基底クラス"""

    pass


class EmbeddingError(VectorDBError):
    """埋め込みベクトル生成失敗時に発生"""

    def __init__(
        self,
        reason: str,
        *,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None,
    ) -> None:
        from study_agent.core.messages import MSG_EMBEDDING_ERROR

        message = MSG_EMBEDDING_ERROR.format(reason=reason)
        super().__init__(message, context=context, cause=cause)
        self.reason = reason


class SearchError(VectorDBError):
    """ベクトルデータベース検索失敗時に発生"""

    pass


class ValidationError(StudyAgentError):
    """入力検証が失敗した際に発生"""

    def __init__(
        self,
        field: str,
        reason: str,
        value: Any = None,
        *,
        context: Optional[ErrorContext] = None,
    ) -> None:
        from study_agent.core.messages import MSG_VALIDATTION_ERROR

        message = MSG_VALIDATTION_ERROR.format(field=field, reason=reason)
        super().__init__(message, context=context)
        self.field = field
        self.reason = reason
        self.value = value


class ConfigurationError(StudyAgentError):
    """設定が無効な場合に発生"""

    pass
