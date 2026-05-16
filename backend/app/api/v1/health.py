from fastapi import APIRouter
import os
from app.db.supabase_client import get_supabase

router = APIRouter(prefix="/health", tags=["Health Check"])

@router.get("/")
async def health_check():
    # 檢查 Gemini
    api_key = os.getenv("GEMINI_API_KEY", "MISSING")
    
    # 檢查 Supabase
    supabase_status = "Unknown"
    try:
        sb = get_supabase()
        # 測試抓取一個科目
        res = sb.table("subjects").select("count", count="exact").limit(1).execute()
        supabase_status = f"Connected (Count: {res.count})"
    except Exception as e:
        supabase_status = f"Supabase Error: {str(e)}"

    return {
        "gemini_status": "OK" if api_key != "MISSING" else "MISSING",
        "supabase_status": supabase_status,
        "environment": os.getenv("VERCEL_ENV", "local"),
        "python_version": os.getenv("PYTHON_VERSION", "unknown")
    }
