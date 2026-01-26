"""ログの設定"""

import logging
import sys
from pathlib import Path
from typing import Optional

from study_agent.core.constants import APP_NAME


def setup_logging(
    level: str = "INFO",
    log_file: Optional[str] = None,
    json_format: bool = False,
) -> None:
    """
    アプリのログの設定

    Args:
        level: ログレベル
        log_file: ログファイルのパス
        json_format: JSON形式で出力するかどうか
    """
    log_level = getattr(logging, level.upper(), logging.INFO)

    if json_format:
        formatter = logging.Formatter(
            '{"timestamp" "%(asctime)s", "level" "%(levelname)s",'
            '{"logger": "%(name)s", "message" "%(message)s"}'
        )
    else:
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

    root_logger = logging.getLogger(APP_NAME.lower().replace(" ", "_"))
    root_logger.setLevel(log_level)

    root_logger.handlers.clear()

    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_path, encoding="utf-8")
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("chromadb").setLevel(logging.WARNING)
    logging.getLogger("langchain").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """アプリケーションプレフィックス付きのログを取得"""
    return logging.getLogger(f"{APP_NAME.lower().replace(' ', '_')}.{name}")
