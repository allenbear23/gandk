import io
from docx import Document
from docx.shared import Pt, Inches
from docx.enum.text import WD_PARAGRAPH_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

from app.models.question import ExamResult

def set_font_style(run, size=12, bold=False, font_name='新細明體'):
    run.font.size = Pt(size)
    run.bold = bold
    run.font.name = 'Times New Roman'
    r = run._element
    rPr = r.get_or_add_rPr()
    rFonts = OxmlElement('w:rFonts')
    rFonts.set(qn('w:ascii'), 'Times New Roman')
    rFonts.set(qn('w:eastAsia'), font_name)
    rPr.append(rFonts)

def add_dynamic_header_table(doc, metadata, default_subject):
    """根據 AI 提取的 Metadata 動態生成表頭"""
    title = metadata.get("title", f"【AI 智慧模擬考】{default_subject} 試題卷")
    fields = metadata.get("header_fields", ["班級", "座號", "姓名"])
    
    # 建立表格：1列大標題 + 1列資訊欄
    table = doc.add_table(rows=2, cols=len(fields) + 1)
    table.style = 'Table Grid'
    
    # 大標題
    a = table.cell(0, 0)
    b = table.cell(0, len(fields) - 1)
    title_cell = a.merge(b)
    p = title_cell.paragraphs[0]
    p.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
    run = p.add_run(title)
    set_font_style(run, size=14, bold=True)
    
    # 得分欄
    score_cell = table.cell(0, len(fields))
    p_score = score_cell.paragraphs[0]
    p_score.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
    run_score = p_score.add_run("得分")
    set_font_style(run_score, size=11)
    
    # 資訊欄位 (班級、座號...)
    for i, field in enumerate(fields):
        cell = table.cell(1, i)
        p = cell.paragraphs[0]
        run = p.add_run(f"{field}：")
        set_font_style(run, size=10)
        
    return table

def export_to_docx(exam_result: ExamResult) -> bytes:
    doc = Document()
    metadata = getattr(exam_result, 'metadata', {})
    
    section = doc.sections[0]
    section.top_margin = Inches(0.4)
    section.bottom_margin = Inches(0.4)
    section.left_margin = Inches(0.4)
    section.right_margin = Inches(0.4)

    # 1. 動態表頭
    add_dynamic_header_table(doc, metadata, exam_result.subject)
    
    # 2. 計分說明
    p_score_info = doc.add_paragraph()
    score_text = metadata.get("score_info", f"總題數：{exam_result.total_questions} 題")
    run_info = p_score_info.add_run(f"範圍：{'、'.join(exam_result.units)} | {score_text}")
    set_font_style(run_info, size=9)
    
    doc.add_paragraph()

    # 3. 雙欄設定
    sectPr = section._element.get_or_add_sectPr()
    cols = OxmlElement('w:cols')
    cols.set(qn('w:num'), '2')
    cols.set(qn('w:sep'), '1')
    cols.set(qn('w:space'), '425')
    sectPr.append(cols)
    
    # 4. 題目區
    for i, q in enumerate(exam_result.questions, 1):
        p_q = doc.add_paragraph()
        run_id = p_q.add_run(f"(  ) {i}. ")
        set_font_style(run_id, size=11, bold=True)
        run_text = p_q.add_run(q.question)
        set_font_style(run_text, size=11)
        
        # 選項處理
        for c in q.choices:
            p_c = doc.add_paragraph()
            p_c.paragraph_format.left_indent = Inches(0.3)
            run = p_c.add_run(f"({c.key}) {c.text}")
            set_font_style(run, size=10)
        
        doc.add_paragraph().paragraph_format.space_after = Pt(2)

    # 5. 換頁：解答
    doc.add_page_break()
    ans_title = doc.add_paragraph()
    ans_title.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
    ans_run = ans_title.add_run("參考答案與解析")
    set_font_style(ans_run, size=14, bold=True)
    
    for i, q in enumerate(exam_result.questions, 1):
        p_exp = doc.add_paragraph()
        exp_run = p_exp.add_run(f"【{i}】 答案：{q.answer}\n")
        set_font_style(exp_run, size=10, bold=True)
        detail_run = p_exp.add_run(f"解析：{q.explanation}")
        set_font_style(detail_run, size=9)
        
    file_stream = io.BytesIO()
    doc.save(file_stream)
    return file_stream.getvalue()
