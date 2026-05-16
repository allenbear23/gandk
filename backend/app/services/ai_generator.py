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
                temperature=0.2, # 降低溫度提高生成速度
                max_output_tokens=2048, # 限制輸出長度拼速度
                response_mime_type="application/json",
            ),
        )
    return _model

async def generate_questions(
    system_prompt: str,
    user_prompt: str,
    target_count: int,
    unit_codes: List[str],
    max_retries: int = 0, # 測試期間不重試
) -> dict:
    loop = asyncio.get_event_loop()
    
    try:
        # 直接呼叫，不使用 retry 裝飾器，減少開銷
        model = _get_model()
        full_prompt = f"{system_prompt}\n\n{user_prompt}"
        
        raw_output_task = loop.run_in_executor(
            None,
            lambda: model.generate_content(full_prompt).text
        )
        
        # 設定 8 秒超時，如果 8 秒沒生完就主動斷掉，避免 Vercel 10秒崩潰
        raw_output = await asyncio.wait_for(raw_output_task, timeout=8.0)
        
        data = extract_and_validate_json(raw_output)
        if isinstance(data, list):
            return {"questions": data}
        return data or {"questions": []}

    except asyncio.TimeoutError:
        logger.error("⚡ AI 生成超時（8秒限制）")
        raise ValueError("AI 生成太慢，請縮減範圍再試一次")
    except Exception as e:
        logger.error(f"生成失敗: {e}")
        raise
