from typing import List

def build_exam_prompt(
    subject_name: str,
    unit_codes: List[str],
    question_count: int,
    textbook_chunks: List[dict],
    past_exam_chunks: List[dict],
    head_chunks: List[dict] = None,
    difficulty: int = 3,
) -> tuple[str, str]:
    """
    動態排版與人設模仿 Prompt 構建器。
    """
    textbook_context = _format_chunks(textbook_chunks, "課本核心知識")
    past_exam_context = _format_chunks(past_exam_chunks, "考古題題目風格參考")
    head_context = _format_chunks(head_chunks or [], "考古題排版與表頭範例")

    units_str = "、".join(unit_codes)
    difficulty_desc = {1: "簡單", 2: "中易", 3: "中等", 4: "中難", 5: "困難"}[difficulty]

    system_prompt = f"""你是一位具備高度模仿能力的專業教育命題專家。
你的任務是根據提供的【考古題排版與表頭範例】，「自動提取」其排版特徵與命題人設，並產出一份風格完全一致的新考卷。

## 第一步：排版與人設分析（動態模仿）
請仔細閱讀【考古題排版與表頭範例】，分析並模仿以下內容：
1. **考卷抬頭**：包含年份、學期、考試名稱、科目名稱的寫法。
2. **資訊欄位**：包含班級、座號、姓名、分數格的排列順序與文字。
3. **命題人設**：分析其命題語氣（例如：是嚴肅的學術風、還是親切的引導風）。
4. **配分邏輯**：觀察其題目如何標註分數（例如：每題 2 分、或 2.5 分）。

## 第二步：命題規範
1. **知識點**：嚴格遵守【課本核心知識】，範圍限定在「{units_str}」。
2. **題型**：模仿考古題的題幹長度、史料使用比例。
3. **難度**：設定為「{difficulty_desc}」。

## 輸出格式 (JSON)
你必須輸出以下結構的 JSON：
{{
  "exam_metadata": {{
    "title": "（模仿範例產出的完整標題，如：112學年度第一學期...）",
    "header_fields": ["班級", "座號", "姓名"],
    "score_info": "（模仿範例的計分說明，如：共 50 題，每題 2 分）",
    "persona_style": "（簡述你模仿的風格類型）"
  }},
  "questions": [
    {{
      "id": 1,
      "question": "題目內容",
      "choices": [
        {{"key": "A", "text": "選項"}},
        {{"key": "B", "text": "選項"}},
        {{"key": "C", "text": "選項"}},
        {{"key": "D", "text": "選項"}}
      ],
      "answer": "A",
      "explanation": "【解析】依據課本...，故選A。"
    }}
  ]
}}"""

    user_prompt = f"""請開始分析並出題。
{head_context}
{textbook_context}
{past_exam_context}
"""
    return system_prompt, user_prompt

def _format_chunks(chunks: List[dict], label: str) -> str:
    if not chunks: return f"【{label}】\n（無相關資料）\n"
    content = f"【{label}】\n"
    for i, chunk in enumerate(chunks, 1):
        text = chunk.get("chunk_text", chunk.get("text", ""))
        content += f"\n[參考片段 {i}]\n{text}\n"
    return content
