import google.generativeai as genai
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
    """使用多重保底嘗試法呼叫 Gemini"""
    global _best_working_model
    settings = get_settings()
    genai.configure(api_key=settings.gemini_api_key)
    
    # 候選名單：按優先順序排列
    candidate_models = [
        "gemini-1.5-flash",
        "gemini-1.5-flash-latest",
        "models/gemini-1.5-flash",
        "models/gemini-1.5-flash-latest",
        "gemini-pro",
        "models/gemini-pro"
    ]
    
    # 如果已經知道哪個能用，就先插隊到第一名
    if _best_working_model:
        candidate_models.insert(0, _best_working_model)

    last_error = None
    for model_name in candidate_models:
        try:
            logger.info(f"🧪 嘗試使用模型: {model_name}...")
            model = genai.GenerativeModel(
                model_name=model_name,
                generation_config=genai.GenerationConfig(
                    temperature=0.2,
                    max_output_tokens=2048,
                    response_mime_type="application/json",
                ),
            )
            
            # 呼叫 API
            response = await model.generate_content_async(
                f"{system_prompt}\n\n{user_prompt}"
            )
            
            raw_output = response.text
            data = extract_and_validate_json(raw_output)
            
            # 成功了！記住這個模型
            _best_working_model = model_name
            logger.info(f"✅ 模型 {model_name} 呼叫成功！")
            
            if isinstance(data, list):
                return {"questions": data}
            return data or {"questions": []}
            
        except Exception as e:
            last_error = e
            logger.warning(f"❌ 模型 {model_name} 失敗: {str(e)[:100]}")
            continue # 試下一個
            
    # 如果全部都失敗
    logger.error(f"🔥 所有模型嘗試均告失敗。最後一個錯誤: {last_error}")
    raise last_error

def _call_gemini_sync(system_prompt: str, user_prompt: str) -> str:
    """同步呼叫保底"""
    settings = get_settings()
    genai.configure(api_key=settings.gemini_api_key)
    # 同步版本直接用最常用的名稱
    model = genai.GenerativeModel("gemini-1.5-flash-latest")
    response = model.generate_content(f"{system_prompt}\n\n{user_prompt}")
    return response.text
