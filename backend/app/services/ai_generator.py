import google.generativeai as genai
from tenacity import (
    retry, stop_after_attempt, wait_exponential,
    retry_if_exception_type, before_sleep_log
)
import logging
import asyncio
from typing import List, Optional

from app.config import get_settings
from app.utils.json_validator import extract_and_validate_json

logger = logging.getLogger(__name__)

_model = None

def _get_model():
    global _model
    if _model is None:
        settings = get_settings()
        genai.configure(api_key=settings.gemini_api_key)
        _model = genai.GenerativeModel(
            model_name="gemini-flash-latest",
            generation_config=genai.GenerationConfig(
                temperature=0.7,
                top_p=0.9,
                max_output_tokens=8192,
                response_mime_type="application/json",
            ),
        )
    return _model

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=2, min=3, max=15),
    retry=retry_if_exception_type(Exception),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True,
)
def _call_gemini_sync(system_prompt: str, user_prompt: str) -> str:
    model = _get_model()
    full_prompt = f"{system_prompt}\n\n{user_prompt}"
    response = model.generate_content(full_prompt)
    return response.text

async def generate_questions(
    system_prompt: str,
    user_prompt: str,
    target_count: int,
    unit_codes: List[str],
    max_retries: int = 1,
) -> dict:
    """穩定版：回傳包含 questions 清單的字典"""
    loop = asyncio.get_event_loop()
    
    try:
        raw_output = await loop.run_in_executor(
            None,
            lambda sp=system_prompt, up=user_prompt: _call_gemini_sync(sp, up)
        )
        
        data = extract_and_validate_json(raw_output)
        
        # 兼容性處理：確保回傳的是 dict { "questions": [...] }
        if isinstance(data, list):
            return {"questions": data}
        if isinstance(data, dict):
            if "questions" not in data and any(isinstance(v, list) for v in data.values()):
                # 嘗試自動修正
                for v in data.values():
                    if isinstance(v, list):
                        data["questions"] = v
                        break
            return data
            
        raise ValueError("AI 回傳了無效的資料格式")

    except Exception as e:
        logger.error(f"生成失敗: {e}")
        raise
