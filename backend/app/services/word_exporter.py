import io
from docx import Document
from docx.shared import Pt, Inches, RGBColor
from docx.enum.text import WD_PARAGRAPH_ALIGNMENT
from docx.enum.section import WD_SECTION, WD_ORIENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

from app.models.question import ExamResult

def set_font_style(run, size=12, bold=False, font_name='新細明體'):
    """設置中文字體與英文字體的 Helper"""
    run.font.size = Pt(size)
    run.bold = bold
    # 設定西文字體
    run.font.name = 'Times New Roman'
    # 設定中文字體 (東亞字體)
    r = run._element
    rPr = r.get_or_add_rPr()
    rFonts = OxmlElement('w:rFonts')
    rFonts.set(qn('w:ascii'), 'Times New Roman')
    rFonts.set(qn('w:eastAsia'), font_name)
    rPr.append(rFonts)

def add_header_table(doc, subject):
    """加入標準考卷表頭：科目、班級、座號、姓名、分數格"""
    table = doc.add_table(rows=2, cols=4)
    table.style = 'Table Grid'
    
    # 合併第一列前三格作為大標題
    a = table.cell(0, 0)
    b = table.cell(0, 2)
    title_cell = a.merge(b)
    p = title_cell.paragraphs[0]
    p.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
    run = p.add_run(f"【AI 智慧模擬考】{subject} 試題卷")
    set_font_style(run, size=16, bold=True)
    
    # 第一列最後一格作為得分欄
    score_cell = table.cell(0, 3)
    p_score = score_cell.paragraphs[0]
    p_score.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
    run_score = p_score.add_run("得分")
    set_font_style(run_score, size=12)
    
    # 第二列格位：班級座號姓名
    cells = [table.cell(1, 0), table.cell(1, 1), table.cell(1, 2)]
    texts = ["班級：", "座號：", "姓名："]
    for cell, text in zip(cells, texts):
        p = cell.paragraphs[0]
        run = p.add_run(text)
        set_font_style(run, size=11)
        
    # 分數空格
    score_val_cell = table.cell(1, 3)
    
    # 設置欄寬
    table.columns[0].width = Inches(1.5)
    table.columns[1].width = Inches(1.0)
    table.columns[2].width = Inches(2.0)
    table.columns[3].width = Inches(1.0)

def export_to_docx(exam_result: ExamResult) -> bytes:
    doc = Document()
    
    # ── 頁面設定 (窄邊距) ──────────────────────────────────
    section = doc.sections[0]
    section.top_margin = Inches(0.5)
    section.bottom_margin = Inches(0.5)
    section.left_margin = Inches(0.5)
    section.right_margin = Inches(0.5)

    # ── 表頭 ──────────────────────────────────────────
    add_header_table(doc, exam_result.subject)
    
    p_info = doc.add_paragraph()
    p_info.alignment = WD_PARAGRAPH_ALIGNMENT.LEFT
    info_run = p_info.add_run(f"範圍：{'、'.join(exam_result.units)} | 題數：{exam_result.total_questions} 題 | 每題 {round(100/exam_result.total_questions, 1)} 分")
    set_font_style(info_run, size=10)
    
    doc.add_paragraph() # 空行

    # ── 設置雙欄排版 ─────────────────────────────────────
    # 在表頭之後，將後續內容設為雙欄
    section = doc.sections[0]
    sectPr = section._element.get_or_add_sectPr()
    cols = OxmlElement('w:cols')
    cols.set(qn('w:num'), '2') # 雙欄
    cols.set(qn('w:sep'), '1') # 顯示中間分隔線
    cols.set(qn('w:space'), '425') # 欄間距
    sectPr.append(cols)
    
    # ── 題目區 ──────────────────────────────────────────
    for i, q in enumerate(exam_result.questions, 1):
        # 題目段落
        p_q = doc.add_paragraph()
        p_q.paragraph_format.space_after = Pt(2)
        run_id = p_q.add_run(f"(  ) {i}. ")
        set_font_style(run_id, size=12, bold=True)
        run_text = p_q.add_run(q.question)
        set_font_style(run_text, size=12)
        
        # 選項排版
        max_choice_len = max(len(str(c.text)) for c in q.choices)
        
        if max_choice_len < 10:
            # 極短選項：一行四個
            p_c = doc.add_paragraph()
            p_c.paragraph_format.left_indent = Inches(0.3)
            p_c.paragraph_format.space_after = Pt(2)
            for c in q.choices:
                run = p_c.add_run(f"({c.key}) {c.text}    ")
                set_font_style(run, size=11)
        elif max_choice_len < 25:
            # 中等選項：一行兩個
            p_c1 = doc.add_paragraph()
            p_c1.paragraph_format.left_indent = Inches(0.3)
            p_c1.paragraph_format.space_after = Pt(0)
            run1 = p_c1.add_run(f"(A) {q.choices[0].text:<20} (B) {q.choices[1].text}")
            set_font_style(run1, size=11)
            
            p_c2 = doc.add_paragraph()
            p_c2.paragraph_format.left_indent = Inches(0.3)
            p_c2.paragraph_format.space_after = Pt(2)
            run2 = p_c2.add_run(f"(C) {q.choices[2].text:<20} (D) {q.choices[3].text}")
            set_font_style(run2, size=11)
        else:
            # 長選項：一題一行
            for c in q.choices:
                p_c = doc.add_paragraph()
                p_c.paragraph_format.left_indent = Inches(0.3)
                p_c.paragraph_format.space_after = Pt(0)
                run = p_c.add_run(f"({c.key}) {c.text}")
                set_font_style(run, size=11)
        
        doc.add_paragraph().paragraph_format.space_after = Pt(4)

    # ── 換頁：解答卷 ──────────────────────────────────────
    doc.add_page_break()
    
    ans_title = doc.add_paragraph()
    ans_title.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
    ans_run = ans_title.add_run("解答與解析")
    set_font_style(ans_run, size=16, bold=True)
    
    # 快速答案表
    p_quick = doc.add_paragraph()
    p_quick.alignment = WD_PARAGRAPH_ALIGNMENT.LEFT
    for i, q in enumerate(exam_result.questions, 1):
        run = p_quick.add_run(f"{i}.({q.answer})  ")
        set_font_style(run, size=11)
        if i % 10 == 0: p_quick.add_run("\n")
        
    doc.add_paragraph()

    # 詳細解析
    for i, q in enumerate(exam_result.questions, 1):
        p_exp = doc.add_paragraph()
        exp_run = p_exp.add_run(f"【{i}】 答案：{q.answer}\n")
        set_font_style(exp_run, size=11, bold=True)
        detail_run = p_exp.add_run(f"解析：{q.explanation}")
        set_font_style(detail_run, size=10)
        
    # ── 匯出 Bytes ────────────────────────────────────────
    file_stream = io.BytesIO()
    doc.save(file_stream)
    return file_stream.getvalue()
