from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
import logging
import traceback
from datetime import datetime, timezone

from app.models.question import ExamGenerateRequest, ExamResult, GenerationMode
from app.db.supabase_client import get_supabase, get_subject_name, get_subject_style
from app.services.rag_engine import retrieve_context
from app.utils.prompt_builder import build_exam_prompt
from app.services.ai_generator import generate_questions

router = APIRouter(prefix="/student/exam", tags=["Student - 考卷生成"])
logger = logging.getLogger(__name__)

@router.post("/generate", summary="生成考卷")
async def generate_exam(req: ExamGenerateRequest):
    try:
        subject_name = await get_subject_name(req.subject_id)
        style_prompt = await get_subject_style(req.subject_id)
        
        # 1. RAG 檢索 (正式恢復)
        logger.info(f"🔍 檢索教材中: {subject_name}")
        context = await retrieve_context(
            subject_id=req.subject_id,
            unit_codes=req.unit_codes,
            subject_name=subject_name,
            top_k=8,
        )

        # 2. 組裝 Prompt
        system_prompt, user_prompt = build_exam_prompt(
            subject_name=subject_name,
            unit_codes=req.unit_codes,
            question_count=req.question_count,
            textbook_chunks=context["textbook_chunks"],
            past_exam_chunks=context["past_exam_chunks"],
            difficulty=req.difficulty or 3,
            style_prompt=style_prompt
        )

        # 3. 呼叫 Gemini AI
        res_data = await generate_questions(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            target_count=req.question_count,
            unit_codes=req.unit_codes,
        )
        
        questions = res_data.get("questions", [])
        if not questions and isinstance(res_data, list):
            questions = res_data

        if not questions:
            raise ValueError("AI 沒有產生題目，請檢查 API Key 或教材內容。")

        # 4. 建立結果
        exam_result = ExamResult(
            subject=subject_name,
            subject_id=req.subject_id,
            units=req.unit_codes,
            total_questions=len(questions),
            questions=questions,
            generated_at=datetime.now(timezone.utc)
        )

        # 5. 回應模式 (正式恢復 Word 匯出)
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
        logger.error(f"❌ 錯誤: {error_detail}")
        raise HTTPException(status_code=500, detail=f"生成失敗：\n{error_detail}")
