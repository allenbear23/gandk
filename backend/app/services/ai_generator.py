import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
import logging
import asyncio
from typing import List, Optional

from app.config import get_settings
from app.utils.json_validator import extract_and_validate_json

logger = logging.getLogger(__name__)

# 使用最新的 2.5-flash
MODEL_NAME = "models/gemini-2.5-flash"

async def generate_questions(
    system_prompt: str,
    user_prompt: str,
    target_count: int,
    unit_codes: List[str],
    max_retries: int = 0,
) -> dict:
    settings = get_settings()
    genai.configure(api_key=settings.gemini_api_key)
    
    # 關閉安全過濾
    safety_settings = {
        HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
    }

    try:
        model = genai.GenerativeModel(
            model_name=MODEL_NAME,
            generation_config=genai.GenerationConfig(
                temperature=0.2,
                max_output_tokens=2048,
                response_mime_type="application/json",
            ),
            safety_settings=safety_settings
        )
        
        response = await model.generate_content_async(
            f"{system_prompt}\n\n{user_prompt}"
        )
        
        raw_output = response.text
        data = extract_and_validate_json(raw_output)
        
        if isinstance(data, list):
            return {"questions": data}
        return data or {"questions": []}
        
    except Exception as e:
        logger.error(f"❌ 使用 {MODEL_NAME} 生成失敗: {e}")
        raise

def _call_gemini_sync(system_prompt: str, user_prompt: str) -> str:
    settings = get_settings()
    genai.configure(api_key=settings.gemini_api_key)
    model = genai.GenerativeModel(MODEL_NAME)
    response = model.generate_content(f"{system_prompt}\n\n{user_prompt}")
    return response.text

async def list_available_models():
    """保留診斷端點"""
    settings = get_settings()
    genai.configure(api_key=settings.gemini_api_key)
    loop = asyncio.get_event_loop()
    models = await loop.run_in_executor(None, genai.list_models)
    return [{"name": m.name} for m in models]
