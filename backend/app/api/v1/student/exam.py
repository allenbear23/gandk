from fastapi import APIRouter
import logging
import traceback
from datetime import datetime, timezone

from app.models.question import ExamGenerateRequest
from app.db.supabase_client import get_subject_name, get_subject_style
from app.utils.prompt_builder import build_exam_prompt
from app.services.ai_generator import _call_gemini_sync

router = APIRouter(prefix="/student/exam", tags=["Student - 考卷生成"])
logger = logging.getLogger(__name__)

@router.post("/generate", summary="生成考卷")
async def generate_exam(req: ExamGenerateRequest):
    # 強制回傳 200，手動封裝錯誤
    try:
        subject_name = await get_subject_name(req.subject_id)
        style_prompt = await get_subject_style(req.subject_id)
        
        # 1. 最簡 Prompt
        system_prompt, user_prompt = build_exam_prompt(
            subject_name=subject_name,
            unit_codes=req.unit_codes,
            question_count=req.question_count,
            textbook_chunks=[],
            past_exam_chunks=[],
            difficulty=req.difficulty or 3,
            style_prompt=style_prompt
        )

        # 2. 改用同步呼叫 (排除 Async 變數)
        raw_res = _call_gemini_sync(system_prompt, user_prompt)
        
        return {
            "status": "success",
            "subject": subject_name,
            "raw_ai_output": raw_res
        }

    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "traceback": traceback.format_exc()
        }
