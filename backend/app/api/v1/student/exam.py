from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
import logging
import traceback
from datetime import datetime, timezone

from app.models.question import ExamGenerateRequest, ExamResult, GenerationMode
from app.db.supabase_client import get_supabase, get_subject_name, get_subject_style
from app.utils.prompt_builder import build_exam_prompt
from app.services.ai_generator import generate_questions

# 保持 rag_engine 隔離，直到 Word 確認成功
router = APIRouter(prefix="/student/exam", tags=["Student - 考卷生成"])
logger = logging.getLogger(__name__)

@router.post("/generate", summary="生成考卷")
async def generate_exam(req: ExamGenerateRequest):
    try:
        subject_name = await get_subject_name(req.subject_id)
        style_prompt = await get_subject_style(req.subject_id)
        
        # 1. 隔離測試：暫時不檢索，確保穩定
        context = {"textbook_chunks": [], "past_exam_chunks": []}

        # 嘗試解析自定義風格 JSON 以進行分大題生成 (100% 複製考古題大題與題數)
        style_json = None
        if style_prompt:
            import json
            import re
            try:
                cleaned = style_prompt.strip()
                if cleaned.startswith("```"):
                    cleaned = re.sub(r'^```(?:json)?\s*\n?', '', cleaned, flags=re.IGNORECASE)
                    cleaned = re.sub(r'\n?```\s*$', '', cleaned)
                style_json = json.loads(cleaned)
            except Exception as e:
                logger.warning(f"⚠️ 解析風格設定失敗，將使用一般命題: {e}")

        # 3. 呼叫 AI 生成試題
        if style_json and "sections" in style_json:
            from app.services.ai_generator import generate_exam_by_sections
            res_data = await generate_exam_by_sections(
                subject_name=subject_name,
                unit_codes=req.unit_codes,
                style_json=style_json,
                difficulty=req.difficulty or 3,
                textbook_chunks=[],
                past_exam_chunks=[]
            )
        else:
            # 2. 組裝 Prompt (一般命題保底)
            system_prompt, user_prompt = build_exam_prompt(
                subject_name=subject_name,
                unit_codes=req.unit_codes,
                question_count=req.question_count,
                textbook_chunks=[],
                past_exam_chunks=[],
                difficulty=req.difficulty or 3,
                style_prompt=style_prompt
            )
            res_data = await generate_questions(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                target_count=req.question_count,
                unit_codes=req.unit_codes,
            )
        
        questions = res_data.get("questions", [])
        if not questions and isinstance(res_data, list):
            questions = res_data

        # 4. 建立結果
        exam_result = ExamResult(
            subject=subject_name,
            subject_id=req.subject_id,
            units=req.unit_codes,
            total_questions=len(questions),
            questions=questions,
            generated_at=datetime.now(timezone.utc)
        )

        # 5. 回應模式 (使用極度穩定的原生二進位制 DOCX 格式)
        if req.mode == GenerationMode.PRINT:
            from app.services.word_exporter import export_to_docx
            docx_bytes = export_to_docx(exam_result)
            return Response(
                content=docx_bytes,
                media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                headers={
                    "Content-Disposition": "attachment; filename=exam_results.docx"
                }
            )
        else:
            return exam_result

    except Exception as e:
        error_detail = traceback.format_exc()
        raise HTTPException(status_code=500, detail=f"解封 Word 失敗：\n{error_detail}")
