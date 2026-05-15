"""
main.py — FastAPI 應用程式入口（Vercel + Supabase 版）

本地啟動: uvicorn app.main:app --reload --port 8000
Vercel 部署: 由 api/index.py 引用此 app
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from app.config import get_settings
from app.db.supabase_client import get_supabase
from app.api.v1.admin.subjects import router as subjects_router
from app.api.v1.admin.uploads import router as uploads_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 AI 考卷生成系統啟動中...")
    settings = get_settings()

    if settings.supabase_url:
        try:
            get_supabase()
            logger.info("✅ Supabase 連線就緒")
        except Exception as e:
            logger.warning(f"⚠️  Supabase 初始化失敗（開發模式可忽略）: {e}")
    else:
        logger.warning("⚠️  未設定 SUPABASE_URL，跳過 Supabase 初始化")

    logger.info("✅ 啟動完成")
    yield
    logger.info("👋 應用程式關閉")


settings = get_settings()

app = FastAPI(
    title="AI 智慧模擬考卷生成系統 API",
    description="""
## 功能說明
- 📁 **後台管理**：科目/單元管理、PDF 上傳與自動解析（Supabase Storage + pgvector）
- 📝 **考卷生成**：RAG + Gemini 生成結構化題目
- 📱 **雙模式輸出**：JSON 刷題模式 / Word 下載列印模式
    """,
    version="1.0.0",
    lifespan=lifespan,
)

cors_origins = get_settings().cors_origins_list
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if "*" in cors_origins else cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

API_PREFIX = "/api/v1"
app.include_router(subjects_router, prefix=API_PREFIX)
app.include_router(uploads_router, prefix=API_PREFIX)

from app.api.v1.student.exam import router as exam_router
app.include_router(exam_router, prefix=API_PREFIX)


@app.get("/health", tags=["系統"])
async def health_check():
    return {"status": "ok", "version": "1.0.0", "env": settings.app_env}


@app.get("/", tags=["系統"])
async def root():
    return {"message": "AI 考卷生成系統 API", "docs": "/docs"}
