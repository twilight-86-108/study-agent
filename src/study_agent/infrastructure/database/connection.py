"""データベース接続管理.

SQLiteデータベースへの接続を管理し、セッションを提供する。
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager, contextmanager
from pathlib import Path
from typing import TYPE_CHECKING, AsyncGenerator, Generator

from sqlmodel import Session, SQLModel, create_engine

if TYPE_CHECKING:
    from sqlalchemy import Engine

logger = logging.getLogger(__name__)


class DatabaseManager:
    """データベース接続マネージャー.

    SQLiteデータベースへの接続を管理し、セッションを提供する。
    シングルトンパターンではなく、DIで使用することを想定。

    Example:
        ```python
        db_manager = DatabaseManager("./data/db/study_agent.db")
        db_manager.initialize()

        with db_manager.get_session() as session:
            documents = session.exec(select(Document)).all()

        db_manager.close()
        ```
    """

    def __init__(
        self,
        database_path: str | Path,
        echo: bool = False,
    ) -> None:
        """初期化.

        Args:
            database_path: データベースファイルのパス
            echo: SQLログを出力するかどうか
        """
        self._database_path = Path(database_path)
        self._echo = echo
        self._engine: Engine | None = None
        self._initialized = False

    @property
    def database_url(self) -> str:
        """SQLAlchemy用のデータベースURL."""
        return f"sqlite:///{self._database_path}"

    @property
    def is_initialized(self) -> bool:
        """初期化済みかどうか."""
        return self._initialized

    @property
    def engine(self) -> Engine:
        """SQLAlchemyエンジンを取得."""
        if self._engine is None:
            raise RuntimeError("Database is not initialized. Call initialize() first.")
        return self._engine

    def initialize(self, create_tables: bool = True) -> None:
        """データベースを初期化する.

        Args:
            create_tables: テーブルを作成するかどうか
        """
        if self._initialized:
            logger.debug("Database already initialized")
            return

        # ディレクトリを作成
        self._database_path.parent.mkdir(parents=True, exist_ok=True)

        # エンジンを作成
        self._engine = create_engine(
            self.database_url,
            echo=self._echo,
            connect_args={"check_same_thread": False},
        )

        # テーブルを作成
        if create_tables:
            self._create_tables()

        self._initialized = True
        logger.info(f"Database initialized: {self._database_path}")

    def _create_tables(self) -> None:
        """すべてのテーブルを作成する."""
        # モデルをインポートして登録
        from study_agent.infrastructure.database import models  # noqa: F401

        SQLModel.metadata.create_all(self._engine)
        logger.debug("Database tables created")

    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """データベースセッションを取得する（同期版）.

        Yields:
            Session: データベースセッション

        Example:
            ```python
            with db_manager.get_session() as session:
                doc = session.get(Document, document_id)
            ```
        """
        if not self._initialized:
            raise RuntimeError("Database is not initialized. Call initialize() first.")

        session = Session(self._engine)
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    @asynccontextmanager
    async def get_async_session(self) -> AsyncGenerator[Session, None]:
        """データベースセッションを取得する（非同期版）.

        Note:
            SQLiteは真の非同期をサポートしていないため、
            これは同期セッションのラッパーです。

        Yields:
            Session: データベースセッション
        """
        with self.get_session() as session:
            yield session

    def close(self) -> None:
        """データベース接続を閉じる."""
        if self._engine is not None:
            self._engine.dispose()
            self._engine = None
        self._initialized = False
        logger.debug("Database connection closed")

    def drop_all_tables(self) -> None:
        """すべてのテーブルを削除する（テスト用）."""
        if not self._initialized:
            return

        SQLModel.metadata.drop_all(self._engine)
        logger.warning("All database tables dropped")

    def __enter__(self) -> DatabaseManager:
        """コンテキストマネージャーのエントリー."""
        self.initialize()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> None:
        """コンテキストマネージャーの終了."""
        self.close()


# グローバルインスタンス（オプション）
_default_manager: DatabaseManager | None = None


def get_database_manager() -> DatabaseManager:
    """デフォルトのDatabaseManagerを取得する."""
    global _default_manager
    if _default_manager is None:
        raise RuntimeError(
            "Default database manager is not set. Call set_database_manager() first."
        )
    return _default_manager


def set_database_manager(manager: DatabaseManager) -> None:
    """デフォルトのDatabaseManagerを設定する."""
    global _default_manager
    _default_manager = manager
