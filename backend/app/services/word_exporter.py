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
    """加強版的動態表頭生成，具備完善的防錯機制"""
    title = metadata.get("title") or f"【AI 智慧模擬考】{default_subject} 試題卷"
    fields = metadata.get("header_fields")
    if not fields or not isinstance(fields, list) or len(fields) == 0:
        fields = ["班級", "座號", "姓名"]
    
    # 建立表格：1列大標題 + 1列資訊欄
    # 欄數 = 資訊欄位數量 + 1 (得分欄)
    cols_count = len(fields) + 1
    table = doc.add_table(rows=2, cols=cols_count)
    table.style = 'Table Grid'
    
    # 處理大標題 (合併前 N-1 格)
    try:
        main_cell = table.cell(0, 0)
        if cols_count > 1:
            end_cell = table.cell(0, cols_count - 2)
            main_cell = main_cell.merge(end_cell)
        
        p = main_cell.paragraphs[0]
        p.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
        run = p.add_run(title)
        set_font_style(run, size=14, bold=True)
        
        # 處理得分欄 (最後一格)
        score_cell = table.cell(0, cols_count - 1)
        ps = score_cell.paragraphs[0]
        ps.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
        run_s = ps.add_run("得分")
        set_font_style(run_s, size=11)
        
        # 處理資訊欄位
        for i, field in enumerate(fields):
            cell = table.cell(1, i)
            p_f = cell.paragraphs[0]
            run_f = p_f.add_run(f"{field}：")
            set_font_style(run_f, size=10)
    except Exception as e:
        print(f"表頭生成發生細微錯誤: {e}")
        
    return table

def export_to_docx(exam_result: ExamResult) -> bytes:
    doc = Document()
    metadata = getattr(exam_result, 'metadata', {})
    if metadata is None: metadata = {}
    
    section = doc.sections[0]
    section.top_margin = Inches(0.4)
    section.bottom_margin = Inches(0.4)
    section.left_margin = Inches(0.4)
    section.right_margin = Inches(0.4)

    # 1. 動態表頭
    add_dynamic_header_table(doc, metadata, exam_result.subject)
    
    # 2. 計分說明
    p_score_info = doc.add_paragraph()
    score_text = metadata.get("score_info") or f"總題數：{exam_result.total_questions} 題"
    run_info = p_score_info.add_run(f"範圍：{'、'.join(exam_result.units)} | {score_text}")
    set_font_style(run_info, size=9)
    
    doc.add_paragraph()

    # 3. 雙欄設定 (包裹在 try 中，防止 XML 錯誤)
    try:
        sectPr = section._element.get_or_add_sectPr()
        cols = OxmlElement('w:cols')
        cols.set(qn('w:num'), '2')
        cols.set(qn('w:sep'), '1')
        cols.set(qn('w:space'), '425')
        sectPr.append(cols)
    except:
        pass
    
    # 4. 題目區
    for i, q in enumerate(exam_result.questions, 1):
        try:
            p_q = doc.add_paragraph()
            run_id = p_q.add_run(f"(  ) {i}. ")
            set_font_style(run_id, size=11, bold=True)
            run_text = p_q.add_run(q.question)
            set_font_style(run_text, size=11)
            
            for c in q.choices:
                p_c = doc.add_paragraph()
                p_c.paragraph_format.left_indent = Inches(0.3)
                run = p_c.add_run(f"({c.key}) {c.text}")
                set_font_style(run, size=10)
            
            doc.add_paragraph().paragraph_format.space_after = Pt(2)
        except:
            continue

    # 5. 解答
    doc.add_page_break()
    ans_title = doc.add_paragraph()
    ans_title.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
    ans_run = ans_title.add_run("參考答案與解析")
    set_font_style(ans_run, size=14, bold=True)
    
    for i, q in enumerate(exam_result.questions, 1):
        try:
            p_exp = doc.add_paragraph()
            exp_run = p_exp.add_run(f"【{i}】 答案：{q.answer}\n")
            set_font_style(exp_run, size=10, bold=True)
            detail_run = p_exp.add_run(f"解析：{q.explanation}")
            set_font_style(detail_run, size=9)
        except:
            continue
        
    file_stream = io.BytesIO()
    doc.save(file_stream)
    return file_stream.getvalue()
