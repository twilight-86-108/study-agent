"""Document management service.

ドキュメントの読み込み、解析、保存を管理するサービス。

主な機能:
    - ドキュメントファイルの読み込みと解析
    - テキストのチャンク分割
    - 埋め込みベクトルの生成
    - VectorDBとRDBへの保存
    - ドキュメントの取得・一覧・削除

Example:
    >>> service = DocumentService(config, db_manager, vectordb, embedding_service)
    >>> result = await service.load_document("/path/to/doc.pdf")
    >>> print(result.document.title)
"""

from __future__ import annotations

import logging
import uuid
from pathlib import Path
from typing import Sequence

from study_agent.core.exceptions import (
    DocumentNotFoundError,
    DocumentTooLargeError,
    UnsupportedFormatError,
    ErrorContext,
)
from study_agent.domain import (
    Document,
    Chapter,
    Topic,
    Chunk,
    FileType,
    LoadDocumentResult,
)
from study_agent.infrastructure.config import AppConfig
from study_agent.infrastructure.database import (
    DatabaseManager,
    DocumentRepository,
    ChapterRepository,
    TopicRepository,
    ChunkRepository,
)
from study_agent.infrastructure.database import (
    Document as DocumentModel,
    Chapter as ChapterModel,
    Topic as TopicModel,
    Chunk as ChunkModel,
)
from study_agent.infrastructure.parsers import ParserFactory
from study_agent.infrastructure.vectordb import (
    BaseVectorDB,
    BaseEmbeddingService,
    ChunkData,
)

logger = logging.getLogger(__name__)


class DocumentService:
    """ドキュメント管理サービス.

    ドキュメントの読み込み、解析、保存、削除を管理する。

    Attributes:
        config: アプリケーション設定
        db_manager: データベースマネージャ
        vectordb: ベクトルDBクライアント
        embedding_service: 埋め込みサービス

    Example:
        >>> service = DocumentService(config, db_manager, vectordb, embedding_service)
        >>> result = await service.load_document("/path/to/doc.pdf")
        >>> docs = await service.list_documents()
    """

    def __init__(
        self,
        config: AppConfig,
        db_manager: DatabaseManager,
        vectordb: BaseVectorDB,
        embedding_service: BaseEmbeddingService,
    ) -> None:
        """初期化.

        Args:
            config: アプリケーション設定
            db_manager: データベースマネージャ
            vectordb: ベクトルDBクライアント
            embedding_service: 埋め込みサービス
        """
        self.config = config
        self.db_manager = db_manager
        self.vectordb = vectordb
        self.embedding_service = embedding_service

    def _generate_id(self) -> str:
        """UUID v4を生成する."""
        return str(uuid.uuid4())

    def _check_file_size(self, file_path: Path) -> None:
        """ファイルサイズをチェックする.

        Args:
            file_path: チェックするファイルパス

        Raises:
            FileTooLargeError: ファイルサイズが上限を超えている場合
        """
        max_size_bytes = self.config.document.max_file_size_mb * 1024 * 1024
        file_size = file_path.stat().st_size

        if file_size > max_size_bytes:
            raise DocumentTooLargeError(
                file_size_mb=file_size / (1024 * 1024),
                max_size_mb=self.config.document.max_file_size_mb,
            )

    def _check_file_extension(self, file_path: Path) -> FileType:
        """ファイル拡張子をチェックしてFileTypeを返す.

        Args:
            file_path: チェックするファイルパス

        Returns:
            FileType: ファイルタイプ

        Raises:
            UnsupportedFormatError: サポートされていない形式の場合
        """
        ext = file_path.suffix.lower().lstrip(".")
        try:
            return FileType.from_extension(ext)
        except ValueError as e:
            raise UnsupportedFormatError(ext) from e

    def _split_into_chunks(
        self,
        content: str,
        chunk_size: int,
        chunk_overlap: int,
    ) -> list[str]:
        """テキストをオーバーラップありでチャンク分割する.

        文や段落の境界でできるだけ区切るようにする。

        Args:
            content: 分割するテキスト
            chunk_size: チャンクサイズ（文字数）
            chunk_overlap: オーバーラップサイズ（文字数）

        Returns:
            チャンクのリスト
        """
        if not content:
            return []

        chunks: list[str] = []
        start = 0

        while start < len(content):
            end = start + chunk_size

            # コンテンツの終わりより前なら、区切り位置を調整
            if end < len(content):
                # 段落区切りを探す
                para_break = content.rfind("\n\n", start, end)
                if para_break > start + chunk_size // 2:
                    end = para_break + 2
                else:
                    # 文の区切りを探す
                    for sep in ["。", ".", "!", "?", "！", "？", "\n"]:
                        sent_break = content.rfind(sep, start, end)
                        if sent_break > start + chunk_size // 2:
                            end = sent_break + 1
                            break

            chunk = content[start:end].strip()
            if chunk:
                chunks.append(chunk)

            # 次の開始位置（オーバーラップ考慮）
            start = end - chunk_overlap
            if start >= len(content):
                break

        return chunks

    async def load_document(
        self,
        file_path: str,
        title: str | None = None,
    ) -> LoadDocumentResult:
        """ドキュメントを読み込み、解析、保存する.

        処理フロー:
        1. ファイルのバリデーション
        2. パーサーでドキュメントを解析
        3. テキストをチャンク分割
        4. 埋め込みベクトルを生成
        5. VectorDBとRDBに保存

        Args:
            file_path: ファイルパス
            title: カスタムタイトル（省略時は自動検出）

        Returns:
            LoadDocumentResult: 読み込み結果

        Raises:
            DocumentNotFoundError: ファイルが存在しない場合
            DocumentTooLargeError: ファイルサイズが上限を超えている場合
            UnsupportedFormatError: サポートされていない形式の場合
            DocumentParseError: 解析に失敗した場合
        """
        path = Path(file_path)
        context = ErrorContext(component="DocumentService", operation="load_document")

        # 1. バリデーション
        if not path.exists():
            raise DocumentNotFoundError(file_path, context=context)

        self._check_file_size(path)
        file_type = self._check_file_extension(path)

        logger.info(f"Loading document: {path}")

        # 2. ドキュメント解析
        parser = ParserFactory.get_parser(path)
        parsed = await parser.parse(path)

        # 3. ID生成
        doc_id = self._generate_id()
        doc_title = title or parsed.title or path.stem

        # 4. チャンク分割
        chunk_texts = self._split_into_chunks(
            parsed.content,
            self.config.chunking.chunk_size,
            self.config.chunking.chunk_overlap,
        )

        logger.info(f"Split into {len(chunk_texts)} chunks")

        # 5. 埋め込み生成
        embeddings_created = False
        chunk_data_list: list[ChunkData] = []
        chunks: list[Chunk] = []

        if chunk_texts:
            logger.info(f"Generating embeddings for {len(chunk_texts)} chunks...")
            embeddings = await self.embedding_service.embed_texts(chunk_texts)
            embeddings_created = True

            for i, (text, embedding) in enumerate(zip(chunk_texts, embeddings)):
                chunk_id = self._generate_id()

                chunk_data_list.append(
                    ChunkData(
                        chunk_id=chunk_id,
                        content=text,
                        embedding=embedding,
                        metadata={
                            "document_id": doc_id,
                            "chunk_index": i,
                        },
                    )
                )

                chunks.append(
                    Chunk(
                        id=chunk_id,
                        document_id=doc_id,
                        content=text,
                        chunk_index=i,
                        embedding_id=chunk_id,
                    )
                )

        # 6. VectorDBに保存
        if chunk_data_list:
            await self.vectordb.add_documents(chunk_data_list)
            logger.info(f"Added {len(chunk_data_list)} chunks to VectorDB")

        # 7. 章・トピックの作成
        chapters: list[Chapter] = []
        topics: list[Topic] = []

        for i, chapter_data in enumerate(parsed.chapters):
            chapter_id = self._generate_id()
            chapters.append(
                Chapter(
                    id=chapter_id,
                    document_id=doc_id,
                    title=chapter_data.title,
                    order_index=i,
                    page_start=chapter_data.page_start,
                    page_end=chapter_data.page_end,
                )
            )

            # 章からトピックを作成
            topic_id = self._generate_id()
            topics.append(
                Topic(
                    id=topic_id,
                    document_id=doc_id,
                    chapter_id=chapter_id,
                    title=chapter_data.title,
                    order_index=i,
                )
            )

        # 8. RDBに保存
        with self.db_manager.get_session() as session:
            doc_repo = DocumentRepository(session)
            chapter_repo = ChapterRepository(session)
            topic_repo = TopicRepository(session)
            chunk_repo = ChunkRepository(session)

            # ドキュメント
            doc_model = DocumentModel(
                id=doc_id,
                title=doc_title,
                file_path=str(path.absolute()),
                file_type=file_type,
                total_pages=parsed.total_pages,
            )
            doc_repo.create(doc_model)

            # 章
            for chapter in chapters:
                chapter_model = ChapterModel(
                    id=chapter.id,
                    document_id=doc_id,
                    title=chapter.title,
                    order_index=chapter.order_index,
                    page_start=chapter.page_start,
                    page_end=chapter.page_end,
                )
                chapter_repo.create(chapter_model)

            # トピック
            for topic in topics:
                topic_model = TopicModel(
                    id=topic.id,
                    document_id=doc_id,
                    chapter_id=topic.chapter_id,
                    title=topic.title,
                    order_index=topic.order_index,
                )
                topic_repo.create(topic_model)

            # チャンク
            for chunk in chunks:
                chunk_model = ChunkModel(
                    id=chunk.id,
                    document_id=doc_id,
                    content=chunk.content,
                    chunk_index=chunk.chunk_index,
                    embedding_id=chunk.embedding_id,
                )
                chunk_repo.create(chunk_model)

        # 9. ドメインモデル作成
        document = Document(
            id=doc_id,
            title=doc_title,
            file_path=str(path.absolute()),
            file_type=file_type,
            total_pages=parsed.total_pages,
            chapters=chapters,
            topics=topics,
        )

        logger.info(
            f"Document loaded: {doc_title} "
            f"({len(chapters)} chapters, {len(topics)} topics, {len(chunks)} chunks)"
        )

        return LoadDocumentResult(
            document=document,
            chapters=chapters,
            topics=topics,
            chunks_count=len(chunks),
            embeddings_created=embeddings_created,
        )

    async def get_document(self, document_id: str) -> Document:
        """IDでドキュメントを取得する.

        Args:
            document_id: ドキュメントID

        Returns:
            Document: ドキュメント

        Raises:
            DocumentNotFoundError: ドキュメントが見つからない場合
        """
        with self.db_manager.get_session() as session:
            doc_repo = DocumentRepository(session)
            doc_model = doc_repo.get_by_id(document_id)

            if doc_model is None:
                raise DocumentNotFoundError(
                    document_id,
                    context=ErrorContext(
                        component="DocumentService",
                        operation="get_document",
                    ),
                )

            return Document(
                id=doc_model.id,
                title=doc_model.title,
                file_path=doc_model.file_path,
                file_type=FileType(doc_model.file_type.value),
                total_pages=doc_model.total_pages,
                description=doc_model.description,
                created_at=doc_model.created_at,
                updated_at=doc_model.updated_at,
            )

    async def list_documents(self) -> list[Document]:
        """全ドキュメントを一覧取得する.

        Returns:
            ドキュメントのリスト
        """
        with self.db_manager.get_session() as session:
            doc_repo = DocumentRepository(session)
            doc_models = doc_repo.get_all()

            return [
                Document(
                    id=m.id,
                    title=m.title,
                    file_path=m.file_path,
                    file_type=FileType(m.file_type.value),
                    total_pages=m.total_pages,
                    description=m.description,
                    created_at=m.created_at,
                    updated_at=m.updated_at,
                )
                for m in doc_models
            ]

    async def delete_document(self, document_id: str) -> None:
        """ドキュメントと関連データを削除する.

        Args:
            document_id: 削除するドキュメントID

        Raises:
            DocumentNotFoundError: ドキュメントが見つからない場合
        """
        # まず存在確認
        await self.get_document(document_id)

        # VectorDBから削除
        await self.vectordb.delete_by_document_id(document_id)
        logger.info(f"Deleted chunks from VectorDB: {document_id}")

        # RDBから削除（カスケード削除）
        with self.db_manager.get_session() as session:
            chunk_repo = ChunkRepository(session)
            topic_repo = TopicRepository(session)
            chapter_repo = ChapterRepository(session)
            doc_repo = DocumentRepository(session)

            # 依存関係の順に削除
            chunk_repo.delete_by_document_id(document_id)
            topic_repo.delete_by_document_id(document_id)
            chapter_repo.delete_by_document_id(document_id)
            doc_repo.delete(document_id)

        logger.info(f"Document deleted: {document_id}")

    async def get_topics(self, document_id: str) -> list[Topic]:
        """ドキュメントのトピック一覧を取得する.

        Args:
            document_id: ドキュメントID

        Returns:
            トピックのリスト
        """
        with self.db_manager.get_session() as session:
            topic_repo = TopicRepository(session)
            topic_models = topic_repo.find_by_document_id(document_id)

            return [
                Topic(
                    id=m.id,
                    document_id=m.document_id,
                    chapter_id=m.chapter_id,
                    title=m.title,
                    description=m.description,
                    order_index=m.order_index,
                    created_at=m.created_at,
                )
                for m in topic_models
            ]

    async def get_chunks(self, document_id: str) -> list[Chunk]:
        """ドキュメントのチャンク一覧を取得する.

        Args:
            document_id: ドキュメントID

        Returns:
            チャンクのリスト
        """
        with self.db_manager.get_session() as session:
            chunk_repo = ChunkRepository(session)
            chunk_models = chunk_repo.find_by_document_id(document_id)

            return [
                Chunk(
                    id=m.id,
                    document_id=m.document_id,
                    content=m.content,
                    chunk_index=m.chunk_index,
                    page_number=m.page_number,
                    embedding_id=m.embedding_id,
                    created_at=m.created_at,
                )
                for m in chunk_models
            ]
