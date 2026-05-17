import logging
import json
import re
import io
from docx import Document
from docx.shared import Pt, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn

from app.models.question import ExamResult

logger = logging.getLogger(__name__)

def set_run_font(run, font_name="新細明體", size_pt=11, bold=False, italic=False, underline=False, color_rgb=None):
    """
    專業級字型控制器：支援 ASCII 與 中日韓東亞字型 (eastAsia) 完美渲染，解決 macOS 下標楷體/新細明體顯示問題。
    """
    run.font.name = font_name
    
    # 強制注入東亞字型 XML 設定
    rPr = run._r.get_or_add_rPr()
    rFonts = OxmlElement('w:rFonts')
    rFonts.set(qn('w:ascii'), font_name)
    rFonts.set(qn('w:hAnsi'), font_name)
    rFonts.set(qn('w:eastAsia'), font_name)
    rPr.append(rFonts)
    
    run.font.size = Pt(size_pt)
    run.bold = bold
    run.italic = italic
    run.underline = underline
    if color_rgb:
        run.font.color.rgb = color_rgb

def add_paragraph_bottom_double_border(paragraph):
    """
    利用 XML 注入段落底部的雙線底線 (中華民國國家考試經典風格)
    """
    pPr = paragraph._p.get_or_add_pPr()
    pBdr = parse_xml(f'<w:pBdr {nsdecls("w")}><w:bottom w:val="double" w:sz="12" w:space="8" w:color="000000"/></w:pBdr>')
    pPr.append(pBdr)

def export_to_docx(exam_result: ExamResult) -> bytes:
    """
    使用 python-docx 產生 100% 原生二進位制 .docx 文件，徹底告別相容性導致的空白問題！
    """
    from app.db.supabase_client import get_supabase
    
    # 建立原生 Word 文件
    doc = Document()
    
    # 設定版面邊距 (四周皆為 1 英吋，公務規格)
    for section in doc.sections:
        section.top_margin = Inches(1.0)
        section.bottom_margin = Inches(1.0)
        section.left_margin = Inches(1.0)
        section.right_margin = Inches(1.0)

    # 嘗試獲取科目的風格設定
    style_json = None
    try:
        sb = get_supabase()
        res = sb.table("subjects").select("style_prompt").eq("id", exam_result.subject_id).single().execute()
        style_prompt = res.data.get("style_prompt") if res.data else None
        
        if style_prompt:
            cleaned = style_prompt.strip()
            if cleaned.startswith("```"):
                cleaned = re.sub(r'^```(?:json)?\s*\n?', '', cleaned, flags=re.IGNORECASE)
                cleaned = re.sub(r'\n?```\s*$', '', cleaned)
            style_json = json.loads(cleaned)
    except Exception as e:
        logger.warning(f"⚠️ 無法讀取或解析風格設定，將使用預設格式: {e}")

    # 1. 建立考卷頁首 (Header)
    if style_json and "document_header" in style_json:
        # 使用考古題風格之自定義頁首
        header_text = style_json["document_header"]
        lines = header_text.strip().split('\n')
        
        # 首行加粗放大
        p_title = doc.add_paragraph()
        p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p_title.add_run(lines[0])
        set_run_font(run, font_name="標楷體", size_pt=15, bold=True)
        
        # 其餘頁首行
        for line in lines[1:]:
            p_line = doc.add_paragraph()
            p_line.alignment = WD_ALIGN_PARAGRAPH.CENTER
            # 增加空段落微調
            run = p_line.add_run(line)
            set_run_font(run, font_name="新細明體", size_pt=10.5)
            
        # 在頁首段落底部加上雙底線
        add_paragraph_bottom_double_border(p_line)
        
    else:
        # 國家級考試預設雙層頁首
        p_title = doc.add_paragraph()
        p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p_title.add_run(f"模擬考卷：{exam_result.subject}")
        set_run_font(run, font_name="標楷體", size_pt=18, bold=True)
        
        p_meta = doc.add_paragraph()
        p_meta.alignment = WD_ALIGN_PARAGRAPH.CENTER
        units_str = "、".join(exam_result.units)
        run_meta = p_meta.add_run(f"範圍：{units_str}  |  總題數：{exam_result.total_questions} 題  |  命題單位：教育部考試評量檢定處")
        set_run_font(run_meta, font_name="新細明體", size_pt=9.5)
        
        p_info = doc.add_paragraph()
        p_info.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run_info = p_info.add_run("班級：___________     座號：_________     姓名：_______________")
        set_run_font(run_info, font_name="新細明體", size_pt=11)
        
        # 段落底部雙底線
        add_paragraph_bottom_double_border(p_info)

    # 加一個空行分隔
    doc.add_paragraph()

    # 2. 依序產生試卷大題與試題
    current_section = None
    for i, q in enumerate(exam_result.questions, 1):
        # 偵測並插入大題標題
        if q.section and q.section != current_section:
            current_section = q.section
            p_sec = doc.add_paragraph()
            p_sec.paragraph_format.space_before = Pt(12)
            p_sec.paragraph_format.space_after = Pt(6)
            run_sec = p_sec.add_run(current_section)
            set_run_font(run_sec, font_name="標楷體", size_pt=12, bold=True, underline=True)
            
        # 題目文字 (新細明體 11pt)
        p_q = doc.add_paragraph()
        p_q.paragraph_format.space_after = Pt(4)
        run_q = p_q.add_run(f"{i}. {q.question}")
        set_run_font(run_q, font_name="新細明體", size_pt=11)
        
        # 選擇題選項橫向並列排版
        if q.choices:
            p_choices = doc.add_paragraph()
            p_choices.paragraph_format.left_indent = Inches(0.35) # 縮排 0.35 英吋
            p_choices.paragraph_format.space_after = Pt(10)
            
            choices_text = "   ".join([f"({c.key}) {c.text}" for c in q.choices])
            run_choices = p_choices.add_run(choices_text)
            set_run_font(run_choices, font_name="新細明體", size_pt=10.5)

    # 3. 實體分頁：參考答案與標準解析頁面
    doc.add_page_break()
    
    p_ans_title = doc.add_paragraph()
    p_ans_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_ans_title.paragraph_format.space_before = Pt(20)
    p_ans_title.paragraph_format.space_after = Pt(20)
    run_ans_title = p_ans_title.add_run("【教育部考試評量檢定處 ‧ 參考答案與標準解析】")
    set_run_font(run_ans_title, font_name="標楷體", size_pt=14, bold=True)
    
    # 答案卷大題標示
    current_ans_section = None
    for i, q in enumerate(exam_result.questions, 1):
        if q.section and q.section != current_ans_section:
            current_ans_section = q.section
            p_ans_sec = doc.add_paragraph()
            p_ans_sec.paragraph_format.space_before = Pt(10)
            run_ans_sec = p_ans_sec.add_run(current_ans_section)
            set_run_font(run_ans_sec, font_name="標楷體", size_pt=11, bold=True)
            
        p_ans_item = doc.add_paragraph()
        p_ans_item.paragraph_format.space_after = Pt(6)
        
        # 標楷體答案
        run_key = p_ans_item.add_run(f"第 {i} 題  參考答案：【")
        set_run_font(run_key, font_name="新細明體", size_pt=10.5)
        
        run_ans = p_ans_item.add_run(q.answer)
        set_run_font(run_ans, font_name="標楷體", size_pt=11, bold=True)
        
        run_end = p_ans_item.add_run("】")
        set_run_font(run_end, font_name="新細明體", size_pt=10.5)
        
        # 智慧解析說明文字
        p_exp = doc.add_paragraph()
        p_exp.paragraph_format.left_indent = Inches(0.2)
        p_exp.paragraph_format.space_after = Pt(12)
        run_exp = p_exp.add_run(q.explanation)
        set_run_font(run_exp, font_name="新細明體", size_pt=10, color_rgb=RGBColor(0x33, 0x33, 0x33))

    # 輸出為二進位制 bytes
    file_stream = io.BytesIO()
    doc.save(file_stream)
    file_stream.seek(0)
    return file_stream.getvalue()
