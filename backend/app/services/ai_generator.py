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
            model_name="gemini-flash-latest",
            generation_config=genai.GenerationConfig(
                temperature=0.2,
                max_output_tokens=2048,
                response_mime_type="application/json",
            ),
        )
    return _model

def _call_gemini_sync(system_prompt: str, user_prompt: str) -> str:
    """補回同步呼叫函式，供其他模組調用"""
    model = _get_model()
    full_prompt = f"{system_prompt}\n\n{user_prompt}"
    response = model.generate_content(full_prompt)
    return response.text

async def generate_questions(
    system_prompt: str,
    user_prompt: str,
    target_count: int,
    unit_codes: List[str],
    max_retries: int = 0,
) -> dict:
    loop = asyncio.get_event_loop()
    try:
        raw_output_task = loop.run_in_executor(
            None,
            lambda: _call_gemini_sync(system_prompt, user_prompt)
        )
        raw_output = await asyncio.wait_for(raw_output_task, timeout=8.0)
        data = extract_and_validate_json(raw_output)
        if isinstance(data, list):
            return {"questions": data}
        return data or {"questions": []}
    except Exception as e:
        logger.error(f"生成失敗: {e}")
        raise
