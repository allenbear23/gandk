from fastapi import APIRouter, HTTPException
import logging
from typing import List, Optional
from app.db.supabase_client import get_supabase
from app.services.ai_generator import _call_gemini_sync

router = APIRouter(prefix="/admin/subjects", tags=["Admin - 科目管理"])
logger = logging.getLogger(__name__)

@router.get("/", summary="取得所有科目")
async def get_subjects():
    try:
        sb = get_supabase()
        res = sb.table("subjects").select("*").order("name").execute()
        return {"subjects": res.data if res.data else []}
    except Exception as e:
        logger.error(f"取得科目失敗: {e}")
        return {"subjects": [], "error": str(e)}

@router.get("/{subject_id}/units", summary="取得科目的所有單元")
async def get_units(subject_id: str):
    try:
        sb = get_supabase()
        res = sb.table("units").select("*").eq("subject_id", subject_id).order("unit_code").execute()
        return {"units": res.data if res.data else []}
    except Exception as e:
        logger.error(f"取得單元失敗: {e}")
        return {"units": [], "error": str(e)}

@router.post("/{subject_id}/analyze-style-from-doc/{document_id}")
async def analyze_style_from_doc(subject_id: str, document_id: str):
    sb = get_supabase()
    # 抓取片段
    chunks_res = sb.table("document_chunks").select("chunk_text").eq("document_id", document_id).limit(10).execute()
    if not chunks_res.data:
        raise HTTPException(status_code=404, detail="找不到文件內容")
    
    sample_text = "\n".join([c["chunk_text"] for c in chunks_res.data])
    
    analysis_prompt = f"""請分析考古題產出『風格指令』。
分析點：標題格式、個人資訊欄、命題語氣、配分。
範本：
{sample_text}
"""
    try:
        style_prompt = _call_gemini_sync("你是一位專業教育文件分析師。", analysis_prompt)
        # 更新資料庫
        sb.table("subjects").update({"style_prompt": style_prompt}).eq("id", subject_id).execute()
        return {"status": "success", "style_prompt": style_prompt}
    except Exception as e:
        logger.error(f"分析失敗: {e}")
        raise HTTPException(status_code=500, detail=str(e))
