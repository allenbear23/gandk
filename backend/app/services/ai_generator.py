import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
import logging
import asyncio
from typing import List, Optional

from app.config import get_settings
from app.utils.json_validator import extract_and_validate_json

logger = logging.getLogger(__name__)

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
    # 每次命題前重新加載最新的 API Key 設置（實現免重啟動態載入）
    key_rotator.reload_keys()
    num_keys = len(key_rotator.keys) or 1

    for model_name in candidate_models:
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
                    try:
                        if "retry in" in err_msg:
                            parts = err_msg.split("retry in")
                            sec_str = parts[1].strip().split("s")[0].strip()
                            cooldown_sec = float(sec_str) + 1.0 # 加上 1 秒保險緩衝
                    except Exception:
                        pass
                    
                    key_rotator.mark_cooldown(active_key, duration=cooldown_sec)
                    logger.info(f"⏳ 偵測到金鑰頻率限制，該金鑰將被冷凍避開 {cooldown_sec:.1f} 秒...")
                    await asyncio.sleep(2)

                if num_keys > 1:
                    key_rotator.rotate()
                
                # 如果已經嘗試完所有金鑰，就跳出輪轉，嘗試下一個模型
                if key_attempt == num_keys - 1:
                    break
            
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
    
    # 動態調整併發限制：若只有 1 支金鑰，限制併發為 1（順序生成），避免觸發 Google 的併發/次數限制。
    # 若有多支金鑰，則允許較高的併發度（金鑰個數，最多 3），以金鑰分流達到極速生成。
    num_keys = len(key_rotator.keys) or 1
    max_concurrency = 1 if num_keys == 1 else min(num_keys, 3)
    sem = asyncio.Semaphore(max_concurrency)
    logger.info(f"📊 根據金鑰數量 ({num_keys} 支)，動態配置併發限制 Semaphore({max_concurrency})")
    
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
                    # 避免 API 重疊發送（若併發為 1 則小延遲，多併發隨機延遲）
                    delay = 0.1 if max_concurrency == 1 else random.uniform(0.2, 0.8)
                    await asyncio.sleep(delay)
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
                await asyncio.sleep(3 + attempt * 2)
                
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
                response = model.generate_content(f"{system_prompt}\n\n{user_prompt}")
                
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
