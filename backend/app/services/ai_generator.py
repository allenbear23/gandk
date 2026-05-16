import google.generativeai as genai
import logging
import asyncio
from typing import List, Optional
from app.config import get_settings
from app.utils.json_validator import extract_and_validate_json

logger = logging.getLogger(__name__)

async def list_available_models():
    """診斷用：列出所有可用的模型"""
    settings = get_settings()
    genai.configure(api_key=settings.gemini_api_key)
    try:
        loop = asyncio.get_event_loop()
        models = await loop.run_in_executor(None, genai.list_models)
        return [{"name": m.name, "supported_methods": m.supported_generation_methods} for m in models]
    except Exception as e:
        return {"error": str(e)}

async def generate_questions(
    system_prompt: str,
    user_prompt: str,
    target_count: int,
    unit_codes: List[str],
    max_retries: int = 0,
) -> dict:
    settings = get_settings()
    genai.configure(api_key=settings.gemini_api_key)
    
    # 根據之前的錯誤，我們改用最保險的幾種嘗試
    # 注意：有的環境需要 'models/' 前綴，有的不需要
    candidate_models = [
        "gemini-1.5-flash-latest",
        "gemini-1.5-flash",
        "gemini-pro",
        "models/gemini-1.5-flash-latest",
        "models/gemini-1.5-flash"
    ]

    last_error = None
    for model_name in candidate_models:
        try:
            model = genai.GenerativeModel(model_name=model_name)
            response = await model.generate_content_async(f"{system_prompt}\n\n{user_prompt}")
            raw_output = response.text
            data = extract_and_validate_json(raw_output)
            return {"questions": data} if isinstance(data, list) else (data or {"questions": []})
        except Exception as e:
            last_error = e
            continue
            
    raise last_error

def _call_gemini_sync(system_prompt: str, user_prompt: str) -> str:
    settings = get_settings()
    genai.configure(api_key=settings.gemini_api_key)
    model = genai.GenerativeModel("gemini-1.5-flash-latest")
    return model.generate_content(f"{system_prompt}\n\n{user_prompt}").text
