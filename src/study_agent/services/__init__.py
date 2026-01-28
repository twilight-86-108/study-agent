"""Business logic services.

ドメイン層のビジネスロジックを提供するサービス群。

このモジュールは以下のサービスを提供する:

- DocumentService: ドキュメントの読み込み、解析、保存
- SearchService: RAG検索とコンテキスト取得
- QuizService: クイズ生成と回答評価
- ProgressService: 学習進捗の記録と分析
- SessionService: 学習セッションの管理

アーキテクチャ上の位置:
    Presentation Layer (CLI)
           ↓
    Application Layer (Agents)
           ↓
    **Domain Layer (Services)** ← ここ
           ↓
    Infrastructure Layer (LLM, VectorDB, Database)

Example:
    >>> from study_agent.services import DocumentService, SearchService
    >>>
    >>> # サービスの初期化（DIコンテナから取得することを推奨）
    >>> doc_service = DocumentService(config, db_manager, vectordb, embedding_service)
    >>> search_service = SearchService(vectordb, embedding_service, db_manager)
    >>>
    >>> # ドキュメントの読み込み
    >>> result = await doc_service.load_document("/path/to/doc.pdf")
    >>>
    >>> # コンテキスト検索
    >>> context = await search_service.get_context_for_explanation("Amazon EC2")
"""

from study_agent.services.document_service import DocumentService
from study_agent.services.search_service import SearchService
from study_agent.services.quiz_service import QuizService
from study_agent.services.progress_service import ProgressService
from study_agent.services.session_service import SessionService

__all__ = [
    # Services
    "DocumentService",
    "SearchService",
    "QuizService",
    "ProgressService",
    "SessionService",
]
