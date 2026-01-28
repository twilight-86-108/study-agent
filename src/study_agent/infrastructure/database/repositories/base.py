"""リポジトリ基底クラス.

すべてのリポジトリの共通インターフェースと基本実装を提供する。
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Generic, TypeVar, Optional, Sequence, Any

from sqlmodel import Session, SQLModel, select

from study_agent.core.exceptions import DatabaseError, RecordNotFoundError

logger = logging.getLogger(__name__)

# 型変数
T = TypeVar("T", bound=SQLModel)


class BaseRepository(ABC, Generic[T]):
    """リポジトリの抽象基底クラス.

    すべてのリポジトリはこのクラスを継承し、
    モデル固有の操作を実装する。

    Type Parameters:
        T: SQLModelを継承したモデルクラス

    Example:
        ```python
        class DocumentRepository(BaseRepository[Document]):
            @property
            def _model_class(self) -> type[Document]:
                return Document

            async def find_by_file_path(self, file_path: str) -> Document | None:
                with self._session_factory() as session:
                    statement = select(Document).where(Document.file_path == file_path)
                    return session.exec(statement).first()
        ```
    """

    def __init__(self, session: Session) -> None:
        """初期化.

        Args:
            session: データベースセッション
        """
        self._session = session

    @property
    @abstractmethod
    def _model_class(self) -> type[T]:
        """モデルクラスを返す."""
        ...

    @property
    def _model_name(self) -> str:
        """モデル名を返す."""
        return self._model_class.__name__

    def get_by_id(self, id: str) -> T | None:
        """IDでレコードを取得する.

        Args:
            id: レコードID

        Returns:
            レコード、存在しない場合はNone
        """
        try:
            return self._session.get(self._model_class, id)
        except Exception as e:
            raise DatabaseError(
                message=f"Failed to get {self._model_name} by id: {id}",
                details={"id": id},
                cause=e,
            ) from e

    def get_by_id_or_raise(self, id: str) -> T:
        """IDでレコードを取得する（存在しない場合は例外）.

        Args:
            id: レコードID

        Returns:
            レコード

        Raises:
            RecordNotFoundError: レコードが存在しない場合
        """
        record = self.get_by_id(id)
        if record is None:
            raise RecordNotFoundError(
                message=f"{self._model_name} not found: {id}",
                details={"model": self._model_name, "id": id},
            )
        return record

    def get_all(
        self,
        offset: int = 0,
        limit: int | None = None,
    ) -> Sequence[T]:
        """すべてのレコードを取得する.

        Args:
            offset: オフセット
            limit: 取得数の上限

        Returns:
            レコードのリスト
        """
        try:
            statement = select(self._model_class).offset(offset)
            if limit is not None:
                statement = statement.limit(limit)
            return self._session.exec(statement).all()
        except Exception as e:
            raise DatabaseError(
                message=f"Failed to get all {self._model_name}",
                cause=e,
            ) from e

    def count(self) -> int:
        """レコード数を取得する.

        Returns:
            レコード数
        """
        try:
            from sqlalchemy import func

            statement = select(func.count()).select_from(self._model_class)
            result = self._session.exec(statement).one()
            return result or 0
        except Exception as e:
            raise DatabaseError(
                message=f"Failed to count {self._model_name}",
                cause=e,
            ) from e

    def create(self, record: T) -> T:
        """レコードを作成する.

        Args:
            record: 作成するレコード

        Returns:
            作成されたレコード
        """
        try:
            self._session.add(record)
            self._session.flush()
            self._session.refresh(record)
            logger.debug(
                f"Created {self._model_name}: {getattr(record, 'id', 'unknown')}"
            )
            return record
        except Exception as e:
            raise DatabaseError(
                message=f"Failed to create {self._model_name}",
                details={"record": str(record)},
                cause=e,
            ) from e

    def create_many(self, records: Sequence[T]) -> Sequence[T]:
        """複数レコードを作成する.

        Args:
            records: 作成するレコードのリスト

        Returns:
            作成されたレコードのリスト
        """
        try:
            for record in records:
                self._session.add(record)
            self._session.flush()
            for record in records:
                self._session.refresh(record)
            logger.debug(f"Created {len(records)} {self._model_name} records")
            return records
        except Exception as e:
            raise DatabaseError(
                message=f"Failed to create multiple {self._model_name}",
                details={"count": len(records)},
                cause=e,
            ) from e

    def update(self, record: T) -> T:
        """レコードを更新する.

        Args:
            record: 更新するレコード

        Returns:
            更新されたレコード
        """
        try:
            self._session.add(record)
            self._session.flush()
            self._session.refresh(record)
            logger.debug(
                f"Updated {self._model_name}: {getattr(record, 'id', 'unknown')}"
            )
            return record
        except Exception as e:
            raise DatabaseError(
                message=f"Failed to update {self._model_name}",
                details={"record": str(record)},
                cause=e,
            ) from e

    def delete(self, record: T) -> None:
        """レコードを削除する.

        Args:
            record: 削除するレコード
        """
        try:
            self._session.delete(record)
            self._session.flush()
            logger.debug(
                f"Deleted {self._model_name}: {getattr(record, 'id', 'unknown')}"
            )
        except Exception as e:
            raise DatabaseError(
                message=f"Failed to delete {self._model_name}",
                details={"record": str(record)},
                cause=e,
            ) from e

    def delete_by_id(self, id: str) -> bool:
        """IDでレコードを削除する.

        Args:
            id: レコードID

        Returns:
            削除成功した場合True
        """
        record = self.get_by_id(id)
        if record is None:
            return False
        self.delete(record)
        return True

    def exists(self, id: str) -> bool:
        """レコードが存在するか確認する.

        Args:
            id: レコードID

        Returns:
            存在する場合True
        """
        return self.get_by_id(id) is not None
