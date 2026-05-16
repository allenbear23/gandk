from fastapi import APIRouter, HTTPException
import logging
from typing import List, Optional
from app.db.supabase_client import get_supabase
from app.services.ai_generator import _call_gemini_sync

router = APIRouter(prefix="/admin/subjects", tags=["Admin - 科目管理"])
logger = logging.getLogger(__name__)

@router.get("/", summary="取得所有科目")
async def get_subjects():
    sb = get_supabase()
    res = sb.table("subjects").select("*").order("name").execute()
    return {"subjects": res.data}

@router.get("/{subject_id}/units", summary="取得科目的所有單元")
async def get_units(subject_id: str):
    sb = get_supabase()
    res = sb.table("units").select("*").eq("subject_id", subject_id).order("unit_code").execute()
    return {"units": res.data}

@router.post("/{subject_id}/analyze-style")
async def analyze_subject_style(subject_id: str, sample_text: str):
    """
    分析考古題文本並產出風格提示詞。
    """
    sb = get_supabase()
    analysis_prompt = f"""請分析以下考古題內容，產出一份「風格指令 (Style Prompt)」。
分析重點：標題格式、個人資訊欄位、命題語氣、配分方式。
產出格式：
【排版規範】...
【命題人設】...
【配分參考】...

範本：
{sample_text[:3000]}
"""
    try:
        style_prompt = _call_gemini_sync("你是一位專業教育文件分析師。", analysis_prompt)
        sb.table("subjects").update({"style_prompt": style_prompt}).eq("id", subject_id).execute()
        return {"status": "success", "style_prompt": style_prompt}
    except Exception as e:
        logger.error(f"分析失敗: {e}")
        raise HTTPException(status_code=500, detail=str(e))
