import io
from docx import Document
from docx.shared import Pt, Inches
from docx.enum.text import WD_PARAGRAPH_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

from app.models.question import ExamResult

def set_font(run, size=12, bold=False):
    """設置標準考卷字體：中文新細明體，英文 Times New Roman"""
    run.font.size = Pt(size)
    run.bold = bold
    run.font.name = 'Times New Roman'
    r = run._element
    rPr = r.get_or_add_rPr()
    rFonts = OxmlElement('w:rFonts')
    rFonts.set(qn('w:ascii'), 'Times New Roman')
    rFonts.set(qn('w:eastAsia'), '新細明體')
    rPr.append(rFonts)

def add_standard_header(doc, subject_name):
    """加入台灣標準考卷表頭表格"""
    # 建立 2x4 的表格
    table = doc.add_table(rows=2, cols=4)
    table.style = 'Table Grid'
    
    # 第一列：標題
    cell_title = table.cell(0, 0).merge(table.cell(0, 2))
    p_title = cell_title.paragraphs[0]
    p_title.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
    run_title = p_title.add_run(f"【AI 智慧模擬考】{subject_name} 試題卷")
    set_font(run_title, size=16, bold=True)
    
    # 第一列最後一格：得分
    cell_score = table.cell(0, 3)
    p_s = cell_score.paragraphs[0]
    p_s.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
    set_font(p_s.add_run("得分"), size=12)
    
    # 第二列：基本資訊
    labels = ["班級：", "座號：", "姓名："]
    for i in range(3):
        p = table.cell(1, i).paragraphs[0]
        set_font(p.add_run(labels[i]), size=11)

def export_to_docx(exam_result: ExamResult) -> bytes:
    doc = Document()
    
    # ── 頁面設定 (窄邊距) ──────────────────────────────────
    section = doc.sections[0]
    section.top_margin = Inches(0.5)
    section.bottom_margin = Inches(0.5)
    section.left_margin = Inches(0.5)
    section.right_margin = Inches(0.5)

    # 1. 插入標準表頭
    add_standard_header(doc, exam_result.subject)
    
    # 2. 考卷資訊
    p_info = doc.add_paragraph()
    info_text = f"範圍：{'、'.join(exam_result.units)}  |  總題數：{exam_result.total_questions} 題"
    set_font(p_info.add_run(info_text), size=10)
    
    doc.add_paragraph() # 空行

    # 3. 開啟雙欄排版 (XML 注入)
    sectPr = section._element.get_or_add_sectPr()
    cols = OxmlElement('w:cols')
    cols.set(qn('w:num'), '2')
    cols.set(qn('w:sep'), '1') # 顯示中間分隔線
    cols.set(qn('w:space'), '425')
    sectPr.append(cols)
    
    # 4. 題目內容
    for i, q in enumerate(exam_result.questions, 1):
        # 題目
        p_q = doc.add_paragraph()
        run_q = p_q.add_run(f"(  ) {i}. {q.question}")
        set_font(run_q, size=11)
        
        # 選項
        for c in q.choices:
            p_c = doc.add_paragraph()
            p_c.paragraph_format.left_indent = Inches(0.3)
            run_c = p_c.add_run(f"({c.key}) {c.text}")
            set_font(run_c, size=10)
        
        # 題與題之間的小間隔
        doc.add_paragraph().paragraph_format.space_after = Pt(2)

    # 5. 強制分頁：解答卷
    doc.add_page_break()
    p_ans = doc.add_paragraph()
    p_ans.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
    set_font(p_ans.add_run("解答與解析"), size=16, bold=True)
    
    for i, q in enumerate(exam_result.questions, 1):
        p_e = doc.add_paragraph()
        set_font(p_e.add_run(f"【{i}】答案：{q.answer}\n"), size=10, bold=True)
        set_font(p_e.add_run(f"解析：{q.explanation}"), size=9)
        
    file_stream = io.BytesIO()
    doc.save(file_stream)
    return file_stream.getvalue()
