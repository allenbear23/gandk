from fastapi import APIRouter, HTTPException
import logging
from typing import List, Optional
from pydantic import BaseModel
from app.db.supabase_client import get_supabase
from app.services.ai_generator import _call_gemini_sync, list_available_models

router = APIRouter(prefix="/admin/subjects", tags=["Admin - 科目管理"])
logger = logging.getLogger(__name__)

@router.get("/debug-models", summary="診斷：列出可用模型")
async def debug_models():
    return await list_available_models()

# 定義請求模型
class SubjectCreate(BaseModel):
    name: str
    description: Optional[str] = ""

class UnitCreate(BaseModel):
    name: str
    unit_code: str
    description: Optional[str] = ""

@router.get("/", summary="取得所有科目")
async def get_subjects():
    try:
        sb = get_supabase()
        res = sb.table("subjects").select("*").order("name").execute()
        return {"subjects": res.data if res.data else []}
    except Exception as e:
        logger.error(f"取得科目失敗: {e}")
        return {"subjects": [], "error": str(e)}

@router.post("/", summary="建立新科目")
async def create_subject(data: SubjectCreate):
    try:
        sb = get_supabase()
        res = sb.table("subjects").insert(data.model_dump()).execute()
        return res.data[0]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"建立科目失敗: {str(e)}")

@router.delete("/{subject_id}", summary="刪除科目")
async def delete_subject(subject_id: str):
    try:
        sb = get_supabase()
        sb.table("subjects").delete().eq("id", subject_id).execute()
        return {"message": "科目已刪除"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"刪除失敗: {str(e)}")

@router.get("/{subject_id}/units", summary="取得單元")
async def get_units(subject_id: str):
    try:
        sb = get_supabase()
        res = sb.table("units").select("*").eq("subject_id", subject_id).order("unit_code").execute()
        return {"units": res.data if res.data else []}
    except Exception as e:
        return {"units": [], "error": str(e)}

@router.post("/{subject_id}/units", summary="建立新單元")
async def create_unit(subject_id: str, data: UnitCreate):
    try:
        sb = get_supabase()
        payload = data.model_dump()
        payload["subject_id"] = subject_id
        res = sb.table("units").insert(payload).execute()
        return res.data[0]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"建立單元失敗: {str(e)}")

@router.post("/{subject_id}/analyze-style-from-doc/{document_id}")
async def analyze_style_from_doc(subject_id: str, document_id: str):
    sb = get_supabase()
    chunks_res = sb.table("document_chunks").select("chunk_text").eq("document_id", document_id).limit(10).execute()
    if not chunks_res.data:
        raise HTTPException(status_code=404, detail="找不到文件內容")
    
    sample_text = "\n".join([c["chunk_text"] for c in chunks_res.data])
    analysis_prompt = f"請分析考古題產出『風格指令』。範本：\n{sample_text}"
    try:
        style_prompt = _call_gemini_sync("你是一位專業教育文件分析師。", analysis_prompt)
        sb.table("subjects").update({"style_prompt": style_prompt}).eq("id", subject_id).execute()
        return {"status": "success", "style_prompt": style_prompt}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
