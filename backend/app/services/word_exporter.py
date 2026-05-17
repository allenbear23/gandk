import logging
import json
import re
from app.models.question import ExamResult

logger = logging.getLogger(__name__)

def export_to_docx(exam_result: ExamResult) -> bytes:
    """
    極速版匯出器 (HTML-to-Doc 模式)：
    支援自定義頁首與大題分段排版，完美克隆考古題格式！
    """
    from app.db.supabase_client import get_supabase
    
    # 嘗試獲取科目的風格設定
    style_json = None
    try:
        sb = get_supabase()
        res = sb.table("subjects").select("style_prompt").eq("id", exam_result.subject_id).single().execute()
        style_prompt = res.data.get("style_prompt") if res.data else None
        
        if style_prompt:
            # 嘗試解析為 JSON 結構
            # 由於 Gemini 可能會回傳含 ```json ... ``` 的字串，先進行清理
            cleaned = style_prompt.strip()
            if cleaned.startswith("```"):
                cleaned = re.sub(r'^```(?:json)?\s*\n?', '', cleaned, flags=re.IGNORECASE)
                cleaned = re.sub(r'\n?```\s*$', '', cleaned)
            
            style_json = json.loads(cleaned)
    except Exception as e:
        logger.warning(f"⚠️ 無法讀取或解析風格設定，將使用預設格式: {e}")

    # 建立頁首
    header_html = ""
    if style_json and "document_header" in style_json:
        # 使用考古題頁首
        header_text = style_json["document_header"]
        header_html = f"""
        <div class="header-custom">
            {header_text.replace('\n', '<br>')}
        </div>
        """
    else:
        # 預設頁首
        header_html = f"""
        <div class="header-default">
            <h1>模擬考卷：{exam_result.subject}</h1>
            <p class="meta">範圍：{"、".join(exam_result.units)} | 總題數：{exam_result.total_questions} | 命題單位：教育部考試評量檢定處</p>
            <div class="student-info">
                班級：___________ &nbsp;&nbsp;&nbsp;&nbsp; 座號：_________ &nbsp;&nbsp;&nbsp;&nbsp; 姓名：_______________
            </div>
        </div>
        """

    html_template = f"""
    <html xmlns:o='urn:schemas-microsoft-com:office:office' xmlns:w='urn:schemas-microsoft-com:office:word' xmlns='http://www.w3.org/TR/REC-html40'>
    <head>
        <meta charset="utf-8">
        <title>{exam_result.subject}</title>
        <style>
            body {{
                font-family: 'PMingLiU', '新細明體', 'Times New Roman', serif;
                line-height: 1.8;
                font-size: 11pt;
                color: #000000;
            }}
            .header-custom {{
                text-align: center;
                font-family: 'DFKai-SB', '標楷體', sans-serif;
                font-size: 15pt;
                font-weight: bold;
                line-height: 1.5;
                margin-bottom: 30px;
                padding-bottom: 10px;
                border-bottom: 3px double #000;
            }}
            .header-default {{
                text-align: center;
                margin-bottom: 30px;
                padding-bottom: 15px;
                border-bottom: 3px double #000000;
            }}
            .header-default h1 {{
                font-family: 'DFKai-SB', '標楷體', sans-serif;
                font-size: 18pt;
                margin: 0 0 10px 0;
            }}
            .header-default .meta {{
                font-size: 10pt;
                margin: 5px 0;
            }}
            .header-default .student-info {{
                font-size: 11pt;
                margin-top: 15px;
                font-family: 'PMingLiU', '新細明體', serif;
            }}
            .section-header {{
                font-family: 'DFKai-SB', '標楷體', sans-serif;
                font-size: 12pt;
                font-weight: bold;
                margin-top: 25px;
                margin-bottom: 15px;
                text-decoration: underline;
            }}
            .question {{
                margin-bottom: 8px;
                font-weight: normal;
                text-align: justify;
                text-justify: inter-ideograph;
            }}
            .choices {{
                margin-left: 24px;
                margin-bottom: 15px;
            }}
            .choices-item {{
                display: inline-block;
                margin-right: 25px;
            }}
            .footer {{
                margin-top: 50px;
                border-top: 2px solid #000000;
                padding-top: 20px;
                page-break-before: always;
            }}
            .footer h2 {{
                font-family: 'DFKai-SB', '標楷體', sans-serif;
                text-align: center;
                font-size: 14pt;
                margin-bottom: 25px;
            }}
            .explanation-block {{
                margin-bottom: 15px;
                font-size: 10pt;
                line-height: 1.5;
            }}
        </style>
    </head>
    <body>
        {header_html}
    """

    # 題目與大題分段編排
    current_section = None
    for i, q in enumerate(exam_result.questions, 1):
        # 檢測大題分段
        if q.section and q.section != current_section:
            current_section = q.section
            html_template += f'<div class="section-header">{current_section}</div>'
        
        # 題目文字
        html_template += f'<div class="question">{i}. {q.question}</div>'
        
        # 選項並列排版
        html_template += '<div class="choices">'
        for c in q.choices:
            html_template += f'<span class="choices-item">({c.key}) {c.text}</span>'
        html_template += '</div>'

    # 答案與解析部分（強制分頁）
    html_template += """
    <div class="footer">
        <h2>【教育部考試評量檢定處 ‧ 參考答案與標準解析】</h2>
    """
    
    # 答案卷大題分段
    current_ans_section = None
    for i, q in enumerate(exam_result.questions, 1):
        if q.section and q.section != current_ans_section:
            current_ans_section = q.section
            html_template += f'<div class="section-header" style="margin-top:15px; font-size:11pt;">{current_ans_section}</div>'
            
        html_template += f"""
        <div class="explanation-block">
            <b>第 {i} 題 參考答案：【{q.answer}】</b><br>
            <span style="color:#333333;">{q.explanation}</span>
        </div>
        """
    
    html_template += """
        </div>
    </body>
    </html>
    """
    
    # 直接將 HTML 字串轉為 bytes 回傳
    return html_template.encode("utf-8")
