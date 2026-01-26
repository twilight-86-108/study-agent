"""エラーメッセージ"""

# Documents errors
MSG_DOCUMENT_NOT_FOUND = "指定されたドキュメントが見つかりません: {path}"
MSG_UNSUPPORTED_FORMAT = "サポートされていないファイル形式です: {format}"
MSG_FILE_TOO_LARGE = "ファイルサイズが大きすぎます: {size}MB (最大: {max_size}MB)"
MSG_PARSE_ERROR = "ドキュメントの解析に失敗しました: {reason}"
# LLM errors
MSG_LLM_CONNECTION_ERROR = "LLMサーバーに接続できません: {url}"
MSG_LLM_TIMEOUT = "LLMの応答がタイム・アウトしました ({timeout}秒)"
MSG_LLM_INVALID_RESPONSE = "LLMから無効な応答を受信しました"
# Database errors
MSG_DB_CONNECTION_ERROR = "データベースに接続できません: {path}"
MSG_RECORD_NOT_FOUND = "レコードが見つかりません: {table} (id={id})"
# VectorDB errors
MSG_VECTORDB_ERROR = "ベクトルDBでエラーが発生しました: {reason}"
MSG_EMBEDDING_ERROR = "埋め込みベクトル生成に失敗しました: {reason}"
# Validation errors
MSG_VALIDATTION_ERROR = "入力値が不正です: {field} - {reason}"
# General errors
MSG_UNEXPECTED_ERROR = "予期せぬエラーが発生しました"
MSG_OPERATION_CANCELLED = "操作がキャンセルされました"
