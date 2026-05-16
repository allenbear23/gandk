"""
utils/prompt_builder.py — System Prompt 組裝工具

設計原則：
- 嚴格要求 JSON 輸出（防止 AI 自由發揮格式）
- 明確指定「參考課本，不超綱」+ 「模仿考古題風格」
- 內建 JSON Schema 讓 AI 照格式輸出
"""
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
    組裝 System Prompt + User Prompt。
    回傳 (system_prompt, user_prompt)。
    """
    # ── 整理知識庫內容 ──────────────────────────────────────────
    textbook_context = _format_chunks(textbook_chunks, "課本知識")
    past_exam_context = _format_chunks(past_exam_chunks, "考古題範例")

    units_str = "、".join(unit_codes)
    difficulty_desc = {1: "簡單", 2: "中易", 3: "中等", 4: "中難", 5: "困難"}[difficulty]

    # ── System Prompt ──────────────────────────────────────────
    system_prompt = f"""你是一位擁有 20 年經驗的台灣高中{subject_name}科名師。你的任務是為全國模考或段考出題。
你的出題風格必須「完全複刻」提供的【考古題範例】。

## 出題核心規範
1. **素材導向**：大量使用史料、地圖描述、社會現象或學術論點作為題幹。
2. **知識對齊**：所有命題點必須嚴格遵守【課本知識】，絕對不考課外偏題。
3. **語氣複刻**：
   - 題幹語氣應正式、嚴謹。
   - 選項設計應具備「誘答性」，避免一眼就能看出答案。
4. **難度控制**：目前設定為「{difficulty_desc}」。
5. **情境化**：盡可能將知識點融入情境題中，而非單純的記憶檢索。

## 輸出 JSON Schema（嚴格遵守）
{{
  "questions": [
    {{
      "id": 1,
      "question": "（在此輸入包含引文或素材的題目文字）",
      "choices": [
        {{"key": "A", "text": "選項內容"}},
        {{"key": "B", "text": "選項內容"}},
        {{"key": "C", "text": "選項內容"}},
        {{"key": "D", "text": "選項內容"}}
      ],
      "answer": "正確選項英文字母",
      "explanation": "【解析】先引述課本依據，再逐一說明 A、B、C、D 的判斷理由。",
      "unit_code": "{units_str.split('、')[0]}",
      "difficulty": {difficulty}
    }}
  ]
}}"""

    # ── User Prompt ────────────────────────────────────────────
    user_prompt = f"""請根據以下資料，出 {question_count} 題{subject_name}選擇題（範圍：{units_str}）。

{textbook_context}

{past_exam_context}

請直接輸出 JSON，不要任何其他文字。"""

    return system_prompt, user_prompt


def _format_chunks(chunks: List[dict], label: str) -> str:
    """將 chunks list 格式化為 prompt 中的段落"""
    if not chunks:
        return f"【{label}】\n（無相關資料）\n"

    content = f"【{label}】\n"
    for i, chunk in enumerate(chunks, 1):
        unit = chunk.get("unit_code", "")
        text = chunk.get("chunk_text", chunk.get("text", ""))
        content += f"\n[片段 {i}｜單元 {unit}]\n{text}\n"

    return content
