from typing import List

def build_exam_prompt(
    subject_name: str,
    unit_codes: List[str],
    question_count: int,
    textbook_chunks: List[dict],
    past_exam_chunks: List[dict],
    difficulty: int = 3,
) -> tuple[str, str]:
    """
    組裝專業的台灣高中命題 Prompt。
    """
    textbook_context = _format_chunks(textbook_chunks, "課本核心內容")
    past_exam_context = _format_chunks(past_exam_chunks, "考古題風格參考")

    units_str = "、".join(unit_codes)
    difficulty_desc = {1: "簡單", 2: "中易", 3: "中等", 4: "中難", 5: "困難"}[difficulty]

    system_prompt = f"""你是一位擁有 20 年經驗的台灣高中{subject_name}科名師。你正在為一份正式的段考考卷命題。

## 命題準則
1. **正式語氣**：題幹應嚴謹，大量使用「下列敘述何者正確？」、「根據上文，...」等標準命題語句。
2. **素材融入**：盡可能將引文、史料或情境融入題幹中。
3. **選項設計**：四個選項 (A,B,C,D) 必須長度相近，且具備合理的干擾性。
4. **內容守備**：嚴格遵守提供之【課本核心內容】，不得超出高中「{units_str}」單元的教學範圍。

## 輸出格式 (JSON)
你必須嚴格依照以下結構輸出：
{{
  "questions": [
    {{
      "id": 1,
      "question": "題目文字",
      "choices": [
        {{"key": "A", "text": "選項內容"}},
        {{"key": "B", "text": "選項內容"}},
        {{"key": "C", "text": "選項內容"}},
        {{"key": "D", "text": "選項內容"}}
      ],
      "answer": "A",
      "explanation": "【解析】說明正確原因與錯誤選項之處。"
    }}
  ]
}}"""

    user_prompt = f"""請出 {question_count} 題{subject_name}選擇題。難度：{difficulty_desc}。

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
