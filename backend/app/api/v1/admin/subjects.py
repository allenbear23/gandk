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

@router.post("/{subject_id}/analyze-style-from-doc/{document_id}")
async def analyze_style_from_doc(subject_id: str, document_id: str):
    """
    從指定的文件 ID 提取風格指令。
    """
    sb = get_supabase()
    
    # 1. 抓取該文件的內容片段
    chunks_res = sb.table("document_chunks").select("chunk_text").eq("document_id", document_id).limit(10).execute()
    if not chunks_res.data:
        raise HTTPException(status_code=404, detail="找不到文件內容，請確認文件已解析完成。")
    
    sample_text = "\n".join([c["chunk_text"] for c in chunks_res.data])
    
    # 2. 讓 AI 分析
    analysis_prompt = f"""請根據以下考古題內容，產出一份極簡、專業的「命題與排版風格指令 (Style Prompt)」。
這段指令將會作為未來 AI 出題時的最高指導原則。

請分析：
1. 標題與表頭欄位（如：班級、座號、姓名、得分格）的排列。
2. 命題語氣與題目長度。
3. 選項的排列風格。
4. 配分資訊。

請產出約 300 字內的繁體中文指令。格式範例：
【排版規範】表頭包含年份、班級、姓名。中間需有垂直分隔線...
【命題人設】嚴謹、學術風...
【配分參考】每題 2 分，共 50 題...

考古題樣本：
{sample_text}
"""
    try:
        style_prompt = _call_gemini_sync("你是一位專業教育文件排版專家。", analysis_prompt)
        # 更新資料庫
        sb.table("subjects").update({"style_prompt": style_prompt}).eq("id", subject_id).execute()
        return {"status": "success", "style_prompt": style_prompt}
    except Exception as e:
        logger.error(f"分析失敗: {e}")
        raise HTTPException(status_code=500, detail=str(e))
