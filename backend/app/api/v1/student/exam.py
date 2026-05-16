from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
import logging
import traceback
from datetime import datetime, timezone

from app.models.question import ExamGenerateRequest, ExamResult, GenerationMode
from app.db.supabase_client import get_supabase, get_subject_name, get_subject_style
from app.utils.prompt_builder import build_exam_prompt
from app.services.ai_generator import generate_questions

# 注意：我暫時移除了 rag_engine 的引用，排除環境衝突
router = APIRouter(prefix="/student/exam", tags=["Student - 考卷生成"])
logger = logging.getLogger(__name__)

@router.post("/generate", summary="生成考卷")
async def generate_exam(req: ExamGenerateRequest):
    try:
        subject_name = await get_subject_name(req.subject_id)
        style_prompt = await get_subject_style(req.subject_id)
        
        # 1. 測試期：跳過 RAG，直接出題
        context = {"textbook_chunks": [], "past_exam_chunks": []}

        # 2. 組裝 Prompt
        system_prompt, user_prompt = build_exam_prompt(
            subject_name=subject_name,
            unit_codes=req.unit_codes,
            question_count=req.question_count,
            textbook_chunks=[],
            past_exam_chunks=[],
            difficulty=req.difficulty or 3,
            style_prompt=style_prompt
        )

        # 3. 呼叫 AI (使用你清單中的穩定型號)
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

        # 5. 回應模式 (測試期：一律回傳 JSON 以排查 Word 崩潰)
        if req.mode == GenerationMode.PRINT:
             return {
                "message": "隔離測試中：暫時僅回傳數據",
                "exam": exam_result
            }
        else:
            return exam_result

    except Exception as e:
        error_detail = traceback.format_exc()
        raise HTTPException(status_code=500, detail=f"深度崩潰訊息：\n{error_detail}")
