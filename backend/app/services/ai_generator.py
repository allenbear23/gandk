import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
import logging
import asyncio
from typing import List, Optional

from app.config import get_settings
from app.utils.json_validator import extract_and_validate_json

logger = logging.getLogger(__name__)

_best_working_model = None

async def generate_questions(
    system_prompt: str,
    user_prompt: str,
    target_count: int,
    unit_codes: List[str],
    max_retries: int = 0,
) -> dict:
    global _best_working_model
    settings = get_settings()
    genai.configure(api_key=settings.gemini_api_key)
    
    candidate_models = [
        "gemini-1.5-flash",
        "gemini-1.5-flash-latest",
        "models/gemini-1.5-flash",
        "gemini-pro"
    ]
    
    if _best_working_model:
        candidate_models.insert(0, _best_working_model)

    # 關閉所有安全過濾，避免題目內容被誤攔截
    safety_settings = {
        HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
    }

    last_error = None
    for model_name in candidate_models:
        try:
            model = genai.GenerativeModel(
                model_name=model_name,
                generation_config=genai.GenerationConfig(
                    temperature=0.2,
                    max_output_tokens=2048,
                    response_mime_type="application/json",
                ),
                safety_settings=safety_settings # 加入安全設定
            )
            
            response = await model.generate_content_async(
                f"{system_prompt}\n\n{user_prompt}"
            )
            
            # 檢查是否有內容
            if not response.parts:
                logger.warning(f"⚠️ 模型 {model_name} 未回傳有效內容 (可能被攔截)")
                continue

            raw_output = response.text
            data = extract_and_validate_json(raw_output)
            
            _best_working_model = model_name
            
            if isinstance(data, list):
                return {"questions": data}
            return data or {"questions": []}
            
        except Exception as e:
            last_error = e
            logger.warning(f"❌ 模型 {model_name} 失敗: {str(e)[:50]}")
            continue
            
    raise last_error

def _call_gemini_sync(system_prompt: str, user_prompt: str) -> str:
    settings = get_settings()
    genai.configure(api_key=settings.gemini_api_key)
    model = genai.GenerativeModel("gemini-1.5-flash-latest")
    response = model.generate_content(f"{system_prompt}\n\n{user_prompt}")
    return response.text
