import json
import re
import logging
from typing import List, Optional

logger = logging.getLogger(__name__)

def scale_style_prompt(style_prompt_str: str, max_total_questions: int = 15) -> tuple[str, int]:
    """
    等比例縮放考古題大題題數，防止 AI 生成題目過多導致輸出截斷 (Token Overflow)
    """
    if not style_prompt_str:
        return style_prompt_str, 0

    try:
        # 清理可能含 ```json 的包裝
        cleaned = style_prompt_str.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r'^```(?:json)?\s*\n?', '', cleaned, flags=re.IGNORECASE)
            cleaned = re.sub(r'\n?```\s*$', '', cleaned)
        
        data = json.loads(cleaned)
        
        total_q = data.get("total_questions_count", 0)
        sections = data.get("sections", [])
        
        if total_q > max_total_questions and sections:
            ratio = max_total_questions / total_q
            new_total = 0
            for sec in sections:
                orig_cnt = sec.get("question_count", 0)
                # 保證各大題至少有 1 題，並等比例縮放
                new_cnt = max(1, round(orig_cnt * ratio))
                sec["question_count"] = new_cnt
                new_total += new_cnt
                
                # 調整描述以符合新題數
                if "scoring_rule" in sec:
                    # 去除大題配分比率（因為題數已改變，由 Word 匯出器與前台以題數重新計算）
                    sec["scoring_rule"] = "本大題均分"
            
            data["total_questions_count"] = new_total
            logger.info(f"⚡ 大題題數等比例縮放完成：由 {total_q} 題 縮放為 {new_total} 題，防止 Token 溢出截斷！")
            return json.dumps(data, ensure_ascii=False, indent=2), new_total
            
    except Exception as e:
        logger.warning(f"⚠️ 無法等比例縮放考古題大題題數，將採用原始設定: {e}")
        
    return style_prompt_str, 0

def build_exam_prompt(
    subject_name: str,
    unit_codes: List[str],
    question_count: int,
    textbook_chunks: List[dict],
    past_exam_chunks: List[dict],
    difficulty: int = 3,
    style_prompt: Optional[str] = None,
) -> tuple[str, str]:
    """
    專業台灣高中命題 Prompt - 支援自定義科目風格與題數防截斷縮放。
    """
    textbook_context = _format_chunks(textbook_chunks, "課本核心內容")
    past_exam_context = _format_chunks(past_exam_chunks, "考古題風格參考")

    units_str = "、".join(unit_codes)
    first_unit = unit_codes[0] if unit_codes else "1-1"
    difficulty_desc = {1: "簡單", 2: "中易", 3: "中等", 4: "中難", 5: "困難"}[difficulty]

    # 風格指令處理
    custom_style = ""
    style_instructions = ""
    if style_prompt:
        # 將總題數限定在 15 題以內，保證生成穩定、完整且不截斷
        scaled_prompt, new_total = scale_style_prompt(style_prompt, max_total_questions=15)
        custom_style = f"\n【重要：此科目專屬風格規範】\n{scaled_prompt}\n"
        
        target_count = new_total if new_total > 0 else "風格規範中的 total_questions_count"
        
        style_instructions = f"""
3. **必須嚴格遵守【此科目專屬風格規範】**中的大題結構（sections）。
4. 大題數量、大題名稱、各大題的題數（question_count）、題型與格式特徵，必須與該規範中的 sections 設置百分之百完全一致！
5. 在輸出 JSON 時，每一題必須包含 "section" 欄位（填寫對應的 sections.section_name 標題，例如 "第一部分：聽力測驗 (看圖辨義)")，以便系統在匯出 Word 時進行精確的分段編排。
6. 考卷的總題數與每一題的題號 id 必須與規範中的 total_questions_count (共 {target_count} 題) 完全一致！請忽略請求中的 question_count 參數，完全以風格規範中的考古題題數與結構為最高準則！
"""

    system_prompt = f"""你是一位擁有 20 年經驗的台灣高中{subject_name}科名師。
請根據提供的素材，出一份正式的、符合高中段考標準的 JSON 格式考卷。
{custom_style}
## 命題與格式規範
1. **語氣**：使用專業的學術命題風格。
2. **結構**：必須嚴格遵守以下 JSON 結構，且每一題都必須包含 "unit_code" 欄位。{style_instructions}

## JSON 結構範例
{{
  "questions": [
    {{
      "id": 1,
      "unit_code": "{first_unit}",
      "section": "第一部分：字彙測驗",
      "question": "題目文字...",
      "choices": [
        {{"key": "A", "text": "選項內容"}},
        {{"key": "B", "text": "選項內容"}},
        {{"key": "C", "text": "選項內容"}},
        {{"key": "D", "text": "選項內容"}}
      ],
      "answer": "A",
      "explanation": "【解析】..."
    }}
  ]
}}"""

    user_prompt = f"""請產出符合風格規範的{subject_name}選擇題。
範圍：{units_str}
難度：{difficulty_desc}

{textbook_context}
{past_exam_context}
"""
    return system_prompt, user_prompt

def _format_chunks(chunks: List[dict], label: str) -> str:
    if not chunks: return f"【{label}】\n（目前無資料）\n"
    content = f"【{label}】\n"
    for i, chunk in enumerate(chunks, 1):
        text = chunk.get("chunk_text", chunk.get("text", ""))
        content += f"\n[片段 {i}]\n{text}\n"
    return content

def build_exam_prompt_for_single_section(
    subject_name: str,
    unit_codes: List[str],
    sec_name: str,
    sec_cnt: int,
    sec_type: str,
    scoring: str,
    difficulty: int = 3,
    textbook_chunks: List[dict] = [],
    past_exam_chunks: List[dict] = [],
    layout_type: str = "",
    custom_requirements: str = "",
) -> tuple[str, str]:
    """
    精簡、高密度的單一大題命題 Prompt，大幅降低 Token 耗費與延遲。
    """
    textbook_context = _format_chunks(textbook_chunks, "課本內容")
    past_exam_context = _format_chunks(past_exam_chunks, "考古題參考")

    units_str = "、".join(unit_codes)
    first_unit = unit_codes[0] if unit_codes else "1-1"
    difficulty_desc = {1: "簡單", 2: "中易", 3: "中等", 4: "中難", 5: "困難"}[difficulty]

    # 特殊題型精簡特規
    special_section_instructions = ""
    lt = (layout_type or "").lower()
    is_vocab_lt = (lt == "vocabulary") or ("字彙" in sec_name)
    is_cloze_lt = (lt == "cloze") or ("克漏字" in sec_name or "克漏" in sec_name)
    is_completion_lt = (lt == "word_bank") or ("文意選填" in sec_name or "選填" in sec_name)
    is_translation_lt = (lt == "translation") or ("翻譯" in sec_name or "填空式翻譯" in sec_name)

    if is_vocab_lt:
        special_section_instructions = """* 📝【字彙題型特規】: choices必須為空陣列 `[]`。題目("question")提供英文句，目標單字呈現首尾字母與底線（如 "r_____e"）。"answer"填入該目標單字的完整拼寫。"""
    elif is_cloze_lt:
        special_section_instructions = f"""* 📝【克漏字題型特規】: 第 1 題 "question" 包含整篇挖空長文（挖空標記 `(1) _______` 到 `({sec_cnt}) _______`），"choices" 為第 1 空格選項。其餘第 2 到 {sec_cnt} 題，"question" 僅填寫題號（如 `(2)`），"choices" 則為對應題號選項。"""
    elif is_completion_lt:
        special_section_instructions = f"""* 📝【文意選填題型特規】: 第 1 題 "question" 開頭為單字庫 `Word Bank: A.單字A  B.單字B...` (正好 10 個英文字)，下方附整篇挖空長文（標記 `(1) _______` 到 `({sec_cnt}) _______`）。其餘第 2 到 {sec_cnt} 題，"question" 僅填寫題號（如 `(2)`），"choices" 固定為 `A` 到 `J` 的 10 個選項。"""
    elif is_translation_lt:
        special_section_instructions = """* 📝【填空式翻譯題型特規】: choices 必須為空陣列 `[]`。題目("question")給予中文段落與挖空英文 `(1) _______`、`(2) _______` 等，"answer"為填入的正確英文字詞。"""
    else:
        if sec_type == "multiple_choice":
            special_section_instructions = """* 📝【一般選擇題型】: 每題提供 4 個選項（A, B, C, D），"question" 為題目句。"""
        else:
            special_section_instructions = """* 📝【非選擇題型】: choices 必須為空陣列 `[]`，"answer" 為正確答案。"""

    custom_req_instructions = f"* ⚠️【自訂限制要求】: {custom_requirements}" if custom_requirements else ""

    system_prompt = f"""你是一位台灣高中{subject_name}教師。請產出剛好 {sec_cnt} 道題目的 JSON 試卷。
【大題資訊】: 名稱: "{sec_name}", 題型: {sec_type}, 配分: {scoring}, 題號 id: 1 到 {sec_cnt}。
{special_section_instructions}
{custom_req_instructions}

請嚴格遵守 JSON 結構輸出:
{{
  "questions": [
    {{
      "id": 1,
      "unit_code": "{first_unit}",
      "section": "{sec_name}",
      "question": "...",
      "choices": [{{"key": "A", "text": "..."}}],
      "answer": "A",
      "explanation": "..."
    }}
  ]
}}"""

    user_prompt = f"""產出高中{subject_name}科大題「{sec_name}」試題。
範圍：{units_str}
難度：{difficulty_desc}
{textbook_context}
{past_exam_context}
"""
    return system_prompt, user_prompt


def build_mega_exam_prompt(
    subject_name: str,
    unit_codes: List[str],
    style_json: dict,
    difficulty: int = 3,
    textbook_chunks: List[dict] = [],
    past_exam_chunks: List[dict] = [],
) -> tuple[str, str]:
    """
    將所有大題打包，構建出一個單次 API 請求即可生成整張考卷所有大題的 Mega-Prompt！
    此模式下，AI 會一次性輸出包含所有大題所有題目的 questions 列表。
    """
    first_unit = unit_codes[0] if unit_codes else "1-1"
    units_str = "、".join(unit_codes)
    difficulty_desc = {1: "簡單", 2: "中易", 3: "中等", 4: "中難", 5: "困難"}[difficulty]
    
    sections = style_json.get("sections", [])
    
    # 建立大題的清單與規則說明
    section_rules = []
    total_q = 0
    
    for idx, sec in enumerate(sections, 1):
        sec_name = sec.get("section_name", f"第 {idx} 大題")
        sec_cnt = sec.get("question_count", 1)
        sec_type = sec.get("question_type", "multiple_choice")
        scoring = sec.get("scoring_rule", "")
        layout_type = sec.get("layout_type", "")
        
        # 題型特殊規則
        lt = (layout_type or "").lower()
        is_vocab_lt = (lt == "vocabulary") or ("字彙" in sec_name)
        is_cloze_lt = (lt == "cloze") or ("克漏字" in sec_name or "克漏" in sec_name)
        is_completion_lt = (lt == "word_bank") or ("文意選填" in sec_name or "選填" in sec_name)
        is_translation_lt = (lt == "translation") or ("翻譯" in sec_name or "填空式翻譯" in sec_name)

        rule_desc = f"【大題 {idx}】: {sec_name} (共 {sec_cnt} 題, 題型: {sec_type}, 配分: {scoring})\n"
        if is_vocab_lt:
            rule_desc += f"  - 📝 字彙題型特規: choices 必須為空陣列 `[]`。題目 question 提供英文句，目標單字呈現首尾字母與底線（如 \"r_____e\"）。\"answer\" 填入該單字完整拼寫。題目 section 欄位必須為 \"{sec_name}\"。\n"
        elif is_cloze_lt:
            rule_desc += f"  - 📝 克漏字題型特規: 這大題共有 {sec_cnt} 題。本大題第 1 題的 question 包含整篇挖空長文（挖空標記 `(1) _______` 到 `({sec_cnt}) _______`），choices 為第 1 個空格選項。本大題其餘第 2 到 {sec_cnt} 題，question 僅填寫題號（如 `(2)`），choices 則為對應題號選項。題目 section 欄位必須為 \"{sec_name}\"。\n"
        elif is_completion_lt:
            rule_desc += f"  - 📝 文意選填題型特規: 這大題共有 {sec_cnt} 題。本大題第 1 題的 question 開頭為單字庫 `Word Bank: A.單字A  B.單字B...` (正好 10 個英文字)，下方附整篇挖空長文（標記 `(1) _______` 到 `({sec_cnt}) _______`）。本大題其餘第 2 到 {sec_cnt} 題，question 僅填寫題號（如 `(2)`），choices 固定為 `A` 到 `J` 的 10 個選項。題目 section 欄位必須為 \"{sec_name}\"。\n"
        elif is_translation_lt:
            rule_desc += f"  - 📝 填空式翻譯題型特規: choices 必須為空陣列 `[]`。題目 question 給予中文段落與挖空英文 `(1) _______` 等，answer 填入正確英文字詞。題目 section 欄位必須為 \"{sec_name}\"。\n"
        else:
            if sec_type == "multiple_choice":
                rule_desc += f"  - 📝 選擇題型特規: 提供 A, B, C, D 四個選項，answer 為選項字母。題目 section 欄位必須為 \"{sec_name}\"。\n"
            else:
                rule_desc += f"  - 📝 非選擇題型特規: choices 為空陣列 `[]`，answer 為正確解答。題目 section 欄位必須為 \"{sec_name}\"。\n"
        
        section_rules.append(rule_desc)
        total_q += sec_cnt

    rules_str = "\n".join(section_rules)
    custom_requirements = style_json.get("custom_requirements", "")
    custom_req_instructions = f"自訂限制要求: {custom_requirements}" if custom_requirements else ""
    
    textbook_context = _format_chunks(textbook_chunks, "課本內容")
    past_exam_context = _format_chunks(past_exam_chunks, "考古題參考")

    system_prompt = f"""你是一位台灣高中{subject_name}教師。請一次性產出包含所有大題、共計剛好 {total_q} 題的 JSON 完整試卷。
請為每道題目的 "id" 欄位設定從 1 到 {total_q} 的遞增序號。

【大題與題型規格說明】：
{rules_str}

【其他規範】：
* 題目的 "section" 欄位必須設定為該題目對應的大題名稱（如 "{sections[0].get('section_name', '第一部分')}" 等）。
* {custom_req_instructions}

請嚴格遵守以下 JSON 輸出結構：
{{
  "questions": [
    {{
      "id": 1,
      "unit_code": "{first_unit}",
      "section": "大題名稱",
      "question": "...",
      "choices": [{{"key": "A", "text": "..."}}],
      "answer": "A",
      "explanation": "..."
    }}
  ]
}}"""

    user_prompt = f"""一次性生成整張高中{subject_name}科完整考卷。
考試範圍：{units_str}
考卷難度：{difficulty_desc}
{textbook_context}
{past_exam_context}
"""
    return system_prompt, user_prompt
