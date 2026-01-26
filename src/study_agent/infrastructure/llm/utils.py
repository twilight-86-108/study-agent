"""LLMユーティリティ関数"""

import json
import re
from typing import Any, Optional

from study_agent.core.exceptions import LLMResponseError
from study_agent.core.logging_config import get_logger

logger = get_logger(__name__)


def parse_llm_json(
    text: str,
    schema: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """
    LLM応答から複数のフォールバック戦略を用いてJSONを解析

    戦略：
    1. 直接的なJSON解析
    2. Markdownコードブロックからの抽出
    3. テキスト内の最初のJSONオブジェクトを検索

    Args:
        text: LLM応答テキスト
        schema: JSONスキーマ

    Returns:
        dict[str, Any]: 解析されたJSONオブジェクト

    Raises:
        LLMResponseError: JSON解析に失敗した場合
    """
    try:
        result = json.loads(text.strip())
        logger.debug("JSON parsed directly")
        return result
    except json.JSONDecodeError:
        pass

    code_block_pattern = r"```(?:json)?\s*\n?([\s\S]*?)\n?```"
    matches = re.findall(code_block_pattern, text)

    for match in matches:
        try:
            result = json.loads(match.strip())
            logger.debug("JSON extracted from code block")
            return result
        except json.JSONDecodeError:
            continue

    json_pattern = r"\{[\s\S]*\}"
    matches = re.findall(json_pattern, text)

    for match in matches:
        try:
            result = json.loads(match)
            logger.debug("JSON found in text")
            return result
        except json.JSONDecodeError:
            continue

    raise LLMResponseError(
        reason="Failed to parse JSON from LLM response",
        raw_response=text[:500],
    )


def extract_text_content(text: str) -> str:
    """
    LLM応答からクリーンなテキストコンテンツを抽出
    コードブロックと余分な空白を除去
    """
    text = re.sub(r"```[\s\S]*?```", "", text)

    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


def build_json_prompt(
    base_prompt: str,
    schema: dict[str, Any],
) -> str:
    """
    JSON形式で応答するよう指示するプロンプトを作成

    Args:
        base_prompt: 基本的なプロンプト
        schema: JSONスキーマ

    Returns:
        str: JSON形式で応答するよう指示するプロンプト
    """
    schema_str = json.dumps(schema, indent=2, ensure_ascii=False)
    return f"""
    {base_prompt}

    有効なJSON形式のみで応答してください。
    他のテキストやコードブロックは不可、JSONのみです。

    期待されるJSONスキーマ:
    ```json
    {schema_str}
    ```

    JSONで応答してください:
    """
