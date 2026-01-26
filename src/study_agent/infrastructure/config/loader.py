"""ファイルローダー設定"""

from pathlib import Path
from typing import Optional, Any

import yaml

from study_agent.core.exceptions import ConfigurationError
from study_agent.core.logging_config import get_logger
from study_agent.infrastructure.config.settings import AppConfig

logger = get_logger(__name__)

DEFAULT_CONFIG_PATH = [
    Path("config/config.yaml"),
    Path("config/config.yml"),
    Path.home() / ".coonfig" / "study_agent" / "config.yaml",
    Path.home() / ".coonfig" / "study_agent" / "config.yml",
]


def load_yaml_file(path: Path) -> dict[str, Any]:
    """TAMLファイルを読み込み、中身を返す"""
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
            return data if data else {}
    except FileNotFoundError:
        raise ConfigurationError(f"Configration file not found: {path}")
    except yaml.YAMLError as e:
        raise ConfigurationError(f"Invalid YAML in {path}: {e}")


def find_config_file() -> Optional[Path]:
    """デフォルトの場所から設定ファイルを見つける"""

    for path in DEFAULT_CONFIG_PATH:
        if path.exists():
            logger.info(f"Found config file: {path}")
            return path
    return None


def load_config(config_path: Optional[str] = None) -> AppConfig:
    """
    アプリケーション設定を読み込む

    優先順位（高い順）：
    1. 環境変数
    2. 指定された設定ファイル
    3. デフォルトの設定ファイル配置場所
    4. デフォルト値

    Args:
        config_path: 設定ファイルのパス

    Returns:
        AppConfig: アプリケーション設定
    """
    config_data: dict[str, Any] = {}

    if config_path:
        file_path = Path(config_path)
        if not file_path.exists():
            raise ConfigurationError(f"Configration file not found: {config_path}")
        config_data = load_yaml_file(file_path)
        logger.info(f"Loading config from {config_path}")
    else:
        found_path = find_config_file()
        if found_path:
            config_data = load_yaml_file(found_path)
            logger.info(f"Loading config from {found_path}")
        else:
            logger.info("Using default configuration")

    try:
        return AppConfig(**config_data)
    except Exception as e:
        raise ConfigurationError(f"Invalid configuration: {e}")


def create_default_config_file(path: Path) -> None:
    """デフォルトの設定ファイルを作成"""
    default_config = {
        "app_name": "StudyAgent",
        "version": "0.1.0",
        "debug": False,
        "llm": {
            "provider": "ollama",
            "temperature": 0.7,
            "max_tokens": 2048,
            "timeout": 30,
            "ollama": {
                "base_url": "http://localhost:11434",
                "model": "llama3.1:8b",
                "embedding_model": "nomic-embed-text",
            },
        },
        "vector_db": {
            "provider": "chroma",
            "persist_directory": "data/vectors/chroma",
            "collection_name": "study_agent",
        },
        "database": {
            "provider": "sqlite",
            "path": "data/db/study_agent.db",
        },
        "logging": {
            "level": "INFO",
            "file": "data/logs/study_agent.log",
        },
    }

    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(default_config, f, default_flow_style=False, allow_unicode=True)

    logger.info(f"Created default config file: {path}")
