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

@router.get("", summary="取得所有科目")
async def get_subjects():
    try:
        sb = get_supabase()
        res = sb.table("subjects").select("*").order("name").execute()
        return {"subjects": res.data if res.data else []}
    except Exception as e:
        logger.error(f"取得科目失敗: {e}")
        return {"subjects": [], "error": str(e)}

@router.post("", summary="建立新科目")
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
    # 移除 .limit(10) 並以 chunk_index 排序，以讀取並還原完整的考古題內容
    chunks_res = sb.table("document_chunks").select("chunk_text").eq("document_id", document_id).order("chunk_index").execute()
    if not chunks_res.data:
        raise HTTPException(status_code=404, detail="找不到文件內容")
    
    sample_text = "\n".join([c["chunk_text"] for c in chunks_res.data])
    
    analyzer_system = """你是一位極度嚴謹且專業的台灣高中命題結構與風格分析師。
你的任務是「精確、無死角地分析考古題的題型與格式結構」，並為該科目建立一套「黃金命題標準指令」。

【極重要核心原則】：
生成的考卷必須與分析的考古題在「格式、題數、題型、配分以及結構上百分之百完全一致」。考古題並非只是參考，而是必須被「一模一樣地克隆」的黃金藍圖！

請根據所提供的完整考古題內文，分析並輸出包含以下結構的 JSON 格式指令（以 Markdown JSON 代碼塊 ```json ... ``` 包裹）：
{
  "style_name": "風格名稱",
  "document_header": "這張考卷的完整頁首文字與結構格式範例（例如：包含測驗名稱、範圍、座號、班級、姓名等欄位的格式，請保留原始排版文字）",
  "total_sections_count": "總大題數",
  "total_questions_count": "整張試卷的總題數，這必須是絕對精確的數字！",
  "sections": [
    {
      "section_id": 1,
      "section_name": "大題名稱（例如：第一部分：字彙能力測驗）",
      "question_count": "本大題包含的精確題數（此大題在生成時必須剛好只有這麼多題！）",
      "question_type": "本大題的精確題型（例如：四選一單選題 (A)(B)(C)(D)、填空題、問答題等）",
      "scoring_rule": "本大題的配分規則（例如：佔比 20%，每題 4 分）",
      "formatting_style": "本大題中每一題的呈現格式規範（例如：題目文字最後要加 '(Handwritten answer: [選項])' 等，必須包含與考古題完全一致的微小格式特徵）",
      "content_rules": "本大題的語意與命題細節規範（例如：考驗哪些特定字彙、文法、文體或長度）"
    }
  ],
  "formatting_rules": {
    "option_style": "選擇題選項的格式（例如使用 (A) (B) (C) (D)）",
    "answer_simulation_pattern": "是否有模擬作答格式（如 '(Handwritten answer: [選項])' 或 '(Handwritten: [單字])'）"
  }
}
"""

    analysis_prompt = f"""請詳讀以下完整的考古題內文，精確分析其每一大題的結構、題型、各題格式、配分及題數。
分析完畢後，請**嚴格按照規定的 JSON 格式**輸出風格指令。

【考古題內文】：
{sample_text}
"""

    try:
        style_prompt = _call_gemini_sync(analyzer_system, analysis_prompt)
        sb.table("subjects").update({"style_prompt": style_prompt}).eq("id", subject_id).execute()
        return {"status": "success", "style_prompt": style_prompt}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
