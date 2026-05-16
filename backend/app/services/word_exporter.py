"""
services/word_exporter.py — JSON 轉 Word (docx) 排版服務

提供下載模式（列印模式）的實作。
排版風格模仿傳統台灣考古題：
- 標題置中
- 題目與選項排版
- 頁碼
- 附錄解答與解析
"""
import io
from docx import Document
from docx.shared import Pt, Inches
from docx.enum.text import WD_PARAGRAPH_ALIGNMENT

from app.models.question import ExamResult


def export_to_docx(exam_result: ExamResult) -> bytes:
    """
    將 ExamResult 轉換為 .docx 檔案的 bytes。
    包含：
    1. 試題卷 (題目 + 空白選項)
    2. 解答與解析卷
    """
    doc = Document()
    
    # ── 樣式設定 ──────────────────────────────────────────
    style = doc.styles['Normal']
    font = style.font
    font.name = 'Arial'  # 預設英文字型，中文會依賴系統 fallback
    font.size = Pt(12)

    # ── 試題卷標題 ────────────────────────────────────────
    title_text = f"【AI 智慧模擬考】{exam_result.subject} 試題卷"
    heading = doc.add_heading(title_text, level=1)
    heading.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
    
    range_text = f"範圍：{'、'.join(exam_result.units)}   |   總題數：{exam_result.total_questions} 題"
    subtitle = doc.add_paragraph(range_text)
    subtitle.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
    
    doc.add_paragraph() # 空一行

    # ── 題目區 ──────────────────────────────────────────
    for i, q in enumerate(exam_result.questions, 1):
        # 題目文字
        p_q = doc.add_paragraph()
        p_q.add_run(f"{i}. ").bold = True
        p_q.add_run(q.question)
        
        # 選項排版 (A) xxx  (B) yyy  (C) zzz  (D) www
        # 為了美觀，根據選項長度決定是一行排四個，還是分行排
        max_choice_len = max(len(c.text) for c in q.choices)
        
        p_c = doc.add_paragraph()
        p_c.paragraph_format.left_indent = Inches(0.25)
        
        if max_choice_len < 15:
            # 短選項，排成同一行
            choices_str = "    ".join([f"({c.key}) {c.text}" for c in q.choices])
            p_c.add_run(choices_str)
        else:
            # 長選項，分兩行或四行
            for c in q.choices:
                p_c.add_run(f"({c.key}) {c.text}\n")
                
        doc.add_paragraph() # 題與題之間空一行

    # ── 換頁：解答與解析卷 ──────────────────────────────────
    doc.add_page_break()
    
    ans_heading = doc.add_heading("解答與解析卷", level=1)
    ans_heading.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
    doc.add_paragraph()

    # 簡單解答表 (例如 1-5: A B C D A)
    doc.add_heading("一、 選擇題解答", level=2)
    p_ans_table = doc.add_paragraph()
    ans_table_text = ""
    for i, q in enumerate(exam_result.questions, 1):
        ans_table_text += f"{i:2d}.{q.answer}   "
        if i % 5 == 0:
            ans_table_text += "  "
        if i % 10 == 0:
            ans_table_text += "\n"
    p_ans_table.add_run(ans_table_text)
    
    doc.add_paragraph()

    # 詳解
    doc.add_heading("二、 試題詳解", level=2)
    for i, q in enumerate(exam_result.questions, 1):
        p_exp = doc.add_paragraph()
        p_exp.add_run(f"{i}. 【答案】{q.answer}").bold = True
        p_exp.add_run(f"  (難度: {q.difficulty}/5)\n")
        p_exp.add_run(f"【解析】{q.explanation}")
        
    # ── 匯出 Bytes ────────────────────────────────────────
    file_stream = io.BytesIO()
    doc.save(file_stream)
    return file_stream.getvalue()
