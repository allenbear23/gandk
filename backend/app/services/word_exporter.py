import logging
from app.models.question import ExamResult

logger = logging.getLogger(__name__)

def export_to_docx(exam_result: ExamResult) -> bytes:
    """診斷期：回傳純文字 JSON 模擬檔案"""
    output = f"題目：{exam_result.subject}\n"
    for i, q in enumerate(exam_result.questions, 1):
        output += f"{i}. {getattr(q, 'question', '')}\n"
    return output.encode("utf-8")
