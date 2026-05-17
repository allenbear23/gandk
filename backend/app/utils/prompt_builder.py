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
) -> tuple[str, str]:
    """
    專為「單一大題」設計的超高擬真度命題 Prompt。
    """
    textbook_context = _format_chunks(textbook_chunks, "課本核心內容")
    past_exam_context = _format_chunks(past_exam_chunks, "考古題風格參考")

    units_str = "、".join(unit_codes)
    first_unit = unit_codes[0] if unit_codes else "1-1"
    difficulty_desc = {1: "簡單", 2: "中易", 3: "中等", 4: "中難", 5: "困難"}[difficulty]

    # 大題專屬極限精準命題與格式規範 (支援 layout_type 與中文關鍵字模糊匹配雙通道)
    special_section_instructions = ""
    lt = (layout_type or "").lower()
    is_vocab_lt = (lt == "vocabulary") or ("字彙" in sec_name)
    is_cloze_lt = (lt == "cloze") or ("克漏字" in sec_name or "克漏" in sec_name)
    is_completion_lt = (lt == "word_bank") or ("文意選填" in sec_name or "選填" in sec_name)
    is_translation_lt = (lt == "translation") or ("翻譯" in sec_name or "填空式翻譯" in sec_name)

    if is_vocab_lt:
        special_section_instructions = """
* 📝【字彙題型特規】
  1. 本大題為「字彙」填空題，每題的 "choices" 欄位必須為空陣列 `[]`（絕對不要有 A, B, C, D 選項）。
  2. 題目 ("question") 必須提供一個英文句子，且目標單字必須呈現為「首尾字母+中間底線」的半拼寫格式（例如，如果答案單字是 remote，必須在題目中寫成 `r_____`；如果是 plenty，必須寫成 `p_____y`；如果是 journey，必須寫成 `j_____y`）。
  3. "answer" 欄位必須是該目標單字的【完整拼寫】（例如：`remote`、`plenty`、`journey`）。
  4. "explanation" 欄位寫出單字中文意思以及整句的句意解析。
"""
    elif is_cloze_lt:
        special_section_instructions = f"""
* 📝【克漏字題型特規】
  1. 本大題為「克漏字」綜合測驗。
  2. 第 1 題的 "question" 欄位必須包含【整篇完整的長篇閱讀文章】，並在文章中要填空的地方用 `(1) _______`、`(2) _______` ... 到 `({sec_cnt}) _______` 標示出所有挖空的位置。第 1 題的 "choices" 則是第 (1) 個挖空的選項。
  3. 隨後的第 2 題到第 {sec_cnt} 題，其 "question" 欄位【只需填寫題號即可】（例如：`(2)`、`(3)`），不可重複整篇文章。其 "choices" 則為對應題號空格 of A, B, C, D 四個選項。
"""
    elif is_completion_lt:
        special_section_instructions = f"""
* 📝【文意選填題型特規】
  1. 本大題為「文意選填」。
  2. 第 1 題的 "question" 欄位必須以特別的【備選單字庫 (Word Bank)】開頭。格式必須精確為：
     `Word Bank: A. 單字A    B. 單字B    C. 單字C    D. 單字D    E. 單字E    F. 單字F    G. 單字G    H. 單字H    I. 單字I    J. 單字J`
     （必須正好提供 10 個備選英文字，與你的單字範圍或課文相關）。
     在單字庫下方，換行提供【整篇完整的長篇閱讀文章】，並在挖空處標記 `(1) _______`、`(2) _______` ... 到 `({sec_cnt}) _______`。第 1 題的 "choices" 為 `A` 到 `J` 共 10 個選項，"answer" 則是第一題對應的單字字母（如 `C`）。
  3. 隨後的第 2 題到第 {sec_cnt} 題，其 "question" 欄位【只需填寫題號即可】（例如：`(2)`、`(3)`）。其 "choices" 固定提供相同的 `A` 到 `J` 共 10 個選項，"answer" 為對應大寫字母。
"""
    elif is_translation_lt:
        special_section_instructions = """
* 📝【填空式翻譯題型特規】
  1. 本大題為中翻英「填空式翻譯」題，每題的 "choices" 欄位必須為空陣列 `[]`（不要有選項）。
  2. 題目 ("question") 必須先給出中文段落，接著給出英文翻譯，並在挖空的位置標示為 `(1) _______`、`(2) _______` 等。
  3. "answer" 欄位為該空格填入的正確單字或片語（例如 `linked to` 或 `appliance`）。
"""
    else:
        # 一般選擇題型
        if sec_type == "multiple_choice":
            special_section_instructions = """
* 📝【一般選擇題型規範】
  1. 每題必須提供 4 個選項（A, B, C, D）。
  2. "question" 為單獨的英文題目句。
"""
        else:
            special_section_instructions = """
* 📝【非選擇題型規範】
  1. 每題的 "choices" 必須為空陣列 `[]`，"answer" 為該題的正確文字答案。
"""

    system_prompt = f"""你是一位擁有 20 年經驗的台灣高中{subject_name}科名師。
請根據提供的素材，出一份正式的、符合高中段考標準的 JSON 格式考卷。

【重要：此大題專屬風格與結構規範】
- 大題名稱：{sec_name}
- 題型類別：{sec_type}
- 配分說明：{scoring}
- 預計題數：此 API 呼叫必須且只能產出剛好 {sec_cnt} 道題目，題號必須為 1 到 {sec_cnt}！
{special_section_instructions}

## 命題與格式規範
1. **語氣**：使用專業的學術命題風格，完全克隆台灣高中考卷的排版與表達方式。
2. **結構**：必須嚴格遵守以下 JSON 結構，且每一題都必須包含 "unit_code" 與 "section" 欄位。

## JSON 結構範例
{{
  "questions": [
    {{
      "id": 1,
      "unit_code": "{first_unit}",
      "section": "{sec_name}",
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

    user_prompt = f"""請產出符合風格規範的{subject_name}大題「{sec_name}」試題。
範圍：{units_str}
難度：{difficulty_desc}

{textbook_context}
{past_exam_context}
"""
    return system_prompt, user_prompt
