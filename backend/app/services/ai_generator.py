import google.generativeai as genai
import logging
import asyncio
from typing import List, Optional

from app.config import get_settings
from app.utils.json_validator import extract_and_validate_json

logger = logging.getLogger(__name__)

_model = None
_detected_model_name = None

async def _get_best_model_name():
    """動態從 API 獲取可用的 Flash 模型名稱"""
    global _detected_model_name
    if _detected_model_name:
        return _detected_model_name

    settings = get_settings()
    genai.configure(api_key=settings.gemini_api_key)
    
    try:
        # 在執行緒中執行同步的 list_models
        loop = asyncio.get_event_loop()
        models = await loop.run_in_executor(None, genai.list_models)
        
        # 優先找 1.5 Flash，其次找任何 Flash
        flash_models = [m.name for m in models if "flash" in m.name.lower()]
        
        if flash_models:
            # 優先選擇 1.5 版本
            v15 = [m for m in flash_models if "1.5" in m]
            _detected_model_name = v15[0] if v15 else flash_models[0]
            logger.info(f"✨ 自動偵測到最佳模型: {_detected_model_name}")
            return _detected_model_name
    except Exception as e:
        logger.warning(f"⚠️ 無法透過 API 獲取模型清單: {e}")
    
    # 最終保底
    return "models/gemini-1.5-flash-latest"

async def _get_model():
    global _model
    if _model is None:
        model_name = await _get_best_model_name()
        _model = genai.GenerativeModel(
            model_name=model_name,
            generation_config=genai.GenerationConfig(
                temperature=0.2,
                max_output_tokens=2048,
                response_mime_type="application/json",
            ),
        )
    return _model

async def generate_questions(
    system_prompt: str,
    user_prompt: str,
    target_count: int,
    unit_codes: List[str],
    max_retries: int = 0,
) -> dict:
    model = await _get_model()
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

def _call_gemini_sync(system_prompt: str, user_prompt: str) -> str:
    """同步呼叫 (用於後台任務，由於 get_model 現在是 async，這裡需特殊處理)"""
    # 為了簡化，同步任務直接用保底名稱
    settings = get_settings()
    genai.configure(api_key=settings.gemini_api_key)
    model = genai.GenerativeModel("models/gemini-1.5-flash-latest")
    response = model.generate_content(f"{system_prompt}\n\n{user_prompt}")
    return response.text
