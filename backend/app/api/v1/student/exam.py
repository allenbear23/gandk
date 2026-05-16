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
        
        # 1. RAG 檢索（含表頭與考古題範例）
        top_k = 15 # 預設檢索量
        context = await retrieve_context(
            subject_id=req.subject_id,
            unit_codes=req.unit_codes,
            subject_name=subject_name,
            top_k=top_k,
        )

        # 2. 自動偵測題數 (如果模式是 PRINT 且題數為 0 或未指定)
        target_count = req.question_count
        if req.mode == GenerationMode.PRINT and (not target_count or target_count <= 0):
            logger.info("🔍 模式為 PRINT 且未指定題數，正在從考古題範例分析題數...")
            # 這裡我們透過一個簡單的啟發式方法，或是在 Prompt 中讓 AI 自己決定
            # 目前我們先設定一個預設值，並在 Prompt 中告訴 AI「盡量模仿範例題數」
            target_count = 50 # 台灣考卷常見題數
        
        # 3. 組裝 Prompt
        system_prompt, user_prompt = build_exam_prompt(
            subject_name=subject_name,
            unit_codes=req.unit_codes,
            question_count=target_count,
            textbook_chunks=context["textbook_chunks"],
            past_exam_chunks=context["past_exam_chunks"],
            head_chunks=context.get("head_chunks"),
            difficulty=req.difficulty or 3,
        )
        
        # 在 Prompt 後面額外加一句：如果範例中有明確題數，請優先參考範例題數
        user_prompt += "\n【重要】如果考古題範例中有顯示總題數，請忽略我要求的數量，直接按照範例的數量出題。"

        # 4. 呼叫 Gemini AI
        logger.info(f"🚀 開始動態模仿生成（模式: {req.mode}）...")
        res_data = await generate_questions(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            target_count=target_count,
            unit_codes=req.unit_codes,
        )
        
        questions = res_data["questions"]
        metadata = res_data["metadata"]

        # 5. 建立結果物件
        exam_result = ExamResult(
            subject=subject_name,
            subject_id=req.subject_id,
            units=req.unit_codes,
            total_questions=len(questions),
            questions=questions,
            generated_at=datetime.now(timezone.utc)
        )
        exam_result.metadata = metadata

        # 6. 回應模式
        if req.mode == GenerationMode.PRINT:
            from app.services.word_exporter import export_to_docx
            docx_bytes = export_to_docx(exam_result)
            
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
        import traceback
        logger.error(f"❌ 考卷生成崩潰！詳細錯誤: \n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"考卷生成失敗: {str(e)}")
