import json
import re
import logging
from typing import Optional, Union, Dict, List
from app.models.question import Question

logger = logging.getLogger(__name__)

def extract_and_validate_json(raw_output: str) -> Optional[Union[Dict, List]]:
    """
    從 AI 輸出中提取 JSON。
    回傳格式可能是:
    1. { "exam_metadata": {...}, "questions": [...] }
    2. [...] (純題目清單)
    """
    cleaned = _strip_markdown_fences(raw_output)
    json_str = _extract_json_object(cleaned)
    if not json_str:
        logger.error("找不到有效 JSON 片段")
        return None

    try:
        data = json.loads(json_str)
    except json.JSONDecodeError as e:
        logger.error(f"JSON 解析失敗: {e}")
        return None

    # 如果是我們新定義的結構物件
    if isinstance(data, dict) and "questions" in data:
        questions_raw = data.get("questions", [])
        validated_qs = _validate_list(questions_raw)
        # 更新回原物件並回傳整個物件 (包含 metadata)
        data["questions"] = validated_qs
        return data
    
    # 如果只是純題目清單
    if isinstance(data, list):
        return _validate_list(data)
    
    # 如果是單個物件（不是清單也不是 metadata 結構）
    if isinstance(data, dict):
        return data

    return None

def _validate_list(questions_raw: list) -> list:
    validated = []
    for i, q_raw in enumerate(questions_raw):
        try:
            q = _validate_single_question(q_raw, i + 1)
            if q: validated.append(q)
        except Exception as e:
            logger.warning(f"第 {i+1} 題驗證失敗: {e}")
    return validated

def _strip_markdown_fences(text: str) -> str:
    text = re.sub(r'^```(?:json)?\s*\n?', '', text.strip(), flags=re.IGNORECASE)
    text = re.sub(r'\n?```\s*$', '', text.strip())
    return text.strip()

def _extract_json_object(text: str) -> Optional[str]:
    start_idx = -1
    start_char, end_char = None, None
    for i, ch in enumerate(text):
        if ch == '{':
            start_idx, start_char, end_char = i, '{', '}'
            break
        elif ch == '[':
            start_idx, start_char, end_char = i, '[', ']'
            break
    if start_idx == -1: return None
    depth, in_string, escape_next = 0, False, False
    for i in range(start_idx, len(text)):
        ch = text[i]
        if escape_next: escape_next = False; continue
        if ch == '\\' and in_string: escape_next = True; continue
        if ch == '"': in_string = not in_string; continue
        if in_string: continue
        if ch == start_char: depth += 1
        elif ch == end_char:
            depth -= 1
            if depth == 0: return text[start_idx:i+1]
    return None

def _validate_single_question(q_raw: dict, idx: int) -> Optional[dict]:
    if not isinstance(q_raw, dict): return None
    if "id" not in q_raw or q_raw["id"] is None: q_raw["id"] = idx
    if "difficulty" not in q_raw or q_raw["difficulty"] is None: q_raw["difficulty"] = 3
    
    choices = q_raw.get("choices", [])
    if isinstance(choices, list) and choices and isinstance(choices[0], dict) and "key" not in choices[0]:
        normalized = []
        for key in ["A", "B", "C", "D"]:
            if key in choices[0]: normalized.append({"key": key, "text": choices[0][key]})
        if normalized: q_raw["choices"] = normalized
        
    try:
        q = Question(**q_raw)
        return q.model_dump()
    except Exception as e:
        logger.warning(f"Pydantic 驗證失敗: {e}")
        return None
