import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
import logging
import asyncio
from typing import List, Optional

from app.config import get_settings
from app.utils.json_validator import extract_and_validate_json

logger = logging.getLogger(__name__)

MODEL_OUTPUT_TOKEN_LIMITS = {
    "models/gemini-2.5-flash": 32768,
    "models/gemini-2.5-flash-lite": 32768,
    "models/gemini-flash-latest": 16384,
    "models/gemini-2.0-flash": 8192,
    "models/gemini-2.0-flash-lite": 8192,
}


class TokenBudgetError(RuntimeError):
    """Raised when the model output is truncated or too small for the request."""


def _estimate_output_tokens(target_count: int) -> int:
    # Exam questions are verbose JSON. Reserve enough room for long stems,
    # choices, answers, explanations, and section metadata.
    return min(32768, max(4096, target_count * 650 + 1200))


def _is_token_budget_error(err_msg: str) -> bool:
    err_lower = err_msg.lower()
    token_terms = [
        "max_tokens",
        "max output tokens",
        "maximum output",
        "finish_reason: max_tokens",
        "token",
        "截斷",
        "truncated",
    ]
    return any(term in err_lower for term in token_terms)


def _response_was_truncated(response) -> bool:
    try:
        candidates = getattr(response, "candidates", None) or []
        if not candidates:
            return False
        finish_reason = getattr(candidates[0], "finish_reason", "")
        return "MAX_TOKENS" in str(finish_reason).upper()
    except Exception:
        return False


class APIKeyRotator:
    def __init__(self):
        self.keys = []
        self._index = 0
        self.cooldowns = {} # key -> float (cooldown end timestamp)
        self.reload_keys()

    def reload_keys(self):
        try:
            from app.config import get_settings
            # 清除 Pydantic Settings cache，強制載入最新修改之環境變數（支援多 API Key）
            get_settings.cache_clear()
            settings = get_settings()
            raw_key = settings.gemini_api_key or ""
            # 以逗號切割多支金鑰，並去除空白字元
            new_keys = [k.strip() for k in raw_key.split(",") if k.strip()]
            
            # 只有當金鑰清單發生改變時，才更新並重置，避免平行呼叫重置索引與冷卻狀態！
            if new_keys != self.keys:
                self.keys = new_keys
                self.cooldowns = {k: 0.0 for k in self.keys}
                self._index = 0
                logger.info(f"🔑 APIKeyRotator 載入新金鑰清單，共 {len(self.keys)} 支金鑰")
        except Exception as e:
            logger.error(f"⚠️ 無法初始化 APIKeyRotator: {e}")

    def mark_cooldown(self, key: str, duration: float = 50.0):
        """將特定金鑰標記為冷卻狀態，避開調用"""
        if key in self.keys:
            import time
            self.cooldowns[key] = time.time() + duration
            logger.warning(f"❄️ 金鑰 [{key[:8]}...] 調用達上限，標記冷卻 {duration:.1f} 秒")

    def get_current_key(self) -> str:
        if not self.keys:
            return ""
        
        import time
        now = time.time()
        # 尋找一個沒有在冷卻中的金鑰，最多嘗試金鑰個數次
        for _ in range(len(self.keys)):
            key = self.keys[self._index % len(self.keys)]
            cooldown_until = self.cooldowns.get(key, 0.0)
            if now >= cooldown_until:
                return key
            # 若在冷卻中，則自動輪轉到下一個
            self._index += 1
            
        # 若全部都在冷卻中，則退回使用原本當前索引的金鑰 (保底)
        return self.keys[self._index % len(self.keys)]

    async def get_available_key_with_backoff(self) -> str:
        """非同步獲取可用金鑰。若全部金鑰都在冷卻中，會自動暫停等待最短的解凍時間，保證不崩潰"""
        if not self.keys:
            return ""
        
        import time
        import asyncio
        
        while True:
            now = time.time()
            shortest_wait = None
            
            # 尋找立即可用的金鑰
            for _ in range(len(self.keys)):
                key = self.keys[self._index % len(self.keys)]
                cooldown_until = self.cooldowns.get(key, 0.0)
                wait_time = cooldown_until - now
                
                if wait_time <= 0:
                    # 找到立即可用的金鑰！
                    return key
                
                # 記錄最短等待時間
                if shortest_wait is None or wait_time < shortest_wait:
                    shortest_wait = wait_time
                
                self._index += 1
                
            # 若所有金鑰都在冷卻中
            if shortest_wait is not None and shortest_wait > 0:
                # 若等待時間過長（大於 8 秒），不要在 Web 請求中死等，直接拋出異常讓使用者更換金鑰！
                if shortest_wait > 8.0:
                    logger.error(f"🔥 所有 API 金鑰均在長冷卻中 (最短需等 {shortest_wait:.1f} 秒)。拒絕死等，直接熔斷！")
                    raise RuntimeError(f"所有 API 金鑰均已耗盡或處於限制中，最短需要等待 {shortest_wait:.1f} 秒。請更換金鑰或稍後再試！")
                
                logger.info(f"⏳ 所有 API 金鑰均在冷卻限制中。將暫停等待最短金鑰解凍 {shortest_wait:.1f} 秒，防止崩潰...")
                await asyncio.sleep(shortest_wait + 0.5)
                continue
                
            # 保底回傳
            return self.keys[self._index % len(self.keys)]

    def rotate(self) -> str:
        if not self.keys:
            return ""
        self._index += 1
        next_key = self.get_current_key()
        logger.info(f"🔄 API Key 已輪轉，目前使用第 {self._index % len(self.keys) + 1} 支金鑰")
        return next_key

key_rotator = APIKeyRotator()

_best_working_model = None

async def generate_questions(
    system_prompt: str,
    user_prompt: str,
    target_count: int,
    unit_codes: List[str],
    max_retries: int = 0,
    max_output_tokens: Optional[int] = None,
) -> dict:
    """使用多重保底嘗試法呼叫 Gemini，支援多金鑰自動輪轉與多模型容錯機制"""
    global _best_working_model
    
    # 關閉安全過濾
    safety_settings = {
        HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
    }

    # 候選名單：包含 Free Tier 友善的 Gemini 2.0 / 2.5 官方 Flash 與 Lite 模型，排除 quota=0 的 Pro 模型
    candidate_models = [
        "models/gemini-2.5-flash",
        "models/gemini-2.5-flash-lite",
        "models/gemini-flash-latest",
        "models/gemini-2.0-flash",
        "models/gemini-2.0-flash-lite",
    ]
    
    # 如果已經知道哪個能用，就先插隊到第一名
    if _best_working_model:
        if _best_working_model in candidate_models:
            candidate_models.remove(_best_working_model)
        candidate_models.insert(0, _best_working_model)

    last_error = None
    # 每次命題前重新加載最新的 API Key 設置（實現免重啟動態載入）
    key_rotator.reload_keys()
    num_keys = len(key_rotator.keys) or 1
    requested_output_tokens = max_output_tokens or _estimate_output_tokens(target_count)

    for model_name in candidate_models:
        model_output_tokens = min(
            requested_output_tokens,
            MODEL_OUTPUT_TOKEN_LIMITS.get(model_name, 8192),
        )
        # 對於每一個模型，我們會對所有已配置的 API 金鑰進行輪轉嘗試
        for key_attempt in range(num_keys):
            active_key = await key_rotator.get_available_key_with_backoff()
            try:
                current_key_num = (key_rotator._index % num_keys) + 1
                logger.info(f"🧪 嘗試模型: {model_name} (使用第 {current_key_num}/{num_keys} 支金鑰)...")
                
                # 配置當前金鑰並建立模型實例
                genai.configure(api_key=active_key)
                model = genai.GenerativeModel(
                    model_name=model_name,
                    generation_config=genai.GenerationConfig(
                        temperature=0.2,
                        max_output_tokens=model_output_tokens,
                        response_mime_type="application/json",
                    ),
                    safety_settings=safety_settings
                )
                
                # 呼叫 API
                response = await model.generate_content_async(
                    f"{system_prompt}\n\n{user_prompt}",
                    request_options={"timeout": 15.0}
                )
                
                if _response_was_truncated(response):
                    raise TokenBudgetError(
                        f"模型輸出因 token 上限被截斷（{model_name}, max_output_tokens={model_output_tokens}）"
                    )

                raw_output = response.text
                data = extract_and_validate_json(raw_output)
                if data is None:
                    raise TokenBudgetError("模型輸出不是完整 JSON，可能因 token 不足被截斷")
                
                # 成功了！記住這個模型
                _best_working_model = model_name
                logger.info(f"✅ 模型 {model_name} (金鑰 {current_key_num}) 呼叫成功！")
                
                if isinstance(data, list):
                    return {"questions": data}
                return data or {"questions": []}
                
            except Exception as e:
                last_error = e
                err_msg = str(e)
                logger.warning(f"❌ 模型 {model_name} 失敗 (金鑰 {key_rotator._index % num_keys + 1} 嘗試 {key_attempt+1}/{num_keys}): {err_msg[:150]}")
                
                if "429" in err_msg or "ResourceExhausted" in err_msg or "quota" in err_msg.lower():
                    # 嘗試從 Google 錯誤訊息中解析具體的冷卻秒數（例如: "Please retry in 46.610192564s."）
                    cooldown_sec = 5.0  # 預設大幅縮短為 5.0 秒，避免被長時間冰凍！
                    
                    is_daily_quota = False
                    if "daily" in err_msg.lower() or "limit exceeded" in err_msg.lower() or "free tier" in err_msg.lower():
                        is_daily_quota = True
                        cooldown_sec = 1800.0 # 每日限額或免費額度限制，冷凍該金鑰 30 分鐘
                        
                    try:
                        if "retry in" in err_msg:
                            parts = err_msg.split("retry in")
                            sec_str = parts[1].strip().split("s")[0].strip()
                            cooldown_sec = float(sec_str) + 1.0 # 加上 1 秒保險緩衝
                    except Exception:
                        pass
                    
                    key_rotator.mark_cooldown(active_key, duration=cooldown_sec)
                    logger.info(f"⏳ 偵測到金鑰頻率限制，該金鑰將被冷凍避開 {cooldown_sec:.1f} 秒...")
                    
                    # 每日配額或免費層限制耗盡，直接拋出異常，不需輪轉其他模型（它們共用同金鑰也會失敗）
                    if is_daily_quota:
                        raise e
                        
                    await asyncio.sleep(2)

                if num_keys > 1:
                    key_rotator.rotate()

                if _is_token_budget_error(err_msg):
                    break
                
                # 如果已經嘗試完所有金鑰，就跳出輪轉，嘗試下一個模型
                if key_attempt == num_keys - 1:
                    break
            
    # 如果全部都失敗
    logger.error(f"🔥 所有模型嘗試均告失敗。最後一個錯誤: {last_error}")
    raise last_error


async def generate_exam_in_single_call(
    subject_name: str,
    unit_codes: List[str],
    style_json: dict,
    difficulty: int,
    textbook_chunks: List[dict] = [],
    past_exam_chunks: List[dict] = [],
) -> dict:
    """
    極致省電模式 (單次 API 呼叫生成整張考卷所有大題)
    只會向 Google API 發送一次請求，產出整張考卷的所有大題與題目！
    """
    from app.utils.prompt_builder import build_mega_exam_prompt
    import copy
    
    # 建立一個深拷貝，避免修改到原始風格 JSON
    style_json_scaled = copy.deepcopy(style_json)
    sections = style_json_scaled.get("sections", [])
    
    total_expected = sum(sec.get("question_count", 1) for sec in sections)
    
    # 單次呼叫只適合中小型考卷。題量過大時改走分大題/分批生成，
    # 保留使用者要求的題數，不再偷偷等比例縮減。
    max_single_call_questions = 18
    if total_expected > max_single_call_questions:
        logger.info(
            f"⚠️ [Token 防護] 預計總題數 {total_expected} 超過單次呼叫安全上限 "
            f"{max_single_call_questions}，自動改用分大題/分批生成以避免輸出截斷。"
        )
        return await generate_exam_by_sections(
            subject_name=subject_name,
            unit_codes=unit_codes,
            style_json=style_json,
            difficulty=difficulty,
            textbook_chunks=textbook_chunks,
            past_exam_chunks=past_exam_chunks,
        )
        
    system_prompt, user_prompt = build_mega_exam_prompt(
        subject_name=subject_name,
        unit_codes=unit_codes,
        style_json=style_json_scaled,
        difficulty=difficulty,
        textbook_chunks=textbook_chunks,
        past_exam_chunks=past_exam_chunks
    )
    
    logger.info(f"⚡ [極致省電模式] 開始單次 API 命題，預計生成 {total_expected} 題...")
    
    try:
        res_data = await generate_questions(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            target_count=total_expected,
            unit_codes=unit_codes
        )
    except TokenBudgetError:
        logger.info("⚠️ 單次呼叫遭遇 token 截斷，改用分大題/分批生成重試。")
        return await generate_exam_by_sections(
            subject_name=subject_name,
            unit_codes=unit_codes,
            style_json=style_json,
            difficulty=difficulty,
            textbook_chunks=textbook_chunks,
            past_exam_chunks=past_exam_chunks,
        )
    
    # 全局 ID 重排，確保 id 遞增
    all_questions = res_data.get("questions", [])
    if not all_questions and isinstance(res_data, list):
        all_questions = res_data
        
    current_global_id = 1
    processed_questions = []
    
    for q in all_questions:
        if isinstance(q, dict):
            q["id"] = current_global_id
            current_global_id += 1
            processed_questions.append(q)
        else:
            q.id = current_global_id
            current_global_id += 1
            processed_questions.append(q)
            
    logger.info(f"🎉 單次生成完成！總共獲得 {len(processed_questions)} 題。")
    return {"questions": processed_questions}


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
    
    # 動態調整併發限制：若只有 1 支金鑰，限制併發為 1（順序生成），避免觸發 Google 的併發/次數限制。
    # 若有多支金鑰，則允許較高的併發度（金鑰個數，最多 3），以金鑰分流達到極速生成。
    num_keys = len(key_rotator.keys) or 1
    max_concurrency = 1 if num_keys == 1 else min(num_keys, 3)
    sem = asyncio.Semaphore(max_concurrency)
    logger.info(f"📊 根據金鑰數量 ({num_keys} 支)，動態配置併發限制 Semaphore({max_concurrency})")

    def should_split_section(sec: dict) -> bool:
        sec_name = sec.get("section_name", "")
        layout_type = (sec.get("layout_type", "") or "").lower()
        joined = f"{layout_type} {sec_name}"
        contiguous_layout_terms = ["cloze", "word_bank", "克漏", "文意選填", "選填"]
        return not any(term in joined for term in contiguous_layout_terms)

    def split_count(total: int, batch_size: int = 8) -> list[int]:
        batches = []
        remaining = total
        while remaining > 0:
            current = min(batch_size, remaining)
            batches.append(current)
            remaining -= current
        return batches
    
    async def generate_single_sec(sec_idx, sec):
        sec_name = sec.get("section_name", f"第 {sec_idx} 大題")
        sec_cnt = sec.get("question_count", 1)
        sec_type = sec.get("question_type", "multiple_choice")
        scoring = sec.get("scoring_rule", "")
        
        logger.info(f"🛫 [大題平行啟動] {sec_name} (預計 {sec_cnt} 題)...")

        batch_counts = [sec_cnt]
        if sec_cnt > 8 and should_split_section(sec):
            batch_counts = split_count(sec_cnt)
            logger.info(f"✂️ [Token 防護] {sec_name} 題數較多，拆成 {len(batch_counts)} 批生成：{batch_counts}")

        sec_questions = []

        for batch_idx, batch_cnt in enumerate(batch_counts, 1):
            batch_suffix = "" if len(batch_counts) == 1 else f"（第 {batch_idx}/{len(batch_counts)} 批）"
            system_prompt, user_prompt = build_exam_prompt_for_single_section(
                subject_name=subject_name,
                unit_codes=unit_codes,
                sec_name=sec_name,
                sec_cnt=batch_cnt,
                sec_type=sec_type,
                scoring=scoring,
                difficulty=difficulty,
                textbook_chunks=textbook_chunks,
                past_exam_chunks=past_exam_chunks,
                layout_type=sec.get("layout_type", ""),
                custom_requirements=(
                    f"{style_json.get('custom_requirements', '')}\n"
                    f"本次只生成「{sec_name}」的 {batch_cnt} 題，且不可與同大題其他批次重複。"
                ).strip()
            )

            # 嘗試呼叫 AI (含 429 緩退重試機制與 Semaphore 併發保護)
            res_data = None
            retries = 2 # 縮減為最多重試 2 次即可，內部已有多模型防護
            for attempt in range(retries):
                try:
                    # 使用信號量限制併發
                    async with sem:
                        # 避免 API 重疊發送（若併發為 1 則小延遲，多併發隨機延遲）
                        delay = 0.1 if max_concurrency == 1 else random.uniform(0.2, 0.8)
                        await asyncio.sleep(delay)
                        res_data = await generate_questions(
                            system_prompt=system_prompt,
                            user_prompt=user_prompt,
                            target_count=batch_cnt,
                            unit_codes=unit_codes
                        )
                    break
                except TokenBudgetError as e:
                    logger.warning(f"⚠️ 大題 [{sec_name}{batch_suffix}] token 不足: {e}")
                    if batch_cnt <= 4:
                        raise e
                    smaller_counts = split_count(batch_cnt, batch_size=max(2, batch_cnt // 2))
                    logger.info(f"✂️ [Token 防護] {sec_name}{batch_suffix} 再拆小批次：{smaller_counts}")
                    nested_results = []
                    for nested_cnt in smaller_counts:
                        nested_sec = dict(sec)
                        nested_sec["question_count"] = nested_cnt
                        _, nested_questions = await generate_single_sec(sec_idx, nested_sec)
                        nested_results.extend(nested_questions)
                    sec_questions.extend(nested_results)
                    res_data = {"questions": []}
                    break
                except Exception as e:
                    logger.warning(f"⚠️ 大題 [{sec_name}{batch_suffix}] 嘗試 {attempt+1} 失敗: {e}")
                    err_lower = str(e).lower()
                    is_fatal_quota = "quota" in err_lower or "limit" in err_lower or "exhausted" in err_lower
                    
                    if attempt == retries - 1 or is_fatal_quota:
                        raise e
                    # 遇到 429 或其他錯誤時，做漸進式指數退避等待
                    await asyncio.sleep(3 + attempt * 2)

            batch_questions = res_data.get("questions", []) if res_data else []
            if not batch_questions and isinstance(res_data, list):
                batch_questions = res_data
            sec_questions.extend(batch_questions)
            
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
    """同步呼叫保底，支援多金鑰自動輪轉與退避重試"""
    global _best_working_model
    key_rotator.reload_keys()
    num_keys = len(key_rotator.keys) or 1
    
    import time
    
    candidate_models = [
        _best_working_model or "models/gemini-2.0-flash-lite",
        "models/gemini-2.0-flash",
        "models/gemini-2.5-flash-lite",
        "models/gemini-2.5-flash",
    ]
    
    last_err = None
    for model_name in candidate_models:
        for attempt in range(num_keys):
            active_key = key_rotator.get_current_key()
            try:
                logger.info(f"🧪 同步分析風格：嘗試 {model_name} (使用金鑰 {key_rotator._index % num_keys + 1}/{num_keys})...")
                genai.configure(api_key=active_key)
                model = genai.GenerativeModel(model_name)
                response = model.generate_content(
                    f"{system_prompt}\n\n{user_prompt}",
                    request_options={"timeout": 15.0}
                )
                
                # 成功了！
                _best_working_model = model_name
                return response.text
            except Exception as e:
                last_err = e
                err_msg = str(e)
                logger.warning(f"❌ 同步分析失敗 (模型 {model_name}, 金鑰嘗試 {attempt+1}/{num_keys}): {err_msg[:150]}")
                
                if "429" in err_msg or "ResourceExhausted" in err_msg or "quota" in err_msg.lower():
                    cooldown_sec = 5.0  # 預設大幅縮短為 5.0 秒，避免被長時間冰凍！
                    try:
                        if "retry in" in err_msg:
                            parts = err_msg.split("retry in")
                            sec_str = parts[1].strip().split("s")[0].strip()
                            cooldown_sec = float(sec_str) + 1.0
                    except Exception:
                        pass
                    key_rotator.mark_cooldown(active_key, duration=cooldown_sec)
                    time.sleep(2)
                
                if num_keys > 1:
                    key_rotator.rotate()
                    
    raise last_err

async def list_available_models():
    """保留診斷端點"""
    key_rotator.reload_keys()
    active_key = key_rotator.get_current_key()
    genai.configure(api_key=active_key)
    loop = asyncio.get_event_loop()
    models = await loop.run_in_executor(None, genai.list_models)
    return [{"name": m.name} for m in models]
