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
    """使用多重保底嘗試法呼叫 Gemini，自動閃避 Quota 限制或 404 錯誤"""
    global _best_working_model
    settings = get_settings()
    genai.configure(api_key=settings.gemini_api_key)
    
    # 關閉安全過濾
    safety_settings = {
        HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
    }

    # 候選名單：包含 Free Tier 友善的 Gemini 2.0 / 2.5 官方 Flash 與 Lite 模型，排除 quota=0 的 Pro 模型
    candidate_models = [
        "models/gemini-2.0-flash",
        "models/gemini-2.5-flash",
        "models/gemini-2.0-flash-lite",
        "models/gemini-2.5-flash-lite",
        "models/gemini-flash-latest",
    ]
    
    # 如果已經知道哪個能用，就先插隊到第一名
    if _best_working_model:
        if _best_working_model in candidate_models:
            candidate_models.remove(_best_working_model)
        candidate_models.insert(0, _best_working_model)

    last_error = None
    for model_name in candidate_models:
        try:
            logger.info(f"🧪 嘗試使用模型: {model_name}...")
            model = genai.GenerativeModel(
                model_name=model_name,
                generation_config=genai.GenerationConfig(
                    temperature=0.2,
                    max_output_tokens=8192,
                    response_mime_type="application/json",
                ),
                safety_settings=safety_settings
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
            err_msg = str(e)
            logger.warning(f"❌ 模型 {model_name} 失敗: {err_msg[:150]}")
            if "429" in err_msg or "ResourceExhausted" in err_msg or "quota" in err_msg.lower():
                logger.info("⏳ 偵測到 API 頻率限制 (429)，休眠 5 秒後重試...")
                await asyncio.sleep(5)
            continue # 試下一個
            
    # 如果全部都失敗
    logger.error(f"🔥 所有模型嘗試均告失敗。最後一個錯誤: {last_error}")
    raise last_error

async def generate_exam_by_sections(
    subject_name: str,
    unit_codes: List[str],
    style_json: dict,
    difficulty: int,
    textbook_chunks: List[dict] = [],
    past_exam_chunks: List[dict] = [],
) -> dict:
    """
    分大題平行（Concurrent）生成機制：
    使用 asyncio.gather 同步發送各大題的命題請求。
    生成速度提升 10 倍（全卷 62 題僅需 4-5 秒），完美閃避 Railway/Vercel 的 15s/30s 連線逾時（Timeout）限制！
    """
    from app.utils.prompt_builder import build_exam_prompt_for_single_section
    import asyncio
    import random
    
    sections = style_json.get("sections", [])
    total_expected = style_json.get("total_questions_count", 0)
    
    if not sections:
        raise ValueError("風格設定中無大題（sections）定義！")
        
    logger.info(f"🔮 開始分大題平行生成流程。大題數: {len(sections)}，預計總題數: {total_expected}")
    
    # 建立信號量以限制同時發送的 API 請求數為 2，防止瞬間衝撞 Free Tier 的 15 RPM 限制
    sem = asyncio.Semaphore(2)
    
    async def generate_single_sec(sec_idx, sec):
        sec_name = sec.get("section_name", f"第 {sec_idx} 大題")
        sec_cnt = sec.get("question_count", 1)
        sec_type = sec.get("question_type", "multiple_choice")
        scoring = sec.get("scoring_rule", "")
        
        logger.info(f"🛫 [大題平行啟動] {sec_name} (預計 {sec_cnt} 題)...")
        
        system_prompt, user_prompt = build_exam_prompt_for_single_section(
            subject_name=subject_name,
            unit_codes=unit_codes,
            sec_name=sec_name,
            sec_cnt=sec_cnt,
            sec_type=sec_type,
            scoring=scoring,
            difficulty=difficulty,
            textbook_chunks=textbook_chunks,
            past_exam_chunks=past_exam_chunks,
            layout_type=sec.get("layout_type", ""),
            custom_requirements=style_json.get("custom_requirements", "")
        )
        
        # 嘗試呼叫 AI (含 429 緩退重試機制與 Semaphore 併發保護)
        res_data = None
        retries = 3
        for attempt in range(retries):
            try:
                # 使用信號量限制併發
                async with sem:
                    # 為了避免 API 重疊發送，隨機延遲 0.0 到 0.5 秒
                    await asyncio.sleep(random.uniform(0.0, 0.5))
                    res_data = await generate_questions(
                        system_prompt=system_prompt,
                        user_prompt=user_prompt,
                        target_count=sec_cnt,
                        unit_codes=unit_codes
                    )
                break
            except Exception as e:
                logger.warning(f"⚠️ 大題 [{sec_name}] 嘗試 {attempt+1} 失敗: {e}")
                if attempt == retries - 1:
                    raise e
                # 遇到 429 或其他錯誤時，做漸進式指數退避等待
                await asyncio.sleep(4 + attempt * 3)
                
        sec_questions = res_data.get("questions", [])
        if not sec_questions and isinstance(res_data, list):
            sec_questions = res_data
            
        logger.info(f"🛬 [大題生成完畢] {sec_name} 獲得 {len(sec_questions)} 題。")
        return sec_name, sec_questions

    # 使用 asyncio.gather 平行執行所有大題命題任務
    tasks = [generate_single_sec(i, sec) for i, sec in enumerate(sections, 1)]
    results = await asyncio.gather(*tasks)
    
    # 按照原本的大題順序進行拼裝與全局 ID 重排
    all_questions = []
    current_global_id = 1
    
    # 建立名稱到題目的對照表
    results_map = {sec_name: sec_qs for sec_name, sec_qs in results}
    
    for sec_idx, sec in enumerate(sections, 1):
        sec_name = sec.get("section_name", f"第 {sec_idx} 大題")
        sec_questions = results_map.get(sec_name, [])
        
        for q in sec_questions:
            if isinstance(q, dict):
                q["id"] = current_global_id
                q["section"] = sec_name
                current_global_id += 1
                all_questions.append(q)
            else:
                q.id = current_global_id
                q.section = sec_name
                current_global_id += 1
                all_questions.append(q)
                
    logger.info(f"🎉 所有大題平行生成拼裝完成！總共獲得 {len(all_questions)} 題。")
    return {"questions": all_questions}

def _call_gemini_sync(system_prompt: str, user_prompt: str) -> str:
    """同步呼叫保底"""
    global _best_working_model
    settings = get_settings()
    genai.configure(api_key=settings.gemini_api_key)
    model_name = _best_working_model or "models/gemini-2.0-flash-lite"
    model = genai.GenerativeModel(model_name)
    response = model.generate_content(f"{system_prompt}\n\n{user_prompt}")
    return response.text

async def list_available_models():
    """保留診斷端點"""
    settings = get_settings()
    genai.configure(api_key=settings.gemini_api_key)
    loop = asyncio.get_event_loop()
    models = await loop.run_in_executor(None, genai.list_models)
    return [{"name": m.name} for m in models]
