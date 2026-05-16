import io
import logging
from docx import Document
from app.models.question import ExamResult

logger = logging.getLogger(__name__)

def export_to_docx(exam_result: ExamResult) -> bytes:
    """穩定版匯出器：確保在所有環境下都能生成基本的 Word 檔"""
    try:
        doc = Document()
        doc.add_heading(f"考試科目：{exam_result.subject}", 0)
        
        doc.add_paragraph(f"範圍：{'、'.join(exam_result.units)}")
        doc.add_paragraph(f"總題數：{exam_result.total_questions}")
        
        for i, q in enumerate(exam_result.questions, 1):
            # 增加安全檢查，防止題目物件屬性缺失
            q_text = getattr(q, 'question', '（題目載入失敗）')
            doc.add_paragraph(f"{i}. {q_text}")
            
            choices = getattr(q, 'choices', [])
            for c in choices:
                doc.add_paragraph(f"({getattr(c, 'key', '?')}) {getattr(c, 'text', '')}")
            doc.add_paragraph("-" * 20)

        doc.add_page_break()
        doc.add_heading("參考答案與解析", 1)
        for i, q in enumerate(exam_result.questions, 1):
            doc.add_paragraph(f"{i}. 答案：{getattr(q, 'answer', 'N/A')}")
            doc.add_paragraph(f"解析：{getattr(q, 'explanation', '無')}")
            
        file_stream = io.BytesIO()
        doc.save(file_stream)
        return file_stream.getvalue()
    except Exception as e:
        logger.error(f"Word 匯出失敗: {e}")
        # 如果 docx 噴錯，至少回傳一個空的 Bytes 避免崩潰
        raise ValueError(f"Word 生成失敗，請聯繫管理員。詳細原因: {str(e)}")
