import logging
from app.models.question import ExamResult

logger = logging.getLogger(__name__)

def export_to_docx(exam_result: ExamResult) -> bytes:
    """
    極速版匯出器 (HTML-to-Doc 模式)：
    完全不依賴 python-docx，解決 Vercel 環境崩潰問題。
    """
    html_template = f"""
    <html xmlns:o='urn:schemas-microsoft-com:office:office' xmlns:w='urn:schemas-microsoft-com:office:word' xmlns='http://www.w3.org/TR/REC-html40'>
    <head>
        <meta charset="utf-8">
        <title>{exam_result.subject}</title>
        <style>
            body {{ font-family: 'Arial', sans-serif; line-height: 1.6; }}
            .header {{ text-align: center; border-bottom: 2px solid #333; margin-bottom: 20px; }}
            .question {{ margin-bottom: 15px; font-weight: bold; }}
            .choices {{ margin-left: 20px; margin-bottom: 10px; }}
            .footer {{ margin-top: 50px; border-top: 1px dashed #ccc; padding-top: 20px; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>模擬考卷：{exam_result.subject}</h1>
            <p>範圍：{"、".join(exam_result.units)} | 總題數：{exam_result.total_questions}</p>
        </div>
    """

    # 題目部分
    for i, q in enumerate(exam_result.questions, 1):
        html_template += f'<div class="question">{i}. {q.question}</div>'
        html_template += '<div class="choices">'
        for c in q.choices:
            html_template += f'<div>({c.key}) {c.text}</div>'
        html_template += '</div>'

    # 答案與解析
    html_template += '<div class="footer"><h2>參考答案與解析</h2>'
    for i, q in enumerate(exam_result.questions, 1):
        html_template += f'<p><b>{i}. 答案：{q.answer}</b><br>解析：{q.explanation}</p>'
    
    html_template += """
        </div>
    </body>
    </html>
    """
    
    # 直接將 HTML 字串轉為 bytes 回傳
    return html_template.encode("utf-8")
