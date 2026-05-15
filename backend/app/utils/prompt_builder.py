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
    system_prompt = f"""你是一位專業的台灣高中{subject_name}科出題老師，擅長設計符合課綱的選擇題。

## 你的任務
根據提供的「課本知識」與「考古題範例」，出 {question_count} 題{subject_name}選擇題。

## 嚴格規則
1. **知識範圍**：所有題目必須完全基於「課本知識」中的內容，絕對不可超出給定的單元範圍（{units_str}）。
2. **題型風格**：模仿「考古題範例」的出題方式、語氣與難易度層次。
3. **難度要求**：整體難度為「{difficulty_desc}」（1-5 級中的 {difficulty} 級）。
4. **選項設計**：四個選項（A/B/C/D）需有明顯區別，且干擾選項須合理（不能明顯離題）。
5. **解析品質**：explanation 必須明確說明正確答案的依據，並點出其他選項的錯誤之處。
6. **輸出格式**：只能輸出 JSON，不得有任何額外說明文字、markdown 代碼塊或前言。

## 輸出 JSON Schema（嚴格遵守）
{{
  "questions": [
    {{
      "id": 1,
      "question": "題目文字（可含史料、引文等）",
      "choices": [
        {{"key": "A", "text": "選項A文字"}},
        {{"key": "B", "text": "選項B文字"}},
        {{"key": "C", "text": "選項C文字"}},
        {{"key": "D", "text": "選項D文字"}}
      ],
      "answer": "B",
      "explanation": "詳細解析，說明為何選B，以及A、C、D錯誤的原因",
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
