import google.generativeai as genai
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
            model_name="gemini-1.5-flash",
            generation_config=genai.GenerationConfig(
                temperature=0.2,
                max_output_tokens=2048,
                response_mime_type="application/json",
            ),
        )
    return _model

def _call_gemini_sync(system_prompt: str, user_prompt: str) -> str:
    """同步呼叫函式，供科目風格分析等後台任務使用"""
    model = _get_model()
    response = model.generate_content(f"{system_prompt}\n\n{user_prompt}")
    return response.text

async def generate_questions(
    system_prompt: str,
    user_prompt: str,
    target_count: int,
    unit_codes: List[str],
    max_retries: int = 0,
) -> dict:
    """使用原生非同步呼叫 Gemini"""
    model = _get_model()
    try:
        response = await model.generate_content_async(
            f"{system_prompt}\n\n{user_prompt}"
        )
        raw_output = response.text
        data = extract_and_validate_json(raw_output)
        if isinstance(data, list):
            return {"questions": data}
        return data or {"questions": []}
    except Exception as e:
        logger.error(f"❌ Gemini 生成失敗: {e}")
        raise
