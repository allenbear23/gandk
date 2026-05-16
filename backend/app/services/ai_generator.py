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
        logger.info("✅ Gemini 1.5 Flash 初始化完成")
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
    # 使用更簡潔的單次 Prompt 模式，確保在 Vercel 上的穩定性
    full_prompt = f"{system_prompt}\n\n請根據以下要求執行任務：\n{user_prompt}"
    response = model.generate_content(full_prompt)
    return response.text

async def generate_questions(
    system_prompt: str,
    user_prompt: str,
    target_count: int,
    unit_codes: List[str],
    max_retries: int = 1,
) -> dict:
    loop = asyncio.get_event_loop()
    all_questions = []
    exam_metadata = {}
    attempt = 0

    # 確保即使 target_count 是 0 (自動偵測模式)，也會至少執行一次分析
    while (len(all_questions) < target_count or attempt == 0) and attempt <= max_retries:
        # 如果是自動偵測模式 (0)，我們期望 AI 第一次就產出題目，所以設定一個較大的剩餘量
        remaining = target_count - len(all_questions) if target_count > 0 else 15
        current_user_prompt = user_prompt
        if attempt > 0:
            current_user_prompt += f"\n\n【補充】請再生成 {remaining} 題，維持同樣風格。"

        try:
            raw_output = await loop.run_in_executor(
                None,
                lambda sp=system_prompt, up=current_user_prompt: _call_gemini_sync(sp, up)
            )
            
            res_json = extract_and_validate_json(raw_output)
            
            # 提取 Metadata (僅在第一次成功時)
            if not exam_metadata and isinstance(res_json, dict):
                exam_metadata = res_json.get("exam_metadata", {})

            # 提取題目
            questions = []
            if isinstance(res_json, list):
                questions = res_json
            elif isinstance(res_json, dict):
                questions = res_json.get("questions", [])

            if questions:
                all_questions.extend(questions)
                logger.info(f"✅ 第 {attempt} 次生成 {len(questions)} 題")

        except Exception as e:
            logger.error(f"❌ 生成失敗: {e}")
            if attempt >= max_retries: raise

        attempt += 1

    return {
        "metadata": exam_metadata,
        "questions": all_questions[:target_count]
    }
