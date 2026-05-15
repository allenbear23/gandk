"""
services/ai_generator.py — Gemini API 呼叫與 JSON 題目生成

設計重點：
1. 使用 Gemini 1.5 Flash（速度快、長文本支援、JSON 輸出穩定）
2. 設定 generation_config 強制 JSON 輸出（response_mime_type）
3. Tenacity retry 機制處理 API 不穩定
4. 若 AI 輸出不足題數，自動補充（最多 2 次補充）
"""
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
            model_name="gemini-1.5-flash",
            generation_config=genai.GenerationConfig(
                temperature=0.7,          # 適度創意，不過於隨機
                top_p=0.9,
                max_output_tokens=8192,
                response_mime_type="application/json",  # 強制 JSON 輸出！
            ),
        )
        logger.info("✅ Gemini 1.5 Flash 模型初始化完成")
    return _model


# ── Retry 裝飾器 ───────────────────────────────────────────────
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=2, min=3, max=15),
    retry=retry_if_exception_type(Exception),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True,
)
def _call_gemini_sync(system_prompt: str, user_prompt: str) -> str:
    """同步呼叫 Gemini API（在 executor 中執行）"""
    model = _get_model()
    response = model.generate_content(
        [
            {"role": "user", "parts": [system_prompt]},
            {"role": "model", "parts": ["我明白了，我會嚴格按照 JSON 格式輸出題目。"]},
            {"role": "user", "parts": [user_prompt]},
        ]
    )
    return response.text


async def generate_questions(
    system_prompt: str,
    user_prompt: str,
    target_count: int,
    unit_codes: List[str],
    max_retries: int = 2,
) -> List[dict]:
    """
    非同步生成題目，包含自動補充機制。

    若 AI 第一次生成數量不足，自動追加生成並合併。
    """
    loop = asyncio.get_event_loop()
    all_questions = []
    attempt = 0

    while len(all_questions) < target_count and attempt <= max_retries:
        remaining = target_count - len(all_questions)

        if attempt > 0:
            logger.info(f"  🔄 補充生成（第 {attempt} 次），還需 {remaining} 題")
            # 修改 prompt 要求補充
            current_user_prompt = user_prompt + f"\n\n【注意】請補充生成 {remaining} 題，id 從 {len(all_questions)+1} 開始。"
        else:
            current_user_prompt = user_prompt

        try:
            raw_output = await loop.run_in_executor(
                None,
                lambda sp=system_prompt, up=current_user_prompt: _call_gemini_sync(sp, up)
            )
            logger.info(f"  📥 Gemini 回應長度: {len(raw_output)} 字元")

            questions = extract_and_validate_json(raw_output)
            if questions:
                # 重新編號，避免 id 重複
                offset = len(all_questions)
                for q in questions:
                    q["id"] = offset + q["id"]
                all_questions.extend(questions)
                logger.info(f"  ✅ 本次生成 {len(questions)} 題，累計 {len(all_questions)} 題")

        except Exception as e:
            logger.error(f"  ❌ 生成失敗（attempt={attempt}）: {e}")
            if attempt >= max_retries:
                raise

        attempt += 1

    # 若超出目標數量，裁剪到剛好 target_count
    if len(all_questions) > target_count:
        all_questions = all_questions[:target_count]

    if not all_questions:
        raise ValueError("AI 生成失敗：無法獲得任何有效題目")

    logger.info(f"✅ 最終生成 {len(all_questions)} 題")
    return all_questions
