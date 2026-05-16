from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
import logging
import json
from datetime import datetime, timezone
from typing import List, Optional

from app.models.question import ExamGenerateRequest, ExamResult, GenerationMode
from app.db.supabase_client import get_supabase, get_subject_name
from app.services.rag_engine import retrieve_context
from app.utils.prompt_builder import build_exam_prompt
from app.services.ai_generator import generate_questions

router = APIRouter(prefix="/student/exam", tags=["Student - 考卷生成"])
logger = logging.getLogger(__name__)

@router.post("/generate", summary="生成考卷")
async def generate_exam(req: ExamGenerateRequest):
    try:
        subject_name = await get_subject_name(req.subject_id)
        
        # 1. RAG 檢索（含表頭片段）
        top_k = min(req.question_count // 2 + 5, 20)
        context = await retrieve_context(
            subject_id=req.subject_id,
            unit_codes=req.unit_codes,
            subject_name=subject_name,
            top_k=top_k,
        )

        # 2. 組裝 Prompt（傳入 head_chunks）
        system_prompt, user_prompt = build_exam_prompt(
            subject_name=subject_name,
            unit_codes=req.unit_codes,
            question_count=req.question_count,
            textbook_chunks=context["textbook_chunks"],
            past_exam_chunks=context["past_exam_chunks"],
            head_chunks=context.get("head_chunks"),
            difficulty=req.difficulty or 3,
        )

        # 3. 呼叫 Gemini AI
        logger.info(f"🚀 開始動態模仿生成（目標 {req.question_count} 題）...")
        res_data = await generate_questions(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            target_count=req.question_count,
            unit_codes=req.unit_codes,
        )
        
        questions = res_data["questions"]
        metadata = res_data["metadata"]

        # 4. 建立結果物件
        exam_result = ExamResult(
            subject=subject_name,
            subject_id=req.subject_id,
            units=req.unit_codes,
            total_questions=len(questions),
            questions=questions,
            generated_at=datetime.now(timezone.utc)
        )
        # 額外掛載動態 metadata
        exam_result.metadata = metadata

        # 5. 回應模式
        if req.mode == GenerationMode.PRINT:
            from app.services.word_exporter import export_to_docx
            docx_bytes = export_to_docx(exam_result)
            
            # 使用 AI 模仿的標題作為檔名
            file_title = metadata.get("title", f"模擬考卷_{subject_name}")
            filename = f"{file_title}.docx"
            
            return Response(
                content=docx_bytes,
                media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                headers={
                    "Content-Disposition": f'attachment; filename="{filename.encode("utf8").decode("latin1")}"'
                }
            )
        else:
            return exam_result

    except Exception as e:
        logger.error(f"❌ 考卷生成失敗: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"考卷生成失敗: {str(e)}")
