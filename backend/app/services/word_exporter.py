import io
import logging
from app.models.question import ExamResult

logger = logging.getLogger(__name__)

def export_to_docx(exam_result: ExamResult) -> bytes:
    """隔離版匯出器：將引用移至內部，防止啟動時崩潰"""
    try:
        # 在函式內部引用，避免全域載入失敗
        from docx import Document
        
        doc = Document()
        doc.add_heading(f"考試科目：{exam_result.subject}", 0)
        
        doc.add_paragraph(f"範圍：{'、'.join(exam_result.units)}")
        doc.add_paragraph(f"總題數：{exam_result.total_questions}")
        
        for i, q in enumerate(exam_result.questions, 1):
            q_text = getattr(q, 'question', '題目內容缺失')
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
        logger.error(f"❌ Word 匯出器核心崩潰: {e}")
        # 如果 python-docx 真的跑不起來，回傳一個友善的錯誤訊息
        raise ImportError(f"伺服器 Word 組件故障 (lxml 衝突)，請聯繫管理員修復。錯誤細節: {str(e)}")
