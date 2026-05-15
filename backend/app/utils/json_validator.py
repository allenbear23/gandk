"""
utils/json_validator.py — AI 輸出 JSON 驗證與修復工具

Gemini 有時會在 JSON 前後加入 markdown 代碼塊（```json ... ```）
或夾雜說明文字，這個模組負責清理並驗證輸出。
"""
import json
import re
import logging
from typing import Optional
from app.models.question import Question, Choice

logger = logging.getLogger(__name__)


def extract_and_validate_json(raw_output: str) -> Optional[list[dict]]:
    """
    從 AI 原始輸出中提取 JSON 並驗證題目格式。

    處理以下常見問題：
    1. ```json ... ``` markdown 代碼塊包裹
    2. JSON 前後有多餘說明文字
    3. 單題 vs 陣列格式不一致
    4. 欄位缺失或型別錯誤

    回傳：驗證通過的 Question dict list，失敗時回傳 None
    """
    # Step 1: 清理 markdown 代碼塊
    cleaned = _strip_markdown_fences(raw_output)

    # Step 2: 嘗試找出 JSON 片段
    json_str = _extract_json_object(cleaned)
    if not json_str:
        logger.error(f"找不到有效 JSON，原始輸出:\n{raw_output[:500]}")
        return None

    # Step 3: 解析 JSON
    try:
        data = json.loads(json_str)
    except json.JSONDecodeError as e:
        logger.error(f"JSON 解析失敗: {e}\n原始: {json_str[:300]}")
        return None

    # Step 4: 統一格式（支援 {questions: [...]} 或直接 [...]）
    if isinstance(data, dict):
        questions_raw = data.get("questions", [])
    elif isinstance(data, list):
        questions_raw = data
    else:
        logger.error(f"意外的 JSON 結構: {type(data)}")
        return None

    # Step 5: 逐題驗證
    validated = []
    for i, q_raw in enumerate(questions_raw):
        try:
            q = _validate_single_question(q_raw, i + 1)
            if q:
                validated.append(q)
        except Exception as e:
            logger.warning(f"第 {i+1} 題驗證失敗（跳過）: {e}")

    if not validated:
        logger.error("所有題目驗證均失敗")
        return None

    logger.info(f"✅ JSON 驗證完成：{len(validated)}/{len(questions_raw)} 題通過")
    return validated


def _strip_markdown_fences(text: str) -> str:
    """移除 ```json ... ``` 或 ``` ... ``` 包裹"""
    # 移除開頭的 ```json 或 ```
    text = re.sub(r'^```(?:json)?\s*\n?', '', text.strip(), flags=re.IGNORECASE)
    # 移除結尾的 ```
    text = re.sub(r'\n?```\s*$', '', text.strip())
    return text.strip()


def _extract_json_object(text: str) -> Optional[str]:
    """
    從文字中提取第一個完整的 JSON 物件或陣列。
    使用括號計數法找到匹配的結尾括號。
    """
    # 尋找 { 或 [ 開頭
    start_idx = -1
    start_char = None
    end_char = None

    for i, ch in enumerate(text):
        if ch == '{':
            start_idx = i
            start_char, end_char = '{', '}'
            break
        elif ch == '[':
            start_idx = i
            start_char, end_char = '[', ']'
            break

    if start_idx == -1:
        return None

    # 括號計數找結尾
    depth = 0
    in_string = False
    escape_next = False

    for i in range(start_idx, len(text)):
        ch = text[i]

        if escape_next:
            escape_next = False
            continue
        if ch == '\\' and in_string:
            escape_next = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue

        if ch == start_char:
            depth += 1
        elif ch == end_char:
            depth -= 1
            if depth == 0:
                return text[start_idx:i+1]

    return None


def _validate_single_question(q_raw: dict, idx: int) -> Optional[dict]:
    """
    驗證單一題目並補全缺失欄位。
    使用 Pydantic Question model 做嚴格驗證。
    """
    if not isinstance(q_raw, dict):
        raise ValueError(f"題目不是 dict 型別: {type(q_raw)}")

    # 補全 id
    if "id" not in q_raw or q_raw["id"] is None:
        q_raw["id"] = idx

    # 補全 difficulty
    if "difficulty" not in q_raw or q_raw["difficulty"] is None:
        q_raw["difficulty"] = 3

    # 確保 choices 格式正確
    choices = q_raw.get("choices", [])
    if isinstance(choices, list) and choices:
        # 支援 {"A": "文字"} 格式轉換為 [{"key":"A","text":"文字"}]
        if isinstance(choices[0], dict) and "key" not in choices[0]:
            normalized = []
            for key in ["A", "B", "C", "D"]:
                if key in choices[0]:
                    normalized.append({"key": key, "text": choices[0][key]})
            if normalized:
                q_raw["choices"] = normalized

    # Pydantic 驗證
    q = Question(**q_raw)
    return q.model_dump()
