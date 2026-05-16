"""
api/v1/student/exam.py — 考卷生成 API

流程：
POST /api/v1/student/exam/generate
  1. 接收前端請求（科目、單元、題數、模式）
  2. RAG 檢索（取得課本與考古題段落）
  3. 組裝 System Prompt
  4. 呼叫 Gemini 1.5 Flash 生成 JSON
  5. 根據模式回傳：
     - mode=quiz: 直接回傳 JSON
     - mode=print: 交給 word_exporter 生成 docx 並回傳檔案下載
"""
from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
import logging
import json
from datetime import datetime, timezone

from app.models.question import ExamGenerateRequest, ExamResult, GenerationMode
from app.db.supabase_client import get_supabase, get_subject_name
from app.services.rag_engine import retrieve_context
from app.utils.prompt_builder import build_exam_prompt
from app.services.ai_generator import generate_questions

router = APIRouter(prefix="/student/exam", tags=["Student - 考卷生成"])
logger = logging.getLogger(__name__)


@router.post("/generate", summary="生成考卷")
async def generate_exam(req: ExamGenerateRequest):
    """
    核心：AI 考卷生成端點。
    """
    try:
        # 1. 取得科目名稱
        subject_name = await get_subject_name(req.subject_id)

        # 2. RAG 檢索
        # 動態調整檢索數量：題數越多，需要的文本越多
        top_k = min(req.question_count // 2 + 5, 20)
        
        context = await retrieve_context(
            subject_id=req.subject_id,
            unit_codes=req.unit_codes,
            subject_name=subject_name,
            top_k=top_k,
        )

        if not context["has_textbook"]:
            logger.warning(f"⚠️ 警告：找不到 {req.subject_id} {req.unit_codes} 的課本資料")
            # 視需求，若無課本也可以嘗試生成，但有幻覺風險

        # 3. 組裝 Prompt
        system_prompt, user_prompt = build_exam_prompt(
            subject_name=subject_name,
            unit_codes=req.unit_codes,
            question_count=req.question_count,
            textbook_chunks=context["textbook_chunks"],
            past_exam_chunks=context["past_exam_chunks"],
            difficulty=req.difficulty or 3,
        )

        # 4. 呼叫 Gemini AI
        logger.info(f"🚀 開始 AI 生成（目標 {req.question_count} 題）...")
        questions = await generate_questions(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            target_count=req.question_count,
            unit_codes=req.unit_codes,
        )

        # 5. 建立結果物件
        exam_result = ExamResult(
            subject=subject_name,
            subject_id=req.subject_id,
            units=req.unit_codes,
            total_questions=len(questions),
            questions=questions,
            generated_at=datetime.now(timezone.utc)
        )

        # 6. 非同步寫入紀錄 (fire-and-forget，不阻塞回應)
        # TODO: 可以加入 FastAPI BackgroundTasks 寫入 generation_logs
        import asyncio
        asyncio.create_task(_log_generation(req, exam_result))

        # 7. 依照模式處理回應
        if req.mode == GenerationMode.PRINT:
            # 模式 A：匯出 Word
            from app.services.word_exporter import export_to_docx
            docx_bytes = export_to_docx(exam_result)
            
            filename = f"模擬考卷_{subject_name}_{'_'.join(req.unit_codes)}.docx"
            return Response(
                content=docx_bytes,
                media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                headers={
                    "Content-Disposition": f'attachment; filename="{filename.encode("utf8").decode("latin1")}"'
                }
            )
        else:
            # 模式 B：直接回傳 JSON (刷題模式)
            return exam_result

    except Exception as e:
        logger.error(f"❌ 考卷生成失敗: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"考卷生成失敗: {str(e)}")


async def _log_generation(req: ExamGenerateRequest, result: ExamResult):
    """將生成結果寫入資料庫供分析"""
    try:
        sb = get_supabase()
        sb.table("generation_logs").insert({
            "subject_id": req.subject_id,
            "unit_codes": req.unit_codes,
            "mode": req.mode.value,
            "question_count": result.total_questions,
            "questions_json": [q.model_dump() for q in result.questions],
        }).execute()
        logger.info("✅ 生成紀錄已儲存")
    except Exception as e:
        logger.warning(f"⚠️ 生成紀錄儲存失敗: {e}")
