import io
from docx import Document
from app.models.question import ExamResult

def export_to_docx(exam_result: ExamResult) -> bytes:
    """極簡版匯出器：排除所有字體與 XML 注入干擾"""
    doc = Document()
    doc.add_heading(f"考試科目：{exam_result.subject}", 0)
    
    doc.add_paragraph(f"範圍：{'、'.join(exam_result.units)}")
    doc.add_paragraph(f"題數：{exam_result.total_questions}")
    
    for i, q in enumerate(exam_result.questions, 1):
        doc.add_paragraph(f"{i}. {q.question}")
        for c in q.choices:
            doc.add_paragraph(f"({c.key}) {c.text}")
        doc.add_paragraph("-" * 20)

    doc.add_page_break()
    doc.add_heading("答案", 1)
    for i, q in enumerate(exam_result.questions, 1):
        doc.add_paragraph(f"{i}. {q.answer} - {q.explanation}")
        
    file_stream = io.BytesIO()
    doc.save(file_stream)
    return file_stream.getvalue()
