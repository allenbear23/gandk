from fastapi import APIRouter
import os
import google.generativeai as genai

router = APIRouter(prefix="/health", tags=["Health Check"])

@router.get("/")
async def health_check():
    api_key = os.getenv("GEMINI_API_KEY", "MISSING")
    api_key_masked = f"{api_key[:5]}***{api_key[-5:]}" if len(api_key) > 10 else "INVALID"
    
    status = "OK"
    try:
        genai.configure(api_key=api_key)
        # 簡單測試模型是否可用
        model = genai.GenerativeModel("gemini-flash-latest")
        status = "Gemini Connected"
    except Exception as e:
        status = f"Gemini Error: {str(e)}"

    return {
        "status": status,
        "api_key_status": "FOUND" if api_key != "MISSING" else "MISSING",
        "api_key_preview": api_key_masked,
        "environment": os.getenv("VERCEL_ENV", "local")
    }
