from typing import List, Optional

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
    專業台灣高中命題 Prompt - 支援自定義科目風格。
    """
    textbook_context = _format_chunks(textbook_chunks, "課本核心內容")
    past_exam_context = _format_chunks(past_exam_chunks, "考古題風格參考")

    units_str = "、".join(unit_codes)
    first_unit = unit_codes[0] if unit_codes else "1-1"
    difficulty_desc = {1: "簡單", 2: "中易", 3: "中等", 4: "中難", 5: "困難"}[difficulty]

    # 風格指令處理
    custom_style = f"\n【重要：此科目專屬風格規範】\n{style_prompt}\n" if style_prompt else ""

    system_prompt = f"""你是一位擁有 20 年經驗的台灣高中{subject_name}科名師。
請根據提供的素材，出一份正式的、符合高中段考標準的 JSON 格式考卷。
{custom_style}
## 命題與格式規範
1. **語氣**：使用專業的學術命題風格。
2. **結構**：必須嚴格遵守以下 JSON 結構，且每一題都必須包含 "unit_code" 欄位。

## JSON 結構範例
{{
  "questions": [
    {{
      "id": 1,
      "unit_code": "{first_unit}",
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

    user_prompt = f"""請產出 {question_count} 題{subject_name}選擇題。
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
