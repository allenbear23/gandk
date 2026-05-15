"""
api/index.py — Vercel Serverless Python Entry Point

Vercel 會將所有 HTTP 請求導向這個檔案。
直接引用 FastAPI app 即可，Vercel Python runtime 會自動處理 ASGI。
"""
from app.main import app

# Vercel 的 Python runtime 需要一個名為 `app` 的 ASGI callable
# 或是 handler，這裡直接 re-export FastAPI app
